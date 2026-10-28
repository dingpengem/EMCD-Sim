"""Exact sampled mirror diagnostics about local qy=0, without interpolation.

Apply to raw reversal components, not paired differences which are odd by
construction. Fractions are L2 norms of mirror-even/odd parts over field norm.
"""
import numpy as np


def row_mirror_diagnostics(qx, qy, fields):
    qx, qy = np.asarray(qx), np.asarray(qy)
    if (qx.ndim != 2 or qx.shape != qy.shape or not np.isfinite(qx).all()
            or not np.isfinite(qy).all() or not np.allclose(qx, qx[::-1], atol=1e-13, rtol=0)
            or not np.allclose(qy, -qy[::-1], atol=1e-13, rtol=0)):
        raise ValueError('Require an exact sampled qy mirror about the local x systematic row')
    metrics, arrays = {}, {}
    for name, value in fields.items():
        value = np.asarray(value, float)
        if value.shape != qx.shape or not np.isfinite(value).all():
            raise ValueError('Finite map matching the reciprocal grid required')
        even, odd = (value + value[::-1])/2, (value - value[::-1])/2
        norm = float(np.linalg.norm(value))
        metrics[name] = dict(l2=norm, mirror_even_l2=float(np.linalg.norm(even)),
            mirror_odd_l2=float(np.linalg.norm(odd)),
            even_fraction=float(np.linalg.norm(even)/norm) if norm else None,
            odd_fraction=float(np.linalg.norm(odd)/norm) if norm else None,
            antisymmetry_residual_max=float(np.max(abs(value + value[::-1]))),
            symmetry_residual_max=float(np.max(abs(value - value[::-1]))))
        arrays.update({name+'__raw':value, name+'__mirror_even':even, name+'__mirror_odd':odd})
    return metrics, arrays
