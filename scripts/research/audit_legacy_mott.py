"""Audit all external XF/Mott rows without altering their interpolation or data.

The high-precision cubics below are independent audit references, never
replacement scattering factors. Their extrema test basic physical consistency
of the source interpolation; they do not establish accuracy against an atom.
"""
import argparse
import csv
from decimal import Decimal, localcontext
import json
from pathlib import Path

import numpy as np

from emcd_sim.legacy_atomic_factors import (
    configured_legacy_factors, SOURCE_POTENTIAL_SCALE, MOTT_MIN_STL,
)


def dec(value):
    return Decimal.from_float(float(value))


def evaluate(coefficients, x):
    result=Decimal(0)
    for value in reversed(coefficients):
        result=result*x+value
    return result


def cubic_reference(module,z,interval):
    """Independent four-point Lagrange cubic through the source's stencil."""
    assert all(v>=0 for v in module._XF[z-1]), 'Review marker-dependent XF stencils explicitly'
    count=len(module._STL)
    if interval==0:
        indices=(1,0,1,2)
    elif interval+2>=count:
        indices=tuple(range(count-4,count))
    else:
        indices=(interval-1,interval,interval+1,interval+2)
    x=[dec(module._STL[i]) for i in indices]
    if interval==0:x[0]=-x[0]
    y=[dec(module._XF[z-1][i]) for i in indices]
    coefficients=[Decimal(0)]*4
    for i in range(4):
        term=[Decimal(1)];denominator=Decimal(1)
        for j in range(4):
            if i==j:continue
            product=[Decimal(0)]*(len(term)+1)
            for k,value in enumerate(term):
                product[k]-=x[j]*value
                product[k+1]+=value
            term=product;denominator*=x[i]-x[j]
        for k,value in enumerate(term):
            coefficients[k]+=y[i]*value/denominator
    return coefficients


def extrema(coefficients,lo,hi):
    """Evaluate a cubic at endpoints and every internal stationary point."""
    points=[lo,hi]
    a,b,c=3*coefficients[3],2*coefficients[2],coefficients[1]
    if a==0:
        if b!=0:
            root=-c/b
            if lo<root<hi:points.append(root)
    else:
        discriminant=b*b-4*a*c
        if discriminant>=0:
            for root in ((-b-discriminant.sqrt())/(2*a),(-b+discriminant.sqrt())/(2*a)):
                if lo<root<hi:points.append(root)
    values=[evaluate(coefficients,x) for x in points]
    return min(values),max(values)


def audit(table):
    m=table._module
    zs=[z for z in range(1,99) if m._METHOD[z-1]==2]
    assert len(zs)==44
    records=[];samples=[];interval_records=[]
    scale=dec(1.145896)/dec(SOURCE_POTENTIAL_SCALE)
    # Roundoff allowance for the 80-digit reference operations, not a
    # tolerance on physical scattering accuracy or on the source data.
    decimal_roundoff=Decimal('1e-55')
    with localcontext() as context:
        context.prec=80
        scale=dec(1.145896)/dec(SOURCE_POTENTIAL_SCALE)
        for z in zs:
            f0=dec(m._EF[z-1][0]);bad=[];references=[]
            for index,(left,right) in enumerate(zip(m._STL[:-1],m._STL[1:])):
                lo,hi=dec(left),dec(right)
                d,c,b,a=cubic_reference(m,z,index)
                # f(s)=C*(Z-P(s))/s^2; these polynomials remove
                # the strictly positive denominator for s>0.
                q=[Decimal(z)-d,-c,-b,-a]
                derivative=[-2*(Decimal(z)-d),c,Decimal(0),-a]
                upper=[scale*q[0],scale*q[1],scale*q[2]-f0,scale*q[3]]
                positive_min,_=extrema(q,lo,hi)
                _,derivative_max=extrema(derivative,lo,hi)
                _,above_origin_max=extrema(upper,lo,hi)
                reasons=[]
                if positive_min < -decimal_roundoff:reasons.append('negative factor')
                if derivative_max > decimal_roundoff:reasons.append('increasing factor')
                if above_origin_max > decimal_roundoff:reasons.append('factor exceeds separate origin')
                if reasons:bad.append((right,reasons))
                interval_records.append(dict(z=z,stl_left=left,stl_right=right,
                    consistency_failures=reasons,minimum_mott_numerator=str(positive_min),
                    maximum_derivative_numerator=str(derivative_max),maximum_origin_excess_numerator=str(above_origin_max)))
                references.append((lo,hi,[d,c,b,a]))
            boundary=max((end for end,reasons in bad),default=m._STL[1])
            worst_error=0.;count=0
            # Use all native intervals at/above the common reviewed boundary;
            # endpoints, interior samples and stationary-point checks are distinct.
            for lo,hi,coefficients in references:
                if lo<dec(MOTT_MIN_STL):continue
                for s in np.linspace(float(lo),float(hi),17):
                    exact=scale*(Decimal(z)-evaluate(coefficients,dec(s)))/(dec(s)**2)
                    raw=m.elastic_atomic_scattering_factor(z,float(s))/SOURCE_POTENTIAL_SCALE
                    relative=float(abs(dec(raw)-exact)/abs(exact))
                    worst_error=max(worst_error,relative);count+=1
                    assert np.isfinite(raw) and raw>0
                    assert relative<1e-9, (z,s,relative)
            # Audit the ORIGINAL source at unsupported inputs for evidence.
            low=[0.,np.nextafter(0.,1.),1e-200,1e-160,1e-12,1e-8,1e-6,1e-5,1e-4,.001,.005]
            for knot in m._STL[1:5]:
                low.extend([np.nextafter(knot,0.),knot,np.nextafter(knot,np.inf)])
            continuity=[]
            for s in sorted(set(low)):
                row=dict(z=z,stl=float(s),source_scaled=None,electron_factor_angstrom=None,
                         source_status='',adapter_status='')
                try:
                    raw=m.elastic_atomic_scattering_factor(z,float(s))
                    if np.isfinite(raw):
                        row.update(source_scaled=float(raw),electron_factor_angstrom=float(raw/SOURCE_POTENTIAL_SCALE),source_status='finite')
                    else:row['source_status']='nonfinite'
                except ArithmeticError as exc:row['source_status']=type(exc).__name__
                try:
                    value=table.factor(z,float(s)*2)
                    row['adapter_status']='accepted'
                    assert np.isfinite(value) and value>0
                except ValueError:
                    row['adapter_status']='explicitly rejected'
                if 0<s<MOTT_MIN_STL:assert row['adapter_status']=='explicitly rejected'
                if s==0:assert row['adapter_status']=='accepted'
                samples.append(row)
            for knot in m._STL[1:5]:
                near=[m.elastic_atomic_scattering_factor(z,float(s))/SOURCE_POTENTIAL_SCALE
                      for s in [np.nextafter(knot,0.),knot,np.nextafter(knot,np.inf)]]
                residual=max(near)-min(near)
                assert residual<1e-8, (z,knot,residual)
                continuity.append(dict(stl=knot,max_native_neighbor_difference_angstrom=float(residual)))
            records.append(dict(z=z,origin_factor_angstrom=float(f0),
                first_usable_positive_xf_stl=next(x for x,v in zip(m._STL,m._XF[z-1]) if x>0 and v>=0),
                last_inconsistent_interval_end=boundary,
                source_consistency_failures=[dict(interval_end=end,reasons=reasons) for end,reasons in bad],
                accepted_range_samples=count,max_relative_error_vs_80_digit_reference=worst_error,
                native_point_continuity=continuity))
    common=max(r['last_inconsistent_interval_end'] for r in records)
    assert common==MOTT_MIN_STL, (common,MOTT_MIN_STL)
    assert common in m._STL
    return dict(source_sha256=table.source_sha256,mott_element_count=len(zs),
        mott_atomic_numbers=zs,common_minimum_positive_stl=common,
        minimum_positive_g_inverse_angstrom=2*common,
        boundary_basis='First common native grid boundary after all physical-consistency failures of the source cubics',
        physical_checks='Positive factors, nonincreasing factors and factor <= separately defined origin; all cubic interval extrema checked at 80 decimal digits',
        reference_scope='Arithmetic/stencil agreement and basic physical consistency only; no independent atomic-scattering accuracy certification',
        quantitative_accuracy='Not established: original table provenance, rounding error bounds and independent atomic references are unavailable',
        records=records,source_interval_checks=interval_records,low_stl_samples=samples)


