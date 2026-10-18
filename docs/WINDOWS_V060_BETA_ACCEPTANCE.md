# EMCD-Sim 0.6.0 Windows Beta acceptance

Identity: **Double-Channeling EMCD Simulation**, planned tag `v0.6.0-beta.1`.
Double Channeling already shipped in 0.4.5; 0.6.0 consolidates the framework
and unifies Raw / EMCD Asymmetry presentation. This report is in progress;
publication is gated on the remaining frozen and package checks.

## Source gate (PASS)

- 81 focused tests passed (7 narrow/offscreen constrained-layout warnings).
- All six actual Single/Double x BW/MS/Both small native worker cases passed,
  including EELS/maps, Advanced Diagnostics, Browser, project and exports.
- Eight accepted 0.4.5 comparisons (six dispatch profiles and two saved
  242-energy references) are bitwise identical: 356 array fingerprints total.
- Physics, memory and cancellation sources match the starting baseline.
- Signed difference/sum and raw components, mirror support, NaN behavior,
  energy views and display-only immutability passed focused checks.
- Native Windows Qt screen DPR is 1.5 (150%).

Evidence: `outputs/v060_release/source_native/acceptance.json`,
`focused.xml`, `old_source_comparison.json`.

## Remaining gates

Windows packaging, extracted frozen execution, source/frozen comparison,
current screenshots and final documentation: PENDING.
Independent clean-machine acceptance: NOT TESTED.

No physics tolerances are relaxed. The older published 0.4.5 tag/assets are
preserved. Known non-Windows portability issues must be reported separately;
Windows acceptance does not certify Linux or macOS. Scientific limitations
remain the approximate XMCD MDFF, projected potentials, frozen longitudinal
transfer, arbitrary uncalibrated EELS units and representative convergence.
