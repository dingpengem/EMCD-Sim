"""macOS bundle launcher; normal application remains the shared Qt entry point."""
import sys

if __name__ == '__main__':
    if len(sys.argv) in (4,5) and sys.argv[1] == '--native-macos-corrections':
        from macos_corrective_acceptance import run
        raise SystemExit(run(sys.argv[2],sys.argv[3],sys.argv[4] if len(sys.argv)==5 else 'bounded'))
    if len(sys.argv) == 3 and sys.argv[1] == '--native-macos-acceptance':
        from macos_acceptance import run
        raise SystemExit(run(sys.argv[2]))
    from emcd_sim.gui.app import main
    raise SystemExit(main())
