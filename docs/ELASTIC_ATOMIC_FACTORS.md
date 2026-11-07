# Neutral-atom elastic scattering providers

Introduced in v0.8.0-beta.1 and retained in the published **v0.8.1-beta.2 Windows Research Beta**, the application bundles **Adaptive Dirac–Padé 2026 neutral Z=1–118** coefficient data under Apache-2.0, alongside the historical Ni Lobato factor and an opt-in external Z=1–98 adapter. These resources are included in the current Windows package; the previous v0.7.0-beta.1 binary does not include them and is preserved. See [main integration](acceptance/unified-elastic-2026-11-03/MAIN_INTEGRATION_ACCEPTANCE.md) and [native candidate acceptance](acceptance/unified-elastic-2026-11-03/WINDOWS_NATIVE_CANDIDATE_ACCEPTANCE.md). Elastic multi-element support does not supply a multi-element MDFF; current supported single-element construction methods and electronic-input limits are described in [MDFF workflows](MDFF_WORKFLOWS.md). The [beta.2 release notes](RELEASE_NOTES_0_8_1_BETA_2.md) describe the current Windows-only scope; the [v0.8.0 notes](RELEASE_NOTES_0_8_0_BETA_1.md) retain their historical validation scope. Linux/macOS are not certified; their existing CI failures remain recorded.

New GUI `Settings()` and `IndependentAtomPotential.from_provider(crystal)` default to `adaptive-dirac-pade-2026`, including Ni. The raw unversioned `IndependentAtomPotential(crystal)` constructor retains the original Ni Lobato–Van Dyck (2014) function and coefficients for script compatibility. Select `nickel-lobato-2014` explicitly to reproduce historical Ni studies. Saved settings without a provider field resolve to Lobato; opening old plots never recalculates them. New results record provider identity, coefficient checksum and upstream pin. Parameterizations differ; agreement is not assumed.

## Bundled unified provider

