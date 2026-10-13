# Ni WIEN2k-constrained MDFF: Windows runbook (2026-10-13)

This is a **research-stage, entrance-only** EMCD calculation, not a quantitatively validated Ni EMCD cross section.

## Physical input and assumptions

- `data/wien2k_ni/Ni_fm.xmcd` provides energy, right/left circular absorption, XMCD (RP-LP), XAS (RP+LP).
- `xmcd-effective` constructs `N=(RP+LP)/2`, `D=(RP-LP)/2`, `Txx=Tyy=N`, `Tzz=beta*N`, `Txy=i*eta*D`, `Tyx=-i*eta*D`; it normalizes relative to peak N.
- Default `eta=beta=1` are assumptions. Longitudinal response, finite-q corrections, exit channeling and absolute scattering scale are not DFT-derived.

## Windows CMD from a fresh clone

```bat
call "C:\Users\peng863\AppData\Local\miniconda3\Scripts\activate.bat" emcd-python
cd /d C:\Users\peng863\EMCD-Sim
git pull --ff-only origin main
python -m pip install -e .
python -c "import emcd_sim; print(emcd_sim.__version__)"
```

Use **Command Prompt** in VS Code rather than PowerShell if execution policy blocks Conda activation. The environment path is specific to the initial Windows workstation.

## Near-2BC baseline

```bat
python -m emcd_sim --mdff-model xmcd-effective --xmcd-file data\wien2k_ni\Ni_fm.xmcd --xmcd-eta 1 --xmcd-beta 1 --diffraction-condition near-2bc --thickness-nm 30 --grid 65 --steps 64 --output outputs\ni_dft_near2bc
```

The user reported this **local** run completed with `L3_ev=852.5859945652173`, `L3_asymmetry=0.0016984368423277173` (~0.16984%), and `quantitative_Ni=false`. This is *not* an independently reproduced CI result and should not be treated as an experimental prediction.

## Four diffraction conditions

```bat
python -m emcd_sim.xmcd_indexed_maps --xmcd-file data\wien2k_ni\Ni_fm.xmcd --output outputs\ni_dft_mdff_maps --thickness-nm 30 --grid 65 --steps 64
```

This generates `zone-axis`, `two-beam`, `near-2bc`, `symmetric-3bc` indexed diffraction and L3/L2 map outputs. Do not claim a new run has completed until its generated files are checked.

## Saving outputs separately

```bat
git status
```

Generated `outputs/` files are local unless specifically committed. Do not blindly `git add .` since local files can be large. For reproducible shared samples, use the existing `.github/workflows/ni-xmcd-maps.yml` or selectively stage the desired result files.

## Interpretation

Compare normalized maps on identical coordinate limits and scaling. Variations in `eta` and `beta` probe the effective-tensor assumptions; single- versus double-channeling error has not yet been established.
