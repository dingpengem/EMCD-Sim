"""Native bundle entry point with explicit local acceptance routes."""
import multiprocessing
import sys
if __name__ == '__main__':
    multiprocessing.freeze_support()
    if len(sys.argv)==3 and sys.argv[1]=='--macos-memory-acceptance':
        from macos_memory_acceptance import run
        raise SystemExit(run(sys.argv[2]))
    if len(sys.argv)>1 and sys.argv[1]=='--release-acceptance':
        del sys.argv[1]
        from native_acceptance import main
    elif len(sys.argv)>1 and sys.argv[1]=='--version':
        from emcd_sim.provenance import build_info
        import json
        print(json.dumps(build_info(),indent=2));raise SystemExit(0)
    else:
        from emcd_sim.gui.app import main
    raise SystemExit(main())
