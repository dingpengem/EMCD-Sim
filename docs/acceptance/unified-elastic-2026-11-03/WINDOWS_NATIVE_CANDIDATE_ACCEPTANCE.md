# Windows native unified-elastic candidate acceptance

**PASS — separate local candidate; no public binary replacement.**

Feature `592dd85893875dfa3d7fbdbb9a85be025d96505d`; fetched main `2810e86cba609dc3dc8cd42208b1c0b8ac747a2d`; normal --no-ff merge `b48b57032e425292775aeaa3ecb5e8d8630a67c5`; exact clean candidate source `29697538f57c5cc9bf84b7012b51a57a40c9a52b`. Public version remains 0.7.0b1, physics convention forward_born_dagger_g_minus_h_v1.

Candidate directory: `C:\Users\peng863\EMCD-Sim\build\unified-elastic-main-integration\build\windows-unified-elastic-candidate-20261103`. Actual executable: `C:\Users\peng863\EMCD-Sim\build\unified-elastic-main-integration\build\windows-unified-elastic-candidate-20261103\final-extracted\EMCD-Sim\EMCD-Sim.exe`.

EXE SHA256 `60961a50509b4b79c36e39d97a2860b365761a94a34bc7b3a7b1e7084d909ca5`. Portable ZIP SHA256 `4dbe3709080b3a24ff488052d8a64cee3cb37edbd0c15e1daea774e3f1e60393`. All 613 manifest files were rehashed after native testing; all4 coefficient/provenance/license resources exactly match source. ASE CIF space-group data are present. No HDF5 archive is packaged and h5py is not imported; all118 factors evaluate through the bundled JSON resource.

The portable ZIP was extracted to a fresh directory and its EXE launched with QT_QPA_PLATFORM=windows, PATH limited to Windows/System32 and Windows, and Python/Conda/Qt override paths removed. Exit code0 and clean worker shutdown were verified after the process ended, with no observed native crash or missing coefficient error. Build metadata identifies the exact clean source and pinned toolchain. Automatic path selection bypassed modal file choosers; calculations/rendering/click callbacks/save/open ran in the actual frozen application.

|Native check|Result|
|---|---|
| bundled_all118_and_notices | PASS |
| default_ni_worker_preview | PASS |
| native_save_reopen_elastic | PASS |
| genuine_historical_project | PASS |
| bcc_fe | PASS |
| cscl | PASS |
| hex_zno | PASS |
| missing_external_provider_diagnostic | PASS |
| ni_native_mdff_and_full_project_roundtrip | PASS |

The genuine historical Ni project predates provider metadata; it restored Lobato and reproduced its selected archived incoming amplitudes at zero measured discrepancy. Original project and saved arrays were not altered. This checks elastic compatibility, not the signed inelastic correctness of an old convention: its existing convention warning is preserved. The new Ni MDFF smoke uses only two selected energies in a bounded entrance-only configuration; it is not a new243-energy quantitative study.

Evidence, process exit and skip details are in [MAIN_INTEGRATION_EVIDENCE.json](MAIN_INTEGRATION_EVIDENCE.json). Raw native JSON/screenshots/projects and source JUnit/log files remain under local `outputs/unified-main-integration/`. The package has unchanged version0.7.0b1 and a LOCAL CANDIDATE build label. Its Apache-2.0 coefficient LICENSE/NOTICE remain separate from MIT; no unlicensed legacy table is bundled.

This establishes same-host Windows application functionality and the stated numerical controls. It does not establish independent clean-machine installation, experimental quantitative accuracy, or universal BW/MS convergence. No release/tag/push or change to the existing public Windows binary occurred.

Build invocation caveat: the outer PowerShell invocation recorded status1 while classifying PyInstaller informational stderr as NativeCommandError (Conda environment detection warning). The build log explicitly records successful EXE/COLLECT completion, ZIP and SHA256 creation. Those artifacts were independently extracted and every manifest file verified, and the actual EXE exited0 after all native checks. The wrapper status is preserved in evidence; no missing build artifact or native failure was ignored.

Actual extracted-EXE screenshots: [default Ni](windows_native_ni.png), [indexed CsCl](windows_native_cscl.png).
