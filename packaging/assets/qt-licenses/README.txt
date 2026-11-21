Qt/PySide/Shiboken inventory for v0.9.0-beta.1 local development candidate

Retained Qt, PySide6 and Shiboken version: 6.12.0, using LGPL v3 alternatives
and the individual third-party license terms. EMCD-Sim remains MIT licensed.
See SOURCE_AND_REPLACEMENT.md for the accompanying source ZIP, build and dynamic
library replacement instructions. No commercial coverage is claimed.

The inventory accounts for 34 retained binaries: 5 Qt module DLLs (Core, Gui,
Widgets, Network, Svg), 20 plugins, 8 binding/runtime binaries and 1 Mesa renderer.
All 99 inherited translation catalogs remain inventoried. Installed-wheel
metadata also records Pdf/WebEngine distributions; those modules are NOT shipped.

Unused Qt PDF and Qt Virtual Keyboard bindings/plugins, and their QML/Quick/
OpenGL module dependency chain, are explicitly excluded by emcd_gui.spec and
windows_dependencies.py. qpdf.dll and qtvirtualkeyboardplugin.dll are not shipped.
No app-local Microsoft runtime DLLs or runtime installer are shipped. Install
the official Microsoft x64 v14 runtime directly as described in the guide.

Existing notice collections are deliberately preserved as a historical superset,
including PDF, VirtualKeyboard and Microsoft terms. Their presence neither means
those binaries are bundled nor changes their licenses. Do not interpret a GPL
notice as LGPL. bundled-qt-components.json identifies the actual retained files,
wheel ownership, hashes and per-file notice assets/license alternatives.
upstream-provenance.json records existing upstream notice provenance and the
matching official source archives supplied alongside this binary distribution.
Mesa/LLVM retain their separate permissive licenses and recorded provenance.
