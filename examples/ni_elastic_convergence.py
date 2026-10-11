"""Focused elastic-only convergence diagnostic for FCC Ni [001].

Runs without EELS/MDFF; reports the exit 000 and total scattered elastic
intensity at selected thickness for systematic-row beam truncations.
This is NOT sufficient to validate a full 2D CBED / EMCD convergence.
"""
import argparse
import csv
from pathlib import Path
import numpy as np
from emcd_sim.crystal import fcc_nickel
from emcd_sim.elastic import BeamSet
from emcd_sim.geometry import Microscope
from emcd_sim.physical_elastic import PhysicalElasticModel
from emcd_sim.scattering import IndependentAtomPotential


def main():
    parser = argparse.ArgumentParser(description="Ni physical elastic row convergence")
    parser.add_argument("--thickness-nm", type=float, default=30.0)
    parser.add_argument("--accelerating-kv", type=float, default=200.0)
    parser.add_argument("--max-order", type=int, default=6)
    parser.add_argument("--output", default="outputs/ni_physical/elastic_row_convergence.csv")
    args = parser.parse_args()
    if args.thickness_nm < 0 or args.max_order < 1:
        parser.error("thickness >= 0 and max-order >= 1 are required")
    ni = fcc_nickel()
    potential = IndependentAtomPotential(ni)
    records = []
    for order in range(1, args.max_order+1):
        elastic = PhysicalElasticModel(ni, Microscope(args.accelerating_kv),
                                       BeamSet.systematic_row(order),potential)
        exit_intensity = np.abs(elastic.amplitudes(np.array([args.thickness_nm]))[0])**2
        records.append((order,len(elastic.beams.hkl),exit_intensity[0],
                        exit_intensity.sum(),elastic.extinction_distance_nm((2,0,0))))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w",newline="") as f:
        writer=csv.writer(f)
        writer.writerow(["row_order","beam_count","I_000_at_thickness","total_elastic_intensity","xi_200_nm"])
        writer.writerows(records)
    for order, count, i0, isum, xi in records:
        print(f"row order {order} ({count} beams): I_000 = {i0:.8f}; "
              f"total = {isum:.8f}; two-beam xi200 = {xi:.4f} nm")
    print("Note: row convergence does not guarantee full 2D ZOLZ or EMCD convergence.")


if __name__ == "__main__":
    main()
