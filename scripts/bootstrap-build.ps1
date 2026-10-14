param()
$ErrorActionPreference = 'Stop'
$repository = Split-Path $PSScriptRoot -Parent
$toolsDirectory = Join-Path $repository '.build-tools'
$toolchain = Get-Content -LiteralPath (Join-Path $repository 'packaging\toolchain.json') -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Path $toolsDirectory -Force | Out-Null
foreach ($name in 'python','inno','poppler') {
    $tool = $toolchain.$name
    $archive = Join-Path $toolsDirectory $tool.archive
    if (-not (Test-Path -LiteralPath $archive)) {
        Invoke-WebRequest -Uri $tool.url -OutFile $archive -UseBasicParsing
    }
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $tool.sha256) {
        throw "Checksum mismatch for $name. Remove the cached download and investigate; it will not be executed."
    }
}
$pythonDirectory = Join-Path $toolsDirectory 'cpython'
$python = Join-Path $pythonDirectory 'tools\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    # Windows PowerShell's Expand-Archive rejects the NuGet .nupkg extension.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::ExtractToDirectory((Join-Path $toolsDirectory $toolchain.python.archive),$pythonDirectory)
}
$popplerDirectory = Join-Path $toolsDirectory 'poppler'
if (-not (Test-Path -LiteralPath (Join-Path $popplerDirectory 'poppler-26.09.0\Library\bin\pdftoppm.exe'))) {
    Expand-Archive -LiteralPath (Join-Path $toolsDirectory $toolchain.poppler.archive) -DestinationPath $popplerDirectory
}
$buildEnvironment = Join-Path $repository '.venv-build'
if (-not (Test-Path -LiteralPath (Join-Path $buildEnvironment 'Scripts\python.exe'))) {
    # PSF's NuGet build runtime contains pip, but deliberately omits ensurepip.
    & $python -m venv --without-pip $buildEnvironment
    if ($LASTEXITCODE -ne 0) {throw 'Could not create the isolated build environment'}
}
& $python -m pip --python (Join-Path $buildEnvironment 'Scripts\python.exe') install --require-hashes -r (Join-Path $repository 'packaging\windows.lock')
if ($LASTEXITCODE -ne 0) {throw 'Pinned build dependencies could not be installed'}
$compilerDirectory = Join-Path $toolsDirectory 'inno'
if (-not (Test-Path -LiteralPath (Join-Path $compilerDirectory 'ISCC.exe'))) {
    $installerArguments = @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/CURRENTUSER','/NOICONS',
                           ('/DIR="'+$compilerDirectory+'"'),('/LOG="'+(Join-Path $toolsDirectory 'inno-install.log')+'"'))
    $setup = Start-Process -FilePath (Join-Path $toolsDirectory $toolchain.inno.archive) -ArgumentList $installerArguments -WindowStyle Hidden -Wait -PassThru
    if ($setup.ExitCode -ne 0) {throw ('Inno Setup compiler installation failed: '+$setup.ExitCode)}
}
Write-Host 'NutCase build toolchain is ready. No Codex runtime is used.'
