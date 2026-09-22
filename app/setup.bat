@echo off

where python >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do echo %%i

echo Creating virtual environment...
python -m venv .venv

echo Installing requirements...
py -m pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt

echo.
echo Setup complete. Activate with:
echo   .venv\Scripts\activate
echo Press any key to close the window...
pause
