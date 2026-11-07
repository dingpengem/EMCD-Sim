# Proposed additive MDFF usability scope

Status: implementation candidate for review, **not an accepted replacement identity map**. Parent is local accepted main `3b0ce6c`. The exact full parent commit, parent/candidate raw and canonical SHA256 values and complete changed-file list are recorded in `outputs/mdff-usability-inventory.json`. These are proposal evidence only; no runtime validator reads or adopts them.

## Narrow changes

| File | Reason |
|---|---|
| `src/emcd_sim/gui/app.py` | Generic Open CIF, dedicated configuration entry, initial Atomic UI selection. |
| `src/emcd_sim/gui/atomic_editor.py` | Complete labelled defaults, reset, compact live preview/schematics, no draft reload during generated-source validation. |
| `src/emcd_sim/gui/provider_ui.py` | Optional file exchange, authenticated automatic preparation on explicit actions, atomic frame/axis consistency. |
| `src/emcd_sim/gui/imported_tensor_ui.py` | Nine-cell constant tensor model delivered through the existing imported provider, explicit reversal assumption, restored/external-source handling. |
| `src/emcd_sim/gui/stage_b.py` | Generic model label, hidden compatibility panel, passive readiness checks, live beam/frame and stale state. |
| `src/emcd_sim/gui/project_io.py` | Optional portable manual-source attachment, SHA256/manifest checks and restored source override; old project behavior retained. |
| `src/emcd_sim/imported_mdff.py` | Strict reserved manual-L2,3 provenance dispatch after existing validation; ordinary/constant imported sources retain their existing return path. |
| `src/emcd_sim/manual_l23.py` | New full-domain normalized Lorentzian model, integrated PSD strengths and exact analytical provider evaluation. |
| `src/emcd_sim/gui/manual_l23_editor.py` | Simple/full/constant spectral drafts, per-element state, explicit frames, real-provider previews and heatmaps. |
| `src/emcd_sim/gui/mdff_usability.py` | New compact layout, parser, validation, constant-source serialization, precise schematic/heatmap graphics. |
| `src/emcd_sim/gui/xmcd_preview.py` | Persistent raw-input/real-provider preview, reversal/even–odd controls, authenticated stale snapshots, direct text-source selection. |
| `tests/test_mdff_usability.py` | New focused functional and scale-tolerance tests. |
| `tests/test_xmcd_usability_preview.py` | XMCD source/provider equality, all preview states, invalidation, model switching and three-model save/reopen. |
| `tests/test_manual_l23.py` | Profile units/area/FWHM, arbitrary matrices, analytical provider/solver agreement and portable restoration. |
| `scripts/mdff_native_walkthrough.py` | Reproducible visible Windows source walkthrough and screenshots. |
| `scripts/xmcd_native_walkthrough.py` | Visible native XMCD preview, calculation, all-model switching and saved-project restoration. |
| `scripts/manual_l23_native_walkthrough.py` | Native spectral controls/matrices, Single/Double BW/MS and relocated-source restoration. |
| `docs/MANUAL_L23_TENSOR_MODEL.md` | Spectral convention, verification, screenshots, launch command and limitations. |
| `docs/MDFF_USABILITY_REDESIGN.md` | Implementation, evidence, launch and limitations. |
| `docs/MDFF_USABILITY_SCOPE_PROPOSAL.md` | This proposed review boundary. |

## Preserve historical identities

## Corrective candidate, 2026-11-06 (pending independent review)

The rejected complete patch `d8b036d37df0e94206ff1e1e5476a7d2a159a7e812f0e5663714fe487917b043`, its inventory and the independent review remain preserved outside this candidate in `outputs/mdff-usability-correction-20261106/rejected-d8b036d3`. The revised complete inventory supersedes the rejected identities only as a proposal. It also includes `gui/results_browser.py` (restoration adapter), new `gui/saved_atomic_ui.py`, `tests/test_mdff_corrective.py`, and the corrective verifier/native walkthrough scripts. There are eight modified existing files; the closed added-file list is in the revised inventory.

Same-path Atomic validation now compares content identity and reloads the actual editor/provider together, invalidating prior spectra. Constant, spectral and ordinary imported modes retain separate source, frame, magnetization and draft bindings. Historical Atomic settings have an exact read-only presentation and continue through the original provider, including explicit zeros; only absent historical fields receive defaults. Lorentzian evaluation avoids normalization overflow and rejects unrepresentably narrow widths explicitly. Full-domain integrated strength remains unchanged; displayed windows are never renormalized.

The previous 90/26 reports contain 21 overlapping identities, hence 95 distinct identities. They lack historical source bindings and are **not** evidence that this corrected frozen source passed those runs. New bounded acceptance records are in `outputs/mdff-usability-correction-20261106/frozen-*` outside the worktree: before/after inventories include tracked and added files, command/environment, exit code, logs and JUnit identities. Failed/diagnostic attempts remain recorded separately. The five independent reproduction functions and four existing control cases are retained without assertion changes.

