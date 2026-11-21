"""Bounded CPU observations of the canonical engine, not a new simulation.

Run --plan, then --run. Each case has a fresh owned subprocess, one warmup,
two unprofiled repeats and, for selected cases, one separately labelled
all-thread profile. Existing synthetic fixture data are reused as inputs.
No references are generated or production functions monkeypatched.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
import gc
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = "a97ccf14e890b9e52fc57d47261117717825f5ba"
THREAD_ENV = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
              "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")


@dataclass(frozen=True)
class Case:
    name: str
    family: str
    method: str = "bloch"
    channel: str = "single"
    material: str = "Ni"
    beam: float = .9
    potential: float = 1.8
    thickness: float = .3
    depth: int = 9
    grid: int = 9
    fft: int = 16
    energies: int = 2
    workers: int = 1
    maps: bool = True
    radius: float = .12
    partition: str = "all"
    repeat_x: int = 1
    afm: bool = False
    profile: bool = False
    persistence: bool = False


def cases():
    base = Case("ni-bw-single", "solver", profile=True, persistence=True)
    rows = [
        base,
        replace(base, name="ni-bw-double", channel="double", persistence=False),
        replace(base, name="ni-ms-single", method="fft-multislice", persistence=False),
        replace(base, name="ni-ms-double", method="fft-multislice",
                channel="double", persistence=False),
    ]
    bw, ms = rows[1], rows[3]
    rows += [replace(bw, name="bw-beams-" + str(cut), family="beams",
                     beam=cut, potential=3.8, profile=False) for cut in (1.3, 2.5)]
    rows += [replace(base, name="bw-single-beams-2.5", family="beams",
                     beam=2.5, potential=3.8, profile=False, persistence=False)]
    for channel in ("single", "double"):
        rows += [replace(ms, name="ms-" + channel + "-fft-" + str(n),
                         family="fft", channel=channel, fft=n, profile=False)
                 for n in (32, 64)]
    rows += [replace(ms, name="ms-depth-33", family="depth", depth=33, profile=False),
             replace(bw, name="bw-depth-33", family="depth", depth=33, profile=False),
             replace(ms, name="ms-thickness-1.2", family="thickness",
                     thickness=1.2, profile=False)]
    rows += [replace(c, name=c.name + "-energy-9", family="energy",
                     energies=9, profile=False) for c in (bw, ms)]
    rows += [replace(ms, name="ni-medium-2d", family="medium", beam=2.5,
                     potential=3.8, fft=32, grid=17, depth=17,
                     thickness=1., maps=False, profile=True)]
    for channel in ("single", "double"):
        for partition in ("all", "sites"):
            rows.append(Case("cr-" + channel + "-" + partition, "groups",
                             "fft-multislice", channel, material="Cr",
                             beam=.55, potential=.8, thickness=.5,
                             maps=False, partition=partition,
                             profile=channel == "double" and partition == "sites",
                             persistence=channel == "double" and partition == "sites"))
    rows += [replace(rows[-1], name="cr-double-4sites", family="sites",
                     repeat_x=2, profile=False, persistence=False),
             replace(rows[-1], name="cr-double-afm", family="magnetism",
                     afm=True, profile=False, persistence=False)]
    for method in ("bloch", "fft-multislice"):
        rows += [replace(bw, name=("bw" if method == "bloch" else "ms")
                         + "-workers-" + str(w), family="workers",
                         method=method, grid=33, fft=32, depth=17,
                         maps=False, radius=.2, workers=w, profile=False)
                 for w in (1, 2, 4)]
    assert len({c.name for c in rows}) == len(rows)
    return rows


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, default=json_value) + "\n", encoding="utf-8")


def json_value(value):
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "tolist"):
        return value.tolist()
    raise TypeError(type(value).__name__)


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def process_memory():
    """Actual payload process, not the Windows venv launcher stub."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "peak_ws", "ws", "peak_paged", "paged", "peak_nonpaged",
                    "nonpaged", "pagefile", "peak_pagefile", "private")]
        handle = ctypes.WinDLL("kernel32").GetCurrentProcess
        handle.restype = ctypes.c_void_p
        query = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
        query.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), wintypes.DWORD]
        c = Counters()
        c.cb = ctypes.sizeof(c)
        if not query(handle(), ctypes.byref(c), c.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return dict(rss_mib=c.ws / 2**20, commit_mib=c.pagefile / 2**20,
                    peak_rss_mib=c.peak_ws / 2**20,
                    peak_commit_mib=c.peak_pagefile / 2**20)
    import resource
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return dict(peak_rss_mib=peak / (2**20 if sys.platform == "darwin" else 1024))


class MemorySamples:
    """10 ms sampled calculation RSS; lifetime OS peak reported separately."""
    def __enter__(self):
        self.stop = threading.Event()
        self.samples = [process_memory()]
        def sample():
            while not self.stop.wait(.01):
                self.samples.append(process_memory())
        self.thread = threading.Thread(target=sample, name="benchmark-memory")
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set()
        self.thread.join()
        self.samples.append(process_memory())

    def summary(self):
        return dict(interval_seconds=.01, sample_count=len(self.samples),
                    sampled_peak_rss_mib=max(s.get("rss_mib", 0.) for s in self.samples),
                    sampled_peak_commit_mib=max(s.get("commit_mib", 0.) for s in self.samples))


class AllThreadProfile:
    """Observation-only Python call regions; no function or kernel replacement.

    Inclusive worker seconds can exceed elapsed wall time. Exclusive CPU/wall
    values subtract tracked descendants only. Profiling is a separate run.
    """
    modules = {
        "emcd_sim.forward_pipeline", "emcd_sim.propagation", "emcd_sim.channeling",
        "emcd_sim.multisite_integration", "emcd_sim.multisite_double_channeling",
        "emcd_sim.multislice_double_channeling", "emcd_sim.double_channeling",
        "emcd_sim.single_channeling_tensor", "emcd_sim.mdff_providers",
        "emcd_sim.physical_elastic", "emcd_sim.projected_potential",
        "emcd_sim.structure_geometry", "emcd_sim.forward_results",
        "emcd_sim.detector_signals",
    }
    numpy_functions = {"eigh", "einsum", "einsum_path", "_raw_fft"}

    def __init__(self):
        self.local = threading.local()
        self.lock = threading.Lock()
        self.totals = {}

    def observe(self, frame, event, arg):
        if event not in ("call", "return"):
            return
        module = frame.f_globals.get("__name__", "")
        name = frame.f_code.co_name
        if not (module in self.modules or
                (module.startswith("numpy.") and name in self.numpy_functions)):
            return
        stack = getattr(self.local, "stack", None)
        if stack is None:
            stack = self.local.stack = []
        now, cpu = time.perf_counter(), time.thread_time()
        if event == "call":
            stack.append([frame, now, cpu, 0., 0.])
        elif stack and stack[-1][0] is frame:
            _, start, start_cpu, nested, nested_cpu = stack.pop()
            wall, used = now - start, cpu - start_cpu
            key = module + ":" + frame.f_code.co_qualname
            with self.lock:
                row = self.totals.setdefault(key, dict(calls=0, inclusive_wall_seconds=0.,
                    exclusive_wall_seconds=0., inclusive_cpu_seconds=0., exclusive_cpu_seconds=0.))
                row["calls"] += 1
                row["inclusive_wall_seconds"] += wall
                row["exclusive_wall_seconds"] += wall - nested
                row["inclusive_cpu_seconds"] += used
                row["exclusive_cpu_seconds"] += used - nested_cpu
            if stack:
                stack[-1][3] += wall
                stack[-1][4] += used

    def __enter__(self):
        self.previous = sys.getprofile(), threading.getprofile()
        threading.setprofile(self.observe)
        sys.setprofile(self.observe)
        return self

    def __exit__(self, *args):
        sys.setprofile(self.previous[0])
        threading.setprofile(self.previous[1])


def configuration(case, directory):
    """Inputs reused from the existing headless/multisite fixture families."""
    import numpy as np
    from emcd_sim.structure_geometry import Structure, Settings
    from emcd_sim.forward_settings import NiForwardSettings, MultiSiteForwardSettings
    from emcd_sim.study_presets import nickel_geometry_settings
    from emcd_sim.provenance import reference_source
    common = dict(propagation=case.method, channeling_model=case.channel,
                  grid=case.grid, depth=case.depth, subpixels=8, fft_grid=case.fft,
                  slice_step=.01, halfwidth=.7, centers=((.2, .2), (.2, -.2)),
                  radius=case.radius, correction=False, worker_mode="manual",
                  parallel_workers=case.workers, memory_mode="manual",
                  memory_budget_mib=2048, angular_maps=case.maps,
                  # Legacy Ni validates this GUI control even when the public
                  # API receives a smaller explicit energy_ev axis.
                  energy_points=max(9, case.energies))
    provenance = []
    if case.material == "Ni":
        structure = Structure.nickel()
        settings = nickel_geometry_settings(thickness=case.thickness,
            beam_cutoff=case.beam, potential_cutoff=case.potential)
        path = reference_source()
        cfg = NiForwardSettings(axis_declared=True, energy_scope="edges",
            source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), **common)
        energy = np.linspace(cfg.l3, cfg.l2, case.energies)
        kwargs = {}
        provenance.append(dict(path=str(path), sha256=cfg.source_sha256,
                               origin="Tracked historical Ni example; explicit preset"))
    else:
        from ase.build import bulk
        from single_element_helpers import document
        from emcd_sim.multisite import IonizationSiteGroup, MultiSiteIonization
        from emcd_sim.mdff_providers import settings_for_source
        atoms = bulk("Cr", "bcc", a=2.88, cubic=True).repeat((case.repeat_x, 1, 1))
        atoms.set_initial_magnetic_moments([1 if not case.afm or i % 2 == 0 else -1
                                          for i in range(len(atoms))])
        structure = Structure(atoms, "Existing synthetic BCC Cr fixture family")
        settings = Settings(zone=(0, 0, 1), target=(case.repeat_x, 1, 0),
            tilt=(-5., 7.), voltage=200., thickness=case.thickness,
            beam_cutoff=case.beam, potential_cutoff=case.potential)
        groups = []
        indices = [tuple(range(len(atoms)))] if case.partition == "all" else [
            (i,) for i in range(len(atoms))]
        for i, selected in enumerate(indices):
            data = document("Cr")
            sign = -1 if case.afm and i % 2 else 1
            if sign < 0:
                data["magnetization_crystal"] = [0, 0, -1]
                data["T_plus"], data["T_minus"] = data["T_minus"], data["T_plus"]
            path = directory / ("cr-" + str(i) + ".json")
            path.write_text(json.dumps(data), encoding="utf-8")
            ref = settings_for_source(path)
            groups.append(IonizationSiteGroup("Cr-" + str(i), "Cr", selected, ref,
                                             (0, 0, sign), len(selected)))
            provenance.append(dict(path=str(path), sha256=ref.source_sha256,
                origin="tests/single_element_helpers.document and test_multisite_forward.system"))
        cfg = MultiSiteForwardSettings(l3=710., l2=723., selected_edges=(("L3", 710.), ("L2", 723.)),
                                      **common)
        energy = np.linspace(710., 723., case.energies)
        kwargs = dict(sites=MultiSiteIonization(structure, groups))
    return structure, settings, cfg, energy, kwargs, provenance


