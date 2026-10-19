@echo off
setlocal
set SCRIPT_DIR=%~dp0
if "%~1"=="" (
    echo [ERROR] Harap tentukan nama level yang ingin dihapus!
    echo Contoh penggunaan:
    echo   .\delete.bat level_02_room
    echo   .\delete.bat level_2_chiller [nama_ekstensi]
    exit /b 1
)
python "%SCRIPT_DIR%tools\dev_tools.py" delete %*
endlocal
