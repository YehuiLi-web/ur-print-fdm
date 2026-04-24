; Inno Setup Script for UR Print FDM
; Generates a Windows installer (.exe)

#define MyAppName "UR Print FDM"
#ifndef MyAppVersion
#define MyAppVersion "0.1.1"
#endif
#ifndef MyReleaseNotesFile
#define MyReleaseNotesFile "release_notes\latest.txt"
#endif
#define MyAppPublisher "UR Print FDM"
#define MyAppExeName "UR Print FDM.exe"
#define MyAppId "{{8F4A2E1C-6B3D-4A7F-9E52-1C8B3D6E9F0A}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={code:GetDefaultInstallDir}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=UR_Print_FDM_Setup_{#MyAppVersion}
InfoAfterFile={#MyReleaseNotesFile}
SetupIconFile=app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
AllowNoIcons=yes
; 再次安装时优先回到上次安装目录，而不是总是回到默认的 Program Files
UsePreviousAppDir=yes
UsePreviousGroup=no
UsePreviousTasks=no
; 禁用自动运行页面，避免启动失败
DisableWelcomePage=no
DisableDirPage=no
DisableFinishedPage=yes

[Code]
const
  AppRegistryKey = 'Software\UR Print FDM';
  LastInstallDirValueName = 'LastInstallDir';

function GetDefaultInstallDir(Param: String): String;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, AppRegistryKey, LastInstallDirValueName, Result) then
    Result := ExpandConstant('{autopf}\{#MyAppName}');
end;

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Registry]
; 保留上次安装目录，供“卸载后再安装”时作为默认路径使用
Root: HKCU; Subkey: "Software\UR Print FDM"; ValueType: string; ValueName: "LastInstallDir"; ValueData: "{app}"

[Files]
Source: "{#MyReleaseNotesFile}"; DestDir: "{app}"; DestName: "Release Notes.txt"; Flags: ignoreversion
Source: "dist\UR Print FDM\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Comment: "UR5 Fiber Printer Studio"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"; Comment: "UR5 Fiber Printer Studio"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent unchecked
