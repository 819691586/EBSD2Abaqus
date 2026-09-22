@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "OUTPUT_DIR=%~dp0output"

if not exist "%OUTPUT_DIR%" (
    mkdir "%OUTPUT_DIR%"
)

echo This will delete all generated files in:
echo   %OUTPUT_DIR%
echo.
choice /C YN /N /M "Continue? [Y/N]: "
if errorlevel 2 exit /b 0

for /f "delims=" %%F in ('dir /b /a-d "%OUTPUT_DIR%" 2^>nul') do (
    if /I not "%%F"==".gitkeep" del /f /q "%OUTPUT_DIR%\%%F"
)
for /f "delims=" %%D in ('dir /b /ad "%OUTPUT_DIR%" 2^>nul') do (
    rmdir /s /q "%OUTPUT_DIR%\%%D"
)

echo Output folder cleaned. Input data and project scripts were not changed.
pause
exit /b 0
