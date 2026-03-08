; Inno Setup Script for UR Print FDM
; Generates a Windows installer (.exe)

#define MyAppName "UR Print FDM"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "UR Print FDM"
#define MyAppExeName "UR Print FDM.exe"
#define MyAppId "{{8F4A2E1C-6B3D-4A7F-9E52-1C8B3D6E9F0A}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=UR_Print_FDM_Setup_{#MyAppVersion}
SetupIconFile=app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
AllowNoIcons=yes
UsePreviousAppDir=no
UsePreviousGroup=no
UsePreviousTasks=no
; 禁用自动运行页面，避免启动失败
DisableWelcomePage=no
DisableDirPage=no
DisableFinishedPage=yes

[Code]
// 卸载后清理注册表
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    // 清理应用相关的注册表项
    RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER, 'Software\UR Print FDM');
  end;
end;

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\UR Print FDM\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Comment: "UR5 Fiber Printer Studio"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"; Comment: "UR5 Fiber Printer Studio"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent unchecked
