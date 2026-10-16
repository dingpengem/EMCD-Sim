param([string]$Python = "$PSScriptRoot/../build/windows-rc/venv/Scripts/python.exe")
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path "$PSScriptRoot/..").Path
Push-Location $root
try {
    & $Python -m PyInstaller --noconfirm --distpath build/windows-rc/dist --workpath build/windows-rc/work packaging/emcd_gui.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed' }
    Compress-Archive -LiteralPath build/windows-rc/dist/EMCD-Sim -DestinationPath build/windows-rc/EMCD-Sim-Windows-RC.zip -Force
    Get-FileHash build/windows-rc/EMCD-Sim-Windows-RC.zip -Algorithm SHA256
} finally { Pop-Location }
