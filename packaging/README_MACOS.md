# Local macOS ARM64 beta.3 build

Use a dedicated native ARM64 Python 3.11 environment with the reviewed dependency
inventory. `PYTHON=/absolute/venv/bin/python bash packaging/build_macos.sh /new/build/root`
builds from clean committed source and refuses to overwrite a build root. This
companion spec does not apply the Windows DLL inventory to macOS. Every bundled
Mach-O must contain ARM64. macOS 15 or newer is required for the verified
Accelerate per-thread BLAS control API; it is set on both the calculation thread
and every detector-executor thread, then restored. Scientific kernels and
precision are unchanged.

The launcher supports the shared `--help`, `--desktop-acceptance`,
`--scientific-acceptance`, `--cancellation-acceptance` and `--parallel-acceptance`
routes. It also supports `--version`, `--release-acceptance OUTPUT [--grouping | --multisite]`
and `--macos-memory-acceptance OUTPUT`. Each acceptance output must be new.
Native GUI checks require a logged-in desktop session and Cocoa, without an
offscreen override. The memory matrix uses actual GUI workers, native resident
bytes and physical footprint, and a 200 ms sample interval. Detector workers are
threads sharing parent-process arrays, not child processes. Single Channeling
manual requests above one worker must be rejected.

Auto uses the shared beta.3 allocation policy: floor(current RSS + 0.5 * current
available physical RAM), with total-process-peak semantics. On macOS availability
is Mach free + inactive pages times the native page size. Speculative pages are
already free; compressor storage, swap and a separate purgeable-page count are
not added. Admission includes current RSS, 128 MiB reserve and a 25% workspace
margin; additional allocations are bounded by half the current availability.
No fixed fallback budget or macOS-specific percentage increase is used.

Create the normal app ZIP using `/usr/bin/ditto -c -k --sequesterRsrc --keepParent
/path/EMCD-Sim.app /new/path/app.zip`. Extract with ditto and verify Mach-O
architectures, symlinks, signatures, provenance and launch again. Supply the exact
committed application source (`git archive HEAD`) plus matching dependency source
archives and replacement instructions described in assets/macos-licenses.
Ad-hoc signing is local execution support; it is not Developer ID signing or
notarization. Do not publish until the user manually accepts the exact candidate.
