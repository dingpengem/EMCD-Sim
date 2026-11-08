"""Explicit physical-pair selection; no source mutation or tensor rotation."""
import numpy as np


class ReversedProviderPair:
    def __init__(self, source):
        if (source.metadata['magnetic_state'] != 'uniform_fm' or
                source.metadata['reversal'] != 'explicit_pair_shared_even'):
            raise ValueError('Direction reversal requires an explicitly declared, validated physical tensor pair')
        self.source = source

    def __getattr__(self, name):
        return getattr(self.source, name)

    @property
    def plus(self):return self.source.minus

    @property
    def minus(self):return self.source.plus

    def tensors(self, energy, crystal_to_microscope, magnetization):
        # The underlying provider still validates its native axis and full frame.
        m=np.asarray(magnetization,float);native=np.asarray(self.metadata['magnetization_crystal'],float)
        if (m.shape!=(3,) or not np.isfinite(m).all() or not np.isfinite(np.linalg.norm(m))
                or np.linalg.norm(m)<1e-12 or not np.allclose(m/np.linalg.norm(m),-native/np.linalg.norm(native),rtol=0,atol=1e-10)):
            raise ValueError('Physical minus-state selection requires the opposite of the declared source axis; it does not rotate the tensor frame')
        pair = self.source.tensors(energy,crystal_to_microscope,-m)
        return pair[1],pair[0]

    def provenance(self):
        return dict(self.source.provenance(),direction_binding=dict(
            pair_state='minus',source_magnetization_crystal=self.metadata['magnetization_crystal'],
            effective_magnetization_crystal=(-np.asarray(self.metadata['magnetization_crystal'])).tolist()))
