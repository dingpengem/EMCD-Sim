# EMCD-Sim v0.9.0-beta.2 — Windows Research Beta

[Home](../README.md) · [Install](INSTALL_WINDOWS.md) · [Quick Start](QUICK_START.md) · [Scientific references](SCIENTIFIC_REFERENCES.md) · [Citation](CITATION.md)

Windows x64 Research Beta, 11 November 2026. The annotated **v0.9.0-beta.2** tag identifies the final packaged application source; its exact SHA is in `_internal/build_info.json` and the matching release build manifest. Python package version is `0.9.0b2`, display version `v0.9.0-beta.2`, PE version `0.9.0.2`. Prior Windows beta.1, macOS ARM64 beta.1 and their tags/assets are unchanged. The Mac app has a different source revision.

## Changes

- **Compute Resources** replaces Resource Estimate. CPU Workers and Memory Budget have independent Auto/Manual modes, hardware detection, effective allocation and remembered Manual values. Auto uses useful work, available logical processors and memory/commit/address-space headroom, without silently changing scientific sampling.
- SC uses one outer worker. DC concurrency follows resource admission, not an arbitrary four-worker cap. BLAS limits are verified during calculations and restored afterward. More workers need not be faster.
- SC admission describes its actual bounded 64-pixel contraction batch rather than a hypothetical full-map beam-pair allocation. Results, FFT/depth buffers, scratch and existing safety margins remain included; scientific kernels and reference values are unchanged.
- New single-element results distinguish requested uniform points from actual evaluated samples; historical projects are not rewritten. The representative Ni request is 241 uniform points plus two exact features = **243 energies**, with two **97×97** maps and detector support at the other energies.
- Existing multi-site Global/Local magnetization, grouping, independent MDFF/energy windows, BW/MS SC/DC, explicit physical reversal pairs, Results/export and persistence remain available.
- Windows guides, verified measured performance, method/data bibliography, software CFF/BibTeX and MIT-consistent source/AI-derivative citation guidance accompany this version. Current main's macOS guides, figures and authentic Quick Start exports are preserved.

## Fresh RC1 packaged acceptance

Extracted RC1 source **6d979d03df5c099792d45fd0dfd0a8c2ac7a4b40**, with no development PATH/PYTHONPATH dependency, was tested through normal GUI controls. Runtime/scientific source and dependencies remain unchanged in final release preparation; final documentation requires a matching new build. These are acceptance timings, not a new performance benchmark.

| Workflow | Actual request | Calculation time | Result |
| --- | --- | ---: | --- |
| Global Ni BW Single | raw CIF 3.520 Å; Global +z; XMCD; 200 kV/10 nm; [017]/(200); full finite ZOLZ/21 beams; cutoffs 2.5/2.0 Å⁻¹; 243 energies; two 97×97 maps; depth/subpixels 64; Auto | 3.190 s | Completed, displayed, saved and exported |
| Local Ni BW Double | indices 0–3, +z; independently configured XMCD; same physical inputs; 2 selected energies, two 9×9 maps | 0.489 s | Completed and retained separately |
| Local Ni MS Single | same bounded Local diagnostic; FFT 32×32, max step 2 nm, 64 depth nodes | 0.277 s | Completed and retained separately |
| Local Ni MS Double | same bounded Local diagnostic; actual incoming FFT and reduced-energy outgoing response | 1.452 s | Completed after a verified cancelled attempt/restart |

The GUI source was the packaged `Ni_fm.xmcd`, exact selected energies **831.271/848.698 eV**, eta=beta=1 and explicit source/convention acknowledgements. **MDFF Done → Viewer Apply and Close** accepted providers; Local mode locked Global M. An unapplied −z direction draft was cancelled and accepted +z persisted. All four saved raw A/B ±M spectra were finite, nonnegative and nonzero; reversal identities held. Local group sums reproduced Total at N=4. Exported Global NPZ arrays exactly matched saved arrays. No SC/DC equality or physical convergence is asserted.

Manual 1 worker/64 MiB blocked Run with insufficient admission; 2048 MiB admitted it, then Auto was restored. Effective SC worker count was 1; bounded DC used 2. Auto budgets varied with live headroom (about 6.6–6.7 GiB). Existing runtime diagnostics show calculation-scoped one-thread BLAS and restoration to 12/12. Request sampling and effective preview/Run work agreed; headroom snapshots need not produce identical budget numbers.

Save/close/reopen retained Global/Local settings and four calculations. CSV/NPZ and PNG/SVG exports completed. Native inspection used actual **150% DPI (144)** at **1597×1003** and **1357×844** client sizes, with scrolling/collapsible Results as designed; no desktop scaling was changed. Independent 100%-DPI hardware, clean-PC/VM and code signing are not claimed. Final extracted-package launch/identity, restored views and documentation checks are reported with the release build evidence; earlier execution is not mislabeled as rerun on final source.

Local evidence is retained under `build/v090b2-release-native/`: `Ni_Global_BW_SC`, `Ni_Local_Backends`, native screenshots, isolated runtime log and ordinary export folders. These private generated project files are not redistributed as new scientific references.

## Existing performance and numerical evidence

The [Windows resource benchmark](WINDOWS_SC_DC_RESOURCE_BENCHMARK.md) retains 16 completed full requests, original and later serial timings, worker scaling and separate Auto cases. Four directly affected SC memory checks passed previously. Measurements on shared laptops have limited statistical/thermal repeatability; memory estimates, whole-process RSS and budgets are distinct.

[Per-array cross-platform evidence](WINDOWS_MACOS_NUMERICAL_EQUIVALENCE.md) records **43 matching BW Single numeric arrays** with scale-aware tolerances. Direct authentic macOS BW Double, MS Single and MS Double raw-array comparisons remain **INCOMPLETE**. The release owner explicitly accepts these gaps as documented Research Beta limitations; they were not rerun, reconstructed or changed to PASS. Timing/settings matches do not prove numerical equivalence.

Historical application regression at an older source recorded 1,448 passed/62 skipped; **it was not repeated for this release**. Historical failures and incomplete broad/source-guard verification remain unchanged. Focused/native checks are not a full-regression acceptance claim.

## Packaging and scientific limitations

The release includes the full Windows ZIP, matching application and Qt/PySide/Shiboken 6.12 corresponding sources, licenses/notices, existing build manifest and SHA256SUMS. Microsoft VC++ v14 remains external; unused Qt PDF/Virtual Keyboard remain excluded. spglib and required Qt plugins are retained. No relabeling of an old EXE or overwrite of previous assets is authorized.

Finite ZOLZ, finite beam/FFT/depth support, projected IAM and continuous-depth localized ionization limit the model. General convergence and some complex BW/MS conditions remain incompletely characterized. The Ni 2.0 Å⁻¹ potential cutoff omits the first off-row harmonic near 2.029 Å⁻¹; the full benchmark's MS step 10/63 nm exceeds the advisory 0.04 nm reference. Synthetic/effective MDFF tensors do not establish quantitative Fe₃O₄/NiFe₂O₄ spectra, absolute cross sections or calibrated magnetic moments. No physics/reference/tolerance changes were made to obtain agreement.

Unsupported fixed-source Z→X changes remain rejected; general tensor rotation and magCIF are future work. Academic software citation is strongly requested, including source-based AI-assisted derivatives, without adding a condition to the unchanged MIT License.
