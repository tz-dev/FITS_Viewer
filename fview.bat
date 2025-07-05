@echo off
if "%~1"=="" (
    echo Usage: fview ^<fits_file_path^>
    exit /b 1
)

python "fits_browser.py" "%~1"
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to run fits_browser.py
    exit /b %ERRORLEVEL%
)