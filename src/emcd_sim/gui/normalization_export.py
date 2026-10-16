"""Export derived data alongside explicitly preserved raw arrays."""
from pathlib import Path
from dataclasses import asdict
import csv,json
import numpy as np
from .signal_normalization import DisplaySettings, normalized_spectra, angular_display, percentage_metrics


def save_figure(figure,path):
    meta=getattr(figure,'_emcd_display_metadata',{'display':'raw','units':'Relative intensity (a.u.)'})
    description=json.dumps(meta,allow_nan=False)
    figure.savefig(path,dpi=200,metadata={'Description':description})
    Path(str(path)+'.json').write_text(description+'\n',encoding='utf-8')


def export_derived(entries,path,settings=None,zoom='Full spectrum'):
    settings=settings or DisplaySettings();normalized=normalized_spectra(entries,settings,zoom)
    root=Path(path);root.mkdir(parents=True,exist_ok=False);arrays={};records=[];scalars=[]
    for i,((label,r,method),(derived,meta)) in enumerate(zip(entries,normalized)):
        spectra=r['spectra'];arrays.update({f'run{i}__raw__{k}':r[k] for k in ('qx','qy')});arrays.update({f'run{i}__raw__weight_{k}':v for k,v in r['weights'].items()});arrays.update({f'run{i}__raw__{key}':a for key,a in spectra.items()})
        arrays.update({f'run{i}__derived__{key}':a for key,a in derived.items()})
        keys=list(derived)
        with (root/f'run{i}_derived_spectra.csv').open('w',encoding='utf-8',newline='') as f:
            writer=csv.writer(f);writer.writerow(['energy_ev']+keys);writer.writerows(zip(spectra['energy_ev'],*(derived[k] for k in keys)))
        maps_meta=[]
        for edge,fields in r['maps'].items():
            for key,a in fields.items():
                arrays[f'run{i}__raw__{edge}__{key}']=a
                try:
                    value,info=angular_display(r,edge,key,settings.map_mode)
                    arrays[f'run{i}__derived__{edge}__{key}']=value;maps_meta.append(dict(edge=edge,field=key,**info))
                except ValueError as exc:maps_meta.append(dict(edge=edge,field=key,unavailable=str(exc)))
        try:
            reference=entries[min(settings.reference,len(entries)-1)][1] if settings.scope=='shared' else None
            windows=None if meta.get('window_note') else (settings.windows or None)
            for edge,row in percentage_metrics(r,windows,reference).items():scalars.append(dict(run=label,method=method,edge=edge,reference_run=meta['reference_run'],**row))
        except ValueError as exc:meta['scalar_unavailable']=str(exc)
        records.append(dict(label=label,method=method,source_sha256=r['config'].source_sha256,
                            software_commit=r['metadata'].get('software_commit'),normalization=meta,maps=maps_meta))
    np.savez_compressed(root/'derived_and_raw.npz',**arrays)
    if scalars:
        keys=list(dict.fromkeys(k for row in scalars for k in row))
        with (root/'percentage_metrics.csv').open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,keys);writer.writeheader();writer.writerows(scalars)
    (root/'normalization_metadata.json').write_text(json.dumps(dict(kind='Derived visualization/analysis data; original arrays unmodified',
        settings=asdict(settings),zoom=zoom,records=records),indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return root
