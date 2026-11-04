# Multi-element elastic provider: integration review

Historical record for commit d1c93ba: statements below describe the original external-provider review. The subsequent unified-provider continuation, new default decision and packaging/provenance checks are recorded in the [2026-11-03 acceptance](acceptance/unified-elastic-2026-11-03/FINAL_INTEGRATION_RECOMMENDATION.md) and current [provider guide](ELASTIC_ATOMIC_FACTORS.md). The original external table and its low-g restrictions remain unchanged.

Reviewed on 2026-11-03, feature branch `feat/neutral-atomic-elastic-local`, base `859870c2cb6ee9034249aecc890703c571b4cbd4`. This records a local feature review and commit, without main integration, push, release or binary rebuild.

## Review inputs and scope

The full preliminary `outputs/elastic-extension-review/proposed.patch` and `VALIDATION_REPORT.md` were reviewed, together with their source files and the supplied external function. Their SHA256 values are respectively `8f2b846a92f00d9a02a8f1742a9b731c3d45587b85d20303b6cad21c0f9eec88` and `06c5a9aa2de5a2bd6b5d1f4ee4b5080157cce14e0a6cb80dfbd87b2996227dfe`. These preliminary artifacts remain preserved. The final low-g audit, validation and logs are under `outputs/elastic-mott-final-review/`; the intermediate review directory is also preserved.

The original Lobato Ni coefficients, scattering function and default provider are unchanged. The independent reference check loads the original scattering, beam and BW classes as well as the old GUI geometry adapter directly from the base commit; it does not reuse modified production classes as its baseline. The protected MDFF/EMCD kernels, Ni spectral input, reference tests and historical figure provenance/selected values are checked for zero diff. No historical simulation array or checkpoint is recalculated or modified.

## Supplied table audit

The external source is pinned to SHA256 `1a93fe5b5fa86ea968049d8f4daee99a00981f225b3e8b8d0d9417460443535a`. It identifies `atomicscatfact.f:ATOMICSCATFACT` but supplies no original-table attribution, copyright holder, license grant or redistribution terms. Searches for the exact file/routine names, `EFARRAY`/`XFARRAY`, and the distinctive scaling constants did not establish a traceable rights grant. A matching number, public code translation or publication would not establish redistribution permission.

**Decision: retain external data.** No original table data or translation source is committed. EMCD-Sim's MIT license grants no rights to that external material. Public bundling remains blocked by missing original provenance and permission; this is not a determination that redistribution is forbidden.

Both EF and XF/Mott returns are divided by the source's `47.878009`, after passing `STL=|g|/2`. IAM retains its own potential conversion once; no extra gamma, volume or Mott conversion is inserted. The interpolation, skipped -1/-2 entries, reflected origin sample and upper-end stencil remain delegated to the hash-checked source. Formal bounds remain `|g|<=3` for H and `|g|<=12` for Z=2–98.

### All-44 low-STL investigation

The XF/Mott branch can produce severely wrong finite values before division underflows. Mo reproduces approximately 491.23, 462.37, 290.31 and -1428.55 in source-scaled units at STL=0, .001, .0001 and .00001 respectively. Catching arithmetic failure alone does not address this problem.

All **44 XF/Mott elements** were audited, including zero, small positive/subnormal inputs, and neighbors of the first native knots .01/.02/.03/.04. The original source remains unchanged and its failures are retained in an ignored diagnostic CSV; the normal adapter rejects unsupported inputs before evaluation. **Numerical operating domain: STL=0 or 0.04<=STL<=6**, corresponding to **|g|=0 or 0.08<=|g|<=12 inverse angstrom**. The common bound follows from the pinned source, not an arbitrary percentage threshold.

The audit independently reconstructs each of the 2,684 source cubic intervals by 80-digit Lagrange interpolation. For a nonnegative spherical neutral-atom density, the Mott kernel `(1-sinc(x))/x^2` is nonnegative and nonincreasing, so the electron factor should be positive, nonincreasing and no larger than its origin. These are necessary consistency conditions, not a complete atomic model. Removing the positive `STL**2`/`STL**3` denominators gives cubic sign tests for these conditions; endpoints and every stationary point are checked. The reference's 1e-55 allowance covers only its own high-precision arithmetic noise, not physical error or tabulation uncertainty.

The final failing source interval is Os (Z=76), STL=.03–.04. The common next native knot .04 is therefore the conservative boundary for all 44 rows, including rows that individually pass earlier. Every accepted interval passes these sign checks. At 42,636 accepted-domain samples, source binary64 results agree with the independent reference within 2.551e-14 relative difference. Neighbor continuity at the first four native knots differs by at most 3.416e-12 angstrom. Exact zero is a separate source definition; continuity to zero across the rejected interval is not asserted.

