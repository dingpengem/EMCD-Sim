# Native macOS ARM64 local development candidate

Use a native Apple Silicon Python 3.11. This candidate requires macOS 15 or newer for verified Accelerate thread
control (the scientific wheels themselves require macOS 14). This is an unsigned development candidate, not a published release.
The shared Qt GUI, scientific kernels, numerical defaults and project formats
are those of v0.9.0-beta.1, source ef81576e2692c2c826bfbe2b89f21e00b05936e4.

From the isolated `feat/macos-arm64-gui` worktree at
`outputs/macos-arm64-development-20261110` under the original checkout:

```sh
/path/to/arm64/python3.11 -m venv .venv-macos
.venv-macos/bin/python -m pip install -e '.[dev,gui]' -r packaging/requirements-macos.txt
.venv-macos/bin/python -c 'from emcd_sim.gui.app import main; raise SystemExit(main())'
bash packaging/build_macos.sh
open build/macos-arm64/dist/EMCD-Sim.app
```

An alternative fresh output root can be passed to the build script. It refuses
to overwrite an existing build. `PYTHON` selects another dedicated ARM64 venv.
The build records installed versions (without a machine-specific editable path)
in `dependencies.txt` and bundle build information. To reproduce the complete
resolved environment, install that freeze in a fresh ARM64 Python 3.11 venv, then
install this checkout with `pip install --no-deps -e .`. PyInstaller collects the Python runtime, Cocoa Qt plugin, scientific
libraries, Matplotlib backends/resources, ASE space-group data, spglib, scientific
tables, examples and dependency licenses. No installed Python is needed to run
the resulting complete `.app`.

Copy the **entire** EMCD-Sim.app to a writable location, then open it normally.
Projects and exports belong outside the app. Default workspace, logs and
preferences live under `~/Library/Application Support/EMCD-Sim`.
`EMCD_GUI_WORKSPACE` overrides the workspace only. No writes to the bundle are
required. Do not disable Gatekeeper; signing/notarization are outside this local
development task. PyInstaller uses local ad-hoc signatures, not a Developer ID.

Native automated acceptance (fresh output path required):

```sh
.venv-macos/bin/python packaging/macos_acceptance.py /tmp/emcd-source-acceptance
open -n build/macos-arm64/dist/EMCD-Sim.app --args --native-macos-acceptance /tmp/emcd-bundle-acceptance
```

This shows native widgets and runs actual small numerical workers. File dialog
selections are injected in automation; human file-dialog/trackpad acceptance
must be recorded separately. Synthetic Cr, magnetite and ferrite tests establish
software behavior, not calibrated spectroscopy. See MACOS_ACCEPTANCE.md for
observed results, incomplete workflows and numerical comparison scope.
