"""Launch one bounded, fresh-process published-app case; no app files changed."""
import argparse, os, subprocess, time,json
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--app',required=True,type=Path);p.add_argument('--project',required=True,type=Path)
p.add_argument('--probe',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
p.add_argument('--case',choices=['bw-sc','bw-dc','ms-sc','ms-dc'],required=True)
p.add_argument('--workers',default='1');p.add_argument('--limit',type=float,default=300)
p.add_argument('--matrix',action='store_true')
p.add_argument('--budget',type=int,default=1024);p.add_argument('--preflight',action='store_true');p.add_argument('--diagnostic',action='store_true')
a=p.parse_args();out=a.output.resolve();assert not out.exists(),out
out.parent.mkdir(parents=True,exist_ok=True)
env=dict(DYLD_INSERT_LIBRARIES=str(a.probe.resolve()),EMCD_BENCHMARK_PROBE=str(a.probe.resolve()),EMCD_BENCHMARK_CONTROLLER=str(Path(__file__).with_name('macos_native_controller.py').resolve()),EMCD_BENCHMARK_OUTPUT=str(out),EMCD_BENCHMARK_PROJECT=str(a.project.resolve()),EMCD_GUI_WORKSPACE=str(out.parent/('workspace-'+out.name)),EMCD_BENCHMARK_MODE=a.case,EMCD_BENCHMARK_WORKERS=a.workers,EMCD_BENCHMARK_LIMIT_SECONDS=str(a.limit),EMCD_BENCHMARK_BUDGET_MIB=str(a.budget),EMCD_BENCHMARK_PREFLIGHT_ONLY=str(int(a.preflight)),EMCD_BENCHMARK_DIAGNOSTIC=str(int(a.diagnostic)),EMCD_BENCHMARK_MATRIX=str(int(a.matrix)))
log=out.parent/(out.name+'-launch.log')
cmd=['open','-n','--stdout',str(log),'--stderr',str(log)]
for k,v in env.items():cmd+=['--env',k+'='+v]
subprocess.run(cmd+[str(a.app.resolve())],check=True)
end=time.monotonic()+a.limit+240;last=None
while time.monotonic()<end:
 if (out/'finished.json').exists():
  r=json.loads((out/'result.json').read_text());print(out.name,r['status'],r.get('exception',''),r.get('measurement',''),flush=True);break
 if (out/'progress.json').exists():
  raw=(out/'progress.json').read_text()
  if raw!=last:print(out.name,raw,flush=True);last=raw
 time.sleep(5)
else:raise TimeoutError('Controller did not finish; inspect isolated launch log and process before another launch')
