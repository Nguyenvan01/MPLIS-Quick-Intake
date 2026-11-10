; Inno Setup 6 — gói dist\NhapPhieuMPLIS thành Setup.exe
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6B1F2D0A-3C4E-4E7B-9A51-2F8C7D3E9B10}
AppName=Thêm mới nhanh MPLIS
AppVersion={#AppVersion}
AppPublisher=Nguyễn Hữu Văn
DefaultDirName={autopf}\NhapPhieuMPLIS
DefaultGroupName=Thêm mới nhanh MPLIS
OutputDir=Output
OutputBaseFilename=NhapPhieuMPLIS-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Cài cho riêng người dùng, không cần quyền admin (máy cơ quan thường bị khóa admin)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\NhapPhieuMPLIS.exe
SetupIconFile=..\assets\icon\NhapPhieuMPLIS.ico

[Tasks]
Name: "desktopicon"; Description: "Tạo shortcut ngoài Desktop"; GroupDescription: "Shortcut:"

[Files]
Source: "..\dist\NhapPhieuMPLIS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Thêm mới nhanh MPLIS"; Filename: "{app}\NhapPhieuMPLIS.exe"
Name: "{group}\Gỡ cài đặt"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Thêm mới nhanh MPLIS"; Filename: "{app}\NhapPhieuMPLIS.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\NhapPhieuMPLIS.exe"; Description: "Mở chương trình"; Flags: nowait postinstall skipifsilent

; Cấu hình, log, trạng thái nằm ở %APPDATA%\NhapPhieuMPLIS và được GIỮ LẠI khi gỡ cài đặt
; để cài bản mới không mất trạng thái các dòng đã chạy.
