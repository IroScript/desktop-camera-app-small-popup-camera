@echo off
title HD Web Camera Live Studio
start "" /b python "C:\Users\Irak\Desktop\CameraStudio\src\web_camera.py"
timeout /t 1 /nobreak >nul
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app="http://127.0.0.1:5500"
) else (
    start "" "http://127.0.0.1:5500"
)
exit
