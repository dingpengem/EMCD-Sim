"""Generate a small visualization suite for WIEN2k Ni XMCD results.

Outputs written under examples/ni_xmcd_indexed/ by default:
- ni_dft_xmcd.svg/.png
- ni_dft_xmcd_zoom_L3L2.svg/.png
- ni_xmcd_indexing_dashboard.svg/.png
- ni_dft_xmcd_summary.txt

This is a visualization helper for the current XMCD-grounded EMCD workflow.
It does not assert quantitative EMCD validation.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch


def load_xmcd(path: Path):
    a = np.loadtxt(path, comments="#")
    e = a[:, 0]
    rp = a[:, 1]
    lp = a[:, 2]
    xmcd = a[:, 3]
    xas = a[:, 4]
    nxmcd = np.divide(xmcd, xas, out=np.zeros_like(xmcd), where=np.abs(xas) > 0)
    return e, rp, lp, xmcd, xas, nxmcd


def save_full_spectrum(outdir: Path, E, RP, LP, XMCD, XAS, NXMCD):
    mask = (E >= 845) & (E <= 878)
    Ef, RPf, LPf, XMCDf, XASf, NXMCDf = E[mask], RP[mask], LP[mask], XMCD[mask], XAS[mask], NXMCD[mask]
    fig = plt.figure(figsize=(8.2, 9.6))
    axs = [fig.add_subplot(4, 1, i + 1) for i in range(4)]
    axs[0].plot(Ef, RPf, label="RIGHT_POL (RP)")
    axs[0].plot(Ef, LPf, label="LEFT_POL (LP)")
    axs[0].plot(Ef, XASf, label="XAS = RP + LP")
    axs[0].set_ylabel("Intensity (arb. units)")
    axs[0].set_title("FCC Ni WIEN2k DFT XAS / XMCD around Ni L3 and L2")
    axs[0].legend(fontsize=8)
    axs[1].plot(Ef, XMCDf)
    axs[1].axhline(0.0, linewidth=0.8)
    axs[1].set_ylabel("XMCD = RP - LP")
    axs[1].set_title("XMCD difference spectrum")
    axs[2].plot(Ef, NXMCDf)
    axs[2].axhline(0.0, linewidth=0.8)
    axs[2].set_ylabel("XMCD / XAS")
    axs[2].set_title("Normalized XMCD")
    axs[3].plot(E, XAS, label="Full-range XAS")
    axs[3].plot(E, XMCD, label="Full-range XMCD")
    axs[3].set_xlabel("Energy (eV)")
    axs[3].set_ylabel("Intensity (arb. units)")
    axs[3].set_title("Full energy range from WIEN2k output")
    axs[3].legend(fontsize=8)
    for ax in axs:
        ax.grid(True, alpha=0.25)
        ax.axvline(852.7, linewidth=0.8)
        ax.axvline(870.0, linewidth=0.8)
    axs[0].text(852.7, axs[0].get_ylim()[1] * 0.92, "L3", ha="center", va="top", fontsize=9)
    axs[0].text(870.0, axs[0].get_ylim()[1] * 0.92, "L2", ha="center", va="top", fontsize=9)
    fig.tight_layout()
    fig.savefig(outdir / "ni_dft_xmcd.svg")
    fig.savefig(outdir / "ni_dft_xmcd.png", dpi=180)
    plt.close(fig)


def save_zoom(outdir: Path, E, RP, LP, XMCD, XAS, NXMCD):
    def window(center, half):
        m = (E >= center - half) & (E <= center + half)
        return E[m], RP[m], LP[m], XMCD[m], XAS[m], NXMCD[m]
    L3 = window(852.7, 6.0)
    L2 = window(870.0, 6.0)
    fig = plt.figure(figsize=(10.2, 7.8))
    axs = [fig.add_subplot(2, 2, i + 1) for i in range(4)]
    for ax, data, title, edge in [(axs[0], L3, 'L3 XAS / RP / LP', 852.7), (axs[2], L2, 'L2 XAS / RP / LP', 870.0)]:
        Ef, RPf, LPf, XMCDf, XASf, NXMCDf = data
        ax.plot(Ef, RPf, label='RP')
        ax.plot(Ef, LPf, label='LP')
        ax.plot(Ef, XASf, label='XAS')
        ax.axvline(edge, linewidth=0.8)
        ax.grid(True, alpha=0.25)
        ax.set_title(title)
        ax.set_ylabel('Intensity (arb. units)')
        ax.legend(fontsize=8)
        ax.set_xlabel('Energy (eV)')
    for ax, data, title, edge in [(axs[1], L3, 'L3 XMCD and normalized XMCD', 852.7), (axs[3], L2, 'L2 XMCD and normalized XMCD', 870.0)]:
        Ef, RPf, LPf, XMCDf, XASf, NXMCDf = data
        ax2 = ax.twinx()
        l1 = ax.plot(Ef, XMCDf, label='XMCD', linewidth=1.8)
        l2 = ax2.plot(Ef, NXMCDf, label='XMCD/XAS', linewidth=1.8)
        ax.axhline(0, linewidth=0.8)
        ax.axvline(edge, linewidth=0.8)
        ax.grid(True, alpha=0.25)
        ax.set_title(title)
        ax.set_ylabel('XMCD = RP - LP')
        ax2.set_ylabel('XMCD / XAS')
        ax.set_xlabel('Energy (eV)')
        lines = l1 + l2
        ax.legend(lines, [ln.get_label() for ln in lines], fontsize=8, loc='upper right')
    fig.suptitle('FCC Ni WIEN2k DFT XMCD: local L3 / L2 zoom views', fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(outdir / 'ni_dft_xmcd_zoom_L3L2.svg')
    fig.savefig(outdir / 'ni_dft_xmcd_zoom_L3L2.png', dpi=180)
    plt.close(fig)


def save_dashboard(outdir: Path, E, RP, LP, XMCD, XAS, NXMCD):
    a0 = 3.524
    g200 = 2.0 / a0
    spots = []
    for h in range(-4, 5):
        for k in range(-4, 5):
            if h % 2 == k % 2:
                gx, gy = h / a0, k / a0
                r = (gx * gx + gy * gy) ** 0.5
                if r <= 1.2 + 1e-9:
                    spots.append((h, k, 0, gx, gy, r))
    spots = sorted(spots, key=lambda x: x[-1])
    fig = plt.figure(figsize=(13.2, 11.2))
    gs = fig.add_gridspec(4, 4, height_ratios=[1.05, 1.0, 1.0, 0.62], hspace=0.65, wspace=0.35)
    ax1 = fig.add_subplot(gs[0, :2]); ax2 = fig.add_subplot(gs[0, 2:])
    mask = (E >= 845) & (E <= 878)
    ax1.plot(E[mask], RP[mask], label='RP'); ax1.plot(E[mask], LP[mask], label='LP'); ax1.plot(E[mask], XAS[mask], label='XAS')
    for v in (852.7, 870.0): ax1.axvline(v, linewidth=0.8)
    ax1.set_title('WIEN2k Ni DFT XAS / circular channels'); ax1.set_xlabel('Energy (eV)'); ax1.set_ylabel('Intensity (arb. units)'); ax1.grid(True, alpha=0.25); ax1.legend(fontsize=8)
    l1 = ax2.plot(E[mask], XMCD[mask], label='XMCD')[0]
    ax2b = ax2.twinx(); l2 = ax2b.plot(E[mask], NXMCD[mask], label='XMCD/XAS')[0]
    ax2.axhline(0, linewidth=0.8)
    for v in (852.7, 870.0): ax2.axvline(v, linewidth=0.8)
    ax2.set_title('XMCD-derived magnetic spectral response'); ax2.set_xlabel('Energy (eV)'); ax2.set_ylabel('XMCD'); ax2b.set_ylabel('XMCD / XAS'); ax2.grid(True, alpha=0.25)
    ax2.legend([l1, l2], ['XMCD', 'XMCD/XAS'], fontsize=8, loc='upper right')
    names = ['zone-axis', 'two-beam', 'near-2bc', 'symmetric-3bc']
    subtitles = ['2D ZOLZ [001] basis', 'ideal 000 / 200 truncation', '7-beam systematic row', 'nominal ±200 symmetric row']
    for idx, (name, subtitle) in enumerate(zip(names, subtitles)):
        ax = fig.add_subplot(gs[1 if idx < 2 else 2, idx % 2 * 2:(idx % 2 * 2) + 2])
        ax.axhline(0, color='0.7', lw=0.7); ax.axvline(0, color='0.7', lw=0.7)
        ax.set_aspect('equal'); ax.grid(True, alpha=0.18)
        ax.set_title(name); ax.text(0.02, 0.98, subtitle, ha='left', va='top', transform=ax.transAxes, fontsize=8)
        if name == 'zone-axis':
            for h, k, l, gx, gy, r in spots:
                ax.plot(gx, gy, 'ko', ms=3)
                if r <= 0.85:
                    ax.annotate(f'({h},{k},{l})', (gx, gy), xytext=(3, 4), textcoords='offset points', fontsize=6)
            ax.set_xlim(-1.05, 1.05); ax.set_ylim(-1.05, 1.05)
        elif name == 'two-beam':
            for h, k, l, gx, gy in [(0, 0, 0, 0, 0), (2, 0, 0, g200, 0)]:
                ax.plot(gx, gy, 'ko', ms=5); ax.annotate(f'({h},{k},{l})', (gx, gy), xytext=(3, 4), textcoords='offset points', fontsize=7)
            ax.add_patch(Circle((0.5 * g200, 0), 0.5 * g200, fill=False, ls=':', ec='0.5', lw=1.0))
            for label, y in [('A', 0.5 * g200), ('B', -0.5 * g200)]:
                ax.add_patch(Circle((0.5 * g200, y), 0.16 * g200, fill=False, ec='C0', lw=1.3)); ax.text(0.5 * g200, y, label, ha='center', va='center', fontsize=8)
            ax.set_xlim(-0.15, 1.35 * g200); ax.set_ylim(-1.0 * g200, 1.0 * g200)
        elif name == 'near-2bc':
            hs = [-6, -4, -2, 0, 2, 4, 6]
            for h in hs:
                gx = h / a0; ax.plot(gx, 0, 'ko', ms=4); ax.annotate(f'({h},0,0)', (gx, 0), xytext=(0, 6), ha='center', textcoords='offset points', fontsize=6)
            ax.add_patch(Circle((0.5 * g200, 0), 0.5 * g200, fill=False, ls=':', ec='0.5', lw=1.0))
            for label, y in [('A', 0.5 * g200), ('B', -0.5 * g200)]:
                ax.add_patch(Circle((0.5 * g200, y), 0.16 * g200, fill=False, ec='C0', lw=1.3)); ax.text(0.5 * g200, y, label, ha='center', va='center', fontsize=8)
            ax.set_xlim(-1.8, 1.8); ax.set_ylim(-1.0 * g200, 1.0 * g200)
        else:
            hs = [-6, -4, -2, 0, 2, 4, 6]
            for h in hs:
                gx = h / a0; ax.plot(gx, 0, 'ko', ms=4); ax.annotate(f'({h},0,0)', (gx, 0), xytext=(0, 6), ha='center', textcoords='offset points', fontsize=6)
            for xc in (-0.5 * g200, 0.5 * g200): ax.add_patch(Circle((xc, 0), 0.5 * g200, fill=False, ls=':', ec='0.5', lw=1.0))
            for label, x, y in [('RU', 0.5 * g200, 0.5 * g200), ('RD', 0.5 * g200, -0.5 * g200), ('LU', -0.5 * g200, 0.5 * g200), ('LD', -0.5 * g200, -0.5 * g200)]:
                ax.add_patch(Circle((x, y), 0.16 * g200, fill=False, ec='C0', lw=1.3)); ax.text(x, y, label, ha='center', va='center', fontsize=7)
            ax.set_xlim(-1.4 * g200, 1.4 * g200); ax.set_ylim(-1.0 * g200, 1.0 * g200)
        ax.set_xlabel('Qx (cycles/Å)'); ax.set_ylabel('Qy (cycles/Å)')
    note1 = fig.add_subplot(gs[3, :2]); note2 = fig.add_subplot(gs[3, 2:])
    for ax in (note1, note2):
        ax.set_axis_off()
        box = FancyBboxPatch((0.01, 0.08), 0.98, 0.84, boxstyle='round,pad=0.02', linewidth=0.8, edgecolor='0.6', facecolor='0.97', transform=ax.transAxes)
        ax.add_patch(box)
    note1.text(0.04, 0.85, 'Interpretation', fontsize=12, weight='bold', transform=note1.transAxes)
    note1.text(0.04, 0.67, 'DFT-grounded now: XAS via RP+LP; magnetic spectral response via RP−LP.', fontsize=9.5, transform=note1.transAxes)
    note1.text(0.04, 0.46, 'Still model-dependent: η (XMCD→EMCD scale/convention), β (Tzz / N), and outgoing channeling.', fontsize=9.5, transform=note1.transAxes)
    note1.text(0.04, 0.25, 'Use these plots as XMCD-grounded inputs and diffraction-condition references.', fontsize=9.5, transform=note1.transAxes)
    note2.text(0.04, 0.85, 'Repo outputs', fontsize=12, weight='bold', transform=note2.transAxes)
    for i, fn in enumerate(['ni_dft_xmcd.svg', 'ni_dft_xmcd_zoom_L3L2.svg', 'ni_xmcd_indexing_dashboard.svg']):
        note2.text(0.06, 0.67 - 0.18 * i, f'• {fn}', fontsize=10, transform=note2.transAxes)
    note2.text(0.54, 0.60, 'PNG companions and summary text included.', fontsize=9.5, transform=note2.transAxes)
    note2.text(0.54, 0.38, 'Future full WIEN2k-derived MDFF can reuse the same folder / interface structure.', fontsize=9.5, transform=note2.transAxes)
    fig.suptitle('FCC Ni WIEN2k XMCD and diffraction-condition indexing dashboard', fontsize=16)
    fig.savefig(outdir / 'ni_xmcd_indexing_dashboard.svg', bbox_inches='tight')
    fig.savefig(outdir / 'ni_xmcd_indexing_dashboard.png', dpi=180, bbox_inches='tight')
    plt.close(fig)


def save_summary(outdir: Path, E, XMCD, XAS):
    with (outdir / 'ni_dft_xmcd_summary.txt').open('w', encoding='utf-8') as f:
        f.write('WIEN2k FCC Ni DFT XMCD summary\n')
        f.write(f'Energy range: {E.min():.3f} to {E.max():.3f} eV\n')
        f.write(f'Max XAS: {XAS.max():.6e}\n')
        f.write(f'Max |XMCD|: {np.max(np.abs(XMCD)):.6e}\n')
        f.write('Figure files: ni_dft_xmcd.svg, ni_dft_xmcd_zoom_L3L2.svg, ni_xmcd_indexing_dashboard.svg\n')


def main(argv=None):
    p = argparse.ArgumentParser(description='Generate WIEN2k XMCD visualization suite')
    p.add_argument('--xmcd-file', type=Path, default=Path('data/wien2k_ni/Ni_fm.xmcd'))
    p.add_argument('--output-dir', type=Path, default=Path('examples/ni_xmcd_indexed'))
    args = p.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    E, RP, LP, XMCD, XAS, NXMCD = load_xmcd(args.xmcd_file)
    save_full_spectrum(args.output_dir, E, RP, LP, XMCD, XAS, NXMCD)
    save_zoom(args.output_dir, E, RP, LP, XMCD, XAS, NXMCD)
    save_dashboard(args.output_dir, E, RP, LP, XMCD, XAS, NXMCD)
    save_summary(args.output_dir, E, XMCD, XAS)


if __name__ == '__main__':
    main()