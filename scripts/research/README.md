# Standalone research drivers

Run these from the repository root after installing the package, for example
`python -m pip install -e ".[gui]"`. They use the maintained `emcd_sim` engines;
they are not installed console entry points or part of the frozen GUI.

| Driver | Purpose | Invocation |
| --- | --- | --- |
| `atomic_slicing_diagnostics.py` | P1 oriented-cell and slice-geometry exports; no propagation | `python scripts/research/atomic_slicing_diagnostics.py --help` |
| `fractional_aperture_validation.py` | Original focused aperture study | `python scripts/research/fractional_aperture_validation.py --help` |
| `ni_017_comparison.py` | Matched saved [017]/[710] comparison, including magnetic contractions | `python scripts/research/ni_017_comparison.py` |
| `plot_wien2k_xmcd.py` | Standalone five-column XMCD visualization | `python scripts/research/plot_wien2k_xmcd.py --help` |
| `plot_wien2k_xmcd_suite.py` | Existing XMCD figure suite used by the manual/conditional workflow | `python scripts/research/plot_wien2k_xmcd_suite.py --help` |

The old `python -m emcd_sim.<driver>` paths above have moved. No compatibility
shims remain in the installed package. Function names, arguments and calculation
bodies are retained; relative package imports now use absolute `emcd_sim` imports.
The comparison driver intentionally has no `--help` parser: executing it runs
the original comparison and requires its existing checkpoints. Moving drivers
does not regenerate or modify historical results.
