@echo off
title CameraStudio - Disable F4 on Windows Startup
set "STARTUP_VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\CameraStudio_F4.vbs"

if exist "%STARTUP_VBS%" (
    del "%STARTUP_VBS%"
    echo [SUCCESS] Removed CameraStudio F4 from Windows Startup.
) else (
    echo [INFO] F4 was not enabled in Windows Startup.
)

python "C:\Users\Irak\Desktop\CameraStudio\src\hotkey_service.pyw" --stop
exit
