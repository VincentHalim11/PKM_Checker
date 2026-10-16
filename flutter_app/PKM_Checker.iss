#define MyAppName "PKM Checker"
#define MyAppVersion "1.0.0"
#define MyAppExeName "PKM_Checker.exe"

[Setup]
AppId={{CE4725EA-957C-4A19-A7F9-D6A82C7FE5A1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\PKM Checker
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
OutputDir=installer_output
OutputBaseFilename=PKM_Checker_Setup_v1.0.0
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "Buat shortcut di Desktop"; GroupDescription: "Shortcut tambahan:"; Flags: unchecked

[Files]
Source: "build\windows\x64\runner\Release\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\PKM Checker"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\PKM Checker"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Jalankan PKM Checker"; Flags: postinstall nowait skipifsilent