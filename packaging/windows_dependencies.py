"""Windows package trimming; never change installed wheels or numerical code."""
from pathlib import Path, PurePosixPath
import re
import struct


EXCLUDED_PLUGINS = {'qpdf.dll', 'qtvirtualkeyboardplugin.dll'}
EXCLUDED_MODULES = [
    'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'PySide6.QtVirtualKeyboard',
    'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuickWidgets',
    'PySide6.QtQuickControls2', 'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
]
EXCLUDED_DLL_PREFIXES = ('qt6pdf', 'qt6virtualkeyboard', 'qt6qml', 'qt6quick', 'qt6opengl')


def system_runtime(name):
    name = PurePosixPath(name.replace('\\', '/')).name.lower()
    return name.endswith('.dll') and name.startswith((
        'msvcp', 'msvcr', 'vcruntime', 'concrt', 'vcomp', 'vcamp', 'ucrtbase', 'api-ms-win-',
    ))


def install_qt_plugin_filter():
    from PyInstaller.utils.hooks.qt import pyside6_library_info
    original = pyside6_library_info.collect_plugins

    def collect(plugin_type):
        return [(source, target) for source, target in original(plugin_type)
                if Path(source).name.lower() not in EXCLUDED_PLUGINS]

    pyside6_library_info.collect_plugins = collect


def normalize_runtime_imports(source, target):
    """Replace delvewheel's MSVC alias with the system DLL's ordinary name.

    The two affected NumPy extensions have no Authenticode signature. Only
    import-name storage and the PE checksum change; executable sections do not.
    """
    import pefile
    original = Path(source).read_bytes()
    pe = pefile.PE(data=original, fast_load=True)
    pe.parse_data_directories(directories=[1, 13])
    data = bytearray(original)
    replacements = []
    for entry in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', []) + getattr(pe, 'DIRECTORY_ENTRY_DELAY_IMPORT', []):
        match = re.fullmatch(rb'(msvcp140)-[0-9a-f]+\.dll', entry.dll, re.I)
        if not match:
            continue
        if pe.OPTIONAL_HEADER.DATA_DIRECTORY[4].Size:
            raise ValueError('Cannot normalize a signed extension: '+str(source))
        offset = pe.get_offset_from_rva(entry.struct.Name)
        name = match.group(1) + b'.dll'
        assert data[offset:offset+len(entry.dll)] == entry.dll
        data[offset:offset+len(entry.dll)] = name.ljust(len(entry.dll), b'\0')
        replacements.append((entry.dll.decode(), name.decode()))
    if not replacements:
        pe.close()
        return None, []
    revised = pefile.PE(data=bytes(data), fast_load=True)
    struct.pack_into('<I', data, pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'), revised.generate_checksum())
    for section in pe.sections:
        if section.Characteristics & 0x20000000:  # IMAGE_SCN_MEM_EXECUTE
            start, size = section.PointerToRawData, section.SizeOfRawData
            assert data[start:start+size] == original[start:start+size]
    pe.close(); revised.close()
    target = Path(target); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return str(target), replacements


def prepare_binaries(entries, stage):
    kept, omitted, imports = [], [], []
    for destination, source, kind in entries:
        name = PurePosixPath(destination.replace('\\', '/')).name.lower()
        if system_runtime(destination) or name in EXCLUDED_PLUGINS or name.startswith(EXCLUDED_DLL_PREFIXES):
            omitted.append(destination)
            continue
        if destination.replace('\\', '/').startswith('numpy/') and name.endswith('.pyd'):
            replacement, changes = normalize_runtime_imports(source, Path(stage)/'runtime-imports'/destination)
            if replacement:
                source = replacement
                imports.append(dict(path=destination, replacements=changes))
        kept.append((destination, source, kind))
    return kept, dict(mode='official system Microsoft v14 runtime; no bundled runtime/installer',
                      omitted=sorted(omitted), normalized_imports=imports)
