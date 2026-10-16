# Ni [017] minor-zone EMCD case study: edge assignment, diffraction geometry, mistilt and figure guide

> **Scope:** Current research code on `main` after the 43-orientation high-mistilt study. This is a **documentation guide**, not a new physical solver, experimental Ni calibration or formal package release. The package metadata still reads v0.4.5. Numerical methods and detailed tables are in [NI_017_MINORZONE.md](NI_017_MINORZONE.md) and [NI_017_HIGH_MISTILT_XY.md](NI_017_HIGH_MISTILT_XY.md).

## 1. What is the WIEN2k Ni L3/L2 energy, and how is it justified?

There are **three distinct energy notions** that must not be interchanged:

1. **Native WIEN2k/JOINT photon-loss axis:** values stored in the five-column `Ni_fm.xmcd` (823.625–882.521 eV). `wien2k_xmcd.py` imports this axis without fitting or shifting it.
2. **Spectral features used to sample EMCD angular maps:** the signed extrema of native magnetic dichroism, chosen from the corresponding edge neighborhoods. These are **not edge onsets** and are not experimental calibration standards.
3. **Experimental/nominal Ni edge energies:** e.g. older map references 852.7/870.0 eV. These are *external reference values*, not peaks of the native computed spectrum; use only after an explicitly documented calibration.

| Edge | Core manifold / WIEN2k edge | Native XAS maximum (eV) | Selected signed XMCD feature for maps (eV) | XMCD sign |
| --- | --- | ---: | ---: | --- |
| L3 | 2p3/2; first raw/broadened edge (`raw1/broad1`) | 831.421 | **831.271** | negative |
| L2 | 2p1/2; second edge (`raw2/broad2`) | 848.752 | **848.698** | positive |

Evidence for the **L3/L2 identification**, as opposed to absolute experimental energy accuracy:

- `Ni_fm.inc` identifies the relativistic 2p1/2 and 2p3/2 core configurations; the WIEN2k optical matrix files label 2p (L3) versus 2ps (L2).
- `Ni_fm.injoint` specifies core energies -60.534300889 Ry (L3) and -61.819104105 Ry (L2); their separation is approximately **17.48 eV**. The combined edge separation is consistent, after the JOINT sampled-grid/broadening convention.
- The checked `raw1/raw2` and `broad1/broad2` magnetic features and their reconstructed sum match the native combined `Ni_fm.xmcd` within printed precision. `ni_017_geometry.energy_audit()` validates this correspondence, original input files and the [001] spin-axis input.
- The two **XAS peak maxima** differ by **17.331 eV**, and their difference from the two older **nominal** map energies is approximately +21.279 eV (L3) / +21.248 eV (L2). This suggests a near-rigid **calibration offset**, **not** evidence of incorrect L3/L2 core assignment or proof of exact absolute excitation energies.
- Using the **magnetic extrema** instead gives 852.7−831.271 = **21.429 eV** and 870.0−848.698 = **21.302 eV**. Do not conflate these feature-specific shifts with the XAS-peak shifts or promise a uniquely determined alignment.

**Limit:** The saved core-energy inputs and JOINT data justify the internal assignment and relative splitting, not the **absolute experimental onset/edge position**. Ground-state/core-hole, screening, many-body terms, Fermi-level conventions, broadening and the experimental reference can affect calibration. The current workflow **does not shift** `Ni_fm.xmcd` and does not claim experimentally accurate absolute binding energies. If experimental alignment is later needed, preserve the raw axis and save an independent, common calibrated axis with reference/source/uncertainty.

**Tensor caveat:** The WIEN2k output provides circular polarization intensities, *not* complex Cartesian 2p-to-band transition dipoles. The `xmcd-effective` dipole tensor uses `N=(RP+LP)/2`, `D=(RP−LP)/2`, transverse `Txx=Tyy=N`, magnetic `Txy=i eta D`, `Tyx=−i eta D`, assumed `Tzz=beta N`, and `eta=beta=1` in this case. It is a **Hermitian XMCD-constrained proxy**, not a full ab initio MDFF or calibrated absolute cross section. [001] crystal magnetization is rotated into the selected experimental frame using `R T R^T`; reversal is applied in the crystal frame before rotation.

