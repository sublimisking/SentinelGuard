
#define MyAppName "SentinelGuard"
; Surum release workflow'unda /DMyAppVersion=... ile verilir.
; Elle derlerken src/sentinelguard/version.py ile ayni tutun.
#ifndef MyAppVersion
  #define MyAppVersion "0.1.0-beta"
#endif
#define MyAppExeName "SentinelGuard.exe"

[Setup]
AppId={{3183D1E2-9B8E-456F-A935-606D0FD0EEC1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName=SentinelGuard v{#MyAppVersion}
AppPublisher=SentinelGuard

DefaultDirName={localappdata}\Programs\SentinelGuard
DefaultGroupName=SentinelGuard

PrivilegesRequired=lowest
WizardStyle=modern

OutputDir=..\release
OutputBaseFilename=SentinelGuard-v{#MyAppVersion}-Setup

Compression=lzma2
SolidCompression=yes

UninstallDisplayIcon={app}\{#MyAppExeName}

; Guncelleme ayni AppId ile eski surumun uzerine kurulur.
; Calisan SentinelGuard'i Restart Manager ile kapat.
CloseApplications=force
RestartApplications=no
UsePreviousAppDir=yes

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
; Uygulama ici guncelleme sessiz kurulum yapar; bitince uygulamayi yeniden ac.
Filename: "{app}\{#MyAppExeName}"; Flags: nowait; Check: WizardSilent

[InstallDelete]
; onedir paketinden kalan eski dosyalar yeni surumle karismasin.
Type: filesandordirs; Name: "{app}\_internal"
