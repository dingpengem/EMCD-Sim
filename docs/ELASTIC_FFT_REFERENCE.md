# P1: Independent elastic FFT multislice / Bloch-wave cross-check (v0.3.6)

## Purpose

Cross-check the **incoming elastic propagator** of FCC Ni [001] in two distinct numerical representations: (1) the existing finite-basis Bloch-wave diagonalization, and (2) a new **real-space FFT split-step propagator**. The input crystal potential is *identical and explicitly Fourier-truncated* in both implementations. This isolates numerical propagation discrepancies from differing atomic scattering models.

**This is not yet a true 3D atom-sliced multislice simulation or a quantitative EMCD benchmark.** The projected [001] potential is constant per propagation slice, with no explicit z-dependent atomic layers, thermal diffuse scattering, absorption, HOLZ, finite-convergence electron probe, DFT MDFF, or outgoing wave. The two propagators are independently implemented but solve the same projected-potential paraxial approximation. This reference tests elastic channeling only.

## Equations and units

For [001] FCC Ni (conventional lattice constant `a=3.524 Å`), the projected repeat period in x/y is `a/2`; discrete FFT indices `(m,n)` correspond to `(hkl)=(2m,2n,0)`. Real-space potential uses:

`U(x,y) = Σ_(G ≠ 0, |G| ≤ G_pot) U_G exp(+2πi G·r)`,

`U_G = 10 γ λ F_G / Ω  [nm^-1]`, where `F_G` is the Lobato–Van Dyck IAM Ni electron structure factor in Å; mean inner potential `U_0` is removed (common phase). Reciprocal `G` is in **cycles/Å**, depth in nm.

The independent FFT split-step updates an envelope wave by

`ψ(z+dz) ≈ exp(iD dz/2) exp(iU(x,y) dz) exp(iD dz/2) ψ(z)`,

where reciprocal kinetic diagonal `D_G = -10π λ (|k_perp+G|² - |k_perp|²) [nm^-1]`. The potential multiplication occurs **in real space**; kinetic multiplication occurs **in Fourier space**. The Bloch solver constructs its finite matrix from the **same Fourier-truncated** `F_(G−G')`. This avoids comparing unlike potentials and mistakenly attributing differences to the propagator.

Potential cutoff, finite Bloch-beam radius, FFT grid size, and slice step are **four separate numerical controls**. Agreement at one set of cutoffs is not convergence of any of them. In addition, an atomic 3D potential (z-dependent slices) must be checked at a later milestone.

## Run on Windows, macOS or Linux

```bash
python -m emcd_sim.elastic_reference --output outputs/ni_elastic_reference
```

Or use the installed `emcd-elastic-reference` entry point. Defaults:

- `zone-axis` and illustrative `symmetric-3bc` incidence (0,0) and (0,25) mrad;
- 200 kV, Ni [001], B = 0 Å², thickness 10/30/50 nm;
- **potential** Fourier cutoffs 1.8, 2.2, 3.0 cycles/Å;
- growing **Bloch** beam radius = potential cutoff + 1.2 cycles/Å;
- periodic real-space FFT grid 32×32; Strang slice step ≤0.08 nm.

Change parameters with `--conditions`, `--potential-cutoffs`, `--thickness-nm`, `--beam-margin`, `--fft-grid`, `--slice-step-nm`, `--b-factor`, `--max-beams` and `--output`. For example:

```bash
python -m emcd_sim.elastic_reference --conditions zone-axis near-2bc --potential-cutoffs 1.8 2.2 3.0 --thickness-nm 10 30 50 --fft-grid 48 --slice-step-nm 0.04 --output outputs/ni_reference_fine
```

**Output files:** `elastic_reference_comparison.png`, `elastic_reference_results.csv`, `elastic_reference_metadata.json`. CSV lists diffraction intensities for transmitted 000 and **total variation distance (TV)** between the two full diffraction intensity distributions, treating absent channels as zero. TV=0 means identical normalized elastic intensity distributions. These files do not include EMCD/MDFF signals.

## Initial numerical observations (illustrative P1 diagnostics)

For the default matched potential settings, 18 comparisons yield elastic-norm errors below `7.1e-14`, and maximum full-pattern TV difference `0.01048` (1.05%) at 50 nm under illustrative symmetric-3BC geometry at potential cutoff 1.8 cycles/Å. The two elastic solvers typically agree much more closely at other points. For example, at 30 nm, [001] with potential cutoff 2.2 cycles/Å, calculated `I000` is approximately `0.1714` (Bloch) versus `0.1708` (FFT), TV ≈ `0.00071`.

**Warning: the untruncated-potential result has not converged.** At 30 nm, zone-axis `I000` changes substantially as the shared potential cutoff increases (≈0.130 at 1.8, 0.171 at 2.2, and 0.506 at 3.0 cycles/Å). Matching the two algorithms at each cutoff does not resolve this substantial **physical model/truncation sensitivity**.

At fixed potential cutoff 2.2 cycles/Å and (0,25) mrad, reducing the FFT step from 0.08 to 0.04 nm changes I000 at 10/30/50 nm by no more than approximately `3.1e-4`, while increasing the FFT grid from 32 to 48 at fixed 0.04 nm changes I000 by ~`7e-13` in this specially band-limited test. These are limited checks, **not universal convergence guarantees**.

## Next P1 acceptance work

1. Grow potential cutoff beyond 3.0 cycles/Å while separately expanding the Bloch basis and FFT grid; look for stabilization over several successive cutoff values and multiple thicknesses, tilts, and diffracted beams.
2. Add layer-resolved 3D atomic Ni potentials and compare with independently established electron-microscopy elastic solvers under identical conventions; the projected z-independent reference is not a replacement for that validation.
3. Independently benchmark reference cross sections or measured diffraction intensities where the structure, beam convergence and specimen thickness are reliably known.
4. Only after incoming elastic results are reliable, proceed with complex dipole MDFF and DFT Ni 2p transition data as specified in `SINGLE_CHANNELING_QUANTITATIVE.md`. Double channeling stays deferred.
