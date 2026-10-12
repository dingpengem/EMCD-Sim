# Cross-platform development (Windows / macOS / Linux)

EMCD-Sim is a Python research application intended for **Windows 10/11 x64**, **macOS**, and **Linux** (Python 3.11). The `emcd-python` Conda environment is separate from QCBED's `qcbed-python`. Standard NumPy/Matplotlib builds do not require WSL, Homebrew, or a C/C++ compiler.

## Windows: Miniconda + VS Code + PowerShell

Open **Miniconda Prompt**, Conda-enabled PowerShell, or VS Code's integrated terminal:

```powershell
git clone https://github.com/dingpengem/EMCD-Sim.git
cd EMCD-Sim
conda create -n emcd-python python=3.11 -y
conda activate emcd-python
python -m pip install -e ".[dev]"
python -m pytest -q
python -m emcd_sim --diffraction-condition two-beam --diffraction-only --output "outputs/ni_2bc"
python -m emcd_sim --diffraction-condition symmetric-3bc --output "outputs/ni_3bc"
```

Find images in `outputs\ni_2bc\diffraction_pattern.png` or `outputs\ni_3bc\ni_emcd.png`. View them in VS Code or Windows File Explorer. If PowerShell cannot find Conda, use Miniconda Prompt, or run `conda init powershell` then restart.

In VS Code open the **EMCD-Sim** folder and select the Conda environment's Python executable; a typical location is `C:\Users\<username>\miniconda3\envs\emcd-python\python.exe`. The installation path varies. Do not commit machine-specific interpreter paths or modify the QCBED interpreter.

## macOS / Linux

```bash
git clone https://github.com/dingpengem/EMCD-Sim.git
cd EMCD-Sim
conda create -n emcd-python python=3.11 -y
conda activate emcd-python
python -m pip install -e ".[dev]"
python -m pytest -q
python -m emcd_sim --diffraction-condition zone-axis --max-beams 13 --diffraction-only --output outputs/ni_zone_axis
```

If you already created the Conda environment, skip its creation. The installed console script `emcd-ni` also works, but `python -m emcd_sim` avoids OS-specific PATH differences.

## Portability conventions

- Prefer `pathlib.Path` over string concatenation or absolute machine-specific paths.
- Use `sys.executable`, `python -m ...` and subprocess argument arrays instead of Bash-specific commands.
- Quote paths with spaces; use relative output paths by default while accepting explicit absolute paths.
- Save PNG figures via the headless Matplotlib Agg backend so an interactive display is not required.
- Keep DFT applications, GPUs, native compilers and transport solvers as optional adapters; they must not be required for the base EMCD CLI.
- GitHub Actions tests Python 3.11 on Windows, macOS and Linux. Portability tests are **not** physics validation.

## Limitations

This is currently an installable Python package, not a Windows `.exe` or a GUI. Packaging can be added at a later release milestone. MDFF remains illustrative and outgoing double channeling is not implemented.
