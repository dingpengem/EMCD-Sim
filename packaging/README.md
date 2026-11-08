# Windows packaging and build

Current published package: [v0.8.1-beta.2](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.8.1-beta.2), Python package `0.8.1b2`, Windows version `0.8.1.2`. Use the current release-build instructions and [beta.2 dependency distribution](#beta2-dependency-distribution) below. The internal-candidate inventory in the next section is historical; it does not describe the dependencies shipped in beta.2.

## Historical packaging inventory — internal candidate 3609dfc7

Packaging correction for internal MDFF candidate 3609dfc7: required CIFs are
`_internal/examples/Fe_BCC_a2.8665.cif` and `Ni_FCC_a3.52.cif` beside their
provenance/redistribution README and MIT license. Qt licenses and component
notices are accessible at `_internal/licenses/qt/README.txt`; the eight readable
notice collections have byte-exact upstream ZIPs and per-member provenance.
These paths are relative to the extracted application folder, not a working
directory. Existing scientific data and registered XMCD bytes remain unchanged.

## Required packaging checks

`check_package_contents.py --environment` authenticates pinned inputs before
PyInstaller (also called by the spec). After collection, `--dist <app-folder>`
requires every asset and its raw hash, the manifest's independently pinned hash,
and the exact reviewed Qt/binding/plugin/translation inventory. Missing/changed assets
or new Qt components stop the build before ZIP creation. These pins are a review
boundary; do not regenerate them as part of building or use a different Qt wheel
without a new license/content review. Direct spec builds collect the same assets;
run the post-collection check before accepting their distribution.

## Historical dependency and acceptance notes

The audited DLLs are Qt 6.12.0 except Qt PDF 6.140.0 (wheel
PySide6_Pdf 6.12.0.140). Virtual Keyboard is GPLv3/commercial. The license
collection is not a complete corresponding-source offer or release approval;
see the component inventory's explicit redistribution limitations. Keep offline
isolation and the upstream HDF5 comparison UNVERIFIED until separately tested.

The Windows-only v0.8.1-beta.1 Research Beta uses version 0.8.1b1 and uses a separate build root and local-candidate label. The Adaptive Dirac–Padé JSON coefficients, provenance, Apache-2.0 LICENSE and NOTICE are collected from `emcd_sim/data/adaptive_dirac_pade_2026`. Neither h5py nor the upstream HDF5 archives are runtime requirements; the original unlicensed atomic table remains external. CIF support still uses the declared ASE imports and space-group data.

After building from a clean committed source, exercise the actual EXE on Windows:

```powershell
EMCD-Sim.exe --unified-elastic-acceptance C:/new-acceptance-output --unified-historical-project C:/existing-Ni-project
```

This opt-in mode requires a fresh output directory and a genuine checksummed historical Ni project. It runs real GUI workers, saves/reopens projects, imports Fe/CsCl/ZnO/monoclinic CIFs, validates rendered indices/clicks, checks the Ni-only MDFF gate and runs only two selected Ni energies for each of Single and Double Channeling, with magnetization reversal and saved-project checks. Automated file-dialog selections choose the supplied local paths. Saved historical arrays are opened read-only; a copy is saved under the new output directory. Run without a headless Qt override for native acceptance and inspect process exit, `acceptance.json`, screenshots and logs. This command only performs acceptance; publishing is a separate authorized step. See [local main acceptance](../docs/acceptance/unified-elastic-2026-11-03/MAIN_INTEGRATION_ACCEPTANCE.md).

## Current Windows release build

Current local development candidate (not published): **v0.9.0-beta.1 / 0.9.0b1**, convention
`forward_born_dagger_g_minus_h_v1`. Use a fresh Python 3.11 Windows build venv
without `--system-site-packages`. Install the same declared inputs as Actions:

```powershell
python -m venv build/windows-build-env
build/windows-build-env/Scripts/python.exe -m pip install -e ".[dev,gui]" -r packaging/requirements-windows.txt
build/windows-build-env/Scripts/python.exe packaging/check_windows_metadata.py
```

The spec collects licenses for 17 distributions. `six==1.17.0` is an explicit
build requirement even when no current transitive dependency installs it.
The preflight checks those distributions plus PyInstaller, lists every missing
metadata name with the installation command, and fails before invoking
PyInstaller. Direct spec builds use the same mandatory check and license list;
missing metadata is not ignored and license collection is not removed.
Scientific dependency pins, production numerical defaults and physics conventions are unchanged. Version metadata is updated separately from cleanup.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File packaging/build_windows.ps1 -Python ./build/windows-build-env/Scripts/python.exe -BuildRoot build/windows-v0.9.0-beta.1-release -CorrespondingSourceRoot C:/path/to/verified-qt-6.12.0-sources
```

Default archive: `EMCD-Sim-v0.9.0-beta.1-Windows.zip`. Windows numeric version:
0.9.0.1; ProductVersion: v0.9.0-beta.1. Use a new output root: previous
packages must not be overwritten. The candidate build_manifest.json and native acceptance.json record the exact
source, environment, provenance and observed checks. Historical redistribution
arrangements are documented in the v0.8.1 acceptance records.
No push, Actions dispatch, release or tag is performed. Native same-host
standalone checks are not independent clean-machine installation.
Older commands below are historical.

Fresh-environment validation may use the official
[CPython Windows NuGet CI package](https://docs.python.org/3.11/using/windows.html#the-nuget-org-packages)
as the Python 3.11 base without installing a launcher or changing system PATH.
Record interpreter origin, `pyvenv.cfg`, pip installation report/freeze,
preflight output, per-distribution license inventory, build fingerprints and
native acceptance. A clean build environment is not an independent
clean-machine installation test of the finished application.


Current source packaging still uses `emcd_gui.spec` and `launcher.py`; all
hidden imports resolve after the [runtime cleanup](../docs/SOURCE_CLEANUP.md).
The source-cleanup stage did not rebuild an executable or ZIP. Older acceptance commands and removed
verification scripts below are historical build records. Current source
acceptance uses the retained GUI/physics tests and native worker/cancellation
diagnostics, not the retired Stage E/F/Beta orchestration modules.


Windows x64 research Beta, package version **0.6.0**. Build the standalone
Double-Channeling EMCD Simulation in a fresh directory; previous 0.4.5
artifacts must remain untouched. Labels, archive names and manifests derive
from the source package version. Publication requires the release acceptance
gates in [the report](../docs/WINDOWS_V060_BETA_ACCEPTANCE.md).

From an environment containing the GUI runtime dependencies:

```powershell
python -m venv --system-site-packages build/windows-rc/venv
build/windows-rc/venv/Scripts/python.exe -m pip install pyinstaller==6.22.3
powershell -NoProfile -ExecutionPolicy Bypass -File packaging/build_windows.ps1 -BuildRoot build/windows-v060-beta-rc -ArchiveName EMCD-Sim-0.6.0-Beta-Windows.zip
```

The separate build venv shares scientific packages without modifying them.
The spec uses explicit GUI imports and normal dependency hooks, rather than
whole-environment collection. It includes NumPy/SciPy native libraries, Qt
platforms, Agg/QtAgg, Matplotlib resources, ASE CIF support and its space-group table, licenses, build
provenance and only the Git-tracked five-column Ni example. The modified
working copy, WIEN2k companions and simulation outputs are excluded. Git is
needed to build, not to run. Conda-backed builds explicitly supply base
OpenSSL/Expat DLLs.

Historical Stage E outputs: `build/windows-rc/dist/EMCD-Sim/` and
`build/windows-rc/EMCD-Sim-Windows-RC.zip`. The command now defaults to the
separate Stage F paths below. Copy/extract the **whole folder**;
keep `_internal` beside the EXE. User files belong outside the program folder.

Opt-in native acceptance uses actual widgets and numerical workers:

```powershell
EMCD-Sim.exe --rc-acceptance C:/RC-validation --rc-source C:/inputs/Ni_fm.xmcd
EMCD-Sim.exe --rc-acceptance C:/RC-validation --rc-reopen
```

Use a fresh calculation directory. Six model/method combinations and one
mistilt produce real exports and saved projects. A second process reopens,
checks fingerprints, compares saved tilts, exports PNG/SVG/NPZ and checks
missing sources. Reports contain local provenance paths; nothing is uploaded.

Use the comparison tab's **Export NPZ/CSV** action for CSV spectra and scalar
metrics. The build command above uses a process-only script-policy override;
it does not change the user or machine execution policy.


Stage F uses the same specification in a fresh location:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File packaging/build_windows.ps1
```

Historical Stage F defaults were `build/windows-stage-f/dist/EMCD-Sim/` and
`build/windows-stage-f/EMCD-Sim-Stage-F-Windows-RC.zip`, labeled
`EMCD-Sim GUI Stage F RC (unreleased)`. Existing distributions are refused;
use `-BuildRoot` and `-BuildLabel` for a new candidate. Stage E remains untouched.
The current release workflow uses the separate v0.6.0 directory above.

Display-only acceptance reopens existing projects, guards forward calls and
exports derived figures/data (fresh output paths required):

```powershell
EMCD-Sim.exe --stage-f-acceptance C:/F-validation --stage-f-project C:/saved/reference_project --stage-f-comparison C:/saved/mistilt_project
```

This does not invoke the expensive Stage E physics acceptance.
## Local v0.6.1-beta.1 candidate

The local candidate and its scope are documented in
[V061_BETA_ACCEPTANCE.md](../docs/V061_BETA_ACCEPTANCE.md). The existing public
v0.6.0 assets are preserved. Build into a fresh directory:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File packaging/build_windows.ps1 -BuildRoot build/windows-v061-beta-final -BuildLabel 'EMCD-Sim v0.6.1-beta.1 local candidate' -ArchiveName EMCD-Sim-0.6.1-beta.1-Windows-RC.zip
```

Package version `0.6.1b1` uses PEP 440 prerelease notation. Verify archived
content and saved-data native GUI acceptance with
`python scripts/verify_v061_candidate.py`. This does not calculate spectra.

## v0.8.1 generalized native acceptance

After extracting the complete ZIP, run `EMCD-Sim.exe --release-acceptance C:/new-output
--historical-project C:/existing-Ni-project` as one command. This opt-in packaging
route runs eight real GUI/worker Ni and synthetic Fe imported/atomic Single/Double
BW/MS cases, source validation, atomic generation, projects and exports. It writes
only a new directory and reads the historical control without migrating it. The
original synthetic parameter example is collected explicitly; no broad hidden
imports or external unlicensed table are added. CI runs this mode in addition to
the five established desktop orientation checks. Same-host native acceptance is
not clean-PC certification or quantitative Fe EMCD validation.

## beta.2 dependency distribution

Keep the established dependency environment unchanged. Download the five official
6.12.0 archives listed in assets/qt-licenses/upstream-provenance.json to the
CorrespondingSourceRoot passed above. The build checks the existing pinned
provenance, creates the Windows ZIP and a companion Qt-sources ZIP including the
exact committed application source. Publish both ZIPs and SHA256SUMS together.
The spec excludes unused PDF/VirtualKeyboard plugins and their dependency chain.
It stages two NumPy DLL import-name fixes without changing executable sections
and excludes all Microsoft CRT/UCRT/API-set copies. The package checker enforces
the retained Qt inventory and absence of app-local Microsoft runtime DLLs.
Users must install the official Microsoft x64 v14 runtime directly. Verify the
extracted EXE loads that system runtime, then preview, calculate, save and reopen.
See [source and replacement instructions](assets/qt-licenses/SOURCE_AND_REPLACEMENT.md).
No scientific regression is added solely for this trimming; the prior failed full
run and scoped prerelease exception remain recorded in the beta.2 release notes.
