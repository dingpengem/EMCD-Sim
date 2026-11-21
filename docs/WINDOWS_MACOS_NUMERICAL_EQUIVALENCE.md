# Windows/macOS numerical equivalence — beta.2 candidate evidence

This record distinguishes numerical implementation agreement, convergence and
experimental calibration. Cross-platform agreement establishes neither of the
last two. No scientific calculation was rerun to replace unavailable Mac data.

## Sources and provenance

- Windows benchmark implementation: `9d6b7fbb6f824e275cf3c266c0ab22f562ee72af`;
  original Windows baseline `527a29063c0f2d76c67fba7117303bcd7f16e7f4`.
  [Completed Windows benchmark](WINDOWS_SC_DC_RESOURCE_BENCHMARK.md).
- Published macOS application: `03dc8f8d1f0374984c9fc81866eaa32ce48008d0`,
  `v0.9.0-beta.1-macos-arm64.1`.
- Mac benchmark report/data revision:
  `6475afed8d133fe39773c08701b216312cd455d5` on
  `feat/macos-sc-dc-resource-benchmark`. Its
  [records](https://github.com/dingpengem/EMCD-Sim/blob/6475afed8d133fe39773c08701b216312cd455d5/docs/MACOS_SC_DC_RESOURCE_BENCHMARK.md)
  report 14 completed full workloads; the cancelled MS-DC v2 attempt is not one.
- Authentic BW-SC [Quick Start exports](https://github.com/dingpengem/EMCD-Sim/tree/32c30a5dfac52b6f100f8a2127ed99b270d36d0b/docs/examples/macos-ni-quickstart)
  were retained locally. The new Mac benchmark report explicitly states its
  corrected BW-SC baseline is bit-for-bit equal to those exports. This preserves
  the earlier accepted comparison; it is not a newly transferred benchmark file.
- Registered CIF identity:
  `ad8372ef427a95957a6182d5a7b7f5aaea5899e1464eb0afa8e540ff2f47d67d`.
  Registered XMCD identity:
  `bb9bdd478d54cc8de60403409f4d90e63deb11a64891bbac6754f867be14deda`.
  Existing identity validation is preserved; no new hash gate is introduced.

## Matched scientific request

FCC Ni, four occupied sites, a=3.520 Å; Global M=(0,0,1); declared XMCD,
eta=beta=1, relative reference 1, source-max nonmagnetic normalization and the
explicit axisymmetric reversal assumption. Scientific status remains
`physical_source_unvalidated`.

Both requests use 200 kV/10 nm, [017]/(200), full finite ZOLZ,
tilt (−7.124812628,0) mrad, Adaptive Dirac–Padé 2026, B=0, beam/potential
cutoffs 2.5/2.0 Å⁻¹ and 21 beams. The source grid has 241 uniform points over
823.625–882.521 eV plus exact 831.271/848.698 eV selections: **243 samples**.
The selected maps are 97×97 over ±1 Å⁻¹; other energies use 162 fractional
detector-support pixels. Depth nodes and aperture subpixels are 64. Thales
A/B centres are (0.2840909090909091, ±0.2840909090909091) Å⁻¹, radius 0.09 Å⁻¹.

MS uses a 32×32 FFT mesh, projected generators (200)/(1,7,−1), requested
maximum step 2 nm and actual step 10/63 nm across 63 depth intervals. Each
comparison must retain its propagation/channeling mode; no BW/MS or SC/DC
equality is assumed. Settings/source matching against the compact Mac record
has passed for all Windows benchmark runs. Matching settings is not a substitute
for direct numerical comparison of the other three backends.

## Numerical comparison matrix

| Backend | Windows completed full reference | Exact Mac benchmark run | Numerical status |
| --- | --- | --- | --- |
| BW SC | `corrected-bloch-single-1` | `bw-sc-manual-1-v2` | PASS retained: 43 numerical arrays against authentic Quick Start exports, with the benchmark's documented bitwise linkage |
| BW DC | `serial-check-bloch-double-1` | `bw-dc-manual-1-v2` | INCOMPLETE: authentic Mac raw arrays not available locally |
| MS SC | `corrected-fft-multislice-single-1` | `ms-sc-manual-1-v2` | INCOMPLETE: authentic Mac raw arrays not available locally |
| MS DC | `serial-check-fft-multislice-double-1` | `ms-dc-manual-1-v3` | INCOMPLETE: authentic Mac raw arrays not available locally |

The complete Windows projects remain under
`build/windows-resource-benchmark-527a290/<reference>/project/`.
Within-platform worker comparisons and Save/Open passed; neither these checks
nor timing/memory summaries prove the three missing cross-platform comparisons.

## Per-array evidence and tolerances

[BW-SC comparison CSV](benchmarks/windows-macos-20261111/bw_sc_array_comparisons.csv)
records archive/key, shape, reference scale, maximum absolute and scale-normalized
differences, rtol/atol, mask identity and PASS/FAIL for **every one of the 43
numeric arrays**. Three method/channeling label arrays also match exactly.
The largest spectral intensity/component difference is 6.94e−17; the largest
angular intensity/component difference is 1.78e−14. Percentage signals use
percentage-point units and are not mixed with intensity errors.

Energy coordinates use absolute tolerance 1e−10 eV; q coordinates and aperture
weights use 1e−14 with zero relative tolerance. Intensities use rtol 1e−9 and
atol 1e−12 times the archive's reference raw-intensity peak. This common raw
scale applies to near-zero magnetic/nonmagnetic differences instead of dividing
by their near-zero values. Percentage fields use scale 100, rtol/atol 1e−9;
coherence uses scale 1, rtol 1e−10/atol 1e−12. Each maximum normalized difference
is max|Windows−Mac| divided by the stated common scale. Shapes and NaN/Inf masks
must match; finite samples alone enter difference metrics. Masked paired
contrasts are not physical zero or failed full-field pixels. No bitwise
cross-platform requirement or data/reference modification is imposed.

## Missing transfer inventory

Targeted checks of Downloads, locally mapped Documents, Desktop, repository outputs/build transfer names,
the Windows benchmark directory and the current GitHub benchmark record found
no approved local transfer of the other three Mac raw datasets. Only C: is
mounted in this session; no network share or whole-disk recursive search was
performed. A transfer path has been requested. Unavailability is an evidence
gap, not a demonstrated scientific-code defect.

Please transfer the existing saved-project or normal numerical-export folder
from each exact completed Mac run below. Compress/copy the original folder;
do not hand-edit JSON, reconstruct arrays, rerun calculations or commit large
NPZ archives to GitHub.

| Priority | Mac run folder under the recorded benchmark output root | Needed evidence |
| --- | --- | --- |
| Required | `bw-dc-manual-1-v2` | Existing full BW-DC numerical project/export |
| Required | `ms-sc-manual-1-v2` | Existing full MS-SC numerical project/export |
| Required | `ms-dc-manual-1-v3` | Existing successful full MS-DC project/export, not cancelled v2 |
| Optional provenance consolidation | `bw-sc-manual-1-v2` | Exact benchmark project/export to accompany the preserved Quick Start linkage |

The recorded Mac root is
`outputs/macos-sc-dc-resource-benchmark-20261111/`. Use the actual saved
project/export subfolder inside each run; its private subfolder name is not
invented here. Minimum comparison files are `virtual_detector_eels.npz`,
`angular_maps.npz`, `metadata.json`, `input_parameters.json`, `structure.json`
and the existing `project.json` provenance/integrity record. Prefer the complete
ordinary saved project so all referenced files, including diffraction/context
data and attachments where present, remain intact. No screenshots or application
bundle are needed solely for numerical comparison.

## Candidate and release interpretation

The beta.2 Windows candidate can be built/tested while this gap is recorded,
but **all-four-backend cross-platform numerical equivalence is INCOMPLETE**.
For beta.2 the release owner explicitly accepted these three incomplete direct
comparisons as a documented Research Beta limitation on 11 November 2026. They
remain INCOMPLETE, not PASS, and are no longer a publication prerequisite.
No new comparisons or reruns were performed to replace the missing data.

The 2.0 Å⁻¹ potential cutoff excludes the first off-row harmonic near 2.029 Å⁻¹.
The actual MS step exceeds the advisory 0.04 nm reference. General beam/FFT/depth
convergence, material calibration, absolute cross sections and magnetic moments
remain unestablished. Existing incomplete broad/source-guard coverage is not
converted into PASS. No kernel/resource-policy change or expensive recalculation
is justified merely by the missing data.
