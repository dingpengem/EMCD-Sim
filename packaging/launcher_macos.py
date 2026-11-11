"""macOS bundle launcher; normal application remains the shared Qt entry point."""
import sys

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--native-macos-acceptance':
        from macos_acceptance import run
        raise SystemExit(run(sys.argv[2]))
    from emcd_sim.gui.app import main
    raise SystemExit(main())