The domain check preserves STL=0 while rejecting **all** `0<STL<.04`, including finite negative/implausible outputs and extreme-underflow cases. It does not apply clipping, absolute values, constant extrapolation, a polynomial correction, or a fallback provider. Regression tests exercise every affected element, both sides of the boundary, the original Mo negative result and original underflow exception, and a Mo supercell with a small nonzero reciprocal vector.

Source compatibility, numerical operating validity and scientifically established quantitative accuracy are distinct. Original-table rounding/error bounds and independent atomic references remain unavailable, so even the accepted domain is **not quantitatively certified**. Large supercells that introduce nonzero XF/Mott vectors below .08 inverse angstrom now fail explicitly, including small BW difference vectors. They are not treated as (000). A manually verified equivalent primitive cell may be appropriate for an artificial supercell; physically real long-period structures need a separately validated provider. Geometry is never changed silently.

## Open alternative investigated

The author-maintained [adaptive Dirac–Padé repository](https://github.com/NeuralSoftX/adaptive_dirac_pade_scattering_factor_2026/tree/1667babb2c5bdb44a0535438b846eb1bbfbc03ac) provides Z=1–118 electron factors. Its [README](https://github.com/NeuralSoftX/adaptive_dirac_pade_scattering_factor_2026/blob/1667babb2c5bdb44a0535438b846eb1bbfbc03ac/README.md), [license](https://github.com/NeuralSoftX/adaptive_dirac_pade_scattering_factor_2026/blob/1667babb2c5bdb44a0535438b846eb1bbfbc03ac/LICENSE), evaluator SPDX header and package-data declaration identify an Apache-2.0 scientific-data/evaluator distribution. This is direct author/upstream evidence, independent of the paper's license. No separate restrictive data notice was found in the inspected root, package, data or coefficient-table locations.

Snapshot: upstream commit `1667babb2c5bdb44a0535438b846eb1bbfbc03ac`; LICENSE Git blob `2aafac0d159c93d253f44658f0252ffa2fe3364e`; coefficient HDF5 blob `1fd1b55266dd674530a1b6177a939e45dac5290d`; adaptive Dirac–Padé text-table blob `aa941874b7a0d48912a6e416d834d1cb6b301820`. These are Git object IDs, not SHA256 checksums. No upstream data or implementation has been copied into this feature.

Apache-2.0 permits redistribution subject to its terms: retain the license and relevant attribution/notices, preserve any NOTICE requirements, and mark modifications. Any future third-party files would keep their Apache notices, rather than being represented as solely MIT-licensed. This makes the author deposit a viable openly redistributable candidate; publication alone was not used as permission.

Scientific/API follow-up remains separate: the candidate returns `f_e(g)` in angstrom for crystallographic inverse-angstrom `g`, uses distinct relativistic-reference coefficients delivered in float32, and reports fits through 36 inverse angstrom. Its maintained package requires Python >=3.11 with pinned dependencies; EMCD-Sim supports >=3.10. Integration needs a pinned data manifest, separate provider identity, units/origin tests and BW/MS validation, with the original Ni default retained. No candidate accuracy or positivity claim is adopted as EMCD-Sim validation.

## Acceptance and public integration limits

The current feature supports fully occupied ordered mixed-element CIFs when the external table is available. It retains partial/disordered-occupancy restrictions, species-weighted factors, CsCl (100), genuine centering extinctions and Hermitian elastic potentials. The inelastic material gate explicitly continues to require Ni, including rejection of Cu with Ni's cell and positions. Unset, missing and hash-mismatched external data fail clearly for non-Ni elastic use while Ni remains available.

Final checks passed: **45 configured Ni/elastic/GUI/provider tests**; **17 passed and 13 external-data tests skipped** with the provider absent. The independent archived Ni probes and 1,001 Ni factor samples are bitwise equal. The small BW/MS set includes CsCl, FCC Cu and XF/Mott BCC Mo. Original no-provider GUI controls are isolated so configuring the extension cannot invalidate their premise; configured desktop controls are tested separately.

The local validation report records the numerical metrics, source hashes and diff checks. Main may review this as an external-data capability with explicit numerical restrictions; claims of bundled Z=1–98 support remain blocked. Rejected near-origin values, quantitative table accuracy, public legacy-data bundling and any alternative-provider integration require the additional work described above. The Apache candidate remains separate until its own units, coefficients, numerical behavior, source-data provenance and redistribution conditions are independently verified for an EMCD-Sim integration. The release version and existing Windows binary remain unchanged.
