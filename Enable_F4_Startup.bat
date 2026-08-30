@echo off
title CameraStudio - Enable F4 on Windows Startup
set "STARTUP_VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\CameraStudio_F4.vbs"

echo Set WshShell = CreateObject("WScript.Shell") > "%STARTUP_VBS%"
echo WshShell.Run "pythonw.exe ""C:\Users\Irak\Desktop\CameraStudio\src\hotkey_service.pyw""", 0, False >> "%STARTUP_VBS%"

echo [SUCCESS] F4 Global Hotkey is now configured to start automatically on Windows boot!
echo Starting F4 service right now...
start "" pythonw "C:\Users\Irak\Desktop\CameraStudio\src\hotkey_service.pyw"
exit
