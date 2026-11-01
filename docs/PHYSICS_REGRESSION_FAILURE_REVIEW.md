# Review of all 15 pre-existing regression failures

Source: local main `a77f7455f5fe57dad6bae5d948477b2390433bb0`.
No production correction or existing-test edit has been applied.

The original complete-suite run was 558 passed, 15 failed, 2 skipped. It
collected the existing tests before audit tests were added. All baseline
production and existing-test fingerprints remain identical. Thus these are
pre-existing at the audited HEAD, not failures introduced by audit edits.
They do not exercise the two disputed physics operations at their failure
points. This does not imply that the convention defects are harmless.

| Classification | Count | Independent check |
|---|---:|---|
| Historical source provenance mismatch | 1 | Reproduced in isolation; numeric source arrays exactly equal |
| Process RSS / GUI test isolation | 9 | All 12 original input cases pass fresh-process; full-suite gate correctly rejects |
| Old default expectation | 2 | Reproduced in isolation; git diff a77f745 establishes approved default change |
| Old widget-ownership expectation | 3 | Reproduced in isolation; same commit intentionally moves editable control |
| Caused by MDFF/site-phase discrepancies at the failing assertion | 0 | Each assertion/call path inspected |

Fresh-process rerun of the six non-resource cases: **6 failed in 72.35 s**,
with the same causes; no new solver or scientific-data changes. Evidence:
`build/physics-matrix-audit/six-isolated.log` and `.xml`.
The earlier original-file GUI rerun remains **12 passed, 20 deselected in
159.23 s**, with its memory policy unchanged (`gui-isolated.log/.xml`).
Neither fresh run changes the original complete-suite result.

Reproduce the six persistent cases in a fresh process with the environment
listed in `PHYSICS_VALIDATION_RESULTS.md`:

```powershell
python -B -m pytest tests/test_double_channeling_full_outputs.py::test_orientation_source_reproduction_and_preservation tests/test_solver_settings_ui.py::test_released_configuration_exactly_preserved tests/test_solver_settings_ui.py::test_solver_visibility_and_classification -q -p no:cacheprovider
```

This currently exits with six failures. No suppression or science change is
proposed as part of the regression diagnosis.

The memory cases fail at `emcd_button.isEnabled()` after preflight, not a
scattering calculation. Their common dense estimate is 418.6 MiB; arrays
445.8 MiB. The selected budget remains 2048 MiB. Estimated peak rises from
2057.2 to 2117.1 MiB as process RSS rises from 1372.0 to 1431.8 MiB. These
measurements support order/process-lifetime sensitivity; they do not by
themselves prove a production leak or an available-system-RAM shortage.
A future test-isolation fix must preserve genuine over-budget rejection,
exercise real input widgets, release Qt resources or isolate test processes,
and keep dedicated low-memory rejection controls. Do not raise the budget
or mock admission to force these assertions to pass.

The source assertion compares this worktree's `4fd517af3e54db94588a76b7a6ed9c2f9a1b745cd8fe52b9fca0f87fc4938db3`
with historical `a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283`.
Those byte hashes genuinely differ; `source_format_comparison.json` records
exact numeric equality, not permission to overwrite old provenance. The
original private source remains untouched. A future compatibility test should
verify the original artifact by its actual provenance and explicitly distinguish
semantic numeric comparison from byte identity. No historical manifest should
be rewritten to match the other copy.

The five UI failures inspect `tests/test_solver_settings_ui.py` against old
controls from `2ede25e63827830617b335a4df6d9d521ac65a9b`. Commit `a77f745`
intentionally changes default .04 to 2 nm and moves the slice-step control
outside the collapsible manual MS group so it is editable in both numerical
modes. The tests were not updated for those two intentional changes. Future
maintenance should compare **matched explicit legacy values** and functional
visibility/editability rather than restoring obsolete defaults/parent widgets.
No test has been suppressed, edited or given a weaker tolerance here.

## Exact per-failure inventory

