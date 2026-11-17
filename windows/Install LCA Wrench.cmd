@echo off
rem Installs LCA Wrench into this folder (Python 3.12, Brightway, the app). The work is done by install.ps1.
chcp 65001 >nul
cd /d "%~dp0"
title LCA Wrench: installation
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
echo.
pause
