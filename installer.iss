; Script do Inno Setup: transforma a pasta do programa em um instalador
#define AppName "Painel SOC"
#define AppVersion "1.0.0"

[Setup]
AppId={{6B1D2F0A-5C3E-4E7B-9A41-0D5C1E8F7A22}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\PainelSOC
DefaultGroupName={#AppName}
PrivilegesRequired=admin
OutputBaseFilename=PainelSOC-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; Flags: unchecked

[Files]
Source: "dist\PainelSOC\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\PainelSOC.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\PainelSOC.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\PainelSOC.exe"; Description: "Abrir o Painel SOC agora"; Flags: nowait postinstall skipifsilent
