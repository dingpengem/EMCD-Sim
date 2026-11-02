# EMCD-Sim v0.7.0-beta.1 release notes

Status: local Windows research candidate preparation; no tag, release, push or
Actions dispatch is authorized by this milestone. Python version 0.7.0b1;
Windows numeric file/product version 0.7.0.1. Archive:
EMCD-Sim-v0.7.0-beta.1-Windows.zip. Artifact label:
EMCD-Sim-v0.7.0-beta.1-Windows.

## Critical scientific compatibility notice

Legacy Windows versions before v0.7.0-beta.1 used a superseded Born/MDFF
convention affecting calculated magnetic-odd EMCD signs. Historical signed
L3/L2 magnetic spectra must be revalidated or recalculated before corrected
interpretation. Preserve original raw arrays and source/version/convention
identifiers; do not silently flip or relabel legacy results. Missing provenance
is unknown or legacy-unverified. Intermediate corrected source 4f578156 still
identified itself as 0.6.1b3; exact source/convention metadata is authoritative.
This does not imply that all historical nonmagnetic EELS, diffraction
intensities or thickness trends are incorrect.

## Coordinated correction and version rationale

This is the first Windows version milestone for the independently validated
forward-Born correction, not a new MDFF model. For d_a=<i|r_a|f> and
Q=k_out-k_in, the target excitation uses d*. The tensor factory remains
T_ab=sum_n w_n d_na conj(d_nb), with T=L L^dagger.

- Legacy intensity: Re sum_ab R_ab T_ab. Corrected intensity:
  Re sum_ab R_ab T_ba = Re Tr(RT), for R_ab=v_a conj(v_b).
- Preserve T=L L^dagger but use forward transition modes L*.
- Double site phase changes from exp(+2*pi*i*(h-g).u) to
  exp(+2*pi*i*(g-h).u). Single's site-phase convention is unchanged.

Single/Double Channeling and BW/MS use the coordinated corrected convention
`forward_born_dagger_g_minus_h_v1`. All three corrected physics kernels remain
unchanged from validated ancestor 4f57815646d023957a81ad15fdaa684c02a54442.
Numerical defaults, worker policies, GUI layout and project schema are unchanged.
New results record software/convention provenance. Loaded old results preserve
arrays and original metadata and show an existing warning mechanism when
convention provenance is absent or superseded.

## Scientific evidence and signed interpretation

The corrected ancestor passed 602 tests with two optional skips, 59 focused
physics controls and 32/32 matched old/corrected BW/MS edge comparisons. These
are bounded model validations, including independent direct Born and nontrivial
site phases; they are not complete experimental or numerical convergence.
Representative conventional FCC Ni tests retain reversal-even intensities and
reverse the magnetic-odd sign relative to legacy. Nontrivial site-phase fixes
can affect more general interference and must not be reduced to an arbitrary
sign-flip instruction for historical arrays.

For the saved 300 kV Ni [017], 30 nm, +15 mrad Double BW case, corrected L3
magnetic-only asymmetry is +1.7099%, while conventional A/B is -2.9371%.
These depend on the recorded geometry, source energies, apertures and denominator;
nonmagnetic diffraction imbalance can dominate conventional A/B. RP/LP is not
an independent calibration of absolute experimental magnetic handedness.
The packaged candidate must independently reproduce a matched new Python/EXE
Ni [017] raw-intensity case; the saved numbers alone do not satisfy acceptance.

## Retained limitations

XMCD-constrained effective MDFF is not full complex-transition DFT MDFF.
Absolute RP/LP magnetic handedness and absolute energy calibration remain
unverified. [111] convergence is incomplete and a known Stage4.2 30 nm,
delta-X=-5 mrad/Y=+15 mrad/L2 detector-grid failure remains. BW/MS agreement
alone is not basis, cutoff, FFT, depth or aperture convergence. Projected IAM,
finite ZOLZ, frozen characteristic longitudinal transfer and existing averaging
remain. Absorption/TDS are not comprehensively included. No experimental
electron-count or shot-noise SNR calibration is added. Coarse steps require
convergence checks; accurate elastic intensity does not certify EMCD accuracy.

## Reproducibility, compatibility and acceptance

Version-development commits are local and must be identified as the actual
build HEAD, with 4f578156 as the validated physics ancestor. Build manifests
record clean/dirty state, source hashes, convention, build time, Python,
PyInstaller and dependency versions; archive SHA256 is recorded independently.
Historical releases, 323 protected files/204 checkpoints and 9756 research
files remain untouched. New outputs use outputs/windows_v070b1_acceptance/.
See [Windows candidate acceptance](WINDOWS_0_7_0_BETA_1_ACCEPTANCE.md) for the
actual candidate SHA, regression results, native checks and local archive path.
No independent clean-machine installation is inferred from offscreen or
same-host native checks. No official prerelease has been published.
