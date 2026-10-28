"""FCC Ni [117] projected IAM geometry, in a right-handed (1-10)/(77-2) frame.

The reciprocal primitive cell is oblique: (2,-2,0), (8,6,-2).
FFT indices enumerate this actual lattice, not a rotated [001] potential.
"""
from dataclasses import dataclass
from itertools import product
import numpy as np
from .crystal import Crystal, fcc_nickel
from .elastic import BeamSet
from .geometry import electron_wavelength_angstrom


@dataclass(frozen=True)
class Ni117Geometry:
    a_angstrom: float = 3.524

    @property
    def frame(self):
        axes = np.array([[1., -1., 0.], [7., 7., -2.], [1., 1., 7.]])
        return axes / np.linalg.norm(axes, axis=1)[:, None]

    @property
    def crystal(self):
        ni = fcc_nickel(self.a_angstrom)
        return Crystal(ni.lattice_angstrom @ self.frame.T, ni.fractional_positions, ni.species)

    @property
    def generators(self):
        return np.array([[2, -2, 0], [8, 6, -2]], dtype=int)

    def beams(self, cutoff):
        if not np.isfinite(cutoff) or cutoff <= 0:
            raise ValueError('Positive finite reciprocal cutoff required')
        reciprocal = (self.generators @ self.crystal.reciprocal_angstrom_inv)[:, :2]
        bounds = np.ceil(cutoff * np.linalg.norm(np.linalg.inv(reciprocal), axis=0)).astype(int)
        items = []
        for coordinates in product(*(range(-b, b+1) for b in bounds)):
            h = tuple(int(v) for v in np.asarray(coordinates) @ self.generators)
            length = np.linalg.norm(self.crystal.g_vector(h))
            if length <= cutoff + 1e-12:
                items.append((length, h))
        items.sort(key=lambda item: (round(item[0], 12), item[1]))
        return BeamSet(tuple(h for _, h in items))

    def harmonics(self, grid_points, cutoff):
        if not isinstance(grid_points, int) or grid_points < 12 or grid_points % 2:
            raise ValueError('Even FFT grid >=12 required')
        for h, k, l in self.beams(cutoff).hkl:
            n = -l // 2
            m = (h - 8*n) // 2
            if max(abs(m), abs(n)) >= grid_points // 2:
                raise ValueError('FFT mesh misses physical [117] oriented harmonics')
        f = np.rint(np.fft.fftfreq(grid_points) * grid_points).astype(int)
        m, n = np.meshgrid(f, f, indexing='ij')
        hkl = (m[..., None]*self.generators[0] + n[..., None]*self.generators[1]).reshape(-1, 3)
        return hkl, (hkl @ self.crystal.reciprocal_angstrom_inv)[:, :2]

    def bragg_tilt(self, kv=200.):
        return -500 * electron_wavelength_angstrom(kv) * np.linalg.norm(self.crystal.g_vector((2, -2, 0)))
