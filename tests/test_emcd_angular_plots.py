"""Current GUI geometry overlays preserve data and transmitted-beam coordinates."""
from dataclasses import replace
import numpy as np
import pytest
from matplotlib.figure import Figure
from emcd_sim.benchmark import nickel_physical_benchmark
from emcd_sim.geometry import Microscope,electron_wavelength_angstrom
from emcd_sim.emcd_angular_plots import decorate_reciprocal_map


@pytest.mark.parametrize('tilt',[(0.,0.),(-7.,25.),(3.,-4.)])
def test_zone_axis_coordinate_sign_and_overlay_limits(tilt):
    model=nickel_physical_benchmark(tilt_mrad_xy=tilt)
    za=-np.asarray(tilt)*1e-3/electron_wavelength_angstrom(200.)
    np.testing.assert_array_equal(za+model.elastic.microscope.incident_k_xy,[0.,0.])
    if tilt==(0.,0.):np.testing.assert_array_equal(za,[0.,0.])
    panels=[];data=np.arange(81).reshape(9,9)
    for method in ('bloch','fft-multislice'):
        fig=Figure();ax=fig.subplots();im=ax.imshow(data)
        decorate_reciprocal_map(ax,model,(-.5,.5,-.5,.5))
        np.testing.assert_array_equal(im.get_array(),data)
        assert ax.get_xlim()==(-.5,.5) and ax.get_ylim()==(-.5,.5) and ax.get_aspect()==1.
        if np.any(abs(za)>.5):assert any('outside view' in t.get_text() for t in ax.texts)
        else:
            marker=next(line for line in ax.lines if line.get_label()=='ZA [001]')
            np.testing.assert_allclose(marker.get_xydata()[0],za)
        panels.append(ax)
    for a,b in zip(panels[0].lines,panels[1].lines):np.testing.assert_array_equal(a.get_xydata(),b.get_xydata())
