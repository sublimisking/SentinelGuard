
#define MyAppName "SentinelGuard"
#define MyAppVersion "0.1.0"
#define MyAppExeName "SentinelGuard.exe"

[Setup]
AppId={{3183D1E2-9B8E-456F-A935-606D0FD0EEC1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName=SentinelGuard v0.1.0-beta
AppPublisher=SentinelGuard

DefaultDirName={localappdata}\Programs\SentinelGuard
DefaultGroupName=SentinelGuard

PrivilegesRequired=lowest
WizardStyle=modern

OutputDir=..\release
OutputBaseFilename=SentinelGuard-v0.1.0-beta-Setup

Compression=lzma2
SolidCompression=yes

UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\SentinelGuard\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SentinelGuard"; Filename: "{app}\{#MyAppExeName}"
Name: "{userdesktop}\SentinelGuard"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch SentinelGuard"; Flags: nowait postinstall skipifsilent