def fingerprint(result):
    import numpy as np
    digest = hashlib.sha256()
    shapes = []
    def collect(value, path):
        if isinstance(value, np.ndarray):
            array = np.ascontiguousarray(value)
            header = [path, array.dtype.str, list(array.shape)]
            digest.update(json.dumps(header, separators=(",", ":")).encode())
            digest.update(array.tobytes())
            shapes.append(header)
        elif isinstance(value, dict):
            for key in sorted(value):
                if key not in ("metadata", "model", "settings", "config", "configuration",
                               "input_configuration", "structure_snapshot", "comparison"):
                    collect(value[key], path + "/" + str(key))
    collect(result["methods"], "methods")
    return dict(sha256=digest.hexdigest(), arrays=len(shapes), shapes=shapes)


def numerical_summary(result):
    import numpy as np
    r = next(iter(result["methods"].values()))
    raw = np.stack([r["spectra"][key] for key in
                    ("I_A_plus", "I_B_plus", "I_A_minus", "I_B_minus")])
    assert raw.dtype == np.float64 and np.isfinite(raw).all()
    assert r["amplitudes"].dtype == np.complex128
    assert r["coherence"].shape == (r["amplitudes"].shape[1],) * 2
    meta = r["metadata"]
    info = meta["numerics"]
    return dict(beams=len(meta["beam_hkl"]), energy_samples=len(r["spectra"]["energy_ev"]),
        groups=len(r.get("groups", {})),
        detector_support_pixels=sum(1 for v in
            np.logical_or(r["weights"]["A"] > 0, r["weights"]["B"] > 0).ravel() if v),
        actual_workers=result["metadata"]["execution"]["effective_workers"],
        estimated_working_mib=info["estimated_working_mib"],
        estimated_process_peak_mib=info.get("estimated_process_peak_mib"),
        dense_working_estimate_mib=info["dense_working_estimate_mib"],
        raw_min=float(raw.min()), raw_max=float(raw.max()),
        output_observations="Current float64/complex128 production outputs; no rendering",
        memory_estimate=info, scientific_status=meta.get("scientific_status"),
        angular_diagnostics=meta.get("angular_evaluation"),
        single_timings=meta.get("single_channeling_timings"),
        double_timings=meta.get("double_channeling_timings"),
        incoming_seconds=meta.get("incoming_propagation_seconds"),
        fft=meta.get("fft"))


