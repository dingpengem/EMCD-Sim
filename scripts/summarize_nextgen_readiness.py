"""Summarize completed Next-Gen A measurements without rerunning calculations.

Run from any directory. The optional positional path selects a measured matrix.
All generated CSV, JSON and PNG files remain beside that matrix under build/.
Memory scenarios are arithmetic models, not allocations or GPU measurements.
"""
import csv
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def memory_models():
    p, d, e, z, f = 128**2, 128**2, 243, 128, 128**2
    scenarios = [
        ("dense scan-detector-energy float32", p*d*e*4),
        ("dense scan-detector-energy complex64", p*d*e*8),
        ("dense scan-detector-energy float64", p*d*e*8),
        ("dense scan-detector-energy complex128", p*d*e*16),
        ("float32 with 128 interaction-depth bins", p*d*e*z*4),
        ("complex64 with 128 interaction-depth bins", p*d*e*z*8),
        ("float32 depth x2 reversal x2 method x2 channel", p*d*e*z*4*8),
        ("four detector-reversal spectra float32", p*e*4*4),
        ("12 raw-derived detector spectra float32", p*e*12*4),
        ("four detector-reversal depth spectra float32", p*e*z*4*4),
        ("one complex64 wavefield", f*8),
        ("16 incoming probes x129 nodes complex64", 16*129*f*8),
        ("32 outgoing fields x129 nodes complex64", 32*129*f*8),
        ("32 streamed outgoing fields complex64", 32*f*8),
        ("16 probes x4 energy x3 modes x2 reversal fields complex64", 16*4*3*2*f*8),
        ("128 real potential slices float32", z*f*4),
        ("5 energy sets x128 transmission slices complex64", 5*z*f*8),
        ("16 probe x32 detector x4 energy x128 depth x3x3 response complex64",
         16*32*4*z*9*8),
    ]
    return [dict(scenario=name, bytes=size, MiB=size/2**20,
                 GiB=size/2**30, TiB=size/2**40) for name, size in scenarios]


def summarize(directory):
    data = json.loads((directory / "measurements.json").read_text(encoding="utf-8"))
    assert data["complete"] and len(data["cases"]) == 29
    rows, profiles, stages, fingerprints = [], [], [], []
    for case in data["cases"]:
        assert case["complete"] and not case["status"]
        runs = case["runs"]
        assert [r["kind"] for r in runs] == ["warmup", "measured", "measured"]
        assert len({r["fingerprint"]["sha256"] for r in runs}) == 1
        cfg, pre = case["exact_inputs"]["case"], case["preflight"]
        observed, headline = runs[-1]["observed"], case["headline"]
        diagnostics = [v for run in runs[1:]
                       for v in (run["observed"]["angular_diagnostics"] or [])]
        active = [v["executor"]["max_concurrent_tasks"] for v in diagnostics if "executor" in v]
        rows.append(dict(case=case["case"], family=cfg["family"], material=cfg["material"],
            method=cfg["method"], channel=cfg["channel"], beams=observed["beams"],
            fft_side=cfg["fft"] if cfg["method"] == "fft-multislice" else 0,
            thickness_nm=cfg["thickness"], depth_nodes=cfg["depth"],
            energy_samples=observed["energy_samples"], groups=observed["groups"],
            requested_workers=cfg["workers"], effective_workers=max(observed["actual_workers"].values()),
            max_active_tasks=max(active, default=0), angular_maps=cfg["maps"],
            setup_seconds=case["setup_seconds"], preflight_seconds=case["preflight_seconds"],
            warmup_seconds=runs[0]["wall_seconds"], mean_seconds=headline["mean_seconds"],
            min_seconds=headline["min_seconds"], max_seconds=headline["max_seconds"],
            mean_process_cpu_seconds=sum(r["process_cpu_seconds"] for r in runs[1:])/2,
            peak_rss_mib=headline["lifetime_peak_before_profile_io"]["peak_rss_mib"],
            peak_commit_mib=headline["lifetime_peak_before_profile_io"]["peak_commit_mib"],
            sampled_calc_peak_rss_mib=max(r["sampled_memory"]["sampled_peak_rss_mib"] for r in runs),
            estimated_working_mib=pre["estimated_working_mib"],
            estimated_process_peak_mib=pre["estimated_process_peak_mib"],
            scientific_array_count=runs[-1]["fingerprint"]["arrays"],
            output_sha256=runs[-1]["fingerprint"]["sha256"], source_commit=case["source_commit"]))
        fingerprints.append(dict(case=case["case"], **runs[-1]["fingerprint"]))
        for run in runs:
            previous = 0.
            for timestamp, message in run["stages"]:
                stages.append(dict(case=case["case"], kind=run["kind"], index=run["index"],
                    seconds_since_start=timestamp, seconds_since_previous=timestamp-previous,
                    message=message))
                previous = timestamp
        if case["profile"]:
            for name, region in case["profile"]["regions"].items():
                profiles.append(dict(case=case["case"], region=name,
                    profile_wall_seconds=case["profile"]["wall_seconds"], **region))
        if case["io"]:
            assert case["io"]["lossless_fingerprint_equal"]
    assert len({r["source_commit"] for r in rows}) == 1
    models = memory_models()
    assert models[0]["GiB"] == 243 and models[4]["TiB"] == 30.375
    write_csv(directory / "measurements.csv", rows)
    write_csv(directory / "profile-regions.csv", profiles)
    write_csv(directory / "progress-stage-intervals.csv", stages)
    write_csv(directory / "memory-models.csv", models)
    (directory / "memory-models.json").write_text(json.dumps(models, indent=2)+"\n", encoding="utf-8")
    (directory / "output-fingerprints.json").write_text(json.dumps(fingerprints, indent=2)+"\n", encoding="utf-8")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11, 10))
    y = list(range(len(rows)))
    means = [r["mean_seconds"] for r in rows]
    ax.barh(y, means, color="#287c8e")
    ax.errorbar(means, y, xerr=[[r["mean_seconds"]-r["min_seconds"] for r in rows],
        [r["max_seconds"]-r["mean_seconds"] for r in rows]], fmt="none", ecolor="#222222", capsize=2)
    ax.set(yticks=y, yticklabels=[r["case"] for r in rows], xlabel="Calculation wall time (s)",
        title="Measured CPU calculations: mean and min/max of two repeats")
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=.2)
    fig.tight_layout()
    fig.savefig(directory / "cpu-timings.png", dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(y, [r["estimated_process_peak_mib"] for r in rows], "o-", label="Preflight estimate")
    ax.plot(y, [r["peak_rss_mib"] for r in rows], "o-", label="OS lifetime peak before profile/IO")
    ax.set(xlabel="Case index (CSV order, zero based)", ylabel="MiB",
           title="Estimated vs measured payload-process memory (different documented scopes)")
    ax.legend()
    ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(directory / "cpu-memory.png", dpi=180)
    plt.close(fig)
    print(f"Summarized {len(rows)} cases, {len(profiles)} profile regions; no scientific calculations rerun.")


if __name__ == "__main__":
    summarize(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "build/nextgen-a/measured")
