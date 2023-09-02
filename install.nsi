!include "MUI2.nsh"



Name "SpotAlong"

!define Product "SpotAlong"

OutFile "SpotAlong-Installer.exe"

InstallDir $PROGRAMFILES64\CriticalElement\SpotAlong

RequestExecutionLevel admin

ShowInstDetails "show"


!define MUI_ICON ".\logo.ico"
!define MUI_UNICON ".\logo.ico"

!insertmacro MUI_PAGE_LICENSE ".\LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$PROGRAMFILES64\CriticalElement\SpotAlong\SpotAlong.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Run SpotAlong"
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"


Section Main SecMainComponent

SectionIn RO

SetOutPath $INSTDIR

InitPluginsDir

File ".\dist\app.zip"

AddSize 150000

nsisunz::UnzipToStack "$INSTDIR\app.zip" "$INSTDIR"

Pop $0
StrCmp $0 "success" ok
  DetailPrint "$0" ;print error message to log
  Goto skiplist
ok:

; Print out list of files extracted to log
next:
  Pop $0
  DetailPrint $0
StrCmp $0 "" 0 next ; pop strings until a blank one arrives

Delete "$INSTDIR\app.zip"

CreateShortcut "$SMPROGRAMS\SpotAlong.lnk" "$INSTDIR\SpotAlong.exe"
ApplicationID::Set "$SMPROGRAMS\SpotAlong.lnk" "CriticalElement.SpotAlong"

WriteRegStr   HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" "DisplayName"          "SpotAlong"
WriteRegStr   HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" "DisplayVersion"       "1.0.0"
WriteRegStr   HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" "DisplayIcon"          "$\"$INSTDIR\logo.ico$\""
WriteRegStr   HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" "UninstallString"      "$\"$INSTDIR\uninstall.exe$\""
WriteRegStr   HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" "QuietUninstallString" "$\"$INSTDIR\uninstall.exe$\" /S"
WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" "NoModify"        1
WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}" "NoRepair"        1
WriteUninstaller "$INSTDIR\uninstall.exe"

skiplist:

SectionEnd


Section "Uninstall"

Delete "$SMPROGRAMS\SpotAlong.lnk"

DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT}"

IfFileExists "$INSTDIR\SpotAlong.exe" file_found end_if

file_found:
RMDir /R /REBOOTOK $INSTDIR

end_if:
RMDir /R /REBOOTOK $LocalAppdata\CriticalElement\SpotAlong

SectionEnd