def write_report(report,out):
    out.mkdir(parents=True,exist_ok=True)
    (out/'mott_low_stl_audit.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    with (out/'mott_low_stl_samples.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(report['low_stl_samples'][0]))
        writer.writeheader();writer.writerows(report['low_stl_samples'])
    lines=['# XF/Mott low-STL audit','',
        'All 44 source XF/Mott elements were checked. The external tables and source function remain unchanged.',
        '',f"Adapter operating domain: **STL=0 or {report['common_minimum_positive_stl']} <= STL <= 6**; equivalently **|g|=0 or 0.08 <= |g| <= 12 inverse angstrom**.",
        '', 'The common lower boundary is the native knot after the last interval with a failed physical-consistency check across all 44 elements. It is not a fitted correction or a guarantee of quantitative accuracy. The Os (Z=76) intervals through STL=0.04 determine the common limit.',
        '', 'Each cubic interval was independently reconstructed by 80-digit Lagrange interpolation solely for audit. Endpoints and all stationary points of the Mott numerator, derivative numerator and origin-bound polynomial were checked. Accepted intervals were also compared to the unmodified binary64 source at 17 samples per interval. First-native-point continuity and extreme-underflow behavior were checked separately.',
        '', '|Z|Last inconsistent interval end (STL)|Accepted samples|Max relative arithmetic discrepancy|',
        '|---:|---:|---:|---:|']
    for r in report['records']:
        lines.append(f"|{r['z']}|{r['last_inconsistent_interval_end']}|{r['accepted_range_samples']}|{r['max_relative_error_vs_80_digit_reference']:.4g}|")
    lines.extend(['', 'These are numerical operating checks and necessary physical-consistency conditions, not scientific validation of the table against independent atomic calculations. Exact-zero values are separate source definitions; continuity to zero is not claimed across the rejected positive interval. No clipping, absolute-value repair, constant extrapolation, or polynomial correction is applied by the adapter.',
        '', 'Large-supercell nonzero vectors with |g|<0.08 are explicitly rejected for any XF/Mott species, including when a small difference vector is encountered in BW coupling. They are not reclassified as (000). Use a manually verified equivalent primitive cell when physically appropriate, or a separately validated provider. No geometry, cutoff or cell transformation is applied silently.',
        '', '[Full interval audit](mott_low_stl_audit.json) and [unrestricted-source low-STL samples](mott_low_stl_samples.csv) retain the evidence.'])
    (out/'MOTT_LOW_STL_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=audit(configured_legacy_factors())
    write_report(result,args.output)
    print(json.dumps({k:v for k,v in result.items() if k not in ('records','source_interval_checks','low_stl_samples')},indent=2))
