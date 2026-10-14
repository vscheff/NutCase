#ifndef AppVersion
  #error AppVersion must be supplied by build-windows.ps1
#endif
#ifndef BundleDir
  #error BundleDir must be supplied by build-windows.ps1
#endif
#ifndef ArtifactDir
  #error ArtifactDir must be supplied by build-windows.ps1
#endif
[Setup]
AppId={{ADE97F43-CC47-4AC6-BDE9-534071E6F20E}
AppName=NutCase
AppVersion={#AppVersion}
AppVerName=NutCase {#AppVersion}
AppPublisher=NutCase Contributors
AppPublisherURL=https://github.com/vscheff/NutCase
AppSupportURL=https://github.com/vscheff/NutCase/issues
DefaultDirName={localappdata}\Programs\NutCase
DefaultGroupName=NutCase
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
DisableProgramGroupPage=yes
LicenseFile={#BundleDir}\LICENSE
InfoBeforeFile=INSTALL-NOTICE.txt
OutputDir={#ArtifactDir}
OutputBaseFilename=NutCase-{#AppVersion}-windows-x64-setup
UninstallDisplayName=NutCase
UninstallDisplayIcon={app}\NutCase.exe
VersionInfoVersion={#AppVersion}
VersionInfoProductName=NutCase
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Excludes: "NutCaseVerify.exe"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\NutCase"; Filename: "{app}\NutCase.exe"; WorkingDir: "{app}"; AppUserModelID: "NutCase.Desktop"
Name: "{group}\Licenses"; Filename: "{app}\licenses\index.html"
Name: "{group}\Uninstall NutCase"; Filename: "{uninstallexe}"
Name: "{autodesktop}\NutCase"; Filename: "{app}\NutCase.exe"; WorkingDir: "{app}"; AppUserModelID: "NutCase.Desktop"; Tasks: desktopicon

[Run]
Filename: "{app}\NutCase.exe"; Description: "Launch NutCase"; Flags: nowait postinstall skipifsilent

; Deliberately no UninstallDelete rule. Inno removes only installed files/shortcuts.
; Settings, caches, drawings and exports live outside {app} and survive uninstall.
