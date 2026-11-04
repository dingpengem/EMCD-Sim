"""Provider declaration vocabulary, independent of propagation/site kernels.

These labels identify supplied dipole responses, not a predicted atomic model.
Energy values and physical edge assignments remain explicit source inputs.
"""
from ase.data import atomic_numbers
import numpy as np

# Conservative occupied-core domain; no tabulated edge energy is inferred.
EDGES = {'K': (1, ('K',)), 'L2,3': (10, ('L3', 'L2'))}
# Additional edge labels require an end-to-end sampling/map/GUI/export test,
# not merely relaxation of the tensor declaration validator.


def validate_edge(element, edge):
    if element not in atomic_numbers or element == 'X':
        raise ValueError('Declare a real ionizing element')
    if edge not in EDGES:
        raise ValueError('Unsupported declared dipole core-loss edge: ' + str(edge))
    minimum, labels = EDGES[edge]
    if atomic_numbers[element] < minimum:
        raise ValueError('Declared element is outside the supported occupied-core domain for ' + edge)
    return labels


def validate_selected(element, edge, selected, bounds):
    labels = validate_edge(element, edge)
    if not isinstance(selected, dict) or set(selected) != set(labels):
        raise ValueError('Explicit native selected energies required for ' + ', '.join(labels))
    values = np.asarray([selected[label] for label in labels], float)
    if (not np.isfinite(values).all() or np.any(np.diff(values) <= 0)
            or values[0] < bounds[0] or values[-1] > bounds[-1]):
        raise ValueError('Selected edge energies must be ascending inside native coverage')
    return tuple(zip(labels, map(float, values)))


def selected_samples(cfg):
    """Historical ordering is retained exactly for old project configurations."""
    selected = getattr(cfg, 'selected_edges', ())
    return tuple(selected) if selected else (('L3', cfg.l3), ('L2', cfg.l2))
