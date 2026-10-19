# Angular sampling and memory defaults

The controls described here are included in the validated v0.6.1-beta.1 Windows ZIP. This document retains the original sampling diagnosis and small-job timing scope; later representative production-profile convergence and final packaging are linked below. Publication reuses the validated ZIP without rebuilding or rerunning simulations.

## Diagnosis

The saved release smoke examples and `outputs/full_field_emcd_maps/` contain actual **9 x 9** arrays: 81 calculated pixels. They were deliberately small acceptance jobs. Their primary full-field maps have 81 valid samples and are not limited to aperture support. A focused inventory of the existing `ni_017*` angular-map files found 52 maps with **33 x 33** q arrays, including `ni_017_high_mistilt_xy/cases/x_p0_y_p0/angular_maps.npz`. No 193 x 193 reusable full-field map was found in that inventory. This does not claim an exhaustive inventory of every unrelated output directory.

The previous new-job default was 33 x 33; the upper supported GUI grid remains 193. Sparse appearance in these examples comes from coarse actual sampling. Invalid denominators remain NaN, and jobs calculated with angular maps disabled do not have supported full-field data. Display interpolation and DPI cannot supply missing calculated intensities. Primary plots now explicitly use nearest-sample rendering, equal physical aspect ratio, and actual saved dimensions and q spacing.

## Controls

| Preset | Actual grid | Pixels | Relative pixel count |
|---|---:|---:|---:|
| Quick Preview | 33 x 33 | 1,089 | 1 |
| Standard, new-job default | 97 x 97 | 9,409 | 8.64 |
| High Resolution | 193 x 193 | 37,249 | 34.21 |
| Custom | odd 9 through 193 | N squared | depends on N |

The spacing is `dq = 2*halfwidth/(N-1)` in cycles/Angstrom. Odd grids sample qy=0 exactly. The GUI rejects even sizes for new calculations rather than silently changing them. Old saved numerical arrays are never resampled, and explicitly saved grid sizes remain unchanged when restored.

These controls have distinct roles:

- **Angular / detector grid:** actual transverse q samples. This minimal implementation retains the existing shared virtual-detector EELS integration grid. Changing this grid can change detector quadrature; it is not a display-only control. Equivalent saved numerical settings retain the same integration implementation and raw spectra.
- **Multislice FFT grid:** spatial propagation mesh and reciprocal harmonic support. Changing an angular preset never changes the FFT mesh, beam basis or slice/depth settings.
- **Aperture boundary subpixels:** deterministic fractional-area sampling at circular aperture boundaries. Angular presets do not change this value.

Detector A/B outlines remain overlays on full-field maps. Reflection uses actual `(qx,qy)` and `(qx,-qy)` samples, not aperture matching or spatial interpolation. Raw magnetic and reversal-even differences remain distinct from total asymmetry. Detector EELS integrates raw intensities before forming ratios; pixelwise percentages are never averaged into a detector asymmetry.

## Memory and measured cost

Internal configuration, memory admission and GUI startup already defaulted to **2048 MiB**. The update ensures **New Project** resets to 2048 MiB even after loading an explicitly smaller budget. Explicit saved 512/1024/2048/4096/8192 MiB budgets remain supported and are preserved on restore. Missing legacy budget fields use 2048 MiB. This is a ceiling on estimated working memory, not a 2 GiB preallocation. Current RSS, concurrent reservations, allocation margin and the available-RAM limit remain in the unchanged admission policy. No calculation parameters are reduced on rejection.

A small actual Ni [017], 200 kV, 2 nm Single-channeling BW/MS example used beam cutoff 0.9, potential cutoff 1.8, and selected native L3/L2 energies only. Both engines calculated all 1,089 pixels at 33 and all 9,409 pixels at 97, without NaN holes in I_plus. At halfwidth 0.5, spacing improved from 0.03125 to 0.0104166667 inverse Angstrom. The measured joint times were about 2.92 s and 1.57 s; the non-monotonic timing is dominated by small-job startup/warmup and must not be extrapolated to a production speedup. Estimated process peaks were about 266 and 291 MiB. Actual peak RAM was not independently measured.

For the ordinary new-job 27-beam BW profile, admission estimates were approximately 268 MiB at 33 and 758 MiB at 97, supporting the Standard default. High resolution has a dense estimate around 1,657 MiB and a total estimate around 2,398 MiB: it is correctly rejected under the default 2048 MiB budget. The precise total depends on current process RSS and active jobs. Users may explicitly select a larger supported budget if available RAM permits. No new 193-grid Double calculation was run.

At fixed propagation settings, outgoing Double-channeling work scales approximately with evaluated detector directions times selected energies and depth/FFT work. Relative pixel counts are a workload guide, not calibrated runtime predictions. A 193 grid adds about 3.96 times as many q samples as 97; this is real finer sampling, but its benefit for a particular physical feature requires convergence evidence. It does not improve MDFF completeness or physical-model accuracy by itself. Use the existing selected-L3/L2 mode when only these maps are needed; presets do not silently alter energy coverage.

## Validation and outputs

`scripts/angular_resolution_assessment.py` reuses its own completed exports and never runs a thickness scan. It saves actual BW/MS PNG/SVG examples, full numerical project arrays, timings, numerical estimates and source/configuration provenance under `outputs/angular_resolution_assessment/`. The 204 production checkpoint hashes are checked unchanged. The shared engine already reuses compatible incoming propagation preparation; this change introduces no new propagation approximation.

Focused memory, full-field and control tests: **22 passed**. They cover presets, new-project defaults, legacy budget handling, physical-grid pairing, NaN behavior, aperture-independent maps and actual dimensions despite a mismatched selected input grid. A subsequent three-test recheck also passed, including explicit saved-project 512 MiB GUI restoration. Existing memory tests retain their original explicit 33-grid workload so the admission test does not accidentally change with new defaults.

This sampling study preserved production checkpoints and did not change solver physics. Subsequent version metadata, historical-source resolution, regression and packaging status are recorded in [release acceptance](V061_BETA_ACCEPTANCE.md).

The existing approximate XMCD-constrained MDFF, incomplete DFT transition tensor, projected IAM potential, longitudinal-transfer approximation, limited convergence evidence and uncalibrated absolute intensity remain. A smoother-looking plot is not proof of physical accuracy or experimental SNR.

The subsequent [validated-profile convergence study](ANGULAR_MAP_CONVERGENCE.md)
now provides actual 33/97/193 Double-channeling maps at Ni [017], 8 nm, L3,
with measured runtime and detector quadrature sensitivity. It also resolves the
historical source-fingerprint issue using exact source recovery and narrow
equivalence checks. The small Single-channeling timings above should not be
used to predict that substantially larger calculation.
