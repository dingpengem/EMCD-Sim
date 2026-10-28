# Generalized Multislice Windows candidate acceptance

The reviewed physics baseline is main `f85f38e28e3aa7e53234b0a0808317bd222e046b`.
Its first Windows build, Actions run `40721756404`, passed compilation and the
existing frozen [017] Single/Double BW/MS desktop acceptance.

The candidate QA extension adds `--desktop-orientation` to the opt-in
`--desktop-acceptance` executable command. Normal startup, numerical defaults,
version and solver physics are unchanged. The Windows build workflow now runs
the extracted executable sequentially for [017], [117], [001], [111] and [710].
Each report identifies its executable, frozen status, source commit, settings,
runtime dependencies, Bragg check, resource/warning preview and two channeling
cases. Both solvers calculate each case. It checks finite spectra, project
save/reopen fingerprints, Raw/Relative display immutability, maps and EELS
exports, About/defaults, layout and clean closure.

The explicit smoke profile is 300 kV, 1 nm, grid9, five depth nodes, selected
L3/L2 energies, four aperture subpixels and maximum slice step 0.25 nm.
[017]/[117] use beam cutoff 3.2 and potential cutoff 3.8 cycles/Angstrom,
FFT32, including off-row beams. Other profiles use 0.9/1.8, FFT24. These are
inexpensive packaging tests, **not numerical convergence settings**. The [111]
report must retain its warning. No production checkpoint is regenerated.

For an extracted candidate, run into a new destination per orientation:

```powershell
./EMCD-Sim.exe --desktop-acceptance C:/candidate-check/117 --desktop-orientation 117
```

The Actions environment uses Qt offscreen. Local Windows-platform automation
can additionally exercise native Qt rendering, but neither establishes a
human-operated clean-machine installation test. Before formal release, a human
must check visible rendering, input, scrolling/dialogs, diffraction alignment,
map/EELS navigation, project reopen, exports and warning readability on the
intended Windows environment.

The scientific limits remain those in
[the merge-readiness review](GENERALIZED_MULTISLICE_MERGE_READINESS.md): projected
IAM/ZOLZ and XMCD-effective MDFF, not Atomic 3D/HOLZ or a full DFT-derived MDFF;
BW/MS agreement is not independent physical convergence. In particular [111]
lower-support raw sensitivity 0.1094% fails the unchanged 0.1% gate. Its targeted
enlarged-support checks do not certify other thicknesses or a full curve.
