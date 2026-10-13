@echo off
setlocal
set SCRIPT_DIR=%~dp0
if "%~1"=="" (
    echo [ERROR] Harap tentukan nama level yang ingin dibuat!
    echo Contoh penggunaan:
    echo   .\add.bat level_02_room
    echo   .\add.bat level_2_chiller
    exit /b 1
)
python "%SCRIPT_DIR%tools\dev_tools.py" add %*
endlocal
