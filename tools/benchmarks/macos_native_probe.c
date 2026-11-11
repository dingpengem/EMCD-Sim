/* External test instrumentation; never compiled into EMCD-Sim.app. */
#include <dispatch/dispatch.h>
#include <dlfcn.h>
#include <libproc.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
static atomic_int running;
static pthread_t sampler;
static FILE *stream;
static void sample(void) {
    struct rusage_info_v0 r; struct timespec t;
    clock_gettime(CLOCK_MONOTONIC,&t);
    if (!proc_pid_rusage(getpid(),RUSAGE_INFO_V0,(rusage_info_t *)&r)) {
        fprintf(stream,"%.9f,%llu,%llu,%llu,%llu\n",t.tv_sec+t.tv_nsec/1e9,
                r.ri_resident_size,r.ri_phys_footprint,r.ri_user_time,r.ri_system_time);
    }
}
static void *collect(void *unused) {
    struct timespec dt={0,20000000};
    while (atomic_load(&running)) {sample();nanosleep(&dt,NULL);}
    sample();return NULL;
}
int emcd_probe_start(const char *path) {
    stream=fopen(path,"w");if (!stream)return -1;
    fprintf(stream,"monotonic_seconds,rss_bytes,footprint_bytes,user_ticks,system_ticks\n");
    sample();atomic_store(&running,1);return pthread_create(&sampler,NULL,collect,NULL);
}
void emcd_probe_stop(void) {
    if (atomic_exchange(&running,0)) {pthread_join(sampler,NULL);fclose(stream);}
}
static void enter(void) {
    int (*initialized)(void)=dlsym(RTLD_DEFAULT,"Py_IsInitialized");
    int (*ensure)(void)=dlsym(RTLD_DEFAULT,"PyGILState_Ensure");
    void (*release)(int)=dlsym(RTLD_DEFAULT,"PyGILState_Release");
    int (*run)(const char*)=dlsym(RTLD_DEFAULT,"PyRun_SimpleString");
    if (initialized && initialized() && ensure && release && run) {
        int gil=ensure();
        run("exec(compile(open(__import__('os').environ['EMCD_BENCHMARK_CONTROLLER']).read(), '<external-native-benchmark>', 'exec'), {})");
        release(gil);
    } else dispatch_after(dispatch_time(DISPATCH_TIME_NOW,NSEC_PER_SEC),dispatch_get_main_queue(),^{enter();});
}
__attribute__((constructor)) static void start(void) {
    if (strcmp(getprogname(),"EMCD-Sim")==0)
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW,NSEC_PER_SEC),dispatch_get_main_queue(),^{enter();});
}
