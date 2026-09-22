@echo off
setlocal
cd /d "%~dp0"

set "SOURCE=%CD%\abaqus_plugin\EBSD2Abaqus"
set "TARGET=%USERPROFILE%\abaqus_plugins\EBSD2Abaqus"

if not exist "%SOURCE%\EBSD2Abaqus_plugin.py" (
    echo [Error] Plugin package is incomplete.
    pause
    exit /b 1
)

if not exist "%USERPROFILE%\abaqus_plugins" mkdir "%USERPROFILE%\abaqus_plugins"
if exist "%TARGET%" rmdir /s /q "%TARGET%"
xcopy "%SOURCE%" "%TARGET%\" /E /I /Y >nul
if errorlevel 1 (
    echo [Error] Plugin installation failed.
    pause
    exit /b 1
)

echo Installed to:
echo   %TARGET%
echo.
echo Restart Abaqus/CAE, then open Plug-ins ^> EBSD2Abaqus.
pause
exit /b 0
