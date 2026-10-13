@echo off
setlocal
set SCRIPT_DIR=%~dp0
if "%~1"=="" (
    echo [ERROR] Harap tentukan nama ekstensi target yang ingin diinisialisasi!
    echo.
    echo Contoh penggunaan:
    echo   .\init_framework.bat company.my_extension
    echo   .\cadit-omniverse-helper\init_framework.bat company.my_extension
    echo.
)
python "%SCRIPT_DIR%tools\dev_tools.py" init %*
endlocal