## 2. Why select minor-zone [017] and target (200)?

The magnetization of the underlying WIEN2k Ni case is along **cubic [001]**, as specified by `Ni_fm.inso` and corroborated in `Ni_fm.outputopup`. The nominal [017] beam axis makes only **arctan(1/7) ≈ 8.13°** with [001], unlike [710], which is perpendicular to [001]. Thus [017] is a useful **near-magnetization beam-direction geometry** while still tilting off a principal [001] zone axis to suppress many competing reflections.

The genuine oriented local frame is:

```text
x_local = [100]
y_local = [0, 7, -1] / sqrt(50)
z_local = [0, 1,  7] / sqrt(50) = [017]
m_crystal = [001]  ->  m_local = (0, -1/sqrt(50), 7/sqrt(50))
```

The zero-order Laue-zone rule is **k + 7l = 0**, alongside FCC allowed-reflection parity. **(200)** is allowed and perpendicular to [017]: `[017]·(200)=0`. The first off-row projected reflections lie at about **sqrt(51)/a = 2.027 cycles/Å**, so a minor-zone row dominates over some off-row scattering near the reference, although multiple beams remain in the physical model.

At **200 kV**, `a=3.524 Å`, the reference is the **exact paraxial (200) Bragg alignment**:
```text
theta_x = -7.116725439974256 mrad
theta_y = 0 mrad
s_200   = 0
```

This **does not** mean incident-zone-axis alignment, nor mathematically guarantee a pure two-beam wavefield. At 30 nm the `(000)+(200)` **exit** population is about 99.43%, but its **depth-averaged** population is 94.50%; competing modes reach **10.57%** at some depths, failing the documented strict 5% outside-pair criterion. Competing `(-200)` and `(400)` reflections matter. Therefore call it a **minor-zone exact-Bragg two-beam-like reference**, never a certified isolated 2BC.

The [017] project rotates the actual projected Ni IAM lattice/potential for both BW and FFT multislice; it does not simply relabel [001] diffraction. The potential is z-independent/projected rather than an atom-layer-resolved 3D specimen.

## 3. Exactly how the X/Y mistilts are set

Use *local* coordinates with the **fixed crystal [017] frame and fixed crystal [001] magnetization**:
```text
absolute theta_x = theta_Bragg,200 + delta_x
absolute theta_y = delta_y
theta_Bragg,200  = -7.116725439974256 mrad
```

Thus `(delta_x,delta_y)=(0,0)` is the exact-(200)-Bragg reference, **not** [017] zone-axis incidence. The **[017] zone-axis incidence** occurs at `delta_x=+7.11672544, delta_y=0`; a separate `delta_x=-7.11672544,delta_y=0` point is approximately (400) Bragg. The horizontal X scan contains **13** offsets (`−10:2:+10` plus these two special points); the Y scan has **13** (`−30:5:+30` at X=0); the coarse X/Y scan has **25** (`x=[−10,−5,0,5,10]`, `y=[−25,−10,0,10,25]`). Shared coordinates are computed only once, producing **43 distinct incident orientations**.

X mistilt primarily changes `s200`, whereas a local Y tilt leaves `s200` unchanged within the present paraxial convention (`g200,y=0`) but changes excitation of **off-row** reflections and the y-reflection symmetry of the wavefield. The projected zone-axis marker is `q_ZA=-k_incident,perp` in the transmitted-(000)-centered detector frame. The (000)/(200) points, Thales circle, and A/B aperture outlines stay fixed; **only ZA moves with incident tilt**. Thales geometry by itself is not a prediction of the strongest EMCD.

