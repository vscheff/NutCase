param(
    [Parameter(Mandatory=$true)][string]$InputFile,
    [string]$OutputDirectory=(Join-Path $PSScriptRoot '..\output'),
    [string]$Config,
    [ValidateSet('basic','comprehensive','custom')][string]$Mode,
    [string]$FreeCADHome,
    [string]$PdfPython=$env:FASTENER_PDF_PYTHON,
    [string]$Poppler=$env:FASTENER_POPPLER,
    [switch]$CatalogOnly,
    [switch]$FreshConfig
)
$ErrorActionPreference='Stop'
$entrypoints=Join-Path $PSScriptRoot '..\src\entrypoints'
if (-not $PdfPython) {
    $venv=Join-Path $PSScriptRoot '..\.venv-pdf\Scripts\python.exe'
    if (Test-Path -LiteralPath $venv) { $PdfPython=$venv }
    else { $command=Get-Command python.exe -ErrorAction SilentlyContinue; if ($command) {$PdfPython=$command.Source} }
}
if (-not $PdfPython) { throw 'Supply -PdfPython or FASTENER_PDF_PYTHON pointing to external Python with requirements-pipeline.txt installed' }
& $PdfPython (Join-Path $entrypoints 'probe_runtime.py') pdf
if ($LASTEXITCODE -ne 0) { throw 'External PDF Python lacks pipeline dependencies; install requirements-pipeline.txt' }
if (-not $Poppler) { $command=Get-Command pdftoppm.exe -ErrorAction SilentlyContinue; if ($command) {$Poppler=$command.Source} }
if (-not $Poppler) { throw 'Supply -Poppler or FASTENER_POPPLER with the pdftoppm executable' }
$inspectionDirectory=Join-Path $PSScriptRoot '..\tmp\pipeline-launcher'
$inspectionArguments=@{InspectEnvironment=$true;OutputDirectory=$inspectionDirectory}
if ($FreeCADHome) {$inspectionArguments.FreeCADHome=$FreeCADHome}
& (Join-Path $PSScriptRoot 'analyze-step.ps1') @inspectionArguments
if ($LASTEXITCODE -ne 0) {throw 'FreeCAD runtime discovery failed'}
$environment=Get-Content -LiteralPath (Join-Path $inspectionDirectory 'environment.json') -Raw | ConvertFrom-Json
$arguments=@((Join-Path $entrypoints 'generate_fastener.py'),$InputFile,'--output-dir',$OutputDirectory,
    '--freecad-python',$environment.python_executable,'--poppler',$Poppler)
if ($Config) {$arguments+=@('--config',$Config)}
if ($Mode) {$arguments+=@('--mode',$Mode)}
if ($CatalogOnly) {$arguments+='--catalog-only'}
if ($FreshConfig) {$arguments+='--fresh-config'}
& $PdfPython @arguments
exit $LASTEXITCODE
