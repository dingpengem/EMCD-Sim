# NI DFT XMCD plot

This folder contains a direct visualization of the WIEN2k FCC Ni XMCD/XAS result based on `data/wien2k_ni/Ni_fm.xmcd`.

Files:
- `ni_dft_xmcd.svg`: committed vector figure for Git.
- `ni_dft_xmcd_summary.txt`: quick numerical summary.
- `scripts/research/plot_wien2k_xmcd.py`: reproducible plotting script.

Suggested Git location:
- `examples/ni_xmcd_indexed/ni_dft_xmcd.svg`
- `examples/ni_xmcd_indexed/ni_dft_xmcd_summary.txt`
- `scripts/research/plot_wien2k_xmcd.py`

The plot shows:
1. RP, LP and XAS around Ni L3/L2;
2. XMCD difference spectrum;
3. normalized XMCD/XAS;
4. full-range XAS and XMCD.

The figure is a visualization of the DFT/WIEN2k XMCD output and does not imply quantitative EMCD validation.


Additional files created in this step:
- ni_dft_xmcd_zoom_L3L2.svg / .png : local L3/L2 zoom figure.
- ni_xmcd_indexing_dashboard.svg / .png : unified XMCD + diffraction indexing dashboard.