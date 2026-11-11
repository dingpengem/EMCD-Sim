param([string]$Python = "$PSScriptRoot/../build/windows-rc/venv/Scripts/python.exe",
      [string]$BuildRoot = "build/windows-v0.9.0-beta.2",
      [string]$BuildLabel = "",
      [string]$ArchiveName = "",
      [string]$SourceArchiveName = "",
      [Parameter(Mandatory=$true)][string]$CorrespondingSourceRoot)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path "$PSScriptRoot/..").Path
Push-Location $root
$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = "$root/src" + $(if ($previousPythonPath) { ";$previousPythonPath" } else { "" })
try {
    & $Python "$PSScriptRoot/check_windows_metadata.py"
    if ($LASTEXITCODE -ne 0) { throw 'Windows build metadata preflight failed; install the declared build requirements into the selected interpreter.' }
    & $Python "$PSScriptRoot/check_package_contents.py" --environment --source-root $CorrespondingSourceRoot
    if ($LASTEXITCODE -ne 0) { throw 'Required packaging assets or reviewed Qt environment failed preflight.' }
    $applicationVersion = (& $Python -c "from emcd_sim import __version__; print(__version__)").Trim()
    if ($LASTEXITCODE -ne 0 -or -not $applicationVersion) { throw 'Cannot read source application version' }
    $displayVersion = (& $Python -c "from emcd_sim import __display_version__; print(__display_version__)").Trim()
    if (-not $BuildLabel) { $BuildLabel = (& $Python -c "from emcd_sim.gui.runtime import LABEL; print(LABEL)").Trim() }
    if (-not $ArchiveName) { $ArchiveName = "EMCD-Sim-$displayVersion-Windows.zip" }
    if (-not $SourceArchiveName) { $SourceArchiveName = "EMCD-Sim-$displayVersion-Qt-sources.zip" }
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
    & $Python "$PSScriptRoot/check_package_contents.py" --dist $appRoot
    if ($LASTEXITCODE -ne 0) { throw 'Required package content or Qt binary inventory failed; do not archive this distribution.' }
    $fileRecords = @(Get-ChildItem -LiteralPath $appRoot -Recurse -File | ForEach-Object {
        [pscustomobject]@{path=$_.FullName.Substring($appRoot.Length+1).Replace('\','/');bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
    })
    $manifest = [ordered]@{label=$BuildLabel;version=$applicationVersion;build=(Get-Content -LiteralPath "$appRoot/_internal/build_info.json" -Raw | ConvertFrom-Json);files=$fileRecords;clean_machine_acceptance='NOT TESTED'}
    $manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath "$BuildRoot/build_manifest.json" -Encoding UTF8
    $fileRecords | ForEach-Object { $_.sha256+'  '+$_.path } | Set-Content -LiteralPath "$appRoot/SHA256SUMS.txt" -Encoding ASCII
    Compress-Archive -LiteralPath $appRoot -DestinationPath "$BuildRoot/$ArchiveName"
    $archiveHash = Get-FileHash -LiteralPath "$BuildRoot/$ArchiveName" -Algorithm SHA256
    ($archiveHash.Hash.ToLowerInvariant()+'  '+$ArchiveName) | Set-Content -LiteralPath "$BuildRoot/SHA256SUMS.txt" -Encoding ASCII
    $sourceStage = "$BuildRoot/corresponding-source"
    New-Item -ItemType Directory -Path $sourceStage | Out-Null
    $sourceProvenance = Get-Content -LiteralPath "$root/packaging/assets/qt-licenses/upstream-provenance.json" -Raw | ConvertFrom-Json
    foreach ($package in $sourceProvenance.source_packages) {
        Copy-Item -LiteralPath (Join-Path $CorrespondingSourceRoot $package.filename) -Destination $sourceStage
    }
    Copy-Item -LiteralPath "$root/packaging/assets/qt-licenses/SOURCE_AND_REPLACEMENT.md" -Destination "$sourceStage/README.md"
    # Keep the reviewed Qt guide intact, but identify this candidate rather
    # than presenting its historical beta.1 archive/tag names as current.
    $qtGuide = Get-Content -LiteralPath "$sourceStage/README.md" -Raw
    $sourceContext = @"
# Corresponding sources for $displayVersion

Application commit: $($manifest.build.commit)
Current source package: $SourceArchiveName
The matching application snapshot is EMCD-Sim-source.zip. This is an unpublished candidate; no new release tag is implied.
The unchanged Qt 6.12 technical guide below retains its original beta.1 filenames/tag references. Use the current package and commit above for this candidate. The listed dependency sources and replacement instructions still apply.

"@
    [IO.File]::WriteAllText((Join-Path $sourceStage 'README.md'), $sourceContext + [Environment]::NewLine + [Environment]::NewLine + $qtGuide, [Text.UTF8Encoding]::new($false))
    Copy-Item -LiteralPath "$root/packaging/assets/qt-licenses/upstream-provenance.json" -Destination $sourceStage
    git archive --format=zip --output="$sourceStage/EMCD-Sim-source.zip" HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Corresponding application source archive failed' }
    Compress-Archive -Path "$sourceStage/*" -CompressionLevel NoCompression -DestinationPath "$BuildRoot/$sourceArchiveName"
    $sourceHash = Get-FileHash -LiteralPath "$BuildRoot/$sourceArchiveName" -Algorithm SHA256
    ($sourceHash.Hash.ToLowerInvariant()+'  '+$sourceArchiveName) | Add-Content -LiteralPath "$BuildRoot/SHA256SUMS.txt" -Encoding ASCII
    $manifest['corresponding_source'] = [ordered]@{archive=$sourceArchiveName;sha256=$sourceHash.Hash.ToLowerInvariant();packages=$sourceProvenance.source_packages}
    $manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath "$BuildRoot/build_manifest.json" -Encoding UTF8
    $archiveHash
} finally { $env:PYTHONPATH = $previousPythonPath; Pop-Location }
