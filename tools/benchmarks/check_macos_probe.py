"""Calibrate external clock units and GUI waits without running a simulation."""
import argparse,csv,ctypes,json,os,resource,tempfile,threading,time
from pathlib import Path
from PySide6 import QtCore,QtTest,__version__
p=argparse.ArgumentParser();p.add_argument('probe',type=Path);a=p.parse_args()
class Timebase(ctypes.Structure):_fields_=[('numer',ctypes.c_uint32),('denom',ctypes.c_uint32)]
tb=Timebase();ctypes.CDLL('/usr/lib/libSystem.B.dylib').mach_timebase_info(ctypes.byref(tb))
lib=ctypes.CDLL(str(a.probe.resolve()));lib.emcd_probe_start.argtypes=[ctypes.c_char_p]
with tempfile.TemporaryDirectory() as tmp:
 path=Path(tmp)/'cpu.csv';before=resource.getrusage(resource.RUSAGE_SELF)
 assert lib.emcd_probe_start(os.fsencode(path))==0
 start=time.thread_time()
 while time.thread_time()-start<.2:pass
 lib.emcd_probe_stop();after=resource.getrusage(resource.RUSAGE_SELF)
 rows=list(csv.DictReader(path.open()))
 def ticks(row):return sum(int(row.get(k+'_ticks',row.get(k+'_nanoseconds'))) for k in ('user','system'))
 native=(ticks(rows[-1])-ticks(rows[0]))*tb.numer/tb.denom/1e9
 direct=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime
 assert abs(native-direct)<.02,(native,direct)
app=QtCore.QCoreApplication([]);waits={}
for kind in ('qwait','event_loop'):
 data={};stop=threading.Event()
 def work():
  start=time.thread_time()
  while not stop.is_set():pass
  data['worker_cpu_seconds']=time.thread_time()-start
 t=threading.Thread(target=work);t.start();start=time.monotonic()
 if kind=='qwait':
  while time.monotonic()-start<.5:app.processEvents();QtTest.QTest.qWait(25)
 else:
  loop=QtCore.QEventLoop();QtCore.QTimer.singleShot(500,loop.quit);loop.exec()
 stop.set();t.join();data['wall_seconds']=time.monotonic()-start;waits[kind]=data
print(json.dumps(dict(pyside_version=__version__,timebase_numer=tb.numer,timebase_denom=tb.denom,native_cpu_seconds=native,getrusage_cpu_seconds=direct,clock_validation='PASS',waits=waits),indent=2))
