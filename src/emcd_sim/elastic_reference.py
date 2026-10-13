"""Cross-check FCC Ni elastic Bloch-wave with independent real-space FFT multislice.

IMPORTANT: the *same cutoff independent-atom Fourier potential* is used in
both methods, so their agreement tests numerical propagation, not whether the
truncated potential or finite diffraction basis represents physical Ni.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
import numpy as np

from .crystal import fcc_nickel
from .diffraction import select_diffraction_setup
from .elastic import BeamSet
from .geometry import Microscope
from .multislice_reference import fft_multislice_ni
from .physical_elastic import PhysicalElasticModel
from .scattering import IndependentAtomPotential

CONDITIONS = ("zone-axis", "symmetric-3bc", "near-2bc")


@dataclass(frozen=True)
class FourierCutoffPotential:
    """Explicit finite Fourier-harmonic reference potential, not full IAM Ni."""
    original: IndependentAtomPotential
    cutoff_inv_angstrom: float

    @property
    def crystal(self):
        return self.original.crystal

    @property
    def cell_volume_angstrom3(self):
        return self.original.cell_volume_angstrom3

    def structure_factor(self, hkl):
        return (self.original.structure_factor(hkl) if
                np.linalg.norm(self.crystal.g_vector(hkl)) <= self.cutoff_inv_angstrom + 1e-10
                else 0j)


@dataclass(frozen=True)
class ElasticReferenceConfig:
    conditions: tuple[str, ...] = ("zone-axis", "symmetric-3bc")
    potential_cutoffs_inv_angstrom: tuple[float, ...] = (1.8, 2.2, 3.0)
    thickness_nm: tuple[float, ...] = (10., 30., 50.)
    beam_margin_inv_angstrom: float = 1.2
    fft_grid: int = 32
    slice_step_nm: float = 0.08
    acceleration_kv: float = 200.
    b_factor_angstrom2: float = 0.
    offzone_tilt_mrad: float = 25.
    max_beams: int = 400

    def validate(self):
        if not self.conditions or len(set(self.conditions)) != len(self.conditions) or any(c not in CONDITIONS for c in self.conditions):
            raise ValueError(f"conditions must be unique and in {CONDITIONS}")
        for label, vals in (("potential cutoffs", self.potential_cutoffs_inv_angstrom),
                            ("thickness", self.thickness_nm)):
            a = np.asarray(vals, dtype=float)
            if a.ndim != 1 or not len(a) or not np.all(np.isfinite(a)) or np.any(a <= 0) or np.any(np.diff(a) <= 0):
                raise ValueError(f"{label} must be positive finite increasing values")
        if (self.fft_grid < 12 or self.fft_grid % 2 or self.max_beams < 5 or
            not np.isfinite(self.slice_step_nm) or self.slice_step_nm <= 0 or
            not np.isfinite(self.beam_margin_inv_angstrom) or self.beam_margin_inv_angstrom <= 0 or
            not np.isfinite(self.acceleration_kv) or self.acceleration_kv <= 0 or
            not np.isfinite(self.b_factor_angstrom2) or self.b_factor_angstrom2 < 0 or
            not np.isfinite(self.offzone_tilt_mrad) or self.offzone_tilt_mrad < 0):
            raise ValueError("invalid physical or numerical reference setting")


def _compare_spots(bloch_hkl, bloch_intensity, fft_hkl, fft_intensity) -> float:
    b = {tuple(h): float(v) for h, v in zip(bloch_hkl, bloch_intensity)}
    f = {tuple(h): float(v) for h, v in zip(fft_hkl, fft_intensity)}
    return 0.5*sum(abs(b.get(k, 0.) - f.get(k, 0.)) for k in b.keys() | f.keys())


def run_elastic_reference(config: ElasticReferenceConfig, output: str | Path) -> dict:
    """Benchmark methods at matched Fourier potential, voltage and tilt.

    A small TV error indicates method agreement for a *given truncated
    potential*. Potential and basis convergence must be checked separately.
    """
    config.validate()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    crystal = fcc_nickel()
    records = []
    results = {name: [] for name in config.conditions}
    max_norm_err = 0.
    for condition in config.conditions:
        tilt = select_diffraction_setup(condition, crystal, config.acceleration_kv,
                                        offzone_tilt_mrad=config.offzone_tilt_mrad).tilt_mrad_xy
        for pcut in config.potential_cutoffs_inv_angstrom:
            bcut = pcut + config.beam_margin_inv_angstrom
            beams = BeamSet.zolz(crystal, bcut, max_beams=config.max_beams)
            if len(beams.hkl) >= config.max_beams:
                raise ValueError("Bloch-wave max_beams truncated basis: increase --max-beams")
            p = FourierCutoffPotential(
                IndependentAtomPotential(crystal,
                    debye_waller_b_angstrom2=config.b_factor_angstrom2), pcut)
            bloch = PhysicalElasticModel(crystal, Microscope(config.acceleration_kv, tilt),
                                          beams, potential=p)
            depth = np.asarray(config.thickness_nm, dtype=float)
            bint = np.abs(bloch.amplitudes(depth))**2
            fft = fft_multislice_ni(
                depth, acceleration_kv=config.acceleration_kv, tilt_mrad_xy=tilt,
                grid_points=config.fft_grid, slice_step_nm=config.slice_step_nm,
                potential_cutoff_inv_angstrom=pcut,
                b_factor_angstrom2=config.b_factor_angstrom2)
            max_norm_err = max(max_norm_err, fft.norm_error,
                               float(np.max(np.abs(bint.sum(axis=1)-1))))
            row = {"condition": condition, "tilt_mrad_xy": tuple(tilt),
                   "potential_cutoff": pcut, "bloch_cutoff": bcut,
                   "beam_count": len(beams.hkl), "thickness": depth.tolist(),
                   "bloch_000": bint[:, 0].tolist(),
                   "fft_000": fft.intensity_at((0,0,0)).tolist(),
                   "total_variation": []}
            for j, thick in enumerate(depth):
                tv = _compare_spots(beams.hkl, bint[j], fft.beam_hkl, fft.intensity[j])
                row["total_variation"].append(tv)
                records.append((condition, tilt[0], tilt[1], pcut, bcut,
                                len(beams.hkl), float(thick),float(bint[j,0]),
                                float(fft.intensity_at((0,0,0))[j]), float(tv),
                                float(fft.intensity[j].sum()),float(bint[j].sum())))
            results[condition].append(row)

    with (output / "elastic_reference_results.csv").open("w", newline="",encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(("condition","tilt_x_mrad","tilt_y_mrad","potential_cutoff_inv_A",
                         "bloch_cutoff_inv_A","bloch_beam_count","thickness_nm",
                         "I000_bloch","I000_fft_multislice","total_variation_distance",
                         "total_intensity_fft","total_intensity_bloch"))
        writer.writerows(records)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(len(config.conditions),2,figsize=(11,4*len(config.conditions)),
                         squeeze=False,constrained_layout=True)
    for rowi,condition in enumerate(config.conditions):
        for thick_i,thick in enumerate(config.thickness_nm):
            cutoffs=np.asarray(config.potential_cutoffs_inv_angstrom)
            bloch=np.asarray([v["bloch_000"][thick_i] for v in results[condition]])
            fft=np.asarray([v["fft_000"][thick_i] for v in results[condition]])
            tv=np.asarray([v["total_variation"][thick_i] for v in results[condition]])
            line,=axs[rowi,0].plot(cutoffs,bloch,"o-",label=f"Bloch, {thick:g} nm")
            axs[rowi,0].plot(cutoffs,fft,"x--",color=line.get_color(),label=f"FFT, {thick:g} nm")
            axs[rowi,1].plot(cutoffs,tv,"o-",label=f"{thick:g} nm")
        axs[rowi,0].set(ylabel="Elastic I(000) (normalized)",xlabel="Matched potential Fourier cutoff (cycles/Å)",
                         title=condition+": Bloch vs FFT multislice")
        axs[rowi,1].set(ylabel="Full diffraction total-variation distance",
                         xlabel="Matched potential Fourier cutoff (cycles/Å)",
                         title="Method agreement, NOT potential convergence")
        for ax in axs[rowi]:
            ax.grid(alpha=.25)
            ax.legend(fontsize=7,ncol=2)
    fig.suptitle("FCC Ni [001] | independent FFT split-step vs Bloch-wave | same truncated IAM potential\n"
                 "Agreement tests numerics only; absolute Ni crystal potential remains cutoff dependent")
    fig.savefig(output/"elastic_reference_comparison.png",dpi=165)
    plt.close(fig)
    metadata={"solver1":"finite-basis Bloch-wave matrix eigensystem",
              "solver2":"periodic 2D real-space FFT Strang-split multislice",
              "conditions":list(config.conditions),
              "potential_cutoffs_inv_angstrom":list(config.potential_cutoffs_inv_angstrom),
              "beam_margin_inv_angstrom":config.beam_margin_inv_angstrom,
              "fft_grid":config.fft_grid,"slice_step_nm":config.slice_step_nm,
              "thickness_nm":list(config.thickness_nm),
              "acceleration_kv":config.acceleration_kv,
              "b_factor_angstrom2":config.b_factor_angstrom2,
              "offzone_tilt_mrad":config.offzone_tilt_mrad,
              "max_norm_error":float(max_norm_err),
              "physics_quantitative":False,"emcd_computed":False,
              "assumptions":"identical *truncated* real IAM Fourier potential; independent FFT versus Bloch propagation; no outgoing wave, absorption, TDS or EMCD in reference",
              "warnings":["Agreement at fixed cutoff does not demonstrate convergence to an untruncated Ni potential.",
                          "FFT grid, slice-step, Bloch basis and Fourier potential cutoff require separate convergence.",
                          "The existing diffraction-based single-channeling Gaussian MDFF still requires independent validation."]}
    (output/"elastic_reference_metadata.json").write_text(json.dumps(metadata,indent=2)+"\n",encoding="utf-8")
    max_tv=max(float(v["total_variation"][j]) for group in results.values()
               for v in group for j in range(len(config.thickness_nm)))
    return {"output":str(output),"comparisons":len(records),
            "max_total_variation_distance":max_tv,"max_norm_error":max_norm_err,
            "potential_converged":False,"emcd_computed":False}


def main(argv: list[str] | None = None):
    p=argparse.ArgumentParser(description="Independent FFT multislice vs Bloch-wave: Ni [001] elastic reference")
    p.add_argument("--output",default="outputs/ni_elastic_reference")
    p.add_argument("--conditions",nargs="+",choices=CONDITIONS,default=["zone-axis","symmetric-3bc"])
    p.add_argument("--potential-cutoffs",nargs="+",type=float,default=[1.8,2.2,3.0])
    p.add_argument("--thickness-nm",nargs="+",type=float,default=[10.,30.,50.])
    p.add_argument("--beam-margin",type=float,default=1.2)
    p.add_argument("--fft-grid",type=int,default=32)
    p.add_argument("--slice-step-nm",type=float,default=.08)
    p.add_argument("--acceleration-kv",type=float,default=200.)
    p.add_argument("--b-factor",type=float,default=0.)
    p.add_argument("--offzone-tilt-mrad",type=float,default=25.)
    p.add_argument("--max-beams",type=int,default=400)
    args=p.parse_args(argv)
    conf=ElasticReferenceConfig(tuple(args.conditions), tuple(args.potential_cutoffs),
        tuple(args.thickness_nm), args.beam_margin,args.fft_grid,args.slice_step_nm,
        args.acceleration_kv,args.b_factor,args.offzone_tilt_mrad,args.max_beams)
    try:
        result=run_elastic_reference(conf,args.output)
    except ValueError as exc:
        p.error(str(exc))
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
