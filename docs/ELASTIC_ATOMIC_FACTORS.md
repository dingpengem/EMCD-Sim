# Neutral-atom elastic scattering providers

This source-only development feature supports neutral atomic elastic factors for Z=1–98 through an **opt-in external table adapter**. Only the historical Ni factor is bundled. The feature is on `feat/neutral-atomic-elastic-local`, pending main integration; the published v0.7.0-beta.1 Windows binary does not include it. Ni-specific inelastic MDFF, transition data and EMCD material eligibility retain their existing scope. No binary was rebuilt.

The default `IndependentAtomPotential` continues to use the original Ni Lobato–Van Dyck (2014) function and coefficients. All-Ni GUI structures also retain this provider even when the external table is configured. To compare Ni providers, construct a second potential explicitly; numerical agreement between parameterizations is not assumed.

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

Non-Ni supported structures then use the external provider for **every species**, including any Ni in a mixed-element structure. All-Ni structures keep Lobato. Without configuration, non-Ni CIFs remain geometry-only. ASE's existing `atomic_numbers` mapping resolves canonical neutral chemical symbols; integer Z is also accepted. Ions, isotope aliases, booleans, fractional atomic numbers and Z outside 1–98 are rejected.

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

An openly licensed alternative candidate is the author's [adaptive Dirac–Padé project](https://github.com/NeuralSoftX/adaptive_dirac_pade_scattering_factor_2026), which provides Z=1–118 factors under [Apache-2.0](https://github.com/NeuralSoftX/adaptive_dirac_pade_scattering_factor_2026/blob/1667babb2c5bdb44a0535438b846eb1bbfbc03ac/LICENSE). It is investigated, not integrated or bundled. Its distinct coefficients need an explicit adapter and independent validation; adopting it would preserve the original Ni default. Third-party license and attribution notices would remain separate from EMCD-Sim's MIT license.

The preliminary report and patch remain under `outputs/elastic-extension-review/`; the completed low-g review is under `outputs/elastic-mott-final-review/`. Reproduce bounded checks with `python scripts/research/validate_atomic_elastic.py --output outputs/my-new-elastic-review`, or run only the low-STL audit with `python scripts/research/audit_legacy_mott.py --output outputs/my-new-mott-review`, after setting the external-table variable. Use a new directory to preserve previous reports. New tests use the real table only when `EMCD_SIM_LEGACY_ATOMIC_TABLE` is set; otherwise external-data cases skip explicitly. Missing/unreadable configured files name the provider, path and variable in the diagnostic. Core Ni, missing-provider and synthetic species-weighting controls do not need the table.
