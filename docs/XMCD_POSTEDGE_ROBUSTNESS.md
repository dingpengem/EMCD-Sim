# Post-edge recovery: matched basis and sampling validation

This focused calculation reuses the existing entrance-channeling forward model,
magnetic reversal, fractional apertures and constant post-edge normalization.
It changes no elastic potential, propagation, MDFF, coherence or normalization
algorithm. Results are numerical checks within the effective Ni model, not
quantitative magnetic-moment recovery or a convergence certificate.

Run from the repository root (with the package installed, or `PYTHONPATH=src`):

```bash
python -m emcd_sim.xmcd_postedge_robustness \
  --xmcd-file data/wien2k_ni/Ni_fm.xmcd \
  --cutoffs 1.2 1.4 1.8 --output outputs/ni_postedge_robustness
```

The eight configurations use FCC Ni [001], 200 kV, 30 nm, eta=beta=1,
the same full independent-atom potential (B=0), fixed physical tilts and
apertures, fractional integration with 64 boundary subpixels, and 185 energies
from 837 to 882.521 eV. The basis series uses grid 65 and 64 depth steps for
near-2BC and nominal symmetric-3BC. Near-2BC at cutoff 1.4 separately changes
the grid to 97 and depth steps to 128. The cutoffs 1.2, 1.4 and 1.8 cycles/A
retain 13, 21 and 37 ZOLZ beams. These are basis cutoffs, not potential cutoffs.
The larger basis was added after the first comparison showed sensitivity.
The largest pair-array estimate is approximately 353 MiB, below the 512 MiB
guard; no simultaneous grid/basis enlargement is performed.

All three existing post-edge windows (878-882, 874-878 and 877-881 eV), observed
and oracle factors, and full/L3/L2 metrics are retained in the comparison CSV.
L3 and L2 integrals use 844-862 and 864-874 eV with interpolated exact endpoints.
Each run saves original detector spectra, parity signals, processed spectra,
validity masks and diagnostic terms in a pickle-free NPZ plus provenance JSON.
Checkpoints are reused only for matching settings, source hash and simulation
file hashes; all analysis is recomputed from original detector spectra.

## Bias interpretation

Let `alpha_o` be the observed factor and `alpha_n` the even-oracle factor.
The saved terms obey, to roundoff:

```
D_corrected - D_mag = (N_A - alpha_n*N_B)
                    - (alpha_o-alpha_n)*N_B
                    - (alpha_o-1)*M_B
```

The first term is residual nonmagnetic spectral mismatch for a constant oracle
factor. The second is the even residual caused by magnetic contamination of
the observed post-edge factor. The third is the magnetic contribution changed
by scaling detector B. The energy-dependent `N_A/N_B` is saved only where
`N_B > 1e-12*max(abs(N_B))`; it is never used to fit or correct spectra.
The unscaled magnetic reference and scaled magnetic contribution have different
normalization conventions. Their norm/integral difference alone is not a
calibrated loss of magnetic moment.

## Interpretation limits and outputs

`robustness_comparison.csv` contains one row per configuration, window,
normalization method and analysis region. `robustness_metadata.json` records
matched differences, classifications, physical/numerical settings, source hash,
software revision and dirty status. Per-run metadata records actual aperture
areas, selected energies and simulation file hashes. The two PNGs compare basis
metrics and L3/L2 spectra (plus the diagnostic oracle ratio). Outputs remain
under the ignored `outputs/ni_postedge_robustness/` directory; earlier published
results are unchanged.

Classification uses an explicit diagnostic threshold: any valid dimensionless
metric change greater than 0.005 across all windows, scopes and observed/oracle
methods flags sensitivity. This is a screening convention, not an accuracy
bound. Undefined suppression for negligible even references stays undefined;
weak/canceled signals are accompanied by absolute spectral differences and
signed-integral validity reasons. Sampling tests are representative near-2BC
checks only: symmetric-3BC sampling and spectral-energy sampling remain
insufficiently tested. Neither aperture-area accuracy nor agreement at these
few settings certifies integration of a spatially varying intensity field,
complete diffraction-basis convergence, or accuracy of the effective MDFF.

## Basis results

Primary 878-882 eV observed normalization; norms cover the full retained range:

