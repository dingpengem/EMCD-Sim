# Diffraction conditions and indexed patterns (v0.3)

## Nominal specimen orientation and coordinate frame

The current crystal model is an oriented conventional cubic FCC Ni cell with the foil normal along **[001]**. The zone-axis label in plots describes that **nominal crystal orientation**; in tilted experiments the incident electron is *not* exactly on that zone axis. Diffraction reciprocal positions use cycles/Å, no `2π`. This version cannot solve general [uvw] zone axes or HOLZ without a crystal orientation adapter.

A plane-wave entrance field excites a finite set of beams. Elastic beam intensities at sample thickness `t` are `|ψ_g(t)|²`, where `ψ(t)=exp(i H t)ψ(0)` from the physical Bloch-wave solver. The signed excitation errors are:

`s_g = λ/2 (|k_perp+g|² - |k_perp|²)` (Å⁻¹),

with positive signs consistent with `H_gg=-20 π s_g` (nm⁻¹). Here `λ` is in Å, `k_perp=tilt_rad/λ` and `g` is in cycles/Å. For the Ni (200) reflection at 200 kV the Bragg angle is `θ_B=λ|g_200|/2 ≈ 7.12 mrad`. A negative x tilt of `θ_B` sets `s_200=0` in this convention.

## Presets

| Condition | Default beam basis | Tilt (x,y) at 200 kV | What it represents |
|---|---|---|---|
| `systematic-row` | 000, ±200, ±400, ±600 | 0, 0 mrad | v0.2 default; *not* full [001] zone-axis |
| `zone-axis` | 2D [001] ZOLZ, cutoff 1.20 Å⁻¹, max 25 | 0, 0 mrad | Finite 2D zone-axis basis; for quick pictures choose 13 beams |
| `two-beam` | 000 and +200 only | −θ_B, +25 mrad | **Idealized two-beam truncation** (all other beams removed by hand) |
| `near-2bc` | Seven (200) systematic-row beams | −θ_B, +25 mrad | +200 exactly Bragg in the paraxial model, additional row beams retained |
| `symmetric-3bc` | Seven (200) systematic-row beams | 0, +25 mrad | ±200 have equal *nonzero* excitation errors; not an exact simultaneous Bragg solution |

The +25 mrad off-row tilt is an **illustrative default** to move away from other [001] zone-axis beams. It is adjustable with `--offzone-tilt-mrad` and should not be interpreted as experimentally optimized for Ni, nor as proof that all off-row reflections are unexcited. The off-row beams are **not propagated** in the `two-beam`, `near-2bc` and `symmetric-3bc` presets. Therefore these modes are approximations, not exact predictions of alignment and Kikuchi geometry in a TEM.

Especially important: **±200 cannot both have s=0 at the same time for finite Ewald-sphere curvature.** Symmetric 3BC is defined here by `s_200 = s_-200`, not simultaneous exact Bragg conditions.

## Quick runs

Run in `~/EM_code/EMCD-Sim` with the `emcd-python` Conda environment:

```bash
emcd-ni --diffraction-condition zone-axis --max-beams 13 --diffraction-only --output outputs/ni_zone_axis
emcd-ni --diffraction-condition near-2bc --diffraction-only --output outputs/ni_near_2bc
emcd-ni --diffraction-condition symmetric-3bc --diffraction-only --output outputs/ni_3bc
emcd-ni --diffraction-condition two-beam --diffraction-only --output outputs/ni_two_beam
```

Remove `--diffraction-only` to also run the present **illustrative**, entrance-only Ni MDFF/EELS simulation (slower for large 2D beam sets). The original `emcd-ni --output ...` command still uses the original seven-beam row.

## Data and display

Each diffraction run writes:

- `diffraction_pattern.png`: calculated Bragg intensities at indexed `(h,k,l)` positions and elastic intensity bars, with the nominal zone axis, condition and tilt.
- `diffraction_pattern.npz`: `beam_hkl`, `g_xy_inv_angstrom`, `elastic_intensity`, complex `amplitudes`, `excitation_error_inv_angstrom`, thickness and tilt.
- `diffraction_spots.csv`: spreadsheet-compatible indexed spot table with coordinates, excitation errors and intensities.
- `metadata.json`: condition and provenance; when EMCD is also run, adds the existing MDFF/EELS metadata.

The Bragg spots represent plane-wave delta-functions convolved with **artificial Gaussian shapes solely for legible display**, *not* a simulated finite convergence disk, PSF, noise or experimental diffraction pattern. Absorption and thermal diffuse scattering remain absent; intensity sums to approximately one. The visualized pattern includes **only the finite Bloch-wave basis**: weak and omitted spots should not be interpreted as structure-factor extinctions. Convergence of the full 2D Bloch-wave solution is not established.
