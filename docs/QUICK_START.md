# First calculation — v0.9 Research Beta candidate

[Home](../README.md) | [User Guide](USER_GUIDE.md) | [MDFF workflows](MDFF_WORKFLOWS.md) | [Candidate status](RELEASE_NOTES_0_9_0_BETA_1.md)

These instructions describe the current local v0.9.0-beta.1 candidate, not the published v0.8 binary. For that binary use its [tagged Quick Start](https://github.com/dingpengem/EMCD-Sim/blob/v0.8.1-beta.2/docs/QUICK_START.md). This is a coarse functional example, not convergence or quantitative spectroscopy.

## 1. Material and accepted Global MDFF

1. Extract the complete Windows folder, install the [Microsoft runtime prerequisite](INSTALL_WINDOWS.md), and launch `EMCD-Sim.exe`.
2. Choose **File → New Project**. Use the existing conventional FCC Ni default (3.524 Å), or explicitly import your Ni CIF through **Material → Open CIF…** and retain its actual cell. Do not substitute one cell for another when reproducing a study.
3. Open **Material → 3D Structure Viewer… → Site groups**. Choose **Global Magnetization Mode** and enter **Global Material M (x y z)** as `0 0 1`.
4. Choose the **Global** context in **Configure MDFF…** and select **XMCD-constrained MDFF**. Browse the packaged `_internal/data/wien2k_ni/Ni_fm.xmcd` (source checkout: `data/wien2k_ni/Ni_fm.xmcd`). Use only a source appropriate for the selected material.
5. Validate the source, inspect its actual native features, and complete the visible magnetic-axis, handedness and edge acknowledgements. Keep eta/beta at 1 for this example. Review **Use explicit material declarations** and its provenance, assumptions, scientific status and reference-scale fields; supply truthful declarations. Ambiguous edge selections must be explicit. Do not replace the file's native energies with generic tabulated Ni edges.
6. Generate the MDFF preview if desired, then **Done** and the Viewer's **Apply and Close**. Preview/Done alone does not accept Material configuration. Global readiness must refer to the accepted Global provider; inactive local structural rows need not be configured.

For Local calculations instead, define original-index memberships and directions, enable ionization only for participating groups, configure each provider, then Apply. Ordinary CIF grouping assigns no M or MDFF. Oxygen may remain elastic-only. See the [group workflow](USER_GUIDE.md#development-site-groups).

## 2. A deliberately small calculation

In **Zone Axis & Diffraction → Orientation / ZA options**, set nominal zone `0 0 1`, target `2 0 0`, and **Apply orientation / target**. Set tilt to `−5, +7 mrad`, voltage **200 kV** and thickness **0.2 nm**. Restore Thales A/B for this actual geometry; inspect detector coverage.

In **Propagation Method**, choose **Single Channeling**, **Bloch-wave**. In **Shared Calculation Settings → Numerical Settings**, use **General settings (editable)** and enter:

| Control | Coarse value |
| --- | ---: |
| Beam / MDFF basis cutoff | 0.6 Å⁻¹ |
| Potential Fourier cutoff | 1.2 Å⁻¹ |
| Explicit target systematic-row approximation | Off |
| Angular / detector grid points (odd) | 9 |
| Depth integration nodes | 5 |
| Aperture boundary subpixels | 4 |
| Map halfwidth | 0.7 Å⁻¹ |
| Energy sampling | Selected energies only |
| Full angular maps at selected energies | On |
| Full angular field at every energy (advanced) | Off |
| Parallel Workers | Manual; requested workers 1 |

This example deliberately overrides the normal **Entire energy range → uniform sampling** default of 241 requested points plus exact selections. Two selected samples are points, not a resolved EELS spectrum. Angular grid, FFT grid, depth nodes and aperture subpixels are independent controls. Review resource admission without silently coarsening an existing research configuration.

## 3. Run, inspect and retain

**Run EMCD / EELS** executes the accepted configuration; **Preview diffraction** is a separate optional elastic calculation. Progress reports current work and elapsed time. Cancel is cooperative; wait for idle before another run. Internal NumPy/SciPy BLAS control is automatic and verified; do not configure environment variables for normal use.

Start with **Total Results**. Raw +M/−M, reversal-even/odd, conventional A−B and magnetic/nonmagnetic A−B have different definitions. Local Group Contribution is additive using the same denominator as Total; Group Mean is per group atom and is not additive. Energy gaps remain unmodeled.

Use **File → Save As…** to save a separate complete project, then reopen it. Subsequent results can be kept with **Keep as New Calculation**. **Project Results** provides **Restore Settings from Selected Run…**, **Delete Selected Calculation…**, and the two-calculation comparison dialog. Figure/data export and details remain near Results. Saved arrays can be viewed when an external source is unavailable, but rerun must remain blocked until the correct source validates.
