"""EXAMPLE ONLY: fictional mu(V) data demonstrate API, not a physical prediction."""
import numpy as np
from emcd_sim.benchmark import nickel_three_beam
from emcd_sim.voltage import TabulatedMagnetization

law = TabulatedMagnetization(voltages_v=(-2, 0, 2), moments_muB=(0.54, 0.60, 0.57))
sim = nickel_three_beam(law)
for voltage in (-2, 0, 2):
    result = sim.run(np.linspace(843, 878, 71), thickness_nm=30, voltage_v=voltage,
                     grid_size=45, depth_steps=32)
    print(f"{voltage:>3} V | {result.moment_muB:.3f} muB/Ni | L3 asymmetry {result.at_edge()[2]:+.6f}")