def worker(case, out, repeats, warmups):
    sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
    start_setup = time.perf_counter()
    import numpy as np
    from emcd_sim.forward_pipeline import calculate
    from emcd_sim.hardware_resources import hardware_snapshot
    from emcd_sim.parallel_resources import native_backend_info
    from emcd_sim.structure_geometry import structure_snapshot
    inputs = out / "inputs" / case.name
    inputs.mkdir(parents=True, exist_ok=False)
    structure, settings, cfg, energy, kwargs, provenance = configuration(case, inputs)
    snapshot = structure_snapshot(structure)
    exact = dict(case=asdict(case), settings=asdict(settings), config=asdict(cfg),
                 energy_ev=energy.tolist(), structure=snapshot, sources=provenance)
    setup = time.perf_counter() - start_setup
    # Uniform completed-method metadata contains the working-array estimate;
    # the full process estimate belongs to request-aware resource preflight.
    from emcd_sim.propagation import numerical_info, resolve_fft_configuration
    before = time.perf_counter()
    planned = resolve_fft_configuration(structure, settings, cfg)
    preflight = numerical_info(structure, settings,
        replace(planned, energy_points=len(energy)), ionization_sites=kwargs.get("sites"))
    preflight_seconds = time.perf_counter() - before
    rows, digests = [], []
    result = None
    for index in range(warmups + repeats):
        result = None
        gc.collect()
        stages = []
        with MemorySamples() as samples:
            before = time.perf_counter()
            cpu = time.process_time()
            result = calculate(structure, settings, cfg, energy_ev=energy,
                progress=lambda message: stages.append([time.perf_counter() - before, str(message)]),
                **kwargs)
            elapsed, used = time.perf_counter() - before, time.process_time() - cpu
        peak = process_memory()
        fp = fingerprint(result)
        digests.append(fp["sha256"])
        observed = numerical_summary(result)
        assert not any(n.startswith(("PySide", "PyQt")) for n in sys.modules)
        assert not any(n.startswith("emcd_sim.gui.") and n != "emcd_sim.gui.memory_budget"
                       for n in sys.modules)
        rows.append(dict(kind="warmup" if index < warmups else "measured",
                         index=index, wall_seconds=elapsed, process_cpu_seconds=used,
                         memory=peak, sampled_memory=samples.summary(), fingerprint=fp,
                         observed=observed, stages=stages))
    assert len(set(digests)) == 1, "Repeated outputs differ; preserve evidence and investigate"
    measurements_peak = process_memory()
    profile = None
    if case.profile:
        with AllThreadProfile() as profiler:
            before = time.perf_counter()
            profiled = calculate(structure, settings, cfg, energy_ev=energy, **kwargs)
            elapsed = time.perf_counter() - before
        assert fingerprint(profiled)["sha256"] == digests[-1]
        profile = dict(wall_seconds=elapsed, overhead_in_headline=False,
                       regions=profiler.totals)
        del profiled
    io = None
    if case.persistence:
        from emcd_sim.gui.project_io import save_project, load_project, fingerprints
        directory = out / "io" / case.name
        before = time.perf_counter()
        save_project(result, directory)
        save = time.perf_counter() - before
        before = time.perf_counter()
        restored = load_project(directory)
        load = time.perf_counter() - before
        assert fingerprints(restored) == fingerprints(result)
        io = dict(save_seconds=save, load_seconds=load, lossless_fingerprint_equal=True,
                  bytes=sum(p.stat().st_size for p in directory.rglob("*") if p.is_file()))
    assert not any(n.startswith(("PySide", "PyQt")) for n in sys.modules)
    measured = [r["wall_seconds"] for r in rows if r["kind"] == "measured"]
    report = dict(case=case.name, pid=os.getpid(), source_commit=git("rev-parse", "HEAD"),
        baseline_commit=BASE, status=git("status", "--short"), exact_inputs=exact,
        setup_seconds=setup, preflight_seconds=preflight_seconds, preflight=preflight,
        runs=rows, profile=profile, io=io,
        headline=dict(repeats=len(measured), mean_seconds=statistics.mean(measured),
                      min_seconds=min(measured), max_seconds=max(measured),
                      lifetime_peak_before_profile_io=measurements_peak),
        memory_scope="OS lifetime peak includes imports/setup/warmup/repeats/fingerprints; excludes later profile and project IO. Calculation RSS additionally sampled every 10 ms.",
        hardware=hardware_snapshot(), native=native_backend_info(),
        python=sys.version, executable=sys.executable, platform=platform.platform(),
        versions={n:importlib.metadata.version(n) for n in ("numpy", "scipy", "ase", "spglib")},
        thread_environment={n:os.environ.get(n) for n in THREAD_ENV},
        rendering_measured=False, current_scan_api=False, complete=True)
    dump(out / "cases" / (case.name + ".json"), report)
    print(case.name, "mean", statistics.mean(measured), "seconds", flush=True)


