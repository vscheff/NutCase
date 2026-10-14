param([switch]$Bootstrap, [switch]$SkipTests, [switch]$AllowUnresolvedLicensing, [string]$ArtifactDirectory)
$ErrorActionPreference = 'Stop'
$repository = Split-Path $PSScriptRoot -Parent
if ($Bootstrap) {& (Join-Path $PSScriptRoot 'bootstrap-build.ps1')}
$python = Join-Path $repository '.venv-build\Scripts\python.exe'
$compiler = Join-Path $repository '.build-tools\inno\ISCC.exe'
if (-not (Test-Path -LiteralPath $python) -or -not (Test-Path -LiteralPath $compiler)) {
    throw 'Run scripts\bootstrap-build.ps1 first or use -Bootstrap.'
}
Push-Location $repository
$previousBuildPath=$env:PATH
$previousBuildPythonHome=$env:PYTHONHOME
$previousBuildPythonPath=$env:PYTHONPATH
try {
    # Binary dependency discovery must not harvest DLLs from developer tools.
    $env:PATH=Join-Path $env:SystemRoot 'System32'
    Remove-Item Env:\PYTHONHOME -ErrorAction SilentlyContinue
    Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
    & $python (Join-Path $repository 'packaging\prepare_bundle.py') --check-toolchain
    if ($LASTEXITCODE -ne 0) {throw 'Toolchain version check failed'}
    if (-not $SkipTests) {
        & $python -m unittest discover -s tests -v
        if ($LASTEXITCODE -ne 0) {throw 'Packaging regression tests failed'}
    }
    & $python -m PyInstaller --noconfirm --clean (Join-Path $repository 'packaging\NutCase.spec')
    if ($LASTEXITCODE -ne 0) {throw 'Frozen application build failed'}
    & $python (Join-Path $repository 'packaging\prepare_bundle.py')
    if ($LASTEXITCODE -ne 0) {throw 'Bundle staging or license collection failed'}
    & $python (Join-Path $repository 'packaging\smoke_bundle.py')
    if ($LASTEXITCODE -ne 0) {throw 'Frozen GUI/worker smoke checks failed'}
    $version = (Get-Content -LiteralPath VERSION -Raw).Trim()
    # The frozen diagnostic tool is not installed. Check exactly the installer
    # scope in a fresh retained staging directory, without ignoring unknown files.
    $bundle = Join-Path $repository ('dist\installer-payload-'+[Guid]::NewGuid().ToString('N'))
    & $python (Join-Path $repository 'packaging\prepare_bundle.py') --installer-payload $bundle
    if ($LASTEXITCODE -ne 0) {throw 'Installer payload staging failed'}
    $artifacts = if ($ArtifactDirectory) {[IO.Path]::GetFullPath($ArtifactDirectory)} else {Join-Path $repository 'artifacts'}
    New-Item -ItemType Directory -Path $artifacts -Force | Out-Null
    $existingCandidates=@((Join-Path $artifacts "NutCase-$version-windows-x64-setup.exe"),
                         (Join-Path $artifacts "NutCase-$version-source.zip"),
                         (Join-Path $artifacts 'SHA256SUMS.txt')) | Where-Object {Test-Path -LiteralPath $_}
    if ($existingCandidates.Count -gt 0) {
        $retainedCandidate=Join-Path $artifacts ('candidate-history\'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8))
        New-Item -ItemType Directory -Path $retainedCandidate -Force | Out-Null
        foreach ($existingCandidate in $existingCandidates) {Copy-Item -LiteralPath $existingCandidate -Destination $retainedCandidate}
    }
    & $compiler ("--define=AppVersion=$version") ("--define=BundleDir=$bundle") ("--define=ArtifactDir=$artifacts") (Join-Path $repository 'packaging\NutCase.iss')
    if ($LASTEXITCODE -ne 0) {throw 'Windows installer build failed'}
    & $python (Join-Path $repository 'packaging\prepare_bundle.py') --release-artifacts --artifact-directory $artifacts
    if ($LASTEXITCODE -ne 0) {throw 'Release checksum/source archive creation failed'}
    & $python (Join-Path $repository 'packaging\licensing\fetch_reviewed.py') --materials (Join-Path $repository 'artifacts\licensing-materials')
    if ($LASTEXITCODE -ne 0) {throw 'Reviewed licensing source material retrieval failed'}
    $complianceReport=Join-Path $artifacts 'compliance-report.json'
    $reviewPath=Join-Path $repository 'packaging\licensing\inventory.json'
    if (-not (Test-Path -LiteralPath $reviewPath)) {$reviewPath=Join-Path $repository 'packaging\licensing\reference-inventory.zip'}
    & $python (Join-Path $repository 'packaging\licensing\verify.py') --bundle $bundle --review $reviewPath --materials (Join-Path $repository 'artifacts\licensing-materials') --supplemental-materials (Join-Path $repository 'artifacts\licensing-candidate\research') --installer (Join-Path $artifacts ("NutCase-$version-windows-x64-setup.exe")) --report $complianceReport
    if ($LASTEXITCODE -ne 0) {
        $compliance=Get-Content -LiteralPath $complianceReport -Raw | ConvertFrom-Json
        $integrityFailures=@($compliance.findings | Where-Object { $_.code -notin @('component_review','obligation') })
        if (-not $AllowUnresolvedLicensing -or $integrityFailures.Count -gt 0) {throw 'Release compliance gate failed; see artifacts/compliance-report.json. Changed files require a new audit, not an automatic inventory refresh.'}
        Write-Warning 'Local candidate only: recorded licensing obligations remain unresolved. Public release is blocked.'
    }
    & $python (Join-Path $repository 'packaging\licensing\package_review.py') --output (Join-Path $artifacts 'licensing-release') --supplemental-materials (Join-Path $repository 'artifacts\licensing-candidate\research')
    if ($LASTEXITCODE -ne 0) {throw 'Source/evidence release package creation failed'}
    Write-Host "Candidate installer: $artifacts\NutCase-$version-windows-x64-setup.exe"
} finally {
    $env:PATH=$previousBuildPath
    $env:PYTHONHOME=$previousBuildPythonHome
    $env:PYTHONPATH=$previousBuildPythonPath
    Pop-Location
}
