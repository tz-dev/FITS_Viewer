@echo off
set FILE=%~1

if "%FILE%"=="" (
    echo No FITS file provided, opening file picker...
    powershell -command "[System.Reflection.Assembly]::LoadWithPartialName('System.windows.forms') | Out-Null; $f=New-Object System.Windows.Forms.OpenFileDialog; $f.Filter='FITS files (*.fits)|*.fits'; if($f.ShowDialog() -eq 'OK'){write-host $f.FileName}" > tmp_file.txt
    set /p FILE=<tmp_file.txt
    del tmp_file.txt
)

if not exist "%FILE%" (
    echo File not found: "%FILE%"
    pause
    exit /b 1
)

python "fits_viewer.py" "%FILE%"