def run_matrix(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    selected = [c for c in cases() if not args.cases or c.name in args.cases.split(",")]
    assert selected, "No selected cases"
    assert not (out / "matrix.json").exists(), "Use a fresh output directory; preserve prior evidence"
    assert git("merge-base", "--is-ancestor", BASE, "HEAD") == ""
    assert not git("diff", BASE, "--", "src", "tests", "packaging", "pyproject.toml")
    assert not git("status", "--porcelain=v1"), "Commit benchmark tooling before recorded measurements"
    (out / "cases").mkdir()
    (out / "logs").mkdir()
    dump(out / "matrix.json", dict(source_commit=git("rev-parse", "HEAD"), baseline_commit=BASE,
         cases=[asdict(c) for c in selected], warmups=args.warmups, repeats=args.repeats,
         per_case_timeout_seconds=120, total_timeout_seconds=900,
         current_scientific_source_unchanged=True))
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(ROOT / "tests")]),
               PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0")
    env.pop("QT_QPA_PLATFORM", None)
    env.update({n:"1" for n in THREAD_ENV})
    temporary = ROOT.parents[1] / "build" / "ng-a-tmp"
    temporary.mkdir(parents=True, exist_ok=True)
    env.update(TEMP=str(temporary), TMP=str(temporary))
    began = time.monotonic()
    for case in selected:
        timeout = min(120., 900. - (time.monotonic() - began))
        if timeout <= 0:
            raise TimeoutError("Bounded matrix exhausted its 900-second budget")
        command = [sys.executable, "-u", "-B", str(Path(__file__).resolve()),
                   "--child", case.name, "--output", str(out),
                   "--repeats", str(args.repeats), "--warmups", str(args.warmups)]
        record = dict(command=command, cwd=str(ROOT), timeout_seconds=timeout)
        with (out / "logs" / (case.name + ".log")).open("wb") as stream:
            child = subprocess.Popen(command, cwd=ROOT, env=env,
                                     stdout=stream, stderr=subprocess.STDOUT)
            record["launcher_pid"] = child.pid
            dump(out / "logs" / (case.name + "-process.json"), record)
            try:
                code = child.wait(timeout=timeout)
            except BaseException:
                if child.poll() is None:
                    if os.name == "nt":
                        subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        child.kill()
                    child.wait()
                raise
        record.update(exit_code=code, ended_wall_seconds=time.monotonic() - began)
        dump(out / "logs" / (case.name + "-process.json"), record)
        print(case.name, "exit", code, "matrix elapsed",
              round(time.monotonic() - began, 2), flush=True)
        if code:
            raise RuntimeError("Case failed: " + case.name + "; see preserved log")
    reports = [json.loads((out / "cases" / (c.name + ".json")).read_text()) for c in selected]
    dump(out / "measurements.json", dict(cases=reports, complete=True,
         elapsed_wall_seconds=time.monotonic() - began))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--child", choices=[c.name for c in cases()])
    parser.add_argument("--cases", help="Comma-separated subset for a bounded pilot")
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "nextgen-a")
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()
    if args.warmups != 1 or args.repeats != 2:
        parser.error("This deliberately bounded design baseline uses one warmup and two repeats")
    if args.plan:
        print(json.dumps([asdict(c) for c in cases()], indent=2))
    elif args.child:
        worker(next(c for c in cases() if c.name == args.child), args.output.resolve(),
               args.repeats, args.warmups)
    elif args.run:
        run_matrix(args)
    else:
        parser.error("Choose --plan or --run")


if __name__ == "__main__":
    main()