| Unchanged superseded workflow test | Retained-contract replacement in `tests/test_mdff_corrective.py` |
|---|---|
| `test_unified_starting_choices_have_no_material_electronic_defaults` | `test_replacement_defaults_preserve_provenance_grid_and_help`: origins, frame/grid, exact references, help; complete synthetic defaults replace blank inputs. |
| `test_required_physical_definitions_and_blank_material_inputs` | `test_replacement_physical_definitions_units_and_holes`: sections, physical fields, units, provenance and hole explanation. |
| `test_element_drafts_do_not_transfer_or_restore_validation` | `test_replacement_element_roundtrip_clears_executable_validation`: independent edits retained, executable provider/validation cleared. |
| `test_missing_references_and_unsupported_element` | `test_replacement_missing_reference_and_unsupported_rejection`: explicit synthetic missing-reference fallback and unsupported execution rejection. |
| `test_historical_ni_is_not_silently_migrated` | `test_replacement_historical_saved_zero_and_absence`: save/reopen, actual saved energies/splitting, zero versus absent, exact provider preview, explicit reset to new draft. |

Historical tests, guard identities, scientific kernels and numerical references remain unchanged. No current-source additive acceptance gate is implemented or approved here. Independent review of the revised patch and closed identities, followed by an explicitly reviewed additive registration with positive-first gate checks, remains pending before acceptance commit/merge or internal EXE build. Existing guards must continue rejecting unregistered candidate bytes; their historical meaning must not be weakened or auto-updated from live hashes. No broad regression or mutation campaign is claimed.

Do not change the existing generalized editor, packaging, BCC, unit, unified MDFF, single-element or atomic scope manifests, parent archives, historical source maps or numerical fixtures. No existing model formula, atomic generator, solver kernel, historical magnetic reversal implementation or scientific tolerance changes are proposed. The new opt-in phenomenological model has its own analytical profile and explicit reversal assumption.

For a later independent acceptance, an additive scope should authenticate the exact accepted-parent bytes for the seven modified files (including the previously protected imported loader), retain their Git blob identities and compare a closed inventory of the reviewed candidate bytes. Parent bytes must come from the pinned parent commit or authenticated historical archives, not be reconstructed from candidate source. Text canonicalization must retain the established UTF-8-sig / CRLF-to-LF policy; no other normalization is proposed. New module/script/test/docs paths should be explicit, with no wildcard exceptions.

Historical validators should continue to mean the historical source identity. Any current-source extension must apply after those checks and must fail on missing paths, altered candidate bytes, changed historical evidence, malformed declarations and arbitrary added paths. Review must include passing positive checks before isolated mutations targeting every newly covered file, plus existing BW/MS kernel mutations. Do not silently regenerate expected hashes from live files.

## Deliberate UI assertion replacements

Five unchanged historical tests assert blank initial electronic inputs, blank missing references, blank drafts for a newly selected element, or the Ni-only default UI. Those expectations conflict with the requested complete-default, general-purpose interface. The replacement behavior is tested in `tests/test_mdff_usability.py`; the exact five names are listed in the implementation report. A later reviewed test-scope change should preserve those historical assertions against authenticated parent source where appropriate and admit only the reviewed current behavior. No such test-guard adaptation has been silently applied here.

## Current evidence and limits

Focused numerical/provider/editor regressions: 117 passed with the five obsolete workflow cases explicitly deselected. Final redesign suite: 33 passed. Native Windows source walkthrough: both Atomic and manual GUI workers completed, with screenshots at the existing 150% scaling. See the implementation report for logs and remaining warnings.

Existing positive source guards currently fail on the changed UI files, as intended. `outputs/source-guard-results.json` records both guard outcomes independently. They must not be described as passing before this additive scope is reviewed and accepted. No merge, commit, publication or packaging action is included in this proposal.

The XMCD follow-up additionally changes presentation in `stage_b.py` and `mdff_usability.py`: actual-provider preview routing, per-model axis retention, and restoration-aware model/axis presentation. These remain within the six modified UI/I/O paths listed above. No provider, solver, source-format validator, physics formula or project authentication rule was changed. Follow-up verification logs are listed in the implementation report, and final candidate identities are refreshed only as proposal evidence in the inventory; existing accepted maps are not updated.

The subsequent L2,3 extension adds the seventh modified file, `imported_mdff.py`, for strict reserved-tag dispatch only. New analytical behavior is isolated in `manual_l23.py`; stored sampled evidence must agree with the model, and partial provenance is rejected. The existing portable manual-source attachment condition additionally accepts this fully validated source. The new constant-specific fixture explicitly selects the constant option, preserving its old semantics. Existing pinned historical workflow tests remain unchanged with their earlier documented disposition.

Spectral evidence: 90 combined focused checks passed; all 26 final spectral checks passed. Native Single/Double calculations each completed with BW and MS, followed by verified project relocation without the original source. These are implementation checks, not independent acceptance of a new source-scope identity. A later additive guard review should include positive-first mutations of the new model, reserved dispatch, UI, attachment predicate, schemas and frame/profile consistency, alongside unchanged historical solver mutation targets.