The existing default numerical study is 200 kV, 30 nm, 27 BW beams at cutoff 3.2 cycles/Å, FFT32, potential cutoff 2.2 cycles/Å, depth64, step≤0.04 nm, detector33 and fractional aperture weights. Both propagators use the same projected potential; the same energy-dependent tensor is contracted with each incoming depth coherence. It sums localized single-ionization contributions through specimen thickness but **does not** propagate the inelastic wave through the remaining specimen (no outgoing/double channeling).

## 4. What pictures to look at and how to interpret them

The **generated images are under the local working directory** `outputs/ni_017_high_mistilt_xy/`, generally ignored by Git. Their names below are **file paths**, not hosted GitHub images. Recreate them with the plotting workflow in the technical report; the same location contains the underlying numeric NPZ and per-case metadata.

| Question | Picture (relative to `outputs/ni_017_high_mistilt_xy/`) | What to look for |
| --- | --- | --- |
| How do magnetic and nonmagnetic contrasts vary in the **same** X/Y grid? | **`aggregate/emcd_xy_heatmaps.png`** | Signed magnetic asymmetry, signed nonmagnetic asymmetry, and relative shot-noise proxy on measured 5×5 grid points (not interpolation) |
| Do raw and postedge-corrected contrasts recover the magnetic signal? | **`aggregate/raw_corrected_xy.png`** | Compare corrected and raw asymmetry **against** intrinsic magnetic/even reference; correction is not the reference itself |
| Where is relative detectability highest? | **`aggregate/detectability_xy.png`** | `abs(D_mag)/sqrt(Sigma_ref)`; relative Poisson-counting proxy, not experimental dose-limited SNR |
| Are trends numerically reproducible? | **`aggregate/bw_ms_xy.png`** | Matched BW–FFT magnetic map differences, rather than magnetic intensity |
| Do candidates survive changing the scattering potential? | **`aggregate/potential_cutoff_controls.png`** | Sensitivity at matched control detector grid (17), **not** proof of convergence |
| How does breaking the vertical mirror symmetry affect even A−B? | **`scan_y/summary_figures/mirror_symmetry.png`** and **`scan_y/summary_figures/emcd_vs_y_mistilt.png`** | ±Y even contrast reverses sign; compare independent ±Y simulations |
| How does horizontal Bragg offset affect EMCD? | **`scan_x/summary_figures/emcd_vs_x_mistilt.png`** | Reference Bragg vs near-(400) / zone-axis incidence and changes in absolute signal and asymmetry |
| Does magnetic signal reverse across L3/L2; what does normalization do? | **`cases/x_p0_y_p0/virtual_detector_eels.png`**, **`cases/x_m6_y_p0/virtual_detector_eels.png`**, **`cases/x_p0_y_m25/virtual_detector_eels.png`** | Side-by-side full BW/MS A/B, reversal-odd/even, raw and corrected spectra (native DFT energy axis) |
| Where are magnetic/even angular features within a specific aperture? | **`cases/x_p0_y_m25/L3_angular_maps.png`** (and `L2_angular_maps.png`) | Local intrinsic odd/even/total maps vs A-supported raw/corrected contrast; note the common color scales and fixed Thales apertures |
| Which additional beams are activated? | **`cases/x_p0_y_m25/diffraction_pattern.png`** | Real hkl, depth-average vs exit intensity; compare `cases/x_p0_y_p0/diffraction_pattern.png` |

**Starting sequence:** open `aggregate/emcd_xy_heatmaps.png`, then `aggregate/raw_corrected_xy.png`, then the three representative `virtual_detector_eels.png` figures, then `scan_y/summary_figures/mirror_symmetry.png` and the diffraction maps. Read `high_mistilt_summary.csv` and `diffraction_summary.csv` for quantitative labels; do not estimate exact values from pixels. These "pictures" are calculated maps and EELS plots, **not experimental diffraction photos**. An experimental evaluation would require a calibrated diffraction image/4D-STEM tilt map, energy-calibrated EELS, reliable aperture centers, dose/background and thickness information.

## 5. Which signals are magnetic and which are nonmagnetic?

For each aperture `A` or `B`, compute spectra for magnetizations `+M` and `−M` (a model reversal, not a claim that both were measured). Define:

