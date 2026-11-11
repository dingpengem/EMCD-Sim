# macOS dependency sources and replacement

EMCD-Sim itself is MIT licensed. Dependencies retain their own licenses; their
notices are under Contents/Resources/licenses in EMCD-Sim.app. Modification and
reverse engineering to debug modifications of LGPL libraries are permitted under
the applicable LGPL terms. No application hash gate prevents library replacement.

## Sources accompanying this release

The macOS release supplies a separate Corresponding-Source ZIP beside the app ZIP.
It includes the exact tagged EMCD-Sim source and packaging scripts, Qt 6.12.0
qtbase, qtsvg, qtimageformats and qttranslations archives, PySide/Shiboken 6.12.0
pyside-setup sources, ASE 3.29.0 sources, and GCC 13.4.0 sources plus the matching
Homebrew Darwin/Apple Silicon patch and build recipe. Source files are supplied,
not merely a promise to obtain them later. No Windows-only source coverage is
assumed. See LIBQUADMATH_PROVENANCE.md for the binary-to-source evidence.

Qt/PySide/Shiboken use their LGPL v3 alternatives for the retained runtime
modules. The unused PDF/Virtual Keyboard plugin roots are excluded, as are their
unused QML/Quick framework dependencies and console readline. Qt sources include
third-party notices for the retained native modules. ASE is LGPL-2.1-or-later.
libquadmath is distributed under LGPL 2.1 or later, consistent with the wheel's
notice; some source headers allow the earlier GNU Library GPL version 2 or later.
The full source preserves individual file terms. GCC runtime support carries the
GCC runtime exception where applicable; do not describe every GCC component as
LGPL. COPYING.LIB, COPYING3 and COPYING.RUNTIME are also in the GCC source archive.
NumPy, SciPy, Matplotlib, Pillow, spglib, Python and other dependencies have their
own bundled notices. System Apple libraries are not redistributed in this ZIP.

## Building or replacing libraries (for developers, not installation steps)

Work on a private copy and keep the original app. Use the supplied tagged source,
native ARM64 Python 3.11, the release dependencies.txt and packaging/build_macos.sh
to rebuild the application with compatible modified shared dependencies. This
source rebuild route supplies the application code needed to recombine it with
modified libraries. It does not require changing scientific reference data.

For Qt, build the supplied qtbase with a shared, release, open-source Cocoa build
using CMake and the macOS SDK; build qtsvg/qtimageformats against that prefix and
pyside-setup against the same Qt, with Core, Gui, Widgets, Network, DBus, Svg and
Test bindings. Follow https://doc.qt.io/qt-6/macos-building.html and
https://doc.qt.io/qtforpython-6/building_from_source/index.html. Match the Qt/Python
ABI and plugin architecture. Qt/PySide sources were not modified by EMCD-Sim.

For the retained GCC runtimes, extract gcc-13.4.0.tar.xz and apply gcc-13.4.0.diff
with patch -p1 at its root. The exact Homebrew gcc13-build-recipe.rb supplies the
configure/build/install options and prerequisite dependency names. It builds
shared ARM64 libraries. Do not use an unrelated current GCC formula/patch.

Compatible replacements in an extracted app live under Contents/Frameworks:
scipy/.dylibs for GCC runtimes; PySide6/Qt/lib and PySide6/Qt/plugins for Qt;
PySide6 and shiboken6 for bindings. Keep names, required exports and install-name
dependencies compatible. Finder aliases/symlinks must still resolve. Python-only
ASE changes can be used through the source rebuild route. A changed macOS bundle
needs valid local code signatures on changed Mach-O code and on the rebuilt app;
the packaging script performs local ad-hoc signing. There is no Developer ID or
notarization claim. Test launch, resource loading and a small calculation after
replacement. These developer instructions are separate from ordinary Finder
installation; they do not instruct users to disable macOS security.