### 1. `tests.test_double_channeling_full_outputs::test_orientation_source_reproduction_and_preservation`

Classification: **Pre-existing provenance mismatch (not physics)**. Historical source SHA256 differs; parsed 4329x5 source values are exactly equal. Failure reproduces in isolated run.

Exact failure message from baseline JUnit (addresses preserved):

```text
AssertionError: assert '4fd517af3e54...0f87fc4938db3' == 'a0e28ea6423b...56b49ba501283'
  
  - a0e28ea6423b6c7832bb3cce6d69d71aa59336a221baeee3d2556b49ba501283
  + 4fd517af3e54db94588a76b7a6ed9c2f9a1b745cd8fe52b9fca0f87fc4938db3
```

### 2. `tests.test_multislice_slice_step_range::test_manual_gui_preserves_requested_maximum[automatic-2.0]`

Classification: **Test isolation / process-memory environment (not physics)**. Full-suite RSS exceeds unmodified 2048 MiB peak gate; all 12 original GUI cases pass in fresh process.

Exact failure message from baseline JUnit (addresses preserved):

```text
AssertionError: RESOURCE REJECTED: Conservative execution allowed with a caution; passing memory admission is not native-stability certification. Memory admission rejected: dense kernel 418.6 MiB; estimated arrays 445.8 MiB; estimated total process peak 2057.2 MiB exceeds selected budget 2048 MiB. Includes current RSS 1372.0 MiB, 0 active calculation(s), 25% allocation margin and 128 MiB reserve. No simulation parameters were changed. Choose a larger supported budget or free RAM; any sampling change must be explicit.
assert False
 +  where False = <built-in method isEnabled of PySide6.QtWidgets.QPushButton object at 0x000001EE9FD05940>()
 +    where <built-in method isEnabled of PySide6.QtWidgets.QPushButton object at 0x000001EE9FD05940> = <PySide6.QtWidgets.QPushButton(0x1ee9ebd5a60) at 0x000001EE9FD05940>.isEnabled
 +      where <PySide6.QtWidgets.QPushButton(0x1ee9ebd5a60) at 0x000001EE9FD05940> = <emcd_sim.gui.app.MainWindow(0x1ee9e9b2460) at 0x000001EE9FCAB240>.emcd_button
```

### 3. `tests.test_multislice_slice_step_range::test_manual_gui_preserves_requested_maximum[automatic-5.0]`

Classification: **Test isolation / process-memory environment (not physics)**. Full-suite RSS exceeds unmodified 2048 MiB peak gate; all 12 original GUI cases pass in fresh process.

Exact failure message from baseline JUnit (addresses preserved):

```text
AssertionError: RESOURCE REJECTED: Conservative execution allowed with a caution; passing memory admission is not native-stability certification. Memory admission rejected: dense kernel 418.6 MiB; estimated arrays 445.8 MiB; estimated total process peak 2064.8 MiB exceeds selected budget 2048 MiB. Includes current RSS 1379.6 MiB, 0 active calculation(s), 25% allocation margin and 128 MiB reserve. No simulation parameters were changed. Choose a larger supported budget or free RAM; any sampling change must be explicit.
assert False
 +  where False = <built-in method isEnabled of PySide6.QtWidgets.QPushButton object at 0x000001EE9B61AFC0>()
 +    where <built-in method isEnabled of PySide6.QtWidgets.QPushButton object at 0x000001EE9B61AFC0> = <PySide6.QtWidgets.QPushButton(0x1ee9ebe9d00) at 0x000001EE9B61AFC0>.isEnabled
 +      where <PySide6.QtWidgets.QPushButton(0x1ee9ebe9d00) at 0x000001EE9B61AFC0> = <emcd_sim.gui.app.MainWindow(0x1ee9e98ef10) at 0x000001EE9A396A40>.emcd_button
```

### 4. `tests.test_multislice_slice_step_range::test_manual_gui_preserves_requested_maximum[automatic-10.0]`