The coefficient source is [Ivan Lobato / NeuralSoftX's deposit](https://github.com/NeuralSoftX/adaptive_dirac_pade_scattering_factor_2026/tree/1667babb2c5bdb44a0535438b846eb1bbfbc03ac), pinned at `1667babb2c5bdb44a0535438b846eb1bbfbc03ac`. The accompanying 2026 manuscript is a submitted preprint, not an established journal acceptance. Full Apache-2.0 LICENSE, NOTICE and machine-readable provenance are shipped in `emcd_sim/data/adaptive_dirac_pade_2026/`; EMCD-Sim's MIT license does not supersede those terms. Only adaptive-model data are extracted, retaining exact float32 coefficient values in JSON; no fit is changed. Production evaluates them in binary64 using existing NumPy, without installing the upstream package, HDF5, SciPy or SymPy.

```python
from emcd_sim.adaptive_scattering import adaptive_factor
from emcd_sim.scattering import IndependentAtomPotential

f = adaptive_factor('Mo', [0., 1e-200, .001, 1., 36.])  # angstrom
potential = IndependentAtomPotential.from_provider(crystal)
historical_ni = IndependentAtomPotential.from_provider(crystal, 'nickel-lobato-2014')
```

The [source Fourier equations](https://arxiv.org/html/2608.14934v1) use `exp(-2*pi*i*g.r)`, density transform `sinc(2*pi*g*r)` and `fe=(Z-fx)/(2*pi²*a0*g²)`. This establishes crystallographic `g=1/d`, beyond matching unit labels. The returned amplitude is already in angstrom: **do not divide by 47.878009, halve g, multiply by 2π, or apply microscope gamma**. IAM performs the existing potential conversion separately.

With `t=1/(1+b*g²)`, the evaluator sums `a*(t+t²)` for NR terms and `a*(t+t²+t³)` for the final DP term. This is the original rational expression rearranged algebraically; it avoids Mott cancellation and division by g² at the origin. Signed coefficients are preserved with no clipping, absolute-value repair or interpolation. The explicit operating range is **0<=g<=36 inverse angstrom**, including g=0 and arbitrarily small positive finite values; invalid/out-of-range arguments fail. Large-supercell small vectors are evaluated directly by this provider and do not relax the external XF/Mott guard.

All118 elements pass sampled finite/positive and 65-digit arithmetic checks; the maximum discrepancy against the pinned deposited atomic reference grid is about 0.0113%. This checks the parameterization fit, not independent experimental accuracy or a universal diffraction error bound. Independent radial-density Fourier quadrature checks the reciprocal convention. Neutral-atom IAM omits ions, bonding charge transfer, absorption and TDS. Configuration-specific beam, potential, FFT and depth convergence remain necessary. New-provider automatic numerical settings are uncertified; Lobato-specific validated profiles are not silently transferred. Full [acceptance reports, configurations, plots and metrics](acceptance/unified-elastic-2026-11-03/FINAL_INTEGRATION_RECOMMENDATION.md) document these limits.

The GUI selector exposes all three providers. Only the external legacy choice uses the file below. Missing external data produce a diagnostic while the two bundled choices work normally. Ordered full-occupancy CIFs support elastic diffraction; partial/disordered CIF occupancies are rejected. Signed three-index hkl refer to the ASE-imported cell without automatic primitive reduction; four-index Miller–Bravais input is unsupported. Independent and actual offscreen Qt checks cover BCC Fe, CsCl, hexagonal ZnO and a monoclinic cell. File > Save/Open Elastic Project saves checksummed arrays and opens them read-only without changing inputs or running a solver.

## Load the supplied table locally

Keep the supplied `scattering.py` outside the repository. The adapter is `emcd_sim.legacy_atomic_factors.LegacyNeutralAtomFactors`; it never shadows or replaces `emcd_sim.scattering`.

```python
from emcd_sim.legacy_atomic_factors import LegacyNeutralAtomFactors
from emcd_sim.scattering import IndependentAtomPotential

table = LegacyNeutralAtomFactors.from_file("/path/to/supplied/scattering.py")
print(table.factor("Ni", 2 / 3.524))  # |g| in inverse angstrom; result in angstrom
potential = IndependentAtomPotential(crystal,
    atomic_factors=table.atomic_factors(crystal.species))
provenance = table.provenance()  # retain this with custom Python results
```

The reviewed file SHA256 is `1a93fe5b5fa86ea968049d8f4daee99a00981f225b3e8b8d0d9417460443535a`. A different file is rejected until its data and implementation are audited. Compilation occurs in memory; no bytecode is written beside the supplied source. The table is not copied into the package, test fixtures or proposed diff.

For elastic CIF diffraction in the GUI, set the environment variable before launching:

```powershell
$env:EMCD_SIM_LEGACY_ATOMIC_TABLE = 'C:\path\to\supplied\scattering.py'
emcd-gui
```

Select **External legacy atomic table (Z=1–98)** in the GUI to use it for **every species**, including Ni in a mixed-element structure. Without configuration this selection is geometry-only with a clear diagnostic. It does not replace the bundled Adaptive default. ASE's existing `atomic_numbers` mapping resolves canonical neutral chemical symbols; integer Z is also accepted. Ions, isotope aliases, booleans, fractional atomic numbers and Z outside 1–98 are rejected by this external provider.

The CIF gate continues to reject mixed/disordered and partial occupancies, including nonfinite occupancy metadata. Ordered, fully occupied sites of different species are supported. The lower-level IAM API already accepts explicit per-site occupancies and B values; that does not establish a disorder, thermal diffuse scattering or alloy model. Unsupported reciprocal ranges produce errors, not extrapolation or silent cutoff changes.

## Units and scaling

Use crystallographic `|g|=1/d` in inverse angstrom, with no 2π in the reciprocal basis. The source input is `STL=sin(theta)/lambda=|g|/2`. Its electron API exposes only `OPTION=2`.

|Source branch|Source return|Adapter electron amplitude in angstrom|
|---|---|---|
|EF (including source method 3 for H)|`47.878009 * interpolated_EF(STL)`|Divide the return by `47.878009`|
|XF/Mott, STL > 0|`1.145896 * (Z - interpolated_XF(STL)) / STL**2`|Divide the return by the **same** `47.878009`|
|XF/Mott, STL = 0|`47.878009 * EF[Z,0]`|Use the source's finite-origin branch, then the same division|

After this conversion, IAM applies its existing `2*pi*hbar**2/(m0*e)` potential conversion once, and divides by the cell volume. The source's `47.878009` differs slightly from the current SI-derived IAM value `47.87764729791723 V angstrom²`. Dividing by the current constant instead would leave an unintended amplitude scale difference. Neither constant nor the microscope gamma factor is changed. Relativistic gamma remains in propagation, outside the atomic factor. Mott conversion happens in the source only; it must not be applied a second time.

## Interpolation and limits

The adapter delegates to the exact reviewed source function. It does not fit new parameters or replace the interpolation with `numpy.interp` or a spline. The source uses 62 nonuniform STL nodes and four-point cubic interpolation, skips negative entries (`-1` missing, `-2` rejected), reflects a preceding sample near the origin, and uses the last four usable entries at the upper boundary. Source method selection is preserved per element.

The source's formal input limits are `0 <= STL <= 1.5` for H (`|g| <= 3`) and `0 <= STL <= 6` for other elements (`|g| <= 12`). These limits alone do not establish numerical reliability. The adapter distinguishes three levels:

|Level|Meaning and current scope|
|---|---|
|Source-compatible interpolation|Original external tables/function are unchanged. In the accepted domain the adapter uses their result with the single scale conversion above. The separately defined STL=0 branch is preserved.|
|Numerically reviewed operating domain|EF retains its source limits. For all **44 XF/Mott elements**, accept **STL=0 or 0.04<=STL<=6**, equivalently **\|g\|=0 or 0.08<=\|g\|<=12 inverse angstrom**. Reject smaller positive values before division or underflow, even when the source result would be finite.|
|Scientifically validated quantitative accuracy|Not established for this legacy table. Arithmetic agreement and basic physical consistency are not an independent atomic-scattering benchmark or an error bound on the tabulated data.|

The low boundary is a source-native knot selected by an all-44 interval audit, rather than clipping or a fitted correction. All source cubics were reconstructed independently at 80 decimal digits for audit only. Endpoints and all stationary points of the positivity, derivative and separate-origin-bound polynomials were checked; Os has the last inconsistent interval, ending at STL=0.04. In the accepted domain, 42,636 samples agree with the unmodified source to within 2.56e-14 relative arithmetic discrepancy. No audit polynomial is used to replace production factors. Original Fortran executable equivalence and default-kind literal rounding remain unverified.

The cutoff must cover every factor actually evaluated, including BW pair differences. **Large-supercell nonzero vectors below 0.08 inverse angstrom are unsupported for XF/Mott species and fail explicitly.** They are not rounded to zero or replaced by `f(0)`. For a cubic repeat L, (100) has `|g|=1/L`; L>12.5 angstrom can therefore encounter this limit. A verified equivalent primitive cell may avoid artificial supercell vectors where physically appropriate; a real long-period structure instead needs another validated provider. No cell, cutoff, geometry or source formula is changed automatically. Ni Lobato is unaffected.

## Structure factors and beam support

IAM already computes the species-dependent formula:

```text
F_G = sum_j occ_j f_species_j(|G|)
      * exp(-2*pi*i*hkl.fractional_position_j)
      * exp(-B_j*|G|^2/4)
```

The phase is equivalently `G.r_j` in Cartesian coordinates. No common equal-atom factor is pulled outside the species sum. Nonfinite factor returns are rejected.

`BeamSet.zolz(..., potential=potential)` selects using the actual IAM structure factor; its omitted-potential path retains legacy equal-atom selection. Supply the potential for multi-element or site-dependent use. The GUI and BW model validation now use this weighted test. CsCl (100) is retained when `f_Cs-f_Cl` is nonzero, whereas FCC Cu (100) remains extinct. A Fourier cutoff is unwrapped for structural beam tests: zeroing a numerical potential harmonic must not be confused with an extinction or eliminate a beam reached indirectly.

The general projected FFT engine already uses decorated species/occupancy/B translations and actual IAM coefficients. It needs no MDFF change. The bounded validation compares BW and FFT split-step propagation using matched finite potentials. It is evidence for these elastic test cases, not global material/convergence certification. Real neutral-atom potentials satisfy `F(-G)=conj(F(G))`; there is no absorption, ionicity, bonding charge transfer or TDS in this extension.

## Provenance and redistribution

The supplied file describes a Python translation of `atomicscatfact.f:ATOMICSCATFACT` and references an unavailable `docs/scattering.md`. It supplies neither an original-table citation nor redistribution/license terms. Public searches for the exact original routine/file names did not establish an upstream source or permission. The Python translation alone cannot establish rights to redistribute the underlying numerical table.

Redistribution status is therefore **unverified**. Local functionality uses the user's external file; no original data are included in the feature commit or attributed to EMCD-Sim's MIT license. Suitable original provenance and permission remain necessary before bundling the table publicly. The [developer review](ELASTIC_PROVIDER_REVIEW.md) records the evidence and remaining integration limits.

The original review at d1c93ba left the author's Adaptive Dirac–Padé deposit as a candidate. The subsequent integration above independently checks its units, Fourier convention, coefficients, licensing and bounded numerical acceptance. Its new GUI/factory default does not alter original Lobato values or historical project selection. Third-party license and attribution notices remain separate from EMCD-Sim's MIT license.

The preliminary report and patch remain under `outputs/elastic-extension-review/`; the completed low-g review is under `outputs/elastic-mott-final-review/`. Reproduce bounded checks with `python scripts/research/validate_atomic_elastic.py --output outputs/my-new-elastic-review`, or run only the low-STL audit with `python scripts/research/audit_legacy_mott.py --output outputs/my-new-mott-review`, after setting the external-table variable. Use a new directory to preserve previous reports. New tests use the real table only when `EMCD_SIM_LEGACY_ATOMIC_TABLE` is set; otherwise external-data cases skip explicitly. Missing/unreadable configured files name the provider, path and variable in the diagnostic. Core Ni, missing-provider and synthetic species-weighting controls do not need the table.
