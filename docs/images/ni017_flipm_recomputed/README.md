# Recalculated Ni [017]: conventional A/B versus fixed-detector Flip-M

[Tutorial and numerical tables](../../TUTORIAL.md#part-vii-practical-ni-017-case-study) ? [Provenance](provenance.json) ? [Selected native-energy CSV](selected_native_L3_L2.csv)

Source: `outputs/ni_300kv_bragg_y15_full_recalculation/20261103T225908Z/` in local worktree `build/v070b1-unit-clean-main`, commit `3fdc9ab83e1aa3bc3629afab62b0c22a7a4adfe9`. The completed run evaluated 486 fresh production responses plus eight selected-energy convergence controls. No arrays from the historical study were inputs. Native selected values independently reproduce that study.

Twelve new primary documentation figures are rendered independently from the saved four spectra in the new study's `documentation_figures/raw_au/` and `documentation_figures/asymmetry_percent/` folders; the original run's figures remain unchanged: 6 x 7 inches, PNG 1800 x 2100 at 300 dpi, plus SVG. This directory contains optimized 900 x 1050 image previews and two 1500 x 1200 summaries. Full-resolution summary PNG/SVG files are also retained locally. Research arrays, checkpoints and full-resolution datasets are excluded from Git.

|Measurement|Raw a.u.|Normalized %|
|---|---|---|
|9 nm Conventional|[Preview](raw_au_01_9nm_conventional.png)|[Preview](asymmetry_percent_01_9nm_conventional.png)|
|9 nm Flip-M|[Preview](raw_au_02_9nm_flipm.png)|[Preview](asymmetry_percent_02_9nm_flipm.png)|
|30 nm Conventional|[Preview](raw_au_03_30nm_conventional.png)|[Preview](asymmetry_percent_03_30nm_conventional.png)|
|30 nm Flip-M|[Preview](raw_au_04_30nm_flipm.png)|[Preview](asymmetry_percent_04_30nm_flipm.png)|
|9 nm Magnetic A/B vs Flip-M|[Preview](raw_au_05_9nm_magcomponent_vs_flipm.png)|[Preview](asymmetry_percent_05_9nm_magcomponent_vs_flipm.png)|
|30 nm Magnetic A/B vs Flip-M|[Preview](raw_au_06_30nm_magcomponent_vs_flipm.png)|[Preview](asymmetry_percent_06_30nm_magcomponent_vs_flipm.png)|

**Primary GitHub example:** [Raw EMCD differences (a.u.)](summary_raw.png). **Supplementary:** [Normalized asymmetry (%)](summary_percent.png).

The primary raw a.u. curves are `D_conv = (M_A-M_B)+(N_A-N_B)` and `D_flip,A = 2*M_A`, with no percentage normalization. Conventional A/B has an energy-dependent nonmagnetic difference; ideal fixed-A Flip-M has a zero nonmagnetic **residual** even though `N_A(E)` remains nonzero. The supplementary percentage figures instead use `I_A(+M)+I_B(+M)` (A/B) or `I_A(+M)+I_A(-M)` (Flip-M); Advanced GUI diagnostics use `N_A+N_B`. These figures are post-processing, not a released GUI mode.

Native L3/L2 markers are 831.271/848.698 eV; the complete grid has 243 evaluated energies over 823.625?882.521 eV. There is no added energy shift, arbitrary smoothing or individual curve rescaling. The near-flat conventional nonmagnetic percentage is calculated, not imposed; its raw spectrum remains energy dependent.

Provenance records voltage, thicknesses, orientation, magnetization, ordered A/B detector centers, integration settings, finite ZOLZ support, XMCD hash, completion reports, limited depth/grid convergence, original and preview figure hashes, and independent algebra residuals. Hashes describe bytes; JSON/CSV hashes use LF in Git. PNG preview resizing changes pixels only. All 603 original manifest entries verified before publication. The old images and original provenance remain in [v070b1](../v070b1/README.md).

Reproduce the verification and documentation summaries from this repository root with `python scripts/research/publish_ni017_example.py` (NumPy, Matplotlib and Pillow required). This reads the completed local dataset and never calls a solver. The full grid is complete; convergence remains limited to eight selected-energy depth/grid controls, not all energies, basis/cutoffs or experiment.
