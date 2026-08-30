@echo off
title CameraStudio - F4 Global Hotkey Service
echo Starting F4 Global Hotkey Service in background...
start "" pythonw "C:\Users\Irak\Desktop\CameraStudio\src\hotkey_service.pyw"
echo [OK] F4 Global Hotkey is active! Press F4 anytime from anywhere to toggle Small Camera.
exit