Classification: **Test isolation / process-memory environment (not physics)**. Full-suite RSS exceeds unmodified 2048 MiB peak gate; all 12 original GUI cases pass in fresh process.

Exact failure message from baseline JUnit (addresses preserved):

```text
AssertionError: RESOURCE REJECTED: Conservative execution allowed with a caution; passing memory admission is not native-stability certification. Memory admission rejected: dense kernel 418.6 MiB; estimated arrays 445.8 MiB; estimated total process peak 2072.4 MiB exceeds selected budget 2048 MiB. Includes current RSS 1387.2 MiB, 0 active calculation(s), 25% allocation margin and 128 MiB reserve. No simulation parameters were changed. Choose a larger supported budget or free RAM; any sampling change must be explicit.
assert False
 +  where False = <built-in method isEnabled of PySide6.QtWidgets.QPushButton object at 0x000001EE9FD73780>()
 +    where <built-in method isEnabled of PySide6.QtWidgets.QPushButton object at 0x000001EE9FD73780> = <PySide6.QtWidgets.QPushButton(0x1ee9ebb5b40) at 0x000001EE9FD73780>.isEnabled
 +      where <PySide6.QtWidgets.QPushButton(0x1ee9ebb5b40) at 0x000001EE9FD73780> = <emcd_sim.gui.app.MainWindow(0x1ee9f6b5740) at 0x000001EEA0551380>.emcd_button
```

### 5. `tests.test_multislice_slice_step_range::test_manual_gui_preserves_requested_maximum[manual-0.04]`

Classification: **Test isolation / process-memory environment (not physics)**. Full-suite RSS exceeds unmodified 2048 MiB peak gate; all 12 original GUI cases pass in fresh process.

Exact failure message from baseline JUnit (addresses preserved):

```text
AssertionError: RESOURCE REJECTED: Conservative execution allowed with a caution; passing memory admission is not native-stability certification. Memory admission rejected: dense kernel 418.6 MiB; estimated arrays 445.8 MiB; estimated total process peak 2079.2 MiB exceeds selected budget 2048 MiB. Includes current RSS 1393.9 MiB, 0 active calculation(s), 25% allocation margin and 128 MiB reserve. No simulation parameters were changed. Choose a larger supported budget or free RAM; any sampling change must be explicit.
assert False
 +  where False = <built-in method isEnabled of PySide6.QtWidgets.QPushButton object at 0x000001EEA194E440>()
 +    where <built-in method isEnabled of PySide6.QtWidgets.QPushButton object at 0x000001EEA194E440> = <PySide6.QtWidgets.QPushButton(0x1eea0d81a10) at 0x000001EEA194E440>.isEnabled
 +      where <PySide6.QtWidgets.QPushButton(0x1eea0d81a10) at 0x000001EEA194E440> = <emcd_sim.gui.app.MainWindow(0x1ee9f6d23f0) at 0x000001EEA176EB40>.emcd_button
```

### 6. `tests.test_multislice_slice_step_range::test_manual_gui_preserves_requested_maximum[manual-0.5]`

Classification: **Test isolation / process-memory environment (not physics)**. Full-suite RSS exceeds unmodified 2048 MiB peak gate; all 12 original GUI cases pass in fresh process.

Exact failure message from baseline JUnit (addresses preserved):

```text
AssertionError: RESOURCE REJECTED: Conservative execution allowed with a caution; passing memory admission is not native-stability certification. Memory admission rejected: dense kernel 418.6 MiB; estimated arrays 445.8 MiB; estimated total process peak 2086.4 MiB exceeds selected budget 2048 MiB. Includes current RSS 1401.1 MiB, 0 active calculation(s), 25% allocation margin and 128 MiB reserve. No simulation parameters were changed. Choose a larger supported budget or free RAM; any sampling change must be explicit.
assert False
 +  where False = <built-in method isEnabled of PySide6.QtWidgets.QPushButton object at 0x000001EEA1AA0480>()
 +    where <built-in method isEnabled of PySide6.QtWidgets.QPushButton object at 0x000001EEA1AA0480> = <PySide6.QtWidgets.QPushButton(0x1eea0d91090) at 0x000001EEA1AA0480>.isEnabled
 +      where <PySide6.QtWidgets.QPushButton(0x1eea0d91090) at 0x000001EEA1AA0480> = <emcd_sim.gui.app.MainWindow(0x1eea0edc990) at 0x000001EEA05D1180>.emcd_button
```

