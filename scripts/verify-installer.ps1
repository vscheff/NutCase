param([switch]$NativeRegression, [switch]$OpenExternal, [switch]$OpenExisting, [switch]$BindLicensingReview, [switch]$VerifyLibraryReplacement,
      [string]$Installer, [string]$Installation, [string]$Evidence, [string]$DataHome)
$ErrorActionPreference='Stop'
$repository=Split-Path $PSScriptRoot -Parent
$version=(Get-Content -LiteralPath (Join-Path $repository 'VERSION') -Raw).Trim()
if (-not $Evidence) {$Evidence=Join-Path $repository 'artifacts\verification'}
if (-not $Installation) {$Installation=Join-Path $repository 'artifacts\Install Ω & Space'}
$uninstallKey='HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{ADE97F43-CC47-4AC6-BDE9-534071E6F20E}_is1'
if (Test-Path -LiteralPath $uninstallKey) {
    throw 'An existing NutCase registration was found. Do not overwrite a real installation with this disposable test.'
}
New-Item -ItemType Directory -Path $evidence -Force | Out-Null
if (-not $Installer) {$Installer=Join-Path $repository ('artifacts\NutCase-'+$version+'-windows-x64-setup.exe')}
$previousDataHome=$env:NUTCASE_DATA_HOME
$previousPath=$env:PATH
if (-not $DataHome) {$DataHome=Join-Path $repository 'artifacts\vdata'}
$env:NUTCASE_DATA_HOME=$DataHome
$env:PATH=Join-Path $env:SystemRoot 'System32'
$checks=[ordered]@{version=$version;installation=$installation;installer_sha256=(Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant();clean_vm=$false}
$savedAcl=$null
function Run-Setup([string]$program,[string[]]$arguments) {
    $process=Start-Process -FilePath $program -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0) {throw ('Installer operation failed with exit '+$process.ExitCode)}
}
function Run-Startup([string]$report) {
    $process=Start-Process -FilePath (Join-Path $installation 'NutCase.exe') -ArgumentList @('--startup-check','--check-report',('"'+$report+'"')) -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit(60000)) {$process.Kill();throw 'Installed startup timeout'}
    if ($process.ExitCode -ne 0) {throw 'Installed GUI startup failed'}
    $result=Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    if ($result.status -ne 'GUI_STARTUP_OK' -or -not $result.frozen) {throw 'Installed GUI diagnostic failed'}
    return $result
}
try {
    Run-Setup $installer @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/DIR="'+$installation+'"'),('/LOG="'+(Join-Path $evidence 'install.log')+'"'),'/TASKS=desktopicon')
    $checks.installed=$true
    $registration=Get-ItemProperty -LiteralPath $uninstallKey
    if ($registration.DisplayName -ne 'NutCase') {throw 'Wrong installed application name'}
    if ($registration.DisplayVersion -ne $version) {throw 'Wrong installed version'}
    $checks.registration=@{name=$registration.DisplayName;version=$registration.DisplayVersion}
    $inventory=Get-Content -LiteralPath (Join-Path $installation 'bundle-manifest.json') -Raw | ConvertFrom-Json
    $installedFiles=@($inventory.files.PSObject.Properties)
    foreach ($entry in $installedFiles) {
        if ((Get-FileHash -LiteralPath (Join-Path $installation $entry.Name) -Algorithm SHA256).Hash -ne $entry.Value) {throw ('Installed file hash mismatch: '+$entry.Name)}
    }
    $checks.installed_manifest_files_verified=$installedFiles.Count
    if ($BindLicensingReview) {
        & (Join-Path $repository '.venv-build\Scripts\python.exe') (Join-Path $repository 'packaging\licensing\bind_installer.py') --installed $installation --installer $installer
        if ($LASTEXITCODE -ne 0) {throw 'Actual installation does not match the independently recorded licensing review'}
        $checks.independent_licensing_inventory_matched=$true
    }
    $shell=New-Object -ComObject Shell.Application
    $startMenu=Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs\NutCase\NutCase.lnk'
    $desktop=Join-Path ([Environment]::GetFolderPath('Desktop')) 'NutCase.lnk'
    foreach ($link in @($startMenu,$desktop)) {
        if (-not (Test-Path -LiteralPath $link)) {throw ('Shortcut missing: '+$link)}
        # WScript.Shell exposes the lossy ANSI target for some Unicode paths.
        # Read the actual Unicode shell property used by Explorer instead.
        $item=$shell.NameSpace((Split-Path $link -Parent)).ParseName((Split-Path $link -Leaf))
        if ($item.ExtendedProperty('System.Link.TargetParsingPath') -ne (Join-Path $installation 'NutCase.exe')) {throw 'Shortcut target mismatch'}
    }
    $checks.shortcuts_verified=$true
    $licenseIndex=Join-Path $installation 'licenses\index.html'
    if (Test-Path -LiteralPath (Join-Path $installation 'THIRD_PARTY_NOTICES.md')) {
        $licenseShortcut=Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs\NutCase\Licenses.lnk'
        if (-not (Test-Path -LiteralPath $licenseIndex) -or -not (Test-Path -LiteralPath $licenseShortcut)) {throw 'Installed licensing index/shortcut missing'}
        $licenseItem=$shell.NameSpace((Split-Path $licenseShortcut -Parent)).ParseName((Split-Path $licenseShortcut -Leaf))
        if ($licenseItem.ExtendedProperty('System.Link.TargetParsingPath') -ne $licenseIndex) {throw 'Licenses shortcut target mismatch'}
        $checks.license_index_and_shortcut_verified=$true
    }
    $checks.first_launch=Run-Startup (Join-Path $evidence 'installed-startup.json')
    if ($VerifyLibraryReplacement) {
        $probe=Join-Path $repository 'packaging\licensing\replace_library_probe.py'
        $probePython=Join-Path $repository '.venv-build\Scripts\python.exe'
        try {
            & $probePython $probe --installed $installation --evidence $evidence
            if ($LASTEXITCODE -ne 0) {throw 'Controlled library modification failed'}
            $checks.modified_library_launch=Run-Startup (Join-Path $evidence 'modified-library-startup.json')
        } finally {
            & $probePython $probe --installed $installation --evidence $evidence --restore
            if ($LASTEXITCODE -ne 0) {throw 'Original library restoration failed'}
        }
        $checks.library_replacement_scope='Four Qt/PySide/shiboken native files, PE checksum header change only; independently rebuilt modified library remains untested'
    }
    $isolatedDataHome=$env:NUTCASE_DATA_HOME
    try {
        Remove-Item Env:\NUTCASE_DATA_HOME -ErrorAction SilentlyContinue
        $checks.default_data_launch=Run-Startup (Join-Path $evidence 'default-data-startup.json')
        if ($checks.default_data_launch.data_root -ne (Join-Path $env:LOCALAPPDATA 'NutCase')) {throw 'Installed user-data default is wrong'}
        if ($checks.default_data_launch.runtime.output -ne (Join-Path $env:LOCALAPPDATA 'NutCase\drawings')) {throw 'Installed drawing default is wrong'}
    } finally {$env:NUTCASE_DATA_HOME=$isolatedDataHome}
    # Deny inherited file/directory writes, retaining read/execute and ACL repair.
    # This target is explicit, resolved and confined to this workspace's artifacts.
    $resolvedInstallation=(Resolve-Path -LiteralPath $installation).Path
    $resolvedArtifacts=(Resolve-Path -LiteralPath (Join-Path $repository 'artifacts')).Path
    if (-not $resolvedInstallation.StartsWith($resolvedArtifacts+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {throw 'Unsafe installation test target'}
    $savedAcl=Get-Acl -LiteralPath $installation
    $restrictedAcl=Get-Acl -LiteralPath $installation
    $identity=[Security.Principal.WindowsIdentity]::GetCurrent().User
    $deny=[Security.AccessControl.FileSystemAccessRule]::new($identity,[Security.AccessControl.FileSystemRights]::Write,
        ([Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit),
        [Security.AccessControl.PropagationFlags]::None,[Security.AccessControl.AccessControlType]::Deny)
    $restrictedAcl.AddAccessRule($deny);Set-Acl -LiteralPath $installation -AclObject $restrictedAcl
    $writeBlocked=$false
    try {[IO.File]::WriteAllText((Join-Path $installation 'write-probe.txt'),'test')}
    catch [UnauthorizedAccessException] {$writeBlocked=$true}
    if (-not $writeBlocked) {throw 'Read-only installation test did not actually block writing'}
    $checks.read_only_launch=Run-Startup (Join-Path $evidence 'read-only-startup.json')
    if ($NativeRegression) {
        & (Join-Path $PSScriptRoot 'verify-windows.ps1') -Worker (Join-Path $installation 'NutCaseWorker.exe') -OpenExternal:$OpenExternal -Evidence $evidence -DataHome $DataHome
        $checks.read_only_native_regression=$true
    }
    if ($OpenExisting) {
        & (Join-Path $PSScriptRoot 'verify-windows.ps1') -Worker (Join-Path $installation 'NutCaseWorker.exe') -OpenExisting -Evidence $evidence -DataHome $DataHome
        $checks.read_only_external_dispatch=$true
    }
    Set-Acl -LiteralPath $installation -AclObject $savedAcl;$savedAcl=$null
    # Hash settings, generated files and policy history before upgrade/uninstall.
    $userFiles=@{}
    Get-ChildItem -LiteralPath $env:NUTCASE_DATA_HOME -Recurse -File | Where-Object FullName -NotMatch '\\cache\\|\\logs\\' | ForEach-Object {
        $userFiles[$_.FullName]=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
    }
    if ($userFiles.Count -eq 0) {
        $sentinel=Join-Path $env:NUTCASE_DATA_HOME 'gui-state\preserved-test.json'
        New-Item -ItemType Directory -Path (Split-Path $sentinel -Parent) -Force | Out-Null
        [IO.File]::WriteAllText($sentinel,'{"preserve":true}')
        $userFiles[$sentinel]=(Get-FileHash -LiteralPath $sentinel).Hash
    }
    Run-Setup $installer @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/DIR="'+$installation+'"'),('/LOG="'+(Join-Path $evidence 'upgrade.log')+'"'))
    foreach ($file in $userFiles.Keys) {if ((Get-FileHash -LiteralPath $file).Hash -ne $userFiles[$file]) {throw 'Upgrade changed user data'}}
    $checks.same_version_upgrade_preserved_files=$userFiles.Count
    Run-Setup (Join-Path $installation 'unins000.exe') @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/LOG="'+(Join-Path $evidence 'uninstall.log')+'"'))
    foreach ($file in $userFiles.Keys) {if ((Get-FileHash -LiteralPath $file).Hash -ne $userFiles[$file]) {throw 'Uninstall changed user data'}}
    if ((Test-Path -LiteralPath $uninstallKey) -or (Test-Path -LiteralPath (Join-Path $installation 'NutCase.exe'))) {throw 'Uninstall left the app registered or executable installed'}
    if ((Test-Path -LiteralPath $startMenu) -or (Test-Path -LiteralPath $desktop)) {throw 'Uninstall did not remove shortcuts'}
    $checks.uninstall_preserved_files=$userFiles.Count
    Run-Setup $installer @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/DIR="'+$installation+'"'),('/LOG="'+(Join-Path $evidence 'reinstall.log')+'"'))
    foreach ($file in $userFiles.Keys) {if ((Get-FileHash -LiteralPath $file).Hash -ne $userFiles[$file]) {throw 'Reinstall changed user data'}}
    $checks.reinstalled_launch=Run-Startup (Join-Path $evidence 'reinstalled-startup.json')
    $checks.reinstall_preserved_files=$userFiles.Count
    Run-Setup (Join-Path $installation 'unins000.exe') @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/LOG="'+(Join-Path $evidence 'final-uninstall.log')+'"'))
    foreach ($file in $userFiles.Keys) {if ((Get-FileHash -LiteralPath $file).Hash -ne $userFiles[$file]) {throw 'Final uninstall changed user data'}}
    if ((Test-Path -LiteralPath $uninstallKey) -or (Test-Path -LiteralPath (Join-Path $installation 'NutCase.exe')) -or (Test-Path -LiteralPath $startMenu) -or (Test-Path -LiteralPath $desktop)) {throw 'Final uninstall left an application registration, executable or shortcut'}
    $checks.final_uninstall_preserved_files=$userFiles.Count
    $checks.status='passed'
} catch {
    $checks.status='failed';$checks.error=$_.ToString();throw
} finally {
    if ($savedAcl) {Set-Acl -LiteralPath $installation -AclObject $savedAcl}
    $env:NUTCASE_DATA_HOME=$previousDataHome;$env:PATH=$previousPath
    $checks | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $evidence 'installer-lifecycle.json') -Encoding UTF8
}
