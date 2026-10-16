# Stage F percentage visualization acceptance

Stage F continues `feat/emcd-desktop-gui` from Stage E commit
`5d7d51bdee001ea0835eb63465e76fddac522bf3`; package version remains 0.4.5.
No merge, tag or release is part of this work.

## Saved Ni example

Existing Stage D Ni [017] exact-(200)-Bragg and +1 mrad X-mistilt projects
were reopened without simulation. The selected magnetic energies are
831.271 and 848.698 eV on the native saved WIEN2k axis. Peak references are
maxima of the **summed reversal-even A+B EELS**, not magnetic extrema.

| Edge | BW peak window (eV) | BW peak energy (eV) | BW P_edge (a.u.) | BW D_mag / Sigma_ref (%) | BW D_mag / P_edge (%) |
| --- | --- | --- | --- | --- | --- |
| L3 | 826.271?836.271 | 831.4778 | 0.2508784247 | -0.37966009 | -0.37556164 |
| L2 | 843.698?853.698 | 848.698 | 0.1662582163 | +0.61515540 | +0.61515540 |

These percentages are evaluated at the selected magnetic map energies.
L2 in a **full spectrum with L3 reference** has a different peak percentage;
the denominator stays P_L3 throughout. Native sampling, no interpolation,
experimental energy shift or invented background subtraction was used.
Corrected BW peak contrasts are -0.38432228% (L3 reference) and +0.60639149%
(L2 reference). They are not pure magnetic signals.

Using the same BW peak for both methods, MS magnetic peak percentages are
-0.37569746% (L3) and +0.61537791% (L2). MS energy-dependent asymmetries are
-0.37979623% and +0.61537602%. The small differences remain visible because
method peaks are not independently scaled. Original solver errors are unchanged.

## Checks and scope

- 26 focused Stage F tests plus 5 Stage E resource tests passed.
- Three selected Stage A geometry/interaction tests passed. Broad B/C/D
  fixtures were deliberately excluded because they invoke forward calculations.
- Native Windows source acceptance at 150% scaling exercised all spectral
  modes and zooms, BW/MS overlays, local/paired angular percentages, saved-run
  comparisons, and PNG/SVG/CSV/NPZ exports. Nine guarded forward entry points
  recorded **zero calls**. Original saved arrays and project files retained
  their SHA256 fingerprints. Legacy B/C data remained read-only.
- A small offscreen canvas can emit Matplotlib constrained-layout warnings;
  native captured/exported figures were inspected for readability. Existing
  Qt high-DPI deprecation warnings are unrelated to scientific normalization.

[Actual native screenshot](images/gui/stage_f_emcd_percentage.png) combines
saved magnetic-odd/even paired maps with fixed-L3-peak BW/MS EELS.
Source reports and derived outputs are local under
`outputs/gui_stage_f/native_prebuild/` (also `native_source_final/`).
All 827 previously fingerprinted Stage B/C artifacts were checked unchanged.

The existing Stage E ZIP SHA256 remains
`2c679fcedb59c3eebcbb5718b509eb28d15cc5419eb3f00f5f034fb385460648`.
Stage E is preserved; the new candidate uses `build/windows-stage-f/`.
No forward model, MDFF, physical parameters, raw spectra, project schema or
numerical discrepancy definitions were changed. Absolute calibration,
incomplete DFT-derived MDFF, outgoing channeling and potential-cutoff
convergence limitations remain. This is development-machine acceptance,
not an independent clean-Windows-machine or signing certification.


## Stage F standalone candidate

The completed candidate is labeled **EMCD-Sim GUI Stage F RC (unreleased)**,
built from `618789717303cbea246cdb0fbccfe6a44040ecb7`. Every bundled GUI source
hash matches that commit. Build metadata reports a dirty workspace because
pre-existing user data/scripts remain; those files were not staged or bundled.
Only the repository-tracked Ni example was packaged.

- Executable: `build/windows-stage-f/dist/EMCD-Sim/EMCD-Sim.exe`
- Archive: `build/windows-stage-f/EMCD-Sim-Stage-F-Windows-RC.zip`
- ZIP SHA256: `523cc3a087a92b4dc7aa790daeefca3399dbe35d0974ad78c7cbb4913cda9ca8`
- ZIP size: 108,541,536 bytes; 608 application files; archive CRC verified.

An initial packaging attempt was stopped before producing an executable to
correct Raw-display scalar export reference labels. The completed executable
was built once from the corrected source. A transient Windows runtime-file
lock interrupted PowerShell ZIP compression; the completed folder was then
archived and CRC-checked with Python, without rebuilding the executable.


Frozen native acceptance **passed** after extraction to
`C:/EMCD-Sim-RC-Test/stage-f-rc-20261016/`, launched from Windows System32 with
Python/Conda environment paths cleared. It reopened copied exact-Bragg and
+1 mrad X-mistilt projects and exercised the same percentage displays,
PNG/SVG/CSV/NPZ exports and saved-run comparison. All original arrays matched
the source acceptance fingerprints exactly; project files were unchanged;
all nine guarded forward entry points recorded zero calls. The actual native
frozen screenshot was visually inspected. Reports are local in that folder's
`validation/`, with a report copy at `outputs/gui_stage_f/standalone_acceptance.json`.
This does not replace independent clean-machine or other-DPI testing.
