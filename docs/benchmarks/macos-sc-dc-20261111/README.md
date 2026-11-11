# Native macOS SC/DC benchmark evidence

[Report](../../MACOS_SC_DC_RESOURCE_BENCHMARK.md) · [Reproduction tools](../../../tools/benchmarks)

- `benchmark_results.json` / `.csv`: exact common configuration, hardware and measured run fields. A stopped feasibility attempt remains INCOMPLETE; its elapsed time is not a completed calculation time.
- `memory_comparison.csv`: SC/DC ratios at identical effective worker count 1, with each memory definition kept separate.
- `worker_scaling.csv`: Double Channeling run records, including separate Auto cases.
- `numerical_comparisons.json`: comparisons against the same backend's completed Manual 1 baseline. Self-reference rows validate baseline arrays but are not independent worker comparisons. Array values use different units; the scale-relative metric uses raw-intensity scales (or 100 percentage points), rather than treating maximum absolute differences across fields as one physical quantity.
- `resource_preflight.json`: 24 packaged-code policy assessments (four modes × 1/2/4/6/8/Auto); this is not a table of 24 executed calculations. SC requests above one are blocked.
- `harness-validation.json`: native CPU-clock calibration and Qt wait/GIL experiment.
- `assessment-context.json`: unavailable Windows references and excluded historical timing trials.
- `runtime-verification.json`: immutable app/release identity and actual numerical-extension dependencies.

The configuration record preserves inherited GUI fields. With the active XMCD provider, `atomic`, `sigma`, `radial` and the disabled post-edge window do not define the calculated source; the acknowledged `provider_declaration` and XMCD file do.

All memory values are MiB (2²⁰ bytes). Budget, conservative total-process estimate, sampled RSS, sampled physical footprint, incremental RSS and lifetime high-water RSS are different quantities. `scientific_window_*` fields select native samples using the direct worker-result timestamp minus the app's calculation duration; signal/sampling latency limits boundary precision. Run/display fields include admission and GUI display. A sampled maximum is not a guaranteed instantaneous peak. A negative incremental RSS is retained when residency fell below the initial baseline; it does not mean negative allocations.

`average_logical_cpus_*` is aggregate process user+system CPU time divided by the corresponding sampled wall interval. Machine CPU percentage divides that value by the detected logical-core count. It includes GUI/probe activity in the same process and does not identify P/E-core placement. Summed queue times are task latency accumulated across tasks, not additive scientific wall time or pure scheduler overhead. Maximum concurrent detector tasks counts overlapping tasks, not proof that all ran simultaneously on CPU.

Raw native samples, large numerical arrays, full saved projects and temporary app/controller builds stay in the dedicated local output directory; they are not committed. No Windows result or timing is synthesized.
