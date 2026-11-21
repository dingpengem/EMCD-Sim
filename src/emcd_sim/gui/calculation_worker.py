"""Qt thread boundary for one validated forward request.

EMCDWorker reports progress, results and failures through queued signals. It
preserves cancellation timing, scoped BLAS limits and per-run input snapshots;
all physics and resource validation stays in the existing forward pipeline.
Qt virtual callbacks run/requestInterruption/isInterruptionRequested keep their
framework names.
"""
from dataclasses import asdict
import logging
import threading
import time
from PySide6 import QtCore
from ..cancellation import Cancelled
from emcd_sim.forward_pipeline import calculate


class EMCDWorker(QtCore.QThread):
    """Run one frozen input request with cooperative cancellation and BLAS limits."""
    result=QtCore.Signal(object);failed=QtCore.Signal(str);stage=QtCore.Signal(str)
    def __init__(self,structure,settings,config,*,sites=None,energy_windows=None,reverse_magnetization=False,input_signature=None):
        super().__init__();self.structure=structure;self.settings=settings;self.config=config
        self.sites=sites;self.energy_windows=energy_windows;self.reverse_magnetization=reverse_magnetization;self.input_signature=input_signature
        self.cancellation_event=threading.Event();self.cancellation_times={}
    def requestInterruption(self):
        # Called directly from the GUI, never queued into this busy thread.
        self.cancellation_times.setdefault('requested',time.perf_counter())
        self.cancellation_event.set();super().requestInterruption()
    def isInterruptionRequested(self):
        return self.cancellation_event.is_set() or super().isInterruptionRequested()
    def cancelled(self):
        requested=self.isInterruptionRequested()
        if requested:self.cancellation_times.setdefault('acknowledged',time.perf_counter())
        return requested
    def run(self):
        from emcd_sim.parallel_resources import calculation_blas_guard, native_backend_info
        logger=logging.getLogger('emcd_sim.gui')
        try:
            with calculation_blas_guard(self.cancelled) as native:
                logger.info('Calculation verified BLAS runtimes=%s',native)
                self._run_calculation()
        except Cancelled:pass
        except Exception as exc:
            logger.exception('Calculation BLAS control failed')
            if not self.cancelled():self.failed.emit(str(exc))
        finally:
            logger.info('Calculation BLAS limits restored=%s',native_backend_info().get('runtimes'))
            self.cancellation_times['stopped']=time.perf_counter()
    def _run_calculation(self):
        try:
            calculation_start=time.perf_counter()
            logging.getLogger('emcd_sim.gui').info('Calculate method=%s model=%s sha256=%s', self.config.propagation, self.config.model, self.config.source_sha256)
            logger=logging.getLogger('emcd_sim.gui')
            configuration=asdict(self.config);configuration.pop('source',None)
            logger.info('Calculation inputs settings=%s config=%s',asdict(self.settings),configuration)
            if self.sites is not None:
                logger.info('Local site inputs=%s',[(g.group_id,g.indices,g.magnetization,g.mdff_reference.model,g.mdff_reference.source,g.mdff_reference.source_sha256) for g in self.sites.groups])
            def progress(message):
                logger.info('Calculation stage: %s',message)
                self.stage.emit(message)
            kwargs={'execution_policy':self.execution_policy} if hasattr(self,'execution_policy') else {}
            local=(dict(sites=self.sites,energy_windows=self.energy_windows,
                        reverse_magnetization=self.reverse_magnetization) if self.sites is not None else {})
            r=calculate(self.structure,self.settings,self.config,progress,self.cancelled,**local,**kwargs)
            if self.sites is not None:
                r['gui_multisite_input']=self.input_signature
                if self.input_signature and len(self.input_signature)>3:
                    r['metadata']['ionization_participation']=dict(
                        selected_atom_count=sum(g.multiplicity for g in self.sites.groups),
                        excluded_structural_groups=[dict(group_id=n,element=e,indices=indices,scope='excluded, not calculated') for n,e,indices in self.input_signature[3]])
            elapsed=time.perf_counter()-calculation_start
            r['metadata']['calculation_seconds']=elapsed
            for entry in r.get('methods',{}).values():entry['metadata']['calculation_seconds']=elapsed
            logger.info('Calculation elapsed_seconds=%.6f (excludes GUI display and project saving)',elapsed)
            if not self.cancelled():self.result.emit(r)
        except Cancelled:pass
        except Exception as exc:
            logging.getLogger('emcd_sim.gui').exception('Calculation failed')
            if not self.isInterruptionRequested():self.failed.emit(str(exc))
        finally:
            self.cancellation_times['stopped']=time.perf_counter()
