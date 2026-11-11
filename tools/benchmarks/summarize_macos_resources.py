"""Generate compact, path-free benchmark tables from native controller evidence."""
import argparse,csv,json
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True)
rows=[];records={};comparisons=[]
for path in sorted(a.input.glob('*/result.json')):
 r=json.loads(path.read_text())
 if r.get('controller_version')!='native-event-loop-v2' or r['status']=='PREFLIGHT':continue
 if not (path.parent/'finished.json').exists():continue
 info=r.get('final_resources',{}).get('info',{});preview=r.get('preview',{}).get('info',{});m=r.get('measurement',{})
 diags=r.get('metadata',{}).get('angular_evaluation',[]);executors=[d['executor'] for d in diags if 'executor' in d]
 def exsum(k):return sum(d.get(k,0) for d in executors)
 mode=r['case'];workers=info.get('execution',{}).get('effective_workers',{})
 row=dict(run_id=path.parent.name,backend=mode,requested_workers=r['requested_workers'],effective_workers=next(iter(workers.values()),None),diagnostic=r.get('diagnostic',False),status=r['status'],calculation_seconds=r.get('calculation_seconds'),run_and_display_seconds=r.get('run_and_display_seconds'),admission_and_start_seconds=r.get('admission_and_start_seconds'),preview_peak_estimate_mib=preview.get('estimated_process_peak_mib'),final_peak_estimate_mib=info.get('estimated_process_peak_mib'),estimated_working_mib=info.get('estimated_working_mib'),final_budget_mib=info.get('memory_budget_mib'),available_before_mib=r.get('environment_before',{}).get('available_ram_mib'),pressure_before=r.get('environment_before',{}).get('memory_pressure'),swap_before_mib=r.get('environment_before',{}).get('swap_used_mib'),swap_after_mib=r.get('environment_after',{}).get('swap_used_mib'),baseline_rss_mib=m.get('first_rss_mib'),sampled_run_display_peak_rss_mib=m.get('peak_rss_mib'),incremental_run_display_rss_mib=m.get('incremental_rss_mib'),sampled_scientific_window_peak_rss_mib=m.get('scientific_peak_rss_mib'),scientific_window_incremental_rss_mib=m.get('scientific_incremental_rss_mib'),sampled_run_display_peak_footprint_mib=m.get('peak_footprint_mib'),baseline_footprint_mib=m.get('first_footprint_mib'),sampled_scientific_window_peak_footprint_mib=m.get('scientific_peak_footprint_mib'),lifetime_peak_rss_mib=r.get('lifetime_peak_mib'),process_cpu_run_display_seconds=m.get('process_cpu_seconds'),average_logical_cpus_run_display=m.get('average_logical_cpus'),sample_count=m.get('sample_count'),max_sample_interval_seconds=m.get('sample_interval_max_seconds'),max_concurrent_detector_tasks=max((d.get('max_concurrent_tasks',0) for d in executors),default=0),detector_task_count=exsum('started_tasks'),summed_task_seconds=exsum('summed_task_seconds'),summed_thread_cpu_seconds=exsum('summed_thread_cpu_seconds'),summed_queue_seconds=exsum('summed_queue_seconds'),executor_wall_seconds=exsum('wall_seconds'),outgoing_response_seconds=sum(d.get('outgoing_response_seconds',0) for d in diags),mdff_contraction_seconds=sum(d.get('mdff_contraction_seconds',0) for d in diags),incoming_propagation_seconds=r.get('metadata',{}).get('incoming_propagation_seconds'),actual_energies=r.get('actual_energies'),full_field_energies=sum(bool(d.get('full_field')) for d in diags),evaluated_pixels=sum(d.get('evaluated_pixels',0) for d in diags),numeric_checks=r.get('numeric_checks'),project_restore=r.get('project_restore'),blas_during_threads=(r.get('blas_during',{}).get('runtimes') or [{}])[0].get('threads'),actual_slice_step_nm=info.get('actual_slice_step_nm'),fft_grid=info.get('fft_grid'),depth_nodes=info.get('depth_nodes'))
 row['admission_decision']='Blocked' if info.get('execution',{}).get('blocked') else ('Ready' if info else 'Unavailable')
 row['calculation_utc']=r.get('metadata',{}).get('calculation_utc')
 if r.get('status')=='PASS' and 'scientific_result_monotonic' in r:
  with (path.parent/'native-memory.csv').open() as f:samples=list(csv.DictReader(f))
  end=r['scientific_result_monotonic'];begin=end-r['calculation_seconds']
  samples=[v for v in samples if begin<=float(v['monotonic_seconds'])<=end]
  if len(samples)>1:
   def ticks(v):return sum(int(v.get(k+'_ticks',v.get(k+'_nanoseconds'))) for k in ('user','system'))
   factor=r['cpu_counter_units']['nanoseconds_per_tick']/1e9
   elapsed=float(samples[-1]['monotonic_seconds'])-float(samples[0]['monotonic_seconds'])
   cpu=(ticks(samples[-1])-ticks(samples[0]))*factor
   row.update(process_cpu_scientific_window_seconds=cpu,average_logical_cpus_scientific_window=cpu/elapsed,cpu_percent_of_machine_scientific_window=cpu/elapsed/r['hardware']['logical_cores']*100)
 if executors:
  assert all(x.get('active_tasks_after_join')==0 for x in executors)
  assert all(rt.get('threads')==1 for x in executors for rt in x['native_runtimes'])
 if r['status']=='PASS':
  assert r['numeric_checks']==r['project_restore']=='PASS'
  manifest=json.loads((path.parent/'project/input_parameters.json').read_text())
  assert manifest['mdff']['worker_mode']==('automatic' if r['requested_workers']=='auto' else 'manual')
  assert manifest['configuration_metadata']['resource_preferences']['memory_auto']==(r['requested_workers']=='auto')
  if r['requested_workers']!='auto':assert manifest['mdff']['parallel_workers']==int(r['requested_workers'])
 rows.append(row);records[row['run_id']]=(path.parent,r)
