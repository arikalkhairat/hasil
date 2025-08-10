@echo off
echo 🚀 Installing QR Watermarking Tool
echo ==================================

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip setuptools wheel

REM Clear cache and install
echo Installing dependencies...
pip cache purge 2>nul
pip install -r requirements.txt

echo.
echo ✅ Installation completed!
echo.
echo To start the application:
echo venv\Scripts\activate.bat
echo python app.py

pause