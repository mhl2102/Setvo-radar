#define RadarName "Radar Startup Intelligence"
#define RadarExe "RadarStartupIntelligence.exe"
#define RadarVersion "2.1.0"
[Setup]
AppId={{9E9210B9-FB9A-4D3B-B637-5DDFE3FA0A3E}
AppName={#RadarName}
AppVersion={#RadarVersion}
AppPublisher=Radar Startup Intelligence
DefaultDirName={autopf}\Radar Startup Intelligence
DefaultGroupName={#RadarName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\release
OutputBaseFilename=RadarStartupIntelligence-Setup-{#RadarVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
WizardStyle=modern
UninstallDisplayIcon={app}\{#RadarExe}
[Files]
Source: "..\dist\RadarStartupIntelligence\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\{#RadarName}"; Filename: "{app}\{#RadarExe}"
Name: "{autodesktop}\{#RadarName}"; Filename: "{app}\{#RadarExe}"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked
[Run]
Filename: "{app}\{#RadarExe}"; Description: "Abrir Radar Startup Intelligence"; Flags: nowait postinstall skipifsilent
