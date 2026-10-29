#define SetvoName "Setvo"
#define SetvoExe "Setvo.exe"
#define SetvoVersion "2.2.0"
[Setup]
AppId={{9E9210B9-FB9A-4D3B-B637-5DDFE3FA0A3E}
AppName={#SetvoName}
AppVersion={#SetvoVersion}
AppPublisher=Setvo
DefaultDirName={autopf}\Setvo
DefaultGroupName={#SetvoName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\release
OutputBaseFilename=Setvo-Setup-{#SetvoVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
WizardStyle=modern
UninstallDisplayIcon={app}\{#SetvoExe}
[Files]
Source: "..\dist\Setvo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\{#SetvoName}"; Filename: "{app}\{#SetvoExe}"
Name: "{autodesktop}\{#SetvoName}"; Filename: "{app}\{#SetvoExe}"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked
[Run]
Filename: "{app}\{#SetvoExe}"; Description: "Abrir Setvo"; Flags: nowait postinstall skipifsilent