### 7. `tests.test_multislice_slice_step_range::test_manual_gui_preserves_requested_maximum[manual-1.0]`

Classification: **Test isolation / process-memory environment (not physics)**. Full-suite RSS exceeds unmodified 2048 MiB peak gate; all 12 original GUI cases pass in fresh process.

Exact failure message from baseline JUnit (addresses preserved):

```text
AssertionError: RESOURCE REJECTED: Conservative execution allowed with a caution; passing memory admission is not native-stability certification. Memory admission rejected: dense kernel 418.6 MiB; estimated arrays 445.8 MiB; estimated total process peak 2094.4 MiB exceeds selected budget 2048 MiB. Includes current RSS 1409.1 MiB, 0 active calculation(s), 25% allocation margin and 128 MiB reserve. No simulation parameters were changed. Choose a larger supported budget or free RAM; any sampling change must be explicit.
assert False
 +  where False = <built-in method isEnabled of PySide6.QtWidgets.QPushButton object at 0x000001EEA2CEFFC0>()
 +    where <built-in method isEnabled of PySide6.QtWidgets.QPushButton object at 0x000001EEA2CEFFC0> = <PySide6.QtWidgets.QPushButton(0x1eea0d9f4f0) at 0x000001EEA2CEFFC0>.isEnabled
 +      where <PySide6.QtWidgets.QPushButton(0x1eea0d9f4f0) at 0x000001EEA2CEFFC0> = <emcd_sim.gui.app.MainWindow(0x1eea0efbec0) at 0x000001EEA1776700>.emcd_button
```

### 8. `tests.test_multislice_slice_step_range::test_manual_gui_preserves_requested_maximum[manual-2.0]`

Classification: **Test isolation / process-memory environment (not physics)**. Full-suite RSS exceeds unmodified 2048 MiB peak gate; all 12 original GUI cases pass in fresh process.

Exact failure message from baseline JUnit (addresses preserved):

```text
AssertionError: RESOURCE REJECTED: Conservative execution allowed with a caution; passing memory admission is not native-stability certification. Memory admission rejected: dense kernel 418.6 MiB; estimated arrays 445.8 MiB; estimated total process peak 2102.4 MiB exceeds selected budget 2048 MiB. Includes current RSS 1417.1 MiB, 0 active calculation(s), 25% allocation margin and 128 MiB reserve. No simulation parameters were changed. Choose a larger supported budget or free RAM; any sampling change must be explicit.
assert False
 +  where False = <built-in method isEnabled of PySide6.QtWidgets.QPushButton object at 0x000001EEA2EA3780>()
 +    where <built-in method isEnabled of PySide6.QtWidgets.QPushButton object at 0x000001EEA2EA3780> = <PySide6.QtWidgets.QPushButton(0x1eea0db3790) at 0x000001EEA2EA3780>.isEnabled
 +      where <PySide6.QtWidgets.QPushButton(0x1eea0db3790) at 0x000001EEA2EA3780> = <emcd_sim.gui.app.MainWindow(0x1eea2160db0) at 0x000001EEA2C7DE00>.emcd_button
```

### 9. `tests.test_multislice_slice_step_range::test_manual_gui_preserves_requested_maximum[manual-5.0]`

Classification: **Test isolation / process-memory environment (not physics)**. Full-suite RSS exceeds unmodified 2048 MiB peak gate; all 12 original GUI cases pass in fresh process.

