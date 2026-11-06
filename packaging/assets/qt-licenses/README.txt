Qt/PySide/Shiboken license and notice inventory for internal candidate 3609dfc7

Core Qt, PySide6, Essentials, Addons and Shiboken: 6.12.0.
Qt PDF DLL PE version: 6.140.0.0, supplied by PySide6_Pdf 6.12.0.140.
PySide6_WebEngine 6.12.0.140 is installed; no Qt6WebEngine DLL is bundled.
bundled-qt-components.json records all 52 bundled Qt/binding/plugin binary
paths, raw hashes, sizes, installed wheel RECORD ownership and metadata hashes.
The source inventory is not a claim that all installed wheels are bundled.
Classification: 13 Qt module DLLs, 22 Qt plugins, 8 binding binaries,
8 Microsoft runtime DLL copies (14.44.35211.0), 1 Mesa software OpenGL DLL.
There are also 99 Qt translation catalogs, all byte-matched to the installed
Essentials wheel RECORD inventory. Every file in the PySide6/shiboken6 bundle
directories is accounted for and pinned, not only DLL/PYD files.
Individual binary entries identify their exact notice assets and license options.
Wheel download URLs and SHA256 from the accepted build's pip report are retained.

Mapping of bundled Qt modules to upstream notice collections:
qtbase: Core, Gui, Network, OpenGL, Widgets; platform/style/TLS/network/
touch/icon image infrastructure, GIF/ICO/JPEG image handlers.
qtdeclarative: Qml, QmlMeta, QmlModels, QmlWorkerScript, Quick.
qtsvg: Svg, SVG icon engine and image handler.
qtimageformats: ICNS, TGA, TIFF, WBMP, WebP image plugins.
qtvirtualkeyboard: VirtualKeyboard and its input-context plugin.
qtpdf-6.140.0: Pdf and the PDF image handler, PDFium and its published
Abseil, Chromium, fast_float, FreeType, ICU, JPEG, PNG and zlib notices.
pyside-setup: PySide6 and Shiboken binding/runtime code.
qttranslations: Qt 6.12.0 translation catalogs, the upstream default module
licensing policy and its license texts. The archive retains all 96 matching
tracked TS source files and their raw hashes. Three 33-byte English QM files
have no matching tracked TS at this tag; their wheel/raw identities are retained
and no source counterpart is invented. The BSD build-system license is not
assumed to cover translation data; preserve the default LGPL/GPL alternatives.
Mesa-LLVM-NOTICES.txt: opengl32sw.dll identifies Mesa 11.2.2 and LLVM 3.6.2.
Its PE sections match Qt's official SHA256-authenticated signed prebuilt archive;
complete-file hashes differ. Both original raw identities are recorded, not
normalized or substituted. The original Mesa source archive license and LLVM
3.6.2 license are included along with Qt's published third-party notices.
Microsoft-VC-Runtime-2015-2022-License.txt and original DOCX: Microsoft runtime
terms; the official VS2022 redistribution page and provenance are retained.
These terms do not license Microsoft runtime code as Qt or establish the
distributor's Visual Studio entitlement. Confirm applicable rights before release.

The source headers retained in each upstream ZIP give the applicable options:
core Qt modules and binding runtime: LGPL-3.0-only OR GPL-2.0-only OR
GPL-3.0-only OR commercial (see each exact header).
IMPORTANT: Virtual Keyboard is GPL-3.0-only OR commercial, not LGPL.
Qt PDF's published 6.140.0 documentation states LGPLv3 OR GPLv2 OR commercial.
The generic license options do not replace third-party notices or change
component-specific terms. LicenseRef-Qt-Commercial.txt is a pointer/notice,
not a commercial license grant to this project.

*-upstream.zip contains unmodified authenticated upstream bytes; each member's
URL, raw SHA256, size and immutable commit where available are recorded in
upstream-provenance.json. *-NOTICES.txt provides a readable offline collection.
The complete module collections intentionally include optional/platform/test
third-party notices as a conservative superset. QtUsage fields identify these;
their inclusion does not claim that all optional upstream libraries are linked.

Qt source tags v6.12.0 were resolved to immutable official qt/qtproject GitHub
commits before download. PDF documentation reports 6.140.0, matching the DLL
version; its URLs redirect to the official 6.140 snapshot. Captured bytes are
pinned. No final v6.140.0 Git tag was available from the mirror during this
audit. These documentation captures establish notice provenance, not the exact
compiler/source revision of that wheel or a complete corresponding-source kit.
Original HTML notices and GFDL-1.3 documentation license are retained.

Redistribution review must address the actual GPL/LGPL obligations, including
corresponding source/build material and relinking/replacement requirements as
applicable. This notice collection does not itself supply corresponding source,
grant a commercial Qt license, or establish release compliance. Retain the
Virtual Keyboard finding for explicit release review; do not silently remove it
or represent the entire distribution as LGPL-only. No release is authorized.
