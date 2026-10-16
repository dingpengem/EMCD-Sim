param([string]$Python = "$PSScriptRoot/../build/windows-rc/venv/Scripts/python.exe",
      [string]$BuildRoot = "build/windows-stage-f",
      [string]$BuildLabel = "EMCD-Sim GUI Stage F RC (unreleased)")
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path "$PSScriptRoot/..").Path
Push-Location $root
try {
    # PyInstaller logs progress to stderr; Windows PowerShell must not treat
    # those informational native records as terminating script errors.
    $nativePreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    if (Test-Path -LiteralPath "$BuildRoot/dist") { throw "Use a new build location; existing distribution is preserved." }
    $env:EMCD_GUI_BUILD_ROOT = $BuildRoot
    $env:EMCD_GUI_BUILD_LABEL = $BuildLabel
    & $Python -m PyInstaller --noconfirm --distpath "$BuildRoot/dist" --workpath "$BuildRoot/work" packaging/emcd_gui.spec
    $buildStatus = $LASTEXITCODE
    $ErrorActionPreference = $nativePreference
    if ($buildStatus -ne 0) { throw 'PyInstaller build failed' }
    Compress-Archive -LiteralPath "$BuildRoot/dist/EMCD-Sim" -DestinationPath "$BuildRoot/EMCD-Sim-Stage-F-Windows-RC.zip"
    Get-FileHash "$BuildRoot/EMCD-Sim-Stage-F-Windows-RC.zip" -Algorithm SHA256
} finally { Pop-Location }
