"""Established Cartesian magnetic-axis frame; independent of element/provider."""
import numpy as np


def axis_rotation(axis):
    m=np.asarray(axis,float)
    if m.shape!=(3,) or not np.isfinite(m).all() or np.linalg.norm(m)<1e-12:raise ValueError('Declare a nonzero finite crystal Cartesian magnetization axis')
    z=m/np.linalg.norm(m);x=np.array([1.,0,0]);x-=x.dot(z)*z
    if np.linalg.norm(x)<1e-8:x=np.array([0.,1,0]);x-=x.dot(z)*z
    x/=np.linalg.norm(x);return np.stack((x,np.cross(z,x),z),axis=1)


