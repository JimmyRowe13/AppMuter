@echo off
cd /d "%~dp0"
echo Building AppMuter.exe...
pyinstaller --onefile --windowed --name AppMuter ^
    --icon app_muter\app_muter.ico ^
    --add-data "app_muter\config.json;." ^
    --hidden-import common ^
    --hidden-import common.config_manager ^
    --hidden-import common.tray_icon ^
    --hidden-import common.notifications ^
    --hidden-import app_muter ^
    --hidden-import app_muter.session_finder ^
    --hidden-import app_muter.muter_core ^
    --hidden-import app_muter.settings_window ^
    app_muter\app_muter.py
echo.
echo Build complete! Output: dist\AppMuter.exe
pause
