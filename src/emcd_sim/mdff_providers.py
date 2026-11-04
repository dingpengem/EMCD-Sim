"""Validated source adapters; no propagation or contraction implementation.

Atomic and XMCD inputs reuse the accepted generators and tensor validator.
Temporary conversion is an internal detail: users select the original input,
and the saved source identity is always that original file's exact bytes.
"""
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
from .imported_mdff import ImportedMDFF


def load_provider(cfg):
    if hasattr(cfg,'provider_schema') and cfg.provider_schema!=1:
        raise ValueError('Unsupported MDFF provider configuration schema')
    if cfg.model == 'imported':
        return ImportedMDFF.load(cfg.source, cfg.source_sha256)
    if cfg.model not in ('xmcd', 'atomic'):
        raise ValueError('Unsupported MDFF provider')
    if not cfg.source_sha256:
        raise ValueError('Validate the original MDFF input checksum before calculation')
    try:
        raw = Path(cfg.source).read_bytes()
    except OSError as exc:
        raise ValueError('Missing/unreadable MDFF provider source: ' + cfg.source) from exc
    if hashlib.sha256(raw).hexdigest() != cfg.source_sha256:
        raise ValueError('MDFF source checksum changed; invalidate acknowledgement and validate again')
    declaration = json.dumps(getattr(cfg, 'provider_declaration', None), sort_keys=True)
    return _converted(cfg.model, str(Path(cfg.source).resolve()), raw, declaration)


@lru_cache(maxsize=8)
def _converted(model, original_path, raw, declaration_json):
    digest = hashlib.sha256(raw).hexdigest()
    with TemporaryDirectory(prefix='emcd-mdff-provider-') as folder:
        original = Path(folder) / ('parameters.json' if model == 'atomic' else 'source.xmcd')
        original.write_bytes(raw)
        output = Path(folder) / 'tensor.json'
        if model == 'atomic':
            from .atomic_ionization import export_atomic_parameters
            converted = export_atomic_parameters(original, output)
        else:
            from .generalized_xmcd import export_declared_xmcd
            converted = export_declared_xmcd(original, json.loads(declaration_json), output)
    metadata = dict(converted.metadata)
    if model == 'atomic':
        metadata['atomic_parameter_path'] = original_path
    else:
        metadata['xmcd_source_path'] = original_path
    metadata['provider_identity'] = model
    return replace(converted, metadata=metadata, path=original_path, sha256=digest)


def prepare_provider(cfg):
    """One preparation interface for XMCD, atomic and imported MDFF models.

    Historical Ni deliberately uses direct evaluation, not converted-grid
    interpolation. Selection here changes no downstream propagation kernel.
    """
    from .gui.generalized_forward import is_declared
    if is_declared(cfg):
        from .gui.provider_preparation import DeclaredMDFFProvider
        return DeclaredMDFFProvider(cfg)
    from .gui.legacy_ni_provider import HistoricalNiProvider
    return HistoricalNiProvider(cfg)