Exact failure message from baseline JUnit (addresses preserved):

```text
AssertionError: RESOURCE REJECTED: Conservative execution allowed with a caution; passing memory admission is not native-stability certification. Memory admission rejected: dense kernel 418.6 MiB; estimated arrays 445.8 MiB; estimated total process peak 2110.1 MiB exceeds selected budget 2048 MiB. Includes current RSS 1424.9 MiB, 0 active calculation(s), 25% allocation margin and 128 MiB reserve. No simulation parameters were changed. Choose a larger supported budget or free RAM; any sampling change must be explicit.
assert False
 +  where False = <built-in method isEnabled of PySide6.QtWidgets.QPushButton object at 0x000001EEA2EFB780>()
 +    where <built-in method isEnabled of PySide6.QtWidgets.QPushButton object at 0x000001EEA2EFB780> = <PySide6.QtWidgets.QPushButton(0x1eea0d809c0) at 0x000001EEA2EFB780>.isEnabled
 +      where <PySide6.QtWidgets.QPushButton(0x1eea0d809c0) at 0x000001EEA2EFB780> = <emcd_sim.gui.app.MainWindow(0x1eea217a970) at 0x000001EEA2C912C0>.emcd_button
```

### 10. `tests.test_multislice_slice_step_range::test_manual_gui_preserves_requested_maximum[manual-10.0]`

Classification: **Test isolation / process-memory environment (not physics)**. Full-suite RSS exceeds unmodified 2048 MiB peak gate; all 12 original GUI cases pass in fresh process.

Exact failure message from baseline JUnit (addresses preserved):

```text
AssertionError: RESOURCE REJECTED: Conservative execution allowed with a caution; passing memory admission is not native-stability certification. Memory admission rejected: dense kernel 418.6 MiB; estimated arrays 445.8 MiB; estimated total process peak 2117.1 MiB exceeds selected budget 2048 MiB. Includes current RSS 1431.8 MiB, 0 active calculation(s), 25% allocation margin and 128 MiB reserve. No simulation parameters were changed. Choose a larger supported budget or free RAM; any sampling change must be explicit.
assert False
 +  where False = <built-in method isEnabled of PySide6.QtWidgets.QPushButton object at 0x000001EEA42EB780>()
 +    where <built-in method isEnabled of PySide6.QtWidgets.QPushButton object at 0x000001EEA42EB780> = <PySide6.QtWidgets.QPushButton(0x1eea2ad14b0) at 0x000001EEA42EB780>.isEnabled
 +      where <PySide6.QtWidgets.QPushButton(0x1eea2ad14b0) at 0x000001EEA42EB780> = <emcd_sim.gui.app.MainWindow(0x1eea3490460) at 0x000001EEA2EEB240>.emcd_button
```

### 11. `tests.test_solver_settings_ui::test_released_configuration_exactly_preserved[0]`

Classification: **Stale pre-existing expectation after approved UI/default change (not physics)**. Expected 0.04 nm from old control versus approved 2 nm default introduced in a77f745. Isolated failure reproduces.

Exact failure message from baseline JUnit (addresses preserved):

```text
AssertionError: assert ForwardSettin...nerators=None) == ForwardSettin...nerators=None)
  
  Omitting 31 identical items, use -vv to show
  Differing attributes:
  ['slice_step']
  
  Drill down into differing attribute slice_step:
    slice_step: 2.0 != 0.04
```

### 12. `tests.test_solver_settings_ui::test_released_configuration_exactly_preserved[1]`

Classification: **Stale pre-existing expectation after approved UI/default change (not physics)**. Expected 0.04 nm from old control versus approved 2 nm default introduced in a77f745. Isolated failure reproduces.

Exact failure message from baseline JUnit (addresses preserved):

```text
AssertionError: assert ForwardSettin...nerators=None) == ForwardSettin...nerators=None)
  
  Omitting 31 identical items, use -vv to show
  Differing attributes:
  ['slice_step']
  
  Drill down into differing attribute slice_step:
    slice_step: 2.0 != 0.04
```

