# EMCD-Sim User Manual

For the unpublished beta.2 Windows candidate, follow the current
[Quick Start](QUICK_START.md) and [Tutorial](TUTORIAL.md) for the 243-energy,
selected-97×97 workflow and unified Compute Resources controls. Historical
screenshots below retain their version labels. Advanced historical/source
references may require the corresponding-source kit or online repository.

[Home](../README.md) · [Installation](INSTALL_WINDOWS.md) · [Quick Start](QUICK_START.md) · [Tutorial](TUTORIAL.md) · [Index](INDEX.md)

This manual describes **v0.9.0-beta.1 Windows Research Beta**, a prerelease. Use the [release notes](RELEASE_NOTES_0_9_0_BETA_1.md) for evidence and remaining verification limits. Older v0.8 binaries retain their [tag-specific instructions](https://github.com/dingpengem/EMCD-Sim/blob/v0.8.1-beta.2/docs/USER_GUIDE.md).

Material owns Global/group target directions. The shared MDFF workspace is reached through **Material → 3D Structure Viewer… → Site groups → Configure MDFF…**. The selected Global/group context is explicit; it does not itself switch magnetic mode. MDFF target M is read-only. Full source-axis and tensor-frame declarations remain separate. Independent clean-PC/VM installation and Linux/macOS packaged support remain unverified.

> **Legacy magnetic results:** earlier released v0.6.1 packages used a superseded Born/MDFF convention. Preserve their raw arrays, source and convention; revalidate signed magnetic results before comparison. Loading a project does not update its physics. Missing convention metadata is unknown/legacy-unverified.

Use the [Quick Start](QUICK_START.md) for a small first run and the [Tutorial](TUTORIAL.md) for the physical workflow and equations. This manual is a reference, not a request to run a large study.

<a id="find-your-way-around"></a>
## 1. Interface and layout

The four familiar regions remain: upper-left **Settings**, upper-center diffraction preview/viewer, upper-right **EMCD Results**, and lower **Project Results**. Collapse sections, scroll panels, resize splitters, or use **Maximize / restore viewer/results**. File contains project actions; settings, results and calculation management stay in their panels.

| Settings section | Purpose |
| --- | --- |
| Material | Open/inspect CIF; 3D viewer, Site groups and MDFF workspace |
| Zone Axis & Diffraction | Orientation, target, tilt and Bragg alignment |
| Microscope & Sample | Voltage and thickness |
| Propagation Method | Single/Double; BW/MS; MS-specific settings |
| Shared Calculation Settings | Numerical support, energy/angular sampling and resources |
| Virtual Detectors | A/B positions, radius and visibility |
| Output Settings | Output controls; plot exports remain near Results |

Results include **Diffraction**, **EMCD Angular Maps**, **Virtual Detector EELS**, **Magnetic / Nonmagnetic**, **Calculation Information**, and additional saved diffraction/comparison views when available. Disabled views generally lack calculated data; enabling a display cannot manufacture missing maps or spectra.

Results controls wrap and the panel scrolls when its contents exceed the available height. Narrow angular views stack the maps while keeping their physical aspect ratio. EELS legends wrap in dedicated rows below the curves, sized from the displayed text; scroll the panel to reach lower plots when needed. Click a legend line or label to hide/show its complete curve across modeled energy windows. Resizing and figure export preserve that selection, and exported figures retain the full legend identification. The canvas heading retains the selected scope and actual energy; **Display details / diagnostics / export** provides the complete caption and figure toolbar. Figure exports include the full context at readable dimensions. Layout changes do not change data, color limits or normalization.

Global and Local Site Group results use the same primary plots: detector A/B EELS above magnetic/nonmagnetic A−B components, and the same paired angular-map display. **Signal Display** switches between raw intensity and conventional **EMCD Asymmetry (%)**; this percentage can include nonmagnetic diffraction asymmetry and is distinct from reversal-odd intensity. Local results start at **Total Results**. The compact spectrum selector adds Element, Group, and Group Comparison views from saved arrays; Group Contribution uses the total selected-atom denominator, while Group Mean is nonadditive. Angular maps have their own explicit **Angular result scope**: Total Results, Group Contribution (n/N), or Group Mean (per atom). The group/energy selector identifies the actual saved group, edge and energy. Total selections list each actual saved energy once, in energy order, with applicable edge/element labels. Group-origin aliases remain in optional details and exports. Distinct energies remain separate even if rounded labels or arrays match; labels use extra precision when needed. Independent windows are identified as modeled-channel aggregates. Older saved aliases restore by scope and actual energy; unavailable selections are reported rather than replaced with another energy. Spectral Group Comparison does not change angular scope. Group map colors share a range across saved groups/energies in the chosen units; percentages remain nonadditive. Additional raw/reversal-state quantities remain available in the spectrum selector. Unmodeled energy gaps are not connected. Source details, normalization definitions, diagnostics and exports remain under **Display details / diagnostics / export**. Presentation changes do not alter saved arrays. Previously accepted EXEs remain unchanged.

![Historical v0.7.0 Windows application with collapsible settings, diffraction viewer and results](images/v070b1/gui_overview.png)

*Actual native packaged EXE, using a deliberately small 1 nm, selected-energy acceptance profile. The plot shows two energy samples, not a full spectrum.*

## 2. Structure import

**File → New Project** starts with conventional FCC Ni (3.524 Å). **Material → Open CIF…** imports the actual ASE/CIF cell; **Inspect structure…** reports the cell, original indices and warnings. Do not silently replace a user's lattice with the historical reference cell.

The viewer can display structures beyond calculation eligibility. Ordered, fully occupied sites are required for the ionization calculation; disorder/partial occupancy is not silently approximated. Adaptive elastic factors support neutral Z=1–118, separately from MDFF eligibility. Legacy reference-Ni adapters retain their reference restrictions; explicitly declared generalized providers and Local groups retain their own validation. CIF import does not construct a material-specific magnetic response.

<a id="development-site-groups"></a>
### Site Groups, Material directions and MDFF acceptance

1. Import the CIF and open **3D Structure Viewer… → Site groups**. Automatic groups describe crystallographic orbits, with original ASE indices, Wyckoff/provenance and tolerance information. They assign neither M nor MDFF. Supercell display replicas refer to original atoms and do not create additional ionization sites.
2. Inspect membership. If magnetic inequivalence differs from crystallographic equivalence, select original atoms and use the existing group creation/assignment/removal controls to form disjoint magnetic subgroups. Renaming a group does not split its membership. No magnetic equivalence is inferred.
3. Choose **Global Magnetization Mode** or **Local Site Magnetization Mode**. Global retains its legacy physical interpretation. Local locks Global M and uses independently declared crystal-Cartesian directions; switching back preserves local drafts. Global-mode local rows are explicitly inactive, not evidence that the Global provider is missing.
4. Enable **Ionize** only for participating groups. Excluded atoms remain in the complete elastic crystal. For example, Fe-only loss from Fe₃O₄ uses N=24 selected Fe atoms, not all 56 atoms. Structural groups may remain unconfigured when excluded; active missing inputs must block Run by group name.
5. Select a whole group once to edit its direction. **Update direction** stages the group-wide draft; inspect **Accepted M** versus **Draft M (unapplied)**. Arrows are normalized directions, not calibrated moment magnitudes. Direction alone does not define an anisotropic tensor frame.
6. Choose **Configure MDFF…** in the explicit Global/group context. Supply compatible models/sources, units/scales, full frames, magnetic-state declarations and modeled energy windows. Validate sources and required acknowledgements, inspect preview, then **Done** and outer **Apply and Close**. Done/preview alone does not accept Material settings.
7. Direction and provider are accepted atomically. Failed Apply preserves the old accepted configuration and the editable draft; Cancel discards unapplied edits. A supported reversal selects the explicitly validated physical pair member. No missing pair, tensor values or arbitrary frame rotation are invented. Unsupported fixed-source Z→X changes remain rejected; use the group's editor or a compatible source.
8. Save/Open preserves accepted directions, provider selection, frames, source identity and provenance; recalculation uses the restored configuration. Pending configured-group edits must be Applied or Cancelled before saving. General tensor rotation and magCIF remain future work.

## 3. Diffraction settings

This Windows release bundles Adaptive Dirac–Padé 2026 neutral Z=1–118 factors for ordered multi-element **elastic** diffraction: see [neutral-atom elastic providers](ELASTIC_ATOMIC_FACTORS.md). The provider selector defaults to Adaptive for new calculations, including Ni; select **Ni Lobato 2014 (legacy compatibility)** to reproduce historical Ni studies. Old projects without a provider field restore Lobato explicitly. Only the external legacy option requires `EMCD_SIM_LEGACY_ATOMIC_TABLE`; its absence does not break bundled-provider calculations. The previous v0.7.0-beta.1 binary is preserved and does not contain this feature. The historical Ni providers retain their Ni eligibility gates; generalized sources require the separately declared element, edges, state, frame and eligible equivalent sites.

In this release, signed three-index hkl labels refer to the ASE-imported CIF cell shown in the structure summary. No automatic primitive reduction is performed. A transformed cell needs an explicit index-basis transformation; four-index Miller–Bravais input is unsupported. [001] hexagonal patterns use the actual nonorthogonal reciprocal metric. BCC Fe (110) belongs to [001] by the zone law; CsCl (100) survives because its species factors differ. Partial/disordered occupancies remain unsupported. Oversized reciprocal searches fail with a diagnostic rather than silently truncating support.

**File > Save Elastic Project** saves the current elastic preview to a new checksummed directory with its provider, numeric structure and diffraction arrays. **File > Open Elastic Project** opens those saved arrays in a read-only diffraction window without changing current input controls or running a solver. Full EMCD projects retain their existing separate workflow. Applying saved EMCD settings restores the recorded provider; missing or mismatched provider provenance blocks rerunning but leaves saved results viewable. Changing providers invalidates a preview. Existing verified automatic Ni convergence profiles apply only to Lobato; the new provider requires configuration-specific convergence checks.

**Tilt X/Y (mrad)** are absolute local transverse incidence parameters relative to the nominal zone. Actual voltage and tilt determine excitation errors. They are not a calibrated mechanical holder-angle transformation. **Tilt step (mrad)** selects spin-box increments (0.01, 0.1 or 1 mrad); changing the step alone neither changes tilt nor starts a scan/solver. Record the actual X/Y values for reproducibility.

- **Reset to zone axis** sets zero X/Y tilt.
- **Reset to reference geometry** restores **[017]/(200), Full finite ZOLZ**, zero Y, Y-locked target Bragg alignment and Thales apertures at the current voltage. It is not a generic reset for another orientation.
- **Align to selected Bragg** aligns the current target subject to **Lock for Bragg alignment → None/X/Y**. Use Y lock to preserve a specified perpendicular mistilt.
- **Preview diffraction** computes elastic intensities for current inputs. It is separate from **Run EMCD / EELS**.

Inspect `s_g`, retained hkl, q and exit populations in **Diffraction details**, the **Diffraction** table and **Calculation Information**. The table can describe the last completed preview while new geometry is stale. An exact target `s_g = 0` is not evidence that other beams are absent.

<a id="change-zone-axis-bragg-alignment-and-mistilt"></a>
## 4. Zone axis and reflection indexing

Expand **Orientation / ZA options**; enter three signed integers in **Nominal zone [uvw]** and **Target (hkl)**, then **Apply orientation / target**. The target must be nonzero, satisfy the zone condition and belong to the allowed retained basis. For cubic Ni, FCC reflections have all-even or all-odd indices. A too-small cutoff can exclude a valid target.

|Diffraction choice|Interpretation|
|---|---|
|Full finite ZOLZ|Finite allowed zone-plane basis within the beam radius|
|Ideal 000 + target|Explicit ideal two-beam truncation|
|Explicit target systematic-row approximation|Row-restricted beams/potential; distinct from the ideal two-beam choice|

Do not combine ideal two-beam and explicit row restriction. The general orientation engine supplies signed indexing and the same physical crystal frame to BW/MS. Five orientations have bounded acceptance: [001], [017], [117], [111], [710]. Other supported directions remain subject to finite-search, target, resource and FFT-support checks; unsupported configurations raise errors rather than falling back to another crystal orientation.

<a id="research-ni-117--2-20"></a>
### Ni [117] and other research orientations

Use zone `1 1 7`, target `2 -2 0`; do not substitute (220). The target lies in the ZOLZ and is FCC-allowed. Default potential cutoff 2.5 Å⁻¹ retains no off-row [117] harmonics, so the visible basis alone does not imply a full multibeam potential. Read the potential-support warning and inspect actual harmonics. Coarse [117] angular sampling can produce significant errors. [111] lower-support quantitative convergence remains uncertified. See the [117 validation](NI_117_FINAL_SYMMETRY_VALIDATION.md) and [generalized merge review](GENERALIZED_MULTISLICE_MERGE_READINESS.md) before interpreting research cases.

## 5. Interactive diffraction visualization

The origin cross is **transmitted (000)**. The yellow star is the **projected crystallographic ZA**, `q_ZA = −tilt_rad/λ`, in the 000-centered coordinates. It generally differs from the origin under tilt. Read **ZA qx/qy (Å⁻¹)** for off-screen coordinates.

|Overlay|Definition|Style in the live viewer|
|---|---|---|
|Thales|Center G/2, radius norm(G)/2; diameter 000–target|Teal dotted, width 1.2, alpha 0.75|
|ZOLZ Laue|Center q_ZA, radius norm(q_ZA); zero-excitation-error locus|Darkorange dashed, width 1.8, alpha 0.95|

The Laue circle is above Thales but below diffraction spots/markers/apertures. Use **Show ZOLZ Laue circle** to toggle it. At exact target Bragg both circles pass through 000 and G, but they need not coincide when there is off-row tilt. Zero incident tilt gives a zero-radius Laue locus. Neither overlay is an intensity contour or a guarantee of magnetic symmetry.

![Historical v0.7.0 elastic diffraction preview with indexed reflections and overlays](images/v070b1/diffraction_preview.svg)

*SVG exported by the accepted EXE before dragging, with trailing whitespace cleaned in the documentation copy only. Geometry/styles are unchanged. This is an actual elastic preview, not an experimental diffraction pattern.*

**Click mode** offers **Select reflection**, **Set projected ZA**, **Move detector A**, **Move detector B**. Set-ZA mode supports click and continuous drag. Release uses the final valid position; an out-of-axes/invalid release keeps the last valid position. Dragging removes cached intensity coloring and marks the prior preview stale; it starts no computation worker and does not change detectors. Request **Preview diffraction** to obtain current intensities.

Matplotlib Pan/Zoom takes priority over geometry clicks. **Show full basis** expands to the selected beam-cutoff bounds and changes to **Restore previous view**; the second click restores saved limits. Geometry changes invalidate incompatible stored views. This is a view operation, not a numerical-setting reset. A large Laue circle can extend beyond the basis bounds; pan/zoom or inspect numeric ZA coordinates rather than moving it artificially.

## 6. Detector positioning

Numeric A/B qx/qy and **Radius (Å⁻¹)** define physical circular apertures. **Restore Thales A/B** uses `G/2 ± (−G_y,G_x)/2` in target-aligned coordinates. A is drawn solid, B dashed. **Show physical A/B apertures** changes visibility only; it does not disable integration.

Integration is `sum(weights * intensity) * dq²` using fixed fractional circle/pixel weights. All reversal states share the same physical apertures. Boundary subpixels improve circle area weighting but not the resolution of a varying intensity field. Fully contain both apertures inside **Map halfwidth**. A manually moved non-mirrored pair is valid for detector spectra but can disable symmetry-dependent diagnostics.

## 7. Magnetization settings

Edit target M in **Material → 3D Structure Viewer… → Site groups**. Global mode uses one accepted crystal-Cartesian direction. Local mode uses each participating group's direction and locks Global M. The MDFF workspace inherits the selected target read-only; source quantization axes and complete tensor frames remain independent declarations.

Global reversal exchanges every participating provider's complete physical +M/−M pair together. It does not replace an AFM/noncollinear configuration with uniform M or assume reversal is complex conjugation. Synthetic ferrimagnetic/AFM configurations do not by themselves establish calibrated moments or a required detector EMCD sign.

## 8. MDFF models

**Configure MDFF…** offers **XMCD-constrained MDFF**, **Atomic Ionization MDFF**, and **Manual tensor**. Sources/models must validate for the actual element, sites, axis/frame and energy coverage. Independent providers may serve different groups of the same element. See [construction details](MDFF_WORKFLOWS.md).

XMCD is an axisymmetric effective response, not complete complex ab-initio MDFF. Atomic is the declared cubic independent-electron Sc–Zn L2,3 model with synthetic electronic defaults. Manual tensors must be Hermitian PSD with explicit units, normalization, frames and reversal assumptions. None infers magnetic order, oxidation state or calibrated material spectroscopy from CIF.

### Historical Ni controls (compatibility reference)

The following descriptions concern the retained historical Ni route, not the full current Atomic editor or Manual models. They do not restrict the generalized editor to Ni or imply that historical implementation-era acceptance applies to every new workflow.

**XMCD-constrained (WIEN2k):** select a **Five-column XMCD** file, then **Validate source / native features**. This reports source SHA256, range/features and available audit information. Check **I declare M axis, RP/LP convention and edge assignments** only for a verified source. `eta` controls dichroic sign/scale; `beta` controls the unmeasured longitudinal response. Invalid/non-positive tensor configurations are rejected.

The bundled source has native range **823.625–882.521 eV** and selected magnetic samples **831.271/848.698 eV**. These calculated energies are not experimentally calibrated Ni thresholds. The five-column source does not supply the complex site/band/k-resolved transitions needed for full DFT MDFF. **Preview source / tensor spectrum...** inspects the model; it is not an EMCD calculation.

<a id="atomic-ionization-mdff"></a>
**Atomic ionization (Ni 2p -> 3d):** non-DFT approximation with L3/L2 energies, 10Dq, exchange, hole counts, Gaussian width and advanced radial settings. Crystal [001] magnetization only is supported in this model. It is not a quantitative metallic-Ni spectral model. Its nominal L3/L2 parameters do not shift or calibrate the XMCD source.

## 9. Single and Double Channeling

|Model|What is included|
|---|---|
|Single Channeling|Incoming elastic propagation followed by localized inelastic scattering; no outgoing elastic diffraction|
|Double Channeling|Incoming propagation, depth-distributed localized inelastic transitions and outgoing elastic propagation at incident energy minus actual energy loss|

They are distinct approximations, not independent experimental switches. Both retain a single inelastic event; Double is not double ionization/plural scattering. Their thickness trends can differ because post-loss propagation changes the depth-dependent detector response. Maxima observed at sampled thicknesses are not automatically continuous/global optima.

<a id="bloch-wave-fft-multislice-and-numerical-settings"></a>
## 10. BW and FFT Multislice

**Propagation Method** selects **Bloch-wave**, **FFT Multislice** or **Both (BW / MS comparison)**. BW uses a finite reciprocal eigenproblem; MS uses a structure-derived projected ZOLZ potential and FFT propagation. Single/Double apply to both. BW/MS comparisons require matched physical structure, frame, support, detector, MDFF, energy and depth conventions.

MS-only controls are in panel E; they hide/disable appropriately for BW and retain their values for MS/Both. Invalid FFT bandwidth/support produces an explicit error. MS may propagate additional FFT harmonics beyond the retained diffraction/MDFF basis. Agreement is neither independent basis convergence nor experimental validation. Atomic-3D potential propagation is not a released backend.

<a id="development-source-shared-and-solver-specific-settings"></a>
<a id="automatic-and-manual-numerical-settings"></a>
## 11. Numerical settings and independent grids

**General settings (editable)** exposes explicit numerical controls. Retained reference/legacy selection modes have their documented narrow meaning; a preset name is not convergence evidence. Saved effective values survive restoration. The angular preset caption names a preset only when its defining values match; otherwise it reports, for example, **Custom – 9×9**, without applying 97×97.

| Control | Normal starting value | Meaning |
| --- | ---: | --- |
| Beam / MDFF basis cutoff | 2.5 Å⁻¹ | Retained diffraction/MDFF beam support |
| Potential Fourier cutoff | 2.0 Å⁻¹ | Elastic potential harmonics; separate from beam radius |
| Angular / detector grid | 97×97 | Requested physical q samples for maps and detector integration |
| Energy sampling points | 241 | Uniform request per modeled window, plus exact selected energies |
| Depth integration nodes | 64 | Depth quadrature/coherence samples |
| Aperture boundary subpixels | 64 | Fractional detector-boundary area integration |
| FFT grid | 32×32 starting mesh | Internal MS potential/wave mesh; geometry can require larger support |
| Max slice step | 2 nm | Upper bound on propagation substeps, not guaranteed actual step |
| Memory budget | 2048 MiB | Estimated process-peak admission allowance |

For depth interval `t/(N_depth−1)`, MS uses `ceil(interval/max_step)` substeps. Record effective dimensions, actual step, beam count and detector sampling. Reducing angular queries does not reduce the internal FFT mesh. These starting values are not universal scientific recommendations.

Wheel scrolling over focused parameters or closed selectors does not edit them; typing, keyboard editing and explicit step buttons remain available. Plots and the 3D viewer retain their intended wheel interaction.

## 12. Worker parallelism and resource safety

**Parallel Workers → Automatic (Recommended)** applies existing CPU/memory policy; **Manual** requests 1–4 outer detector workers. Single Channeling has no parallel detector executor and uses one. Double Channeling reuses incoming/outgoing work across groups. Four workers are not universally faster.

For supported normal-threading OpenBLAS runtimes, execution automatically sets and verifies one internal thread in both NumPy and SciPy, then restores prior limits after workers join. Normal users do not need BLAS/OpenMP environment overrides. Unsupported control remains a visible rejection, not a fabricated verified state or silent manual-worker reduction.

**Resource estimate** includes current RSS, concurrent reservations, allocation margin and reserve, and checks the selected budget plus the existing available-RAM guard. Automatic workers may be limited by admission; manual requests are rejected rather than silently coarsening physics or changing solvers. Admission is not convergence or a universal native-stability guarantee.

Progress reports the current stage, completed response batches/depth planes where available, elapsed time and a busy state. Reduction/integration follows response completion; an elapsed timer alone is not completed work. **Cancel** is cooperative; wait for owned workers to stop and the GUI to return idle before running again.

<a id="development-source-energy-dependent-angular-sampling"></a>
<a id="energy-sampling"></a>
## 13. Energy sampling and angular evaluation

**Energy sampling** independently offers:

- **Entire energy range → uniform sampling** (default): request 241 points in each declared modeled source window and insert exact selected samples. Actual merged count depends on windows and existing coincidences; 241 becoming 243 is an example, not a rule.
- **All native source energies**: retain supported native source samples and valid selected energies.
- **Selected energies only**: evaluate only declared selected samples. Two points are not a resolved white-line spectrum.

Provider coverage is checked within each participating channel's required window. Excluded/unmodeled channels are distinct from missing data. Do not extrapolate, invent spectral tails, or connect unsupported gaps. Output is a modeled partial core-edge spectrum, with original relative amplitudes.

**Full angular maps at selected energies** evaluates the full angular grid only at distinct selected energies and detector-support coordinates elsewhere. With maps off, all energies use nonzero fractional-detector support. This applies to BW/MS Single and Double. **Full angular field at every energy (advanced)** explicitly requests full-grid work everywhere; only selected maps are retained. Full/native spectral sampling does not enable that option.

The counter is unique energy–detector-coordinate work, not FFT grid cells or group/magnetic-state contractions. For constant active support it is `N_selected*N_grid + (N_energy−N_selected)*N_detector_support`. Equal-energy group aliases do not duplicate a response. Excluded channels may require no response; metadata records actual evaluations. Existing source interpolation is not angular/spectral-response interpolation.

<a id="first-simulation-fcc-ni-017-exact-200-bragg"></a>

## 14. EELS and EMCD calculation

The [Quick Start](QUICK_START.md) supplies a small Manual Ni example. In general: set crystal/frame and physical geometry → set fixed apertures → validate model/axis → choose channeling and propagation → review effective numerics/resources → **Preview diffraction** → **Run EMCD / EELS**.

Both reversal tensors are computed using the same geometry, not by moving detectors. Raw `I_A_plus`, `I_A_minus`, `I_B_plus`, `I_B_minus` are retained. In Both mode, finish one solver before preparing the other; do not treat an interrupted/failed run as completed evidence. Numerical selection, source verification, memory and unsupported-configuration errors are reported rather than bypassed.

**Cancel** requests cooperative interruption. Wait for idle/acknowledgement before another Run. Large native operations can bound responsiveness; the packaged acceptance has specific active-worker evidence, not a universal timing guarantee. Closing while busy requests cancellation and defers closure; close again after idle if needed. Previously completed results remain separate from the interrupted calculation. The GUI does not promise automatic resumption of arbitrary unsaved jobs from per-energy research checkpoints.

<a id="read-angular-maps"></a>
## 15. Angular maps

The maps use stored physical q samples; display zoom and nearest-pixel rendering do not add numerical resolution. **Angular Map Resolution** offers **Quick Preview - 33x33**, **Standard - 97x97**, **High Resolution - 193x193**, and **Custom**. The caption follows the effective grid when opening a project, selecting a calculation, or editing numerical settings: a 9×9 grid displays **Custom – 9×9**, without applying a preset or changing the saved grid. Named angular presets describe only the matching angular grid, not depth or FFT sampling. In Manual, inspect **Angular / detector grid points (odd)** and halfwidth. Refining a saved map requires a new explicitly configured calculation, not image enlargement.

The primary **Raw (a.u.)** angular view shows magnetic and nonmagnetic **mirrored-point differences** at `q=(qx,qy)` and `q′=(qx,−qy)`. **EMCD Asymmetry (%)** uses `100*[I_plus(q)−I_plus(q′)]/[I_plus(q)+I_plus(q′)]`. Detector outlines are overlays; they do not limit the full field. These are not finite-aperture detector ratios.

Advanced fields distinguish `I_mag=(I_plus−I_minus)/2`, `I_nonmag=(I_plus+I_minus)/2`, total +M intensity, paired differences and post-edge diagnostics. An antisymmetric paired difference is not evidence that the **original raw magnetic map** obeys mirror antisymmetry. Crystal magnetization, mistilt and multibeam geometry matter.

![Actual 9x9 native acceptance map showing magnetic and nonmagnetic mirrored-point differences](images/v070b1/angular_smoke.png)

*Deliberately coarse 9×9, 1 nm packaged acceptance result. It demonstrates field/coordinate presentation, not research-quality sampling or physical convergence. Current full maps retain their actual sample count.*

Missing full-field data disables/unavailable fields; it is not reconstructed from detector spectra. Unsupported mirror coverage produces a diagnostic instead of fabricated values. Undefined percentage pixels remain masked/gray. To calculate a detector ratio, integrate raw A/B intensities first; never average pixel percentages.

<a id="signal-definitions-in-060"></a>
<a id="signal-definitions-in-061"></a>
<a id="interpret-percentages"></a>
## 16. Raw and normalized signal definitions

Let `ap=I_A(+M)`, `am=I_A(−M)`, `bp=I_B(+M)`, `bm=I_B(−M)` at one energy:

```text
N_A=(ap+am)/2; M_A=(ap-am)/2
N_B=(bp+bm)/2; M_B=(bp-bm)/2
D_mag=M_A-M_B; D_nonmag=N_A-N_B
D_conv=ap-bp=D_mag+D_nonmag
D_flip,A=ap-am=2*M_A
```

|Observable|Definition and actual scope|
|---|---|
|GUI Raw components|Signed `D_mag`, `D_nonmag` in original a.u.; not separately peak-normalized|
|Conventional / PRB-compatible asymmetry|`100*(ap−bp)/(ap+bp)`; default **EMCD Asymmetry (%)**; may include nonmagnetic imbalance|
|GUI advanced magnetic/nonmagnetic diagnostics|`100*D_mag/(N_A+N_B)` and `100*D_nonmag/(N_A+N_B)`; common even denominator, **not** the conventional denominator|
|Conventional percentage contributions, tutorial case|`100*D_mag/(ap+bp)` and `100*D_nonmag/(ap+bp)`; these sum to the conventional percentage|
|Fixed-detector Flip-M A, derived from exports|`100*(ap−am)/(ap+am)`; own denominator; raw signal is full `2*M_A`|
|Mean-normalized contrast|Replacing a sum denominator with half that sum doubles the percentage; label as a different convention|

The main **Signal Display** offers **Raw (a.u.)** and **EMCD Asymmetry (%)**. Extra legacy/relative views are under **Advanced Diagnostics**; there is no default four-curve common-denominator/Flip-M panel. The [tutorial](TUTORIAL.md#part-vi-conventional-emcd-versus-flip-m) shows how to derive the requested measurement quantities from raw data without changing physics.

The PRB scalar benchmark is a separately labeled raw +M A/B readout with selected-energy/edge controls. It does not establish quantitative reproduction of a literature figure; geometry, source, energy/collection settings and approximations must match independently.

Legacy advanced **EELS Peak (%)** is another presentation normalization: a fixed `max_E in edge window [N_A+N_B]` reference, not an energy-by-energy difference/sum asymmetry. Its shared versus independent reference choices and **Peak windows (native eV)** must be recorded; independent peaks can conceal real amplitude differences. These controls do not alter raw arrays or solver-comparison metrics and are not used in the tutorial's case-study figures.

The released EELS percentage helper masks nonpositive/nonfinite denominators and those below `1e−8 × positive-finite P95(denominator)`; maps use `1e−6`. Invalid support remains NaN/gray. Record actual export metadata. The advanced 9/30 nm study used a separately documented maximum-based `1e−12` mask; do not imply that criterion is a new GUI default. Percentages alone are not detectability or shot-noise SNR.

<a id="read-virtual-detector-eels-and-post-edge-correction"></a>
## 17. Magnetization reversal and decomposition

Reversal-even and reversal-odd are defined by the four raw spectra; preserve the identity `D_conv=D_mag+D_nonmag`. Fixed-detector Flip-M A has magnetic contribution `2*M_A` and exactly zero nonmagnetic residual under identical geometry and nonmagnetic conditions within the ideal model. The underlying `N_A(E)` remains nonzero. It is a different measurement from magnetic A/B; its magnitude can be larger or smaller. Real drift/background/counting variance requires separate experimental modeling.

**Advanced post-edge diagnostics → Enable post-edge A/B correction** derives a +M A/B scaling from **Window start/end (eV)**. It does not change the MDFF, propagation or raw spectra. Its corrected contrast is **not intrinsically magnetic**; processed magnetic bias and residual even terms must be inspected separately. A selected-energy run may not contain the post-edge window and can report correction unavailable. Record the window, scale factors and definitions instead of calling every corrected signal magnetic.

That optional control is retained here as a historical v0.8 reference. **Dev4 retires it from the active GUI:** new requests always disable it. Opening a legacy enabled configuration shows a notice and disables only the working flag; Save is required to change the project file. Historical result arrays/settings remain unchanged. See the [development workflow](MDFF_WORKFLOWS.md#development-group-direction-workflow) for preview eligibility, model previews and current controls.

<a id="project-management"></a>
## 18. Project management

**File → New Project / Open Project… / Save / Save As… / Close Project** manages complete multi-calculation projects, including uncalculated accepted configuration. Use Save As for a separate study and preserve the entire folder. Portable editor attachments and source identity are retained where supported; arbitrary external sources are not automatically embedded. No manually edited JSON is required.

After calculation, **Keep as New Calculation** preserves earlier runs. Replacing/deleting a run requires the corresponding explicit action. Saved arrays remain viewable when an external source is missing/changed, but rerun must remain blocked until the correct source validates. Opening a project does not upgrade its physics or source declarations.

<a id="save-reopen-and-reconnect-inputs"></a>
Current inputs and saved results remain separate. A real input change marks the displayed result stale; reverting an exactly supported comparison restores matching status. Insufficient historical comparison evidence is **unavailable**, not automatically stale or matching. Read-only viewing does not change original arrays. Pending configured Material/MDFF drafts must be Applied or Cancelled before save/run.

## 19. Calculation history and comparisons

The lower **Project Results** panel lists runs from the active project. **View Results** displays arrays; **Restore Settings from Selected Run…** explicitly changes working inputs; **Delete Selected Calculation…** removes that run from the working project, committed on Save. Preserve independent copies before deletion.

Select exactly two distinct active-project runs for **Compare Calculations**, a separate resizable dialog. Review physical/numerical differences, normalization and common-scale choices. More actions remain near history, not duplicated across top-level settings menus. Comparing or switching Total/Element/Group views does not calculate new science.

<a id="compare-two-conditions"></a>
There is no general automatic thickness/convergence sweep in this workflow.

<a id="export-figures-and-data"></a>
## 20. Export formats

Use the corresponding Results figure toolbar and **Display details / diagnostics / export** for figure/data exports; no duplicate top-menu workflow is required. Export the displayed Total/Element/Group/Comparison selection without recalculating. CSV retains numerical precision, signal definitions, source/magnetic metadata, actual energies and active/excluded channel information. Group Mean is per group atom; additive Group Contribution and Element contributions use Total's fixed selected-atom denominator. Do not peak-normalize independent sources for a scientific comparison.

Figure export preserves full context and readable dimensions. Advanced existing NPZ/project exports retain original arrays and provenance. Unsupported windows remain unmodeled; no spectral interpolation across gaps or invented tails is added. Keep the complete project for restoring configuration and multiple calculations; a figure or CSV alone is not a project backup.

## 21. Troubleshooting

|Message/symptom|Interpretation and next step|
|---|---|
|Run disabled / source changed|Read source validation/declaration and rerun requirements; restore the checksum-matching source or configure a new verified source explicitly.|
|Unsupported material/geometry|CIF inspection does not supply a Ni MDFF for arbitrary structures. Check zone/target selection and supported model bounds.|
|FFT mesh does not contain common hkl / support error|The mesh/bandwidth is inconsistent. Review explicit FFT and potential/basis settings; no [001] or row fallback is applied.|
|No off-row potential harmonics|The chosen potential cutoff omits those couplings; merely displaying off-row basis positions does not add them.|
|Coarse sampling / [111] warning|Configuration-specific numerical uncertainty remains. Refine independently and preserve failed checks.|
|Coarse maximum slice step warning|Advisory split-step accuracy risk, not a forced clamp or proof of failure; inspect actual step and test smaller values.|
|Memory admission rejected / unsafe workers|Budget/available RAM or execution policy prevents admission. Do not silently alter physical settings to call the same case successful.|
|Stale preview / gray geometry|Inputs changed; request a new **Preview diffraction**. The last table/result is not automatically current.|
|Angular maps unavailable|Maps were not computed or mirror support is invalid; genuine full-field calculation is required.|
|Legacy convention warning|Preserve old arrays; opening is not sign/convention revalidation.|

For startup/security/log paths, use [installation troubleshooting](INSTALL_WINDOWS.md#troubleshooting-and-data-locations). Runtime logs default to `%LOCALAPPDATA%\EMCD-Sim\logs`. Include version, source/convention, requested/effective settings and the exact error when reporting a problem.

<a id="scientific-limitations-and-responsible-interpretation"></a>
## 22. Scientific limitations and convergence

The implemented model uses projected real IAM, finite ZOLZ support, localized single inelastic events and the documented energy-dependent but branch-frozen longitudinal transfer approximation. It is not a genuine atomic-3D potential, full HOLZ, comprehensive TDS/absorption, physical CBED/convergent-probe scan, complete DFT MDFF, domain/equilibrium-magnetization or calibrated detector/noise model.

Check actual structure, frame, signed hkl, magnetization and detector geometry first. Then separate beam-basis, potential-cutoff, FFT, depth/step, angular/aperture and energy-sampling sensitivity. BW/MS agreement tests matched approximations, not every independent convergence direction. Existing [111] lower-profile and historical detector-grid failures remain explicit; no threshold is relaxed by this documentation. A successful run is not a claim of quantitative Ni EMCD at untested conditions.

Keep raw reversal-even/odd fields separate from paired maps and normalization. Exact target Bragg is not physical beam isolation; a Thales circle does not enforce uniform signal or raw magnetic antisymmetry. Native energies, absolute handedness and arbitrary intensities require independent experimental calibration. Mean- and sum-normalized percentages differ by a factor two. Experimental SNR requires a count/dose/efficiency/background/noise model and correct variance propagation for the measurement estimator.

Independent clean-machine Windows installation remains untested. Linux/macOS are not certified by this candidate. General beam-basis and complex-condition BW/MS convergence remain incomplete; continuous-depth localized ionization and synthetic/effective tensors do not establish quantitative Fe₃O₄/NiFe₂O₄ spectra or magnetic-moment accuracy. General tensor rotation and magCIF remain absent. See the candidate release notes for scoped evidence and incomplete broad verification.

<a id="what-the-application-calculates"></a>
<a id="forward-born-convention-correction-and-historical-results"></a>
## 23. Version compatibility and provenance

Current convention is **forward_born_dagger_g_minus_h_v1**, with `Re Tr(RT)`, conjugated forward transition modes and corrected Double site phase. Earlier same-index signed results cannot automatically be combined with it. Some intermediate corrected source commits still had old version labels, so exact commit/convention metadata takes precedence. Keep unknown metadata unknown; never relabel old arrays as corrected.

Current candidate identity is **v0.9.0-beta.1 / 0.9.0b1 / 0.9.0.1**; exact committed source is embedded in `_internal/build_info.json` and the existing manifest. It is not published. See [candidate notes](RELEASE_NOTES_0_9_0_BETA_1.md). The table below preserves the historical published package identity.

|Identity|Historical published Windows package|
|---|---|
|Display / Python / Windows numeric version|v0.8.1-beta.2 / 0.8.1b2 / 0.8.1.2|
|Release tag target|`88dc9ecaed4871043c96a6aa05f0972e23b3b93d`; see [beta.2 release notes](RELEASE_NOTES_0_8_1_BETA_2.md)|
|Binary source|`88dc9ec`, matching the v0.8.1-beta.2 tag target|
|Windows verification|21 focused packaging/safeguard checks and native EXE workflow passed; no final full-suite rerun; see [recorded scope](RELEASE_NOTES_0_8_1_BETA_2.md#validation-evidence-and-scoped-exception)|
|Portable ZIP SHA256|See SHA256SUMS.txt on the [v0.8.1-beta.2 release](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.8.1-beta.2)|
|Physics compatibility|Ni event kernels unchanged; new calculations use Adaptive elastic factors|

Five native orientations, eight exact scientific comparisons, eighteen worker/cancellation scenarios and native overlay/export tests passed within their recorded profiles. These are bounded, partly overlapping inventories, not universal certification. Those earlier inventories refer to v0.7.0. See the [v0.8.0 release](https://github.com/dingpengem/EMCD-Sim/releases/tag/v0.8.0-beta.1), [release notes](RELEASE_NOTES_0_8_0_BETA_1.md) and [Windows acceptance](https://github.com/dingpengem/EMCD-Sim/blob/main/docs/WINDOWS_0_8_0_BETA_1_ACCEPTANCE.md); the [v0.7.0 acceptance](WINDOWS_ZOLZ_97B2220_CANDIDATE_ACCEPTANCE.md) is preserved. Historical acceptance/release notes retain their milestone-specific “not published” statements; the public release entry is authoritative for current publication state.

<a id="validated-ni-017-8-nm-double-example"></a>
<a id="complete-200-kv-thickness-workflow"></a>
### Historical study walkthroughs

The earlier 8 nm, 200 kV walkthrough remains in the [pre-overhaul manual at its immutable source revision](https://github.com/dingpengem/EMCD-Sim/blob/08d04fc35fca2071cc7e73af0aaa1de45e49a3f4/docs/USER_GUIDE.md#validated-ni-017-8-nm-double-example). It is not the small current Quick Start. The completed 200 kV thickness and corrected 300 kV studies are separate datasets; neither is recalculated or relabeled here. The [new tutorial case study](TUTORIAL.md#part-vii-practical-ni-017-case-study) reuses verified existing 9/30 nm spectra with explicitly different percentage definitions.

Historical development, validation reports and older galleries remain linked in the [Documentation Index](INDEX.md). Planned/experimental features must not be treated as available merely because a source or architecture document exists.

## Generalized sources in v0.8.1-beta.1

The following describes the Part 1B source/candidate workflow. Its acceptance
status and exact candidate identity are recorded in
[the consolidation report](GENERALIZED_CODE_CONSOLIDATION_0_8_1.md); it does not
alter the historical published binary or scientific examples.

The three MDFF choices remain visible for every crystal. **XMCD-constrained MDFF**
reads the original five-column XAS/XMCD file directly. Outside historical Ni,
declare the file's element/edge, native selected energies, axis, RP-minus-LP
handedness, relative reference scale, provenance and assumptions. Two reliable
L3/L2 features may populate native energies; ambiguous assignments remain user
declarations. No WIEN2k installation or separate tensor JSON is required. The
bundled Ni source cannot substitute for another element.

**Atomic Ionization MDFF** accepts explicit atomic parameter JSON directly;
validate its checksum, then acknowledge the approximate cubic 2p-to-3d model.
The bundled synthetic Fe example is software test data, never physical Fe constants.
With no parameter file, historical Ni controls retain their original interpretation.

**Imported Complex MDFF Tensor** reads declared complex 3x3 tensors with explicit
nonmagnetic or magnetic-state inputs. XMCD/import adapters support L2,3 and the
end-to-end-tested K-edge declaration; other edge families remain rejected. K-edge
maps, selected samples and exports keep their K label. L3/L2-specific peak
normalization and L3 white-line diagnostics are unavailable for other edges.
All declared providers use Manual numerics and supported equivalent sites in a
fully occupied single-element crystal. Approximately 1.6% detector-refinement
sensitivity remains a limitation; no broad convergence or experimental accuracy
is established. Missing/altered inputs block rerun and invalidate acknowledgement
while saved arrays remain viewable.

### Historical Part 1 workflow

Select the imported-MDFF provider for an explicitly declared Hermitian PSD complex
3x3 dipole tensor source. Review element/L2,3 selection, frame, magnetic axis, units,
explicit opposite states and SHA256; acknowledge the declarations and use Manual
numerics. Source replacement or a missing source blocks rerun while saved arrays
remain viewable. Multi-element/site-resolved ionization and AFM/SDW remain unsupported.

The same panel's **Generate approximate atomic tensor from declared parameters**
button accepts a complete parameter JSON and a fresh output path. The portable ZIP
includes `_internal/examples/synthetic_fe_atomic_parameters.json`. This is an original
synthetic software fixture, not measured/fitted Fe constants. The model supports
2p-to-3d transitions in a declared cubic field, explicit radial integrals and spin
holes, local +z spin and proper rigid frame rotations; material inputs are physically
unvalidated. No quantitative Fe, Co or Cr model, many-body multiplet accuracy,
general crystal-field symmetry or complete DFT MDFF is supplied. The original Ni
provider/project behavior is unchanged. See [parameters and limits](GENERALIZED_ATOMIC_IONIZATION.md)
and [import contract](GENERALIZED_SINGLE_ELEMENT_EMCD_DESIGN.md).

Generalized XMCD-effective conversion is a Python API with explicit declarations;
the portable GUI imports its generated tensor JSON, not an automatic Fe XMCD model.
Intensities remain relative. Approximately 1.6% detector-refinement sensitivity in
the reviewed finite cases remains a limitation; BW/MS agreement is not general
convergence or experimental accuracy. [Release notes](RELEASE_NOTES_0_8_1_BETA_1.md).
