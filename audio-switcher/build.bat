@echo off
cd /d "%~dp0"
echo Building AudioSwitcher.exe...
pyinstaller --onefile --windowed --name AudioSwitcher --add-data "config.json;." audio_switcher.py
echo.
echo Build complete! Output: dist\AudioSwitcher.exe
pause
