param([string]$Python = "$PSScriptRoot/../build/windows-rc/venv/Scripts/python.exe",
      [string]$BuildRoot = "build/windows-beta-rc",
      [string]$BuildLabel = "EMCD-Sim Beta RC (unreleased)",
      [string]$ArchiveName = "EMCD-Sim-0.4.5-Beta-RC-Windows.zip")
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
    $appRoot = (Resolve-Path "$BuildRoot/dist/EMCD-Sim").Path
    Copy-Item -LiteralPath "$root/packaging/BETA_README.txt" -Destination "$appRoot/README.txt"
    $fileRecords = @(Get-ChildItem -LiteralPath $appRoot -Recurse -File | ForEach-Object {
        [pscustomobject]@{path=$_.FullName.Substring($appRoot.Length+1).Replace('\','/');bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
    })
    $manifest = [ordered]@{label=$BuildLabel;version='0.4.5';build=(Get-Content -LiteralPath "$appRoot/_internal/build_info.json" -Raw | ConvertFrom-Json);files=$fileRecords;clean_machine_acceptance='NOT TESTED'}
    $manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath "$BuildRoot/build_manifest.json" -Encoding UTF8
    $fileRecords | ForEach-Object { $_.sha256+'  '+$_.path } | Set-Content -LiteralPath "$appRoot/SHA256SUMS.txt" -Encoding ASCII
    Compress-Archive -LiteralPath $appRoot -DestinationPath "$BuildRoot/$ArchiveName"
    $archiveHash = Get-FileHash -LiteralPath "$BuildRoot/$ArchiveName" -Algorithm SHA256
    ($archiveHash.Hash.ToLowerInvariant()+'  '+$ArchiveName) | Set-Content -LiteralPath "$BuildRoot/SHA256SUMS.txt" -Encoding ASCII
    $archiveHash
} finally { Pop-Location }