baseline_ids={r['backend']:r['run_id'] for r in rows if r['status']=='PASS' and r['requested_workers']=='1' and not r['diagnostic']}
for row in rows:
 if row['status']!='PASS':continue
 baseid=baseline_ids.get(row['backend'],row['backend']+'-manual-1-diagnostic')
 if baseid not in records:continue
 basepath,base=records[baseid];path,r=records[row['run_id']]
 if bool(base.get('diagnostic'))!=bool(row['diagnostic']):continue
 with np.load(basepath/'numerical-arrays.npz') as x,np.load(path/'numerical-arrays.npz') as y:
  assert x.files==y.files
  maxabs=0.;maxrel=0.;all_exact=True
  for key in x.files:
   if key.endswith('__I_plus') or key.endswith('__I_minus'):
    for z in (x,y):assert float(np.min(z[key]))>=-1e-12*max(float(np.max(np.abs(z[key]))),1e-30),key
   if key=='spectrum__energy_ev':np.testing.assert_array_equal(x[key],y[key]);continue
   if key.endswith('_percent'):scale=100.
   elif key.startswith('spectrum__'):
    scale=max(float(np.max(np.abs(z['spectrum__I_'+d+'_'+state]))) for z in (x,y) for d in ('A','B') for state in ('plus','minus'))
   else:
    edge=key.split('__')[0]
    scale=max(float(np.max(np.abs(z[edge+'__I_'+state]))) for z in (x,y) for state in ('plus','minus'))
   np.testing.assert_allclose(x[key],y[key],rtol=1e-10,atol=scale*1e-12)
   diff=float(np.max(np.abs(x[key]-y[key])));maxabs=max(maxabs,diff);maxrel=max(maxrel,diff/scale)
   all_exact &= np.array_equal(x[key],y[key])
  comparisons.append(dict(run_id=row['run_id'],reference=baseid,status='PASS',bitwise_equal=bool(all_exact),max_absolute_difference=maxabs,max_scale_relative_difference=maxrel,rtol=1e-10,scale_relative_atol=1e-12))
 if row['calculation_seconds']:row['speedup_vs_manual_1']=base['calculation_seconds']/row['calculation_seconds']
 if row['final_peak_estimate_mib'] is not None:
  row['estimate_minus_sampled_run_display_peak_mib']=row['final_peak_estimate_mib']-row['sampled_run_display_peak_rss_mib']
  row['estimate_minus_scientific_window_peak_mib']=row['final_peak_estimate_mib']-row['sampled_scientific_window_peak_rss_mib']
def csvout(name,data):
 if not data:return
 keys=list(dict.fromkeys(k for row in data for k in row))
 with (a.output/name).open('w',newline='') as f:
  w=csv.DictWriter(f,keys,lineterminator='\n');w.writeheader();w.writerows(data)
