@echo off
rem Starts LCA Wrench on this PC and opens it in the browser. Closing this window stops it.
chcp 65001 >nul
cd /d "%~dp0"
rem edition.env (only in other editions, e.g. LCA Wrench Extended): own name and port, so it runs next to LCA Wrench
set "NAME=LCA Wrench"
set "DEFAULT_PORT=8787"
if exist "edition.env" for /f "usebackq tokens=1,* delims==" %%a in ("edition.env") do (
  if "%%a"=="NAME" set "NAME=%%b"
  if "%%a"=="PORT" set "DEFAULT_PORT=%%b"
)
if "%PORT%"=="" set "PORT=%DEFAULT_PORT%"
set "URL=http://127.0.0.1:%PORT%"

if exist ".venv\Scripts\python.exe" goto installed
echo Run "Install LCA Wrench" first.
pause
exit /b 1

:installed
netstat -ano -p tcp | findstr /R /C:":%PORT% .*LISTENING" >nul
if errorlevel 1 goto start
echo %NAME% is already running: %URL%
start "" "%URL%"
exit /b 0

:start
title %NAME%
echo %NAME%: %URL%
echo Keep this window open. Closing it stops %NAME%.
echo The first time a large project, e.g. ecoinvent, is opened, preparing it takes a minute or two.
echo If something goes wrong, send the file lca-wrench.log from this folder.
set "PYTHONWARNINGS=ignore::UserWarning:bw2calc,ignore::UserWarning:bw2calc.lca"
set "PYTHONUTF8=1"
set "LCA_WRENCH_LOG=%CD%\lca-wrench.log"
rem opens the browser once the server answers (a fixed wait was too short on slow PCs: "cannot reach this page")
start "" /b powershell -NoProfile -WindowStyle Hidden -Command "for ($i = 0; $i -lt 240; $i++) { try { $c = New-Object Net.Sockets.TcpClient('127.0.0.1', %PORT%); $c.Close(); break } catch { Start-Sleep -Milliseconds 500 } }; Start-Process '%URL%'"
".venv\Scripts\python.exe" -m uvicorn lca_wrench.api:app --host 127.0.0.1 --port %PORT% --log-level warning
echo.
echo %NAME% has stopped.
pause
