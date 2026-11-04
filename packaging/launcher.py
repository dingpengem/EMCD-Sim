from emcd_sim.gui.app import main

if __name__ == '__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='--release-acceptance':
        del sys.argv[1]
        from native_acceptance import main as acceptance
        raise SystemExit(acceptance())
    raise SystemExit(main())
