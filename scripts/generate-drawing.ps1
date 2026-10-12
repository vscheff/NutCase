param(
    [Parameter(Mandatory = $true)][string]$InputFile,
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '..\output'),
    [ValidateSet('ANSI-B', 'ANSI-C', 'ANSI-D', 'ANSI-A', 'A3', 'A4')][string]$SheetSize = 'ANSI-B',
    [string]$FreeCADHome,
    [switch]$NoIsometric,
    [switch]$NoOppositeEnd,
    [switch]$Dimensions,
    [ValidateSet('basic','comprehensive')][string]$DimensionScope = 'comprehensive'
)
$ErrorActionPreference = 'Stop'
$entrypoints = Join-Path $PSScriptRoot '..\src\entrypoints'
# Share the existing, tested discovery path without copying fixed installation paths.
# Environment inspection writes to a dedicated launcher diagnostic directory.
$inspectionDirectory = Join-Path $PSScriptRoot '..\tmp\drawing-launcher'
$inspectionArguments = @{ InspectEnvironment = $true; OutputDirectory = $inspectionDirectory }
if ($FreeCADHome) { $inspectionArguments.FreeCADHome = $FreeCADHome }
& (Join-Path $PSScriptRoot 'analyze-step.ps1') @inspectionArguments
if ($LASTEXITCODE -ne 0) { throw 'FreeCAD runtime discovery/inspection failed' }
$environment = Get-Content -LiteralPath (Join-Path $inspectionDirectory 'environment.json') -Raw | ConvertFrom-Json
$drawingArguments = @((Join-Path $entrypoints 'generate_drawing.py'), $InputFile, '--output-dir', $OutputDirectory, '--sheet-size', $SheetSize)
if ($NoIsometric) { $drawingArguments += '--no-isometric' }
if ($NoOppositeEnd) { $drawingArguments += '--no-opposite-end' }
if ($Dimensions) { $drawingArguments += '--dimensions' }
$drawingArguments += @('--dimension-scope',$DimensionScope)
& $environment.python_executable @drawingArguments
exit $LASTEXITCODE