| Geometry | Cutoff | Beams | alpha observed | alpha oracle | Even suppression (%) | Magnetic norm change (%) | Corrected/reference error (%) |
|---|---:|---:|---:|---:|---:|---:|---:|
| near-2BC | 1.2 | 13 | 0.802350 | 0.801077 | 99.0502 | -11.9521 | 14.4914 |
| near-2BC | 1.4 | 21 | 0.758520 | 0.755778 | 98.6253 | -16.2671 | 18.1862 |
| near-2BC | 1.8 | 37 | 0.761456 | 0.759048 | 98.7540 | -16.6037 | 18.5464 |
| symmetric-3BC | 1.2 | 13 | 1.000714 | 1.000000 | undefined | +0.03570 | 2.86867 |
| symmetric-3BC | 1.4 | 21 | 1.000694 | 1.000000 | undefined | +0.03472 | 2.87019 |
| symmetric-3BC | 1.8 | 37 | 1.000673 | 1.000000 | undefined | +0.03364 | 2.87016 |

Near-2BC is sensitive to diffraction-basis truncation across the tested series.
The primary 1.4-to-1.8 changes are smaller than 1.2-to-1.4, but this does not
establish convergence. The L3/L2 processed magnetic integral changes are
-11.9522/-11.9539%, -16.2675/-16.2740% and -16.6041/-16.6117% respectively.
Strong nonmagnetic suppression and substantial magnetic scaling persist:
this is a processing tradeoff within the current effective model.

Symmetric-3BC is stable within these tested bases. Original even differences
are negligible, so suppression percentages are undefined. Normalization can be
unnecessary or counterproductive: it introduces an even residual and a roughly
2.87% corrected/reference error. This does not establish an optimal experimental
geometry. Its magnetic integral changes are approximately +0.03570%, +0.03472%
and +0.03364% for both L3 and L2.

Focused validation: 14 tests pass in the normalization and robustness modules,
including exact three-term reconstruction, observed/oracle independence,
diagnostic ratio validity and rejection of confounded comparisons. No broad
regression suite or major parameter sweep was run.

At cutoff 1.4, near-2BC has diagnostic `N_A/N_B` spanning 0.754973-0.755829,
whereas the observed factor is 0.758520 (oracle 0.755778). Thus a constant
oracle factor leaves a small energy-dependent mismatch, and magnetic tail
contamination adds a separate bias. The full-range norms of oracle mismatch,
tail-bias even contribution and magnetic scaling change are respectively
7.68e-5, 3.33e-4 and 2.23e-3 in the model's relative-intensity units; these
are contributions to a signed vector identity, not additive error norms.
The unscaled magnetic norm is 1.37e-2. For symmetric-3BC the ratio is one
to roundoff, the oracle mismatch norm is 6.75e-17, and the observed-factor
bias even norm is 2.10e-4 (magnetic reference norm 7.26e-3). This separates
nonmagnetic shape mismatch from magnetic contamination of the scale factor.

## Sampling results and decision

At cutoff 1.4, the primary full-range observed metrics are:

| Grid | Depth steps | Even suppression (%) | Magnetic norm change (%) | Corrected/reference error (%) |
|---:|---:|---:|---:|---:|
| 65 | 64 | 98.625254 | -16.267111 | 18.186250 |
| 97 | 64 | 98.624317 | -16.267629 | 18.186445 |
| 65 | 128 | 98.625137 | -16.263035 | 18.182121 |

The maximum valid dimensionless metric differences over every window, scope
and method are 3.05e-5 for grid refinement and 4.81e-5 for depth refinement,
well below the stated 0.005 screening tolerance. Absolute spectral difference
norms (raw / magnetic / even) are 1.93e-5 / 3.87e-6 / 1.68e-5 for the grid
check and 3.52e-6 / 2.88e-7 / 3.34e-6 for the depth check. The maximum
three-term reconstruction error across all eight runs is 2.72e-17.

The normalization conclusions are **sensitive to diffraction-basis truncation**
for near-2BC across 1.2-1.8, but **stable within tested sampling settings**.
The maximum metric changes are 0.04530 for 1.2-to-1.4 and 0.00461 for
1.4-to-1.8; the latter passing the screening threshold is not convergence.
Symmetric-3BC normalization metrics are **stable within tested bases**
(maximum changes below 5.92e-5), with sampling **insufficiently tested**.
Stability of normalization metrics does not mean the underlying magnetic
spectra are basis-converged: their absolute difference norms remain 1.24e-3
(near-2BC) and 6.45e-4 (3BC) for 1.4-to-1.8. No geometry or physical
magnetic-moment accuracy claim follows from these checks.
