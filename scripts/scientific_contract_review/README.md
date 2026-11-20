# Scientific numerical contract diagnostics

These investigation scripts observe existing tests and archived Git source.
They are not production calculation routes, acceptance tests, new reference
arrays, or numerical gates. See
[the review](../../docs/SCIENTIFIC_NUMERICAL_CONTRACT_REVIEW.md).

- `contract_capture.py`: pytest observation plugin. It profiles returns and
  copies arrays; it does not replace the original assertions or numerical
  functions. `capture_error.txt`, if present, indicates incomplete observation,
  independently of the original pytest outcome.
- `history_sweep.py`: original-input Ni kernel history, followed by archived
  pre-refactor and Phase 2 orchestration comparisons. Software import/type
  adapters are explicit. It does not reconstruct old dependency installations.
- `analyze_observations.py`: full-array distributions, repeatability, restored
  operand layouts, Decimal(80) arithmetic, and Cr reduction conditioning.
- `resolution_checks.py`: symmetry on saved Cr arrays, current cancellation
  behavior, a SciPy matrix-exponential cross-check, and earlier Cr source
  comparisons. Its `--history-only` option avoids rerunning the other checks.

Original raw evidence is in `build/scientific-contract-review/`, including each
run's command, environment, source identity, times, PID and exit code in
`*-run.json`. Those ignored local files are not committed expected results.
Do not overwrite that evidence. Failed adapter attempts are retained and are
not counted as scientific passes or failures.

Run from the existing worktree with the Phase 2 Python environment. The recorded
interpreter is `C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe`.
Its NumPy/SciPy packages resolve from the existing `emcd-python` installation;
the capture records the actual loaded BLAS libraries, not just the executable.

For an intentional future reproduction, choose a new evidence directory:

```powershell
$reviewRepo = 'C:\Users\peng863\EMCD-Sim\.worktrees\windows-adaptive-compute'
Set-Location -LiteralPath $reviewRepo
$reviewPython = 'C:\Users\peng863\EMCD-Sim\build\windows-rc\venv\Scripts\python.exe'
$env:PYTHONPATH = "$reviewRepo\src;$reviewRepo\tests;$reviewRepo\scripts\scientific_contract_review"
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONHASHSEED = '0'
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:QT_QPA_PLATFORM = 'offscreen'
Remove-Item Env:OPENBLAS_CORETYPE -ErrorAction SilentlyContinue
Remove-Item Env:NPY_DISABLE_CPU_FEATURES -ErrorAction SilentlyContinue
$env:SCI_REVIEW_ROOT = "$reviewRepo\build\scientific-contract-review\reproduction-example"
if (Test-Path -LiteralPath $env:SCI_REVIEW_ROOT) { throw 'Choose a fresh evidence directory' }
New-Item -ItemType Directory -Path $env:SCI_REVIEW_ROOT | Out-Null
```

Run one pytest node per fresh process, saving stdout and JUnit XML separately.
Expected baseline exit status is **1**, not a clean suite. Do not suppress or
rewrite an assertion. For example:

```powershell
$reviewName = 'a1-r1'
$env:SCI_CONTRACT_OUTPUT = "$env:SCI_REVIEW_ROOT\$reviewName-capture"
& $reviewPython -B -m pytest `
  'tests/test_double_cancellation.py::test_bw_unchanged_and_depth_cancel[numerical]' `
  -q --tb=short -p contract_capture -p no:cacheprovider `
  "--basetemp=$env:SCI_REVIEW_ROOT\$reviewName-tmp" `
  "--junitxml=$env:SCI_REVIEW_ROOT\$reviewName.xml" `
  *> "$env:SCI_REVIEW_ROOT\$reviewName.log"
$LASTEXITCODE
```

Names consumed by the analysis script:

| Case | Original pytest node, relative to `tests/` | Baseline capture names |
| --- | --- | --- |
| a1 | `test_double_cancellation.py::test_bw_unchanged_and_depth_cancel[numerical]` | `a1-r1`, `a1-r2` |
| a2 | `test_double_cancellation.py::test_full_spectrum_unchanged[bloch]` | `a2-r1`, `a2-r2` |
| a3 | `test_double_cancellation.py::test_full_spectrum_unchanged[both]` | `a3-r1`, `a3-r2` |
| b1 | `test_multisite_scientific_validation.py::test_bcc_cr_independent_events_and_symmetry[unequal-mdff-double-bloch]` | `b1-r1-fixed`, `b1-r2` |
| c1 | `test_single_element_ni_compatibility.py::test_original_ni_all_numeric_arrays_exact[double-xmcd]` | `c1-r1`, `c1-r2` |
| c2 | `test_single_element_ni_compatibility.py::test_original_ni_all_numeric_arrays_exact[double-atomic]` | `c2-r1`, `c2-r2` |

The `-fixed` suffix preserves the original observer-repair history; the
scientific test was not fixed. Also capture a1, a2, c1 as `a1-layout`, `a2-layout`,
`c1-layout`, and b1 as `b1-pixel-reduction`. These supply intermediate operands
and their original strides to `analyze_observations.py`. The current plugin
includes that observation support in every capture.

Once those observations exist, unset the pytest-specific output and run the
analysis scripts sequentially:

```powershell
Remove-Item Env:SCI_CONTRACT_OUTPUT -ErrorAction SilentlyContinue
& $reviewPython -B scripts/scientific_contract_review/analyze_observations.py
& $reviewPython -B scripts/scientific_contract_review/history_sweep.py
& $reviewPython -B scripts/scientific_contract_review/resolution_checks.py resolution-current
```

Each script refuses to reuse its output directory. Do not delete original
evidence to make a rerun possible. Choose another `SCI_REVIEW_ROOT`, or another
resolution output name. An archived import/schema error is recorded in the
resolution JSON; **inspect `adapter_error`**, not just the launcher's exit code.

For the environment experiment, set `NPY_DISABLE_CPU_FEATURES=AVX2,FMA3` **or**
`OPENBLAS_CORETYPE=NEHALEM` before starting a new Python process. Give each
capture a new name. NumPy dispatch and OpenBLAS dispatch are independent controls;
verify the actual runtime configuration recorded in `capture.json`. The report
does not recommend changing production environment settings.

Limits: capture retains only the first four returns per observed function/module
and no arbitrary Python objects. Profiling can affect timing, so these are not
performance measurements. Decimal calculations independently evaluate selected
binary64 operands; they are not an independent physical model. Git-source
execution shares modern dependencies and explicitly documented adapters.
