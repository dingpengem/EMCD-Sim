# Qt source, building and replacement (v0.9.0-beta.1)

EMCD-Sim remains MIT licensed. This distribution dynamically uses Qt 6.12.0,
PySide6 6.12.0 and Shiboken6 6.12.0 under their LGPL v3 alternatives, with
the applicable exceptions and third-party terms included alongside this file.
This does not relicense all dependencies as LGPL. See bundled-qt-components.json
for each retained binary and its notices; the full LGPL/GPL texts are included.
No commercial Qt coverage is claimed or needed for the chosen LGPL alternative.
Users may modify and replace these libraries, and reverse engineer the combined
work to debug modifications to them, as permitted by LGPL v3.

## Corresponding source supplied with this release

The accompanying **EMCD-Sim-v0.9.0-beta.1-Qt-sources.zip** is supplied beside
the local Windows candidate ZIP; this candidate has not been published. It contains the following unmodified official source archives,
this guide and the exact EMCD-Sim source snapshot (including packaging scripts).
The existing upstream-provenance.json records the official URLs, versions,
archive sizes and checksums checked against the publisher's SHA256 sidecars.

| Retained material | Matching source archive |
| --- | --- |
| Qt Core, Gui, Widgets, Network, platform/TLS/style plugins and their bundled third-party code | qtbase-everywhere-src-6.12.0.tar.xz |
| SVG library, image/icon plugins | qtsvg-everywhere-src-6.12.0.tar.xz |
| Additional image-format plugins and their bundled third-party code | qtimageformats-everywhere-src-6.12.0.tar.xz |
| Translation catalogs (including catalogs inherited from the installed wheel) | qttranslations-everywhere-src-6.12.0.tar.xz |
| PySide6 bindings and Shiboken runtime/generator | pyside-setup-everywhere-src-6.12.0.tar.xz |

The binaries come from the official upstream 6.12.0 Windows wheels identified in
the inventory. Qt reports a shared release build with MSVC 2022, x86-64; the
Python bindings use the limited ABI. These are matching upstream release sources,
not a claim that locally rebuilding them yields byte-identical vendor wheels.
The upstream source archives contain their CMake/setup scripts, license files,
third-party source and notices. No changes to Qt/PySide/Shiboken sources were made.
The exact EMCD-Sim source is also available at the release's Git tag.

Qt PDF and Virtual Keyboard are unused by the application. Their bindings,
qpdf.dll and qtvirtualkeyboardplugin.dll are explicitly excluded, together with
the QML/Quick/OpenGL DLL dependency chain they formerly pulled into the bundle.
Their old notices remain as a conservative historical superset; retaining a
notice does not mean its binary is shipped or change GPL terms into LGPL terms.
QtSvg remains needed by Matplotlib's Qt backend; QtNetwork supports retained
QtGui plugin dependencies. Software rendering opengl32sw.dll is retained.

## Build shared replacements

Use an x64 MSVC 2022 developer command prompt, CMake (at least 3.25), Ninja,
Python 3.11 x64 with development headers, and the LLVM/libclang prerequisite
specified by the supplied pyside-setup sources. Obtain tools under their own
licenses. Extract sources to short paths without spaces, for example C:\qsrc.
Use the release versions above together; do not mix incompatible Qt or binding
ABIs. Official build instructions:

- https://doc.qt.io/qt-6/windows-building.html
- https://doc.qt.io/qtforpython-6/building_from_source/index.html

A minimal shared release configuration for the retained modules is illustrated
below. This is a replacement build recipe, not the undisclosed vendor CI flags.
Run in a fresh build directory; substitute your extracted source paths.

```bat
mkdir C:\qbuild\base
cd /d C:\qbuild\base
C:\qsrc\qtbase-everywhere-src-6.12.0\configure.bat -release -shared -opensource -confirm-license -prefix C:\qinstall -nomake examples -nomake tests
cmake --build .
cmake --install .
cmake -S C:\qsrc\qtsvg-everywhere-src-6.12.0 -B C:\qbuild\svg -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=C:\qinstall -DCMAKE_INSTALL_PREFIX=C:\qinstall
cmake --build C:\qbuild\svg
cmake --install C:\qbuild\svg
cmake -S C:\qsrc\qtimageformats-everywhere-src-6.12.0 -B C:\qbuild\images -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=C:\qinstall -DCMAKE_INSTALL_PREFIX=C:\qinstall
cmake --build C:\qbuild\images
cmake --install C:\qbuild\images
cd /d C:\qsrc\pyside-setup-everywhere-src-6.12.0
python setup.py bdist_wheel --qtpaths=C:\qinstall\bin\qtpaths.exe --module-subset=Core,Gui,Widgets,Network,Svg --limited-api=yes --standalone
```

Install the build prerequisites listed in pyside-setup's requirements and follow
its libclang setup instructions before the last command. Its build produces the
Shiboken and PySide components together. The runtime Shiboken source is included;
the separately licensed generator is a build tool, not a bundled application
component. Build optional plugins/third-party features you wish to replace using
their supplied source configuration and licenses. A normal Qt build need not
rebuild the optional precompiled software OpenGL renderer. The renderer is
separate Mesa 11.2.2/LLVM 3.6.2 code under the permissive terms recorded in
Mesa-LLVM-NOTICES.txt and Mesa-LLVM-provenance.json; it is not included in qtbase's
source archive. Its upstream sources are available from archive.mesa3d.org and
the llvmorg-3.6.2 tag of llvm/llvm-project. Translation source
is supplied in qttranslations; rebuild catalogs with Qt Linguist's lrelease if
changing them. Empty English catalogs supplied by the wheel contain no text.

## Replace libraries in a private extracted copy

Close EMCD-Sim. Preserve an original copy of the extracted package. Put your
compatible Qt DLLs in `_internal/PySide6`, with plugins in matching `plugins`
subdirectories. Replace the PySide6 `.pyd` files and `pyside6.abi3.dll` together
when rebuilding bindings; replace `Shiboken.pyd` and `shiboken6.abi3.dll` under
`_internal/shiboken6` with the compatible Shiboken runtime. Keep required plugin
names/paths (especially platforms/qwindows.dll). Replace translations under
`_internal/PySide6/translations` if changed. Launch the EXE normally and check
preview, project load/save and a small calculation. No Qt signature/hash gate in
the application prevents library replacement. The distribution inventory checks
authenticate our shipped package; they do not restrict a user's private changes.
Alternatively rebuild the application using the included source and modified
libraries, following packaging/README.md and packaging/emcd_gui.spec. Scientific
input validation remains active regardless of library replacement.

## Microsoft runtime is an external prerequisite

This package includes neither Microsoft VC/UCRT/API-set runtime DLL copies nor
a Microsoft runtime installer. Redistribution entitlement for copies inherited
from dependency wheels was not established; public availability is not a grant
of redistribution rights. Users install the official **x64 Visual C++ v14
Redistributable**, version **14.44.35211 or newer**, directly from Microsoft:
https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
and https://aka.ms/vc14/vc_redist.x64.exe . Windows 10/11 supplies the UCRT/API sets.
Microsoft's separate redistribution conditions are documented at
https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files .

Two staged NumPy extensions originally imported a wheel-renamed MSVCP140 DLL.
Our packaging script changes only those import strings to `msvcp140.dll` and the
PE checksum, verifies executable sections are unchanged, and omits the renamed
DLL. Installed wheels are untouched. The installed system runtime then supplies
the standard dependency. No numerical implementation is changed. The package
build information records the two adjusted imports and all omitted runtime files.