```text
M_A = (I_A,+ - I_A,-)/2       N_A = (I_A,+ + I_A,-)/2
M_B = (I_B,+ - I_B,-)/2       N_B = (I_B,+ + I_B,-)/2

D_mag      = M_A - M_B
D_nonmag   = N_A - N_B
D_raw      = I_A,+ - I_B,+ = D_mag + D_nonmag
D_corrected= I_A,+ - alpha * I_B,+

D_corrected = (M_A - alpha*M_B) + (N_A - alpha*N_B)
```

Here the `alpha` factor comes from the actual +M A/B integrals over **878–882 eV** *separately at each orientation and method*. A small nonmagnetic difference may be created by the correction itself when `D_nonmag≈0`. Thus **corrected EMCD must never be relabeled as intrinsically magnetic**. The intrinsic asymmetry uses the common reversal-averaged `Sigma_ref=N_A+N_B`; reported percentage `100*D_mag/Sigma_ref`. The detectability proxy uses `abs(D_mag)/sqrt(Sigma_ref)`, without experimental noise/dose calibration.

**Observed representative model results (BW, potential cutoff 2.2 cycles/Å, native magnetic features):**

| Offset `(delta_x,delta_y)` mrad | L3 magnetic asymmetry | L2 magnetic asymmetry | Interpretation |
| --- | ---: | ---: | --- |
| `(0,0)` | −0.380% | +0.615% | Exact (200) Bragg; mirror-symmetric intrinsic even difference ≈0 |
| `(−6,0)` | −2.553% | +4.147% | Largest **sampled** absolute magnetic difference, minimal even imbalance on Y=0 |
| `(0,−25)` | −2.724% | +4.416% | Largest **sampled** magnetic asymmetry and relative shot-noise proxy, but appreciable nonmagnetic imbalance |

Across the sampled grid the largest absolute intrinsic nonmagnetic asymmetry is **4.94%** at `(5,−25)` (L3). For `(0,−25)` at L3, `D_mag≈−0.005759` and `D_nonmag≈−0.002490` (relative model units). The nonmagnetic even signal obeys antisymmetry under reversing Y tilt within the projected, mirror-symmetric `beta=1` model; the magnetic signal need not obey the same symmetry because the magnetization direction is held fixed in crystal coordinates.

The observed postedge correction reduces error versus intrinsic magnetic difference at all **112 nonzero-Y method/edge comparisons** in this saved study, but **introduces artifacts on the Y=0 symmetry plane**. It is not universally an unbiased magnetic extraction.

## 6. Scientific limitations and reproducibility

The original data are **model outputs** (relative units), not validated measured Ni cross sections. The model uses a projected (z-independent) IAM elastic potential, single/incoming channeling only, circular-intensity-derived XMCD-effective dipole tensor rather than full complex DFT MDFF, fixed original virtual apertures, and no HOLZ/outgoing channeling/TDS/experimental energy calibration.

A matched BW/FFT difference of up to **0.6025%** across the coarse survey does **not** resolve physical-potential convergence. At exact Bragg, increasing cutoff from 2.2 to 3.2 cycles/Å changes the selected L3 magnetic difference by about **21.8%**; it also **reverses the ordering** of the `(−6,0)` versus `(0,−25)` absolute-signal candidates. These are **candidate orientations**, not a converged global optimum.

Reproduce from the repository root with your validated WIEN2k input files present in `data/wien2k_ni/`:

```powershell
$env:PYTHONPATH='src'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
python -m emcd_sim.ni_017_high_mistilt_xy --scan all
python -m emcd_sim.ni_017_high_mistilt_xy --scan all --plot-only
```

Full implementation, controls, file layout, provenance and test outcomes are documented in [NI_017_HIGH_MISTILT_XY.md](NI_017_HIGH_MISTILT_XY.md). See also [NI_017_MINORZONE.md](NI_017_MINORZONE.md) for the native-edge audit and the [710]/[017] orientation comparison.
