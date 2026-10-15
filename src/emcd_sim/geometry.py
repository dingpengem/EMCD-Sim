"""Relativistic wavelength and reciprocal-space virtual detectors."""
from dataclasses import dataclass
from functools import lru_cache
import numpy as np

HC_EV_ANGSTROM = 12398.419843320026
MC2_EV = 510998.95


def electron_wavelength_angstrom(acceleration_kv: float) -> float:
    """Relativistic de Broglie wavelength in angstroms."""
    if acceleration_kv <= 0:
        raise ValueError("accelerating voltage must be positive")
    kinetic_ev = acceleration_kv * 1e3
    return HC_EV_ANGSTROM / np.sqrt(kinetic_ev * (kinetic_ev + 2 * MC2_EV))


def electron_beta(acceleration_kv: float) -> float:
    if acceleration_kv <= 0:
        raise ValueError("accelerating voltage must be positive")
    gamma = 1.0 + acceleration_kv * 1e3 / MC2_EV
    return float(np.sqrt(1.0 - 1.0 / gamma**2))


def characteristic_qz_angstrom_inv(loss_ev: float, acceleration_kv: float) -> float:
    """Small-loss longitudinal momentum transfer E/(h*v), cycles per angstrom."""
    if loss_ev <= 0:
        raise ValueError("energy loss must be positive")
    return loss_ev / (HC_EV_ANGSTROM * electron_beta(acceleration_kv))


@dataclass(frozen=True)
class Microscope:
    acceleration_kv: float = 200.0
    tilt_mrad_xy: tuple[float, float] = (0.0, 0.0)

    def __post_init__(self) -> None:
        electron_wavelength_angstrom(self.acceleration_kv)
        if len(self.tilt_mrad_xy) != 2:
            raise ValueError("tilt_mrad_xy must be a pair")

    @property
    def incident_k_xy(self) -> np.ndarray:
        return np.asarray(self.tilt_mrad_xy, dtype=float) * 1e-3 / electron_wavelength_angstrom(self.acceleration_kv)


@dataclass(frozen=True)
class VirtualDetector:
    """Circular virtual EELS aperture in reciprocal units, cycles per angstrom."""
    center_q_xy: tuple[float, float]
    radius_q: float

    def __post_init__(self) -> None:
        if len(self.center_q_xy) != 2 or self.radius_q <= 0:
            raise ValueError("detector needs center (qx,qy) and positive radius")

    def mask(self, qx: np.ndarray, qy: np.ndarray) -> np.ndarray:
        return ((qx - self.center_q_xy[0]) ** 2
                + (qy - self.center_q_xy[1]) ** 2 <= self.radius_q**2)

    def integration_weights(self, qx, qy, *, mode='binary', subpixels=64):
        """Area fractions for pixels centered on a regular Cartesian xy grid.

        Binary weights retain center membership. Fractional weights estimate
        circle/square overlap by midpoint sampling only boundary pixels. The
        pixel domain extends half a spacing beyond the outer sample centers.
        Cached geometry-only weights are reused across energies and states.
        """
        validate_detector_integration(mode, subpixels)
        qx, qy = np.asarray(qx, float), np.asarray(qy, float)
        if (qx.ndim != 2 or qx.shape != qy.shape or min(qx.shape)<2
                or not np.isfinite(qx).all() or not np.isfinite(qy).all()
                or not np.isfinite(self.center_q_xy).all() or not np.isfinite(self.radius_q)):
            raise ValueError('Weights require finite detector geometry and a 2D grid of at least 2x2')
        x, y = qx[0,:], qy[:,0]
        if (not np.allclose(qx,x[None,:],rtol=0,atol=1e-14)
                or not np.allclose(qy,y[:,None],rtol=0,atol=1e-14)
                or np.any(np.diff(x)<=0) or np.any(np.diff(y)<=0)
                or not np.allclose(np.diff(x),x[1]-x[0],rtol=1e-10,atol=1e-14)
                or not np.allclose(np.diff(y),y[1]-y[0],rtol=1e-10,atol=1e-14)):
            raise ValueError('Weights require an increasing uniform Cartesian xy grid')
        return _circle_pixel_weights(tuple(self.center_q_xy),float(self.radius_q),
                                     tuple(x),tuple(y),mode,subpixels)

    def integration_info(self, qx, qy, *, mode='binary', subpixels=64):
        """Actual represented area; never rescale weights to the analytic area."""
        weights = self.integration_weights(qx,qy,mode=mode,subpixels=subpixels)
        dx,dy = qx[0,1]-qx[0,0], qy[1,0]-qy[0,0]
        area = float(weights.sum()*dx*dy)
        analytic = float(np.pi*self.radius_q**2)
        cx,cy = self.center_q_xy
        return dict(integration_mode=mode,aperture_subpixels=subpixels,
            effective_area=area,analytical_area=analytic,area_error=area-analytic,
            relative_area_error=(area-analytic)/analytic,
            weight_sum=float(weights.sum()),weighted_pixels=int(np.count_nonzero(weights)),
            aperture_fully_covered=bool(qx.min()-dx/2 <= cx-self.radius_q
                and cx+self.radius_q <= qx.max()+dx/2 and qy.min()-dy/2 <= cy-self.radius_q
                and cy+self.radius_q <= qy.max()+dy/2))


def validate_detector_integration(mode: str, subpixels: int) -> None:
    if mode not in ('binary', 'fractional'):
        raise ValueError("Detector integration must be binary or fractional")
    if not isinstance(subpixels, int) or isinstance(subpixels, bool) or subpixels < 1:
        raise ValueError("Aperture subpixels must be a positive integer")


@lru_cache(maxsize=128)
def _circle_pixel_weights(center, radius, x_axis, y_axis, mode, subpixels):
    """Cached read-only weights: only intersected boundary pixels are sampled."""
    qx, qy = np.meshgrid(x_axis, y_axis, indexing='xy')
    x, y = np.abs(qx-center[0]), np.abs(qy-center[1])
    if mode == 'binary':
        weights = (x*x+y*y <= radius**2).astype(float)
    else:
        hx, hy = (x_axis[1]-x_axis[0])/2, (y_axis[1]-y_axis[0])/2
        inside = (x+hx)**2+(y+hy)**2 <= radius**2
        outside = np.maximum(x-hx,0)**2+np.maximum(y-hy,0)**2 >= radius**2
        weights = inside.astype(float)
        boundary = ~(inside | outside)
        bx, by = (qx-center[0])[boundary], (qy-center[1])[boundary]
        offsets = (np.arange(subpixels)+.5)/subpixels-.5
        # Accumulate one subpixel row at a time to keep temporary memory small.
        counts = np.zeros(len(bx), dtype=np.int64)
        xx = bx[:,None]+offsets[None,:]*(2*hx)
        for offset in offsets:
            yy = by[:,None]+offset*(2*hy)
            counts += np.count_nonzero(xx*xx+yy*yy <= radius**2, axis=1)
        weights[boundary] = counts/float(subpixels**2)
    weights.setflags(write=False)
    return weights
