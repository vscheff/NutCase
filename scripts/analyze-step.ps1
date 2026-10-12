param(
    [string]$InputFile,
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '..\output'),
    [string]$FreeCADHome,
    [switch]$InspectEnvironment
)
$ErrorActionPreference = 'Stop'
$entrypoints = Join-Path $PSScriptRoot '..\src\entrypoints'

# Discover installations instead of assuming a particular FreeCAD release directory.
$candidateRoots = [System.Collections.Generic.List[string]]::new()
if ($FreeCADHome) { $candidateRoots.Add($FreeCADHome) }
elseif ($env:FREECAD_HOME) { $candidateRoots.Add($env:FREECAD_HOME) }
else {
    foreach ($name in 'freecad.exe', 'freecadcmd.exe') {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { $candidateRoots.Add((Split-Path (Split-Path $command.Source -Parent) -Parent)) }
    }
    $uninstallPaths = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    foreach ($entry in (Get-ItemProperty $uninstallPaths -ErrorAction SilentlyContinue | Where-Object DisplayName -Match 'FreeCAD')) {
        if ($entry.InstallLocation) { $candidateRoots.Add($entry.InstallLocation) }
        if ($entry.DisplayIcon) {
            $icon = ($entry.DisplayIcon -replace ',\d+$', '').Trim('"')
            $candidateRoots.Add((Split-Path (Split-Path $icon -Parent) -Parent))
        }
    }
    foreach ($parent in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, (Join-Path $env:LOCALAPPDATA 'Programs'))) {
        if ($parent -and (Test-Path -LiteralPath $parent)) {
            foreach ($directory in (Get-ChildItem -LiteralPath $parent -Directory | Where-Object Name -Match '^FreeCAD')) {
                $candidateRoots.Add($directory.FullName)
            }
        }
    }
}
$runtimePython = $null
foreach ($root in ($candidateRoots | Select-Object -Unique)) {
    $candidatePython = Join-Path $root 'bin\python.exe'
    if (-not (Test-Path -LiteralPath $candidatePython -PathType Leaf)) { continue }
    $probeOutput = & $candidatePython (Join-Path $entrypoints 'probe_runtime.py') freecad 2>&1
    if ($LASTEXITCODE -eq 0 -and $probeOutput -contains 'NATIVE_FREECAD_OK') {
        $runtimePython = $candidatePython
        break
    }
}
if (-not $runtimePython) {
    throw 'No working FreeCAD bundled Python found. Pass -FreeCADHome with the installation root (containing bin\python.exe).'
}
Write-Host "Using $runtimePython"
$scriptArguments = @((Join-Path $entrypoints 'analyze_step.py'))
if ($InputFile) { $scriptArguments += $InputFile }
if ($InspectEnvironment) { $scriptArguments += '--inspect-environment' }
$scriptArguments += @('--output-dir', $OutputDirectory)
& $runtimePython @scriptArguments
exit $LASTEXITCODE
