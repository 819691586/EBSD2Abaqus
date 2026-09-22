@echo off
setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo EBSD2Abaqus: CTF to reusable Abaqus CAE model
echo ============================================================
echo.

if not exist "config.json" (
    echo [Error] Missing config.json
    goto fail
)
if not exist "input\ebsd.ctf" (
    echo [Error] Missing input\ebsd.ctf
    echo Copy the Oxford CTF file into the input folder first.
    goto fail
)
where matlab >nul 2>nul
if errorlevel 1 (
    echo [Error] MATLAB was not found in PATH.
    goto fail
)
where python >nul 2>nul
if errorlevel 1 (
    echo [Error] Python was not found in PATH.
    goto fail
)
where abaqus >nul 2>nul
if errorlevel 1 (
    echo [Error] Abaqus was not found in PATH.
    goto fail
)

echo [1/3] Reconstructing grains and exporting orientations with MTEX...
matlab -batch "run('scripts/export_ebsd.m')"
if errorlevel 1 goto fail

echo.
echo [2/3] Writing the neutral Abaqus INP model...
python scripts\build_inp.py
if errorlevel 1 goto fail

echo.
echo [3/3] Importing the INP and saving the CAE database...
pushd output
abaqus cae noGUI=..\scripts\import_cae.py
set "ABAQUS_EXIT=%ERRORLEVEL%"
popd
if not "%ABAQUS_EXIT%"=="0" goto fail

echo.
echo Completed successfully.
echo Output files:
echo   %CD%\output\ebsd_base_model.inp
echo   %CD%\output\ebsd_base_model.cae
echo.
echo No load, boundary condition, analysis step, crack, or damage model was added.
pause
exit /b 0

:fail
echo.
echo Conversion failed. Review the first error above.
pause
exit /b 1