first=next(r for _,r in records.values() if r.get('status')=='PASS')
expected=first['configuration']
variable={'propagation','channeling_model','worker_mode','parallel_workers','memory_budget_mib','fft_generators','source'}
for _,r in records.values():
 assert r['settings']==first['settings']
 if not r.get('diagnostic'):
  assert {k:v for k,v in r['configuration'].items() if k not in variable}=={k:v for k,v in expected.items() if k not in variable}
 assert r['build']['commit']==first['build']['commit'] and not r['build']['dirty']
 assert r.get('input_identity')==first.get('input_identity')
s=first['settings'];c=first['configuration']
assert s['zone']==[0,1,7] and s['target']==[2,0,0] and s['voltage']==200 and s['thickness']==10
assert abs(s['tilt'][0]+7.124812628)<1e-10 and s['tilt'][1]==0 and s['basis_mode']=='full'
assert s['beam_cutoff']==2.5 and s['potential_cutoff']==2 and s['b_factor']==0 and s['elastic_provider']=='adaptive-dirac-pade-2026'
assert c['depth']==64 and c['grid']==97 and c['energy_points']==241 and c['subpixels']==64 and c['halfwidth']==1
assert c['fft_grid']==32 and c['slice_step']==2 and c['radius']==.09 and c['eta']==c['beta']==1
assert c['magnetization']==[0,0,1] and c['l3']==831.271 and c['l2']==848.698
assert c['energy_sampling']=='uniform' and c['angular_evaluation']=='selected' and c['angular_maps'] and not c['systematic_row']

config=dict(first['configuration']);config['source']=Path(config['source']).name
config.update(worker_mode='experimental variable',parallel_workers='experimental variable',memory_budget_mib='1024 Manual; dynamic Auto',propagation='experimental variable',channeling_model='experimental variable')
public=dict(configuration_id='ni-fcc-3p520-017-200kV-10nm-e243-q97-d64-b2p5-p2p0',source_commit=first['build']['commit'],release_tag=first['build']['release_tag'],hardware=first['hardware'],settings=first['settings'],configuration=config,input_identity=first.get('input_identity'),measurement='20 ms target native pthread proc_pid_rusage sampler; Mach CPU ticks converted with runtime mach_timebase_info; sampled RSS/footprint maxima, not guaranteed instantaneous peaks',rows=rows,numerical_comparisons=comparisons)
(a.output/'benchmark_results.json').write_text(json.dumps(public,indent=2)+'\n');csvout('benchmark_results.csv',rows);csvout('worker_scaling.csv',[r for r in rows if r['backend'].endswith('dc')])
ratios=[]
for backend in ['bw','ms']:
 sc=next((r for r in rows if r['run_id']==baseline_ids.get(backend+'-sc')),None);dc=next((r for r in rows if r['run_id']==baseline_ids.get(backend+'-dc')),None)
 if not sc or not dc or sc['status']!=dc['status'] or sc['status']!='PASS':continue
 ratio=dict(backend=backend,effective_workers=1)
 for k in ['final_peak_estimate_mib','estimated_working_mib','sampled_run_display_peak_rss_mib','incremental_run_display_rss_mib','sampled_scientific_window_peak_rss_mib','scientific_window_incremental_rss_mib','sampled_run_display_peak_footprint_mib']:
  ratio[k+'_sc_over_dc']=sc[k]/dc[k] if dc[k] else None
 ratios.append(ratio)
csvout('memory_comparison.csv',ratios)
(a.output/'numerical_comparisons.json').write_text(json.dumps(comparisons,indent=2)+'\n')
matrix=a.input/'preflight-matrix/preflight-matrix.json'
if matrix.exists():
 compact=[]
 for r in json.loads(matrix.read_text()):
  info=r['info'];e=info['execution']
  compact.append(dict(backend=r['backend'],channeling=r['channeling'],request=r['request'],assessment_seconds=r['assessment_seconds'],effective_workers=e['effective_workers'],blocked=e['blocked'],reason=e['messages'],estimated_working_mib=info['estimated_working_mib'],memory_budget_mib=info['memory_budget_mib'],estimated_process_peak_mib=info['estimated_process_peak_mib'],process_rss_mib=info['process_rss_mib'],memory_breakdown_mib=info.get('memory_breakdown_mib'),fft_storage_working_mib=info['fft_storage_working_mib'],coherence_working_mib=info['coherence_working_mib'],retained_results_working_mib=info['retained_results_working_mib']))
 (a.output/'resource_preflight.json').write_text(json.dumps(compact,indent=2)+'\n')
print('Summarized',len(rows),'runs;',len(comparisons),'matched numerical comparisons;',len(ratios),'SC/DC memory comparisons')