### 13. `tests.test_solver_settings_ui::test_solver_visibility_and_classification[0]`

Classification: **Stale pre-existing layout expectation after approved UI change (not physics)**. Slice-step control moved outside legacy MS group in a77f745 for editing in Automatic mode. Isolated failure reproduces.

Exact failure message from baseline JUnit (addresses preserved):

```text
assert False
 +  where False = <built-in method isAncestorOf of PySide6.QtWidgets.QGroupBox object at 0x000001EEAA2A6CC0>(<PySide6.QtWidgets.QDoubleSpinBox(0x1eea8ad9a30) at 0x000001EEAA3126C0>)
 +    where <built-in method isAncestorOf of PySide6.QtWidgets.QGroupBox object at 0x000001EEAA2A6CC0> = <PySide6.QtWidgets.QGroupBox(0x1eea8ea7a90, name="legacy_settings_Multislice_numerical_settings") at 0x000001EEAA2A6CC0>.isAncestorOf
 +      where <PySide6.QtWidgets.QGroupBox(0x1eea8ea7a90, name="legacy_settings_Multislice_numerical_settings") at 0x000001EEAA2A6CC0> = <emcd_sim.gui.app.MainWindow(0x1eea8eb5e60) at 0x000001EEA9ED8040>.ms_settings_group
```

### 14. `tests.test_solver_settings_ui::test_solver_visibility_and_classification[1]`

Classification: **Stale pre-existing layout expectation after approved UI change (not physics)**. Slice-step control moved outside legacy MS group in a77f745 for editing in Automatic mode. Isolated failure reproduces.

Exact failure message from baseline JUnit (addresses preserved):

```text
assert False
 +  where False = <built-in method isAncestorOf of PySide6.QtWidgets.QGroupBox object at 0x000001EEAA34EE40>(<PySide6.QtWidgets.QDoubleSpinBox(0x1eea8adfef0) at 0x000001EEAB63C500>)
 +    where <built-in method isAncestorOf of PySide6.QtWidgets.QGroupBox object at 0x000001EEAA34EE40> = <PySide6.QtWidgets.QGroupBox(0x1eeaa930010, name="legacy_settings_Multislice_numerical_settings") at 0x000001EEAA34EE40>.isAncestorOf
 +      where <PySide6.QtWidgets.QGroupBox(0x1eeaa930010, name="legacy_settings_Multislice_numerical_settings") at 0x000001EEAA34EE40> = <emcd_sim.gui.app.MainWindow(0x1eeaa92f290) at 0x000001EEAB643840>.ms_settings_group
```

### 15. `tests.test_solver_settings_ui::test_solver_visibility_and_classification[2]`

Classification: **Stale pre-existing layout expectation after approved UI change (not physics)**. Slice-step control moved outside legacy MS group in a77f745 for editing in Automatic mode. Isolated failure reproduces.

Exact failure message from baseline JUnit (addresses preserved):

```text
assert False
 +  where False = <built-in method isAncestorOf of PySide6.QtWidgets.QGroupBox object at 0x000001EEAA2A6E40>(<PySide6.QtWidgets.QDoubleSpinBox(0x1eea8ae6b70) at 0x000001EEAB99A6C0>)
 +    where <built-in method isAncestorOf of PySide6.QtWidgets.QGroupBox object at 0x000001EEAA2A6E40> = <PySide6.QtWidgets.QGroupBox(0x1eeaa950620, name="legacy_settings_Multislice_numerical_settings") at 0x000001EEAA2A6E40>.isAncestorOf
 +      where <PySide6.QtWidgets.QGroupBox(0x1eeaa950620, name="legacy_settings_Multislice_numerical_settings") at 0x000001EEAA2A6E40> = <emcd_sim.gui.app.MainWindow(0x1eeaa946780) at 0x000001EEAB7DA4C0>.ms_settings_group
```
