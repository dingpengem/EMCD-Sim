"""Plot measured compact records; no numerical arrays or synthetic benchmark data."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('data',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
rows=json.loads(a.data.read_text())['rows'];passed=[r for r in rows if r['status']=='PASS' and not r['diagnostic']]
base={r['backend']:r for r in passed if r['requested_workers']=='1'}
fig,axes=plt.subplots(1,2,figsize=(12,4.7),layout='constrained')
ax=axes[0];keys=['bw-sc','bw-dc','ms-sc','ms-dc'];x=np.arange(4)
ax.bar(x-.17,[base[k]['sampled_scientific_window_peak_rss_mib'] for k in keys],width=.32,label='Sampled calculation RSS')
ax.bar(x+.17,[base[k]['final_peak_estimate_mib'] for k in keys],width=.32,label='Conservative Run estimate')
ax.scatter(x-.17,[base[k]['baseline_rss_mib'] for k in keys],c='black',marker='_',s=160,label='Initial probe RSS')
ax.set(xticks=x,xticklabels=['BW SC','BW DC','MS SC','MS DC'],ylabel='Process memory (MiB)',title='Manual 1 worker, common 1,024 MiB budget')
ax.legend(fontsize=8);ax.grid(axis='y',alpha=.2)
ax=axes[1]
for backend,color,label in [('bw-dc','C0','BW Double'),('ms-dc','C1','MS Double')]:
 manual=sorted((r for r in passed if r['backend']==backend and r['requested_workers']!='auto'),key=lambda r:int(r['requested_workers']))
 ax.plot([r['effective_workers'] for r in manual],[base[backend]['calculation_seconds']/r['calculation_seconds'] for r in manual],'o-',color=color,label=label+' Manual')
 for r in passed:
  if r['backend']==backend and r['requested_workers']=='auto':
   ax.scatter(r['effective_workers'],base[backend]['calculation_seconds']/r['calculation_seconds'],color=color,marker='*',s=150,label=label+' Auto')
ax.axhline(1,color='gray',linewidth=.8)
ax.set(xlabel='Effective outer workers',ylabel='Scientific wall-time speedup vs Manual 1',title='Single observations; no error bars',xticks=[1,2,4,6,8])
ax.legend(fontsize=8);ax.grid(alpha=.2)
fig.suptitle('Published EMCD-Sim ARM64 · M2 Pro · Ni 243 energies / selected 97×97 maps')
fig.savefig(a.output,dpi=170);plt.close(fig)
