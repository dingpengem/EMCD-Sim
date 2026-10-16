"""Compare Stage C, source GUI and packaged GUI scientific exports without solvers."""
import argparse, json
from pathlib import Path
import numpy as np


def compare(reference, candidate):
    report={}
    for model in ('xmcd','atomic'):
        for propagation in ('bloch','fft-multislice','both'):
            case=model+'_'+propagation;entries={}
            for name in ('virtual_detector_eels.npz','angular_maps.npz','diffraction_pattern.npz'):
                with np.load(reference/case/name,allow_pickle=False) as a, np.load(candidate/case/name,allow_pickle=False) as b:
                    assert set(a.files)==set(b.files),(case,name,'keys')
                    for key in a.files:
                        x,y=a[key],b[key]
                        if x.dtype.kind not in 'fci':
                            np.testing.assert_array_equal(x,y);continue
                        np.testing.assert_array_equal(np.isnan(x),np.isnan(y))
                        valid=np.isfinite(x)&np.isfinite(y)
                        error=float(np.max(abs(x[valid]-y[valid]))) if valid.any() else 0.
                        scale=float(np.max(abs(x[valid]))) if valid.any() else 0.
                        entries[name+'__'+key]=dict(max_abs=error,relative_to_max=error/scale if scale else 0.,bitwise=np.array_equal(x,y,equal_nan=True))
                        np.testing.assert_allclose(y,x,rtol=1e-12,atol=1e-15,equal_nan=True)
            report[case]=dict(all_bitwise=all(v['bitwise'] for v in entries.values()),max_abs=max(v['max_abs'] for v in entries.values()),arrays=entries)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,default=Path('outputs/gui_stage_c/windows_20261016_000116'))
    p.add_argument('--source',type=Path,required=True);p.add_argument('--packaged',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();report=dict(tolerance=dict(rtol=1e-12,atol=1e-15),source_vs_stage_c=compare(a.baseline,a.source),packaged_vs_stage_c=compare(a.baseline,a.packaged),packaged_vs_source=compare(a.source,a.packaged))
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:{case:{x:v for x,v in r.items() if x!='arrays'} for case,r in value.items()} for k,value in report.items() if k!='tolerance'},indent=2))


if __name__=='__main__':main()
