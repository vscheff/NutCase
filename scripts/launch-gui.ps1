param(
    [string]$InputFile,
    [string]$OutputDirectory,
    [string]$FreeCADHome,
    [string]$GuiPython=$env:FASTENER_GUI_PYTHON,
    [string]$Poppler=$env:FASTENER_POPPLER,
    [switch]$StartupCheck
)
$ErrorActionPreference='Stop'
$entrypoints=Join-Path $PSScriptRoot '..\src\entrypoints'
if (-not $GuiPython) {$GuiPython=Join-Path $PSScriptRoot '..\.venv-gui\Scripts\python.exe'}
if (-not (Test-Path -LiteralPath $GuiPython)) {throw 'Create .venv-gui and install requirements-gui.txt, or pass -GuiPython with an external Python environment.'}
& $GuiPython (Join-Path $entrypoints 'probe_runtime.py') gui
if ($LASTEXITCODE -ne 0) {throw 'The external GUI Python requires requirements-gui.txt, including Qt PDF support.'}
if (-not $Poppler) {$command=Get-Command pdftoppm.exe -ErrorAction SilentlyContinue;if ($command) {$Poppler=$command.Source}}
$inspectionDirectory=Join-Path $PSScriptRoot '..\tmp\gui-launcher'
$inspectionArguments=@{InspectEnvironment=$true;OutputDirectory=$inspectionDirectory}
if ($FreeCADHome) {$inspectionArguments.FreeCADHome=$FreeCADHome}
& (Join-Path $PSScriptRoot 'analyze-step.ps1') @inspectionArguments
if ($LASTEXITCODE -ne 0) {throw 'FreeCAD runtime discovery failed'}
$environment=Get-Content -LiteralPath (Join-Path $inspectionDirectory 'environment.json') -Raw | ConvertFrom-Json
if ([System.IO.Path]::GetFullPath($GuiPython) -eq $environment.python_executable) {throw 'The GUI must not run in FreeCAD bundled Python.'}
$arguments=@((Join-Path $entrypoints 'fastener_gui.py'),'--freecad-python',$environment.python_executable)
if ($InputFile) {$arguments+=@($InputFile)}
if ($OutputDirectory) {$arguments+=@('--output-dir',$OutputDirectory)}
if ($Poppler) {$arguments+=@('--poppler',$Poppler)}
if ($StartupCheck) {$arguments+='--startup-check'}
& $GuiPython @arguments
exit $LASTEXITCODE
