param([switch]$OpenExternal, [switch]$OpenExisting, [string]$Worker, [string]$Evidence, [string]$DataHome)
$ErrorActionPreference='Stop'
$repository=Split-Path $PSScriptRoot -Parent
if (-not $Evidence) {$Evidence=Join-Path $repository 'artifacts\verification'}
New-Item -ItemType Directory -Path $evidence -Force | Out-Null
$previousDataHome=$env:NUTCASE_DATA_HOME
$previousPath=$env:PATH
$previousPythonHome=$env:PYTHONHOME
$previousPythonPath=$env:PYTHONPATH
try {
    # Short retained output roots avoid the native pipeline's MAX_PATH guard.
    if (-not $DataHome) {$DataHome=Join-Path $repository 'artifacts\vdata'}
    $env:NUTCASE_DATA_HOME=$DataHome
    $env:PATH=Join-Path $env:SystemRoot 'System32'
    Remove-Item Env:\PYTHONHOME -ErrorAction SilentlyContinue
    Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
    $reportName=if ($OpenExisting) {'external-opening.json'} elseif ($Worker) {'installed-regression.json'} else {'frozen-regression.json'}
    $verificationArguments=@('--models',(Join-Path $repository 'input'),'--report',(Join-Path $evidence $reportName))
    if ($Worker) {$verificationArguments+=@('--worker',$Worker)}
    if ($OpenExternal) {$verificationArguments+='--open-external'}
    if ($OpenExisting) {$verificationArguments+='--open-existing'}
    & (Join-Path $repository 'dist\NutCase\NutCaseVerify.exe') @verificationArguments
    if ($LASTEXITCODE -ne 0) {throw ('Frozen regression failed; inspect artifacts\verification\'+$reportName)}
} finally {
    $env:NUTCASE_DATA_HOME=$previousDataHome
    $env:PATH=$previousPath
    $env:PYTHONHOME=$previousPythonHome
    $env:PYTHONPATH=$previousPythonPath
}
