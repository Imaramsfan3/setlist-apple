@echo off
REM Windows Setup Script for Setlist to Apple Music Playlist

echo ========================================
echo Setlist to Apple Music - Windows Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ERROR: Python is not installed or not in PATH
        echo.
        echo Please install Python from: https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH" during installation!
        echo.
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=py
    )
) else (
    set PYTHON_CMD=python
)

echo Python found: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

echo Installing dependencies...
echo.

%PYTHON_CMD% -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install dependencies
    echo Try running PowerShell as Administrator and run this script again
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo Next steps:
echo 1. Get your API key from: https://www.setlist.fm/settings/api
echo 2. Set it as environment variable:
echo    PowerShell: $env:SETLISTFM_API_KEY='your-key'
echo    CMD: set SETLISTFM_API_KEY=your-key
echo.
echo 3. Run the script:
echo    %PYTHON_CMD% setlist_to_playlist.py "your-setlist-url"
echo.
echo For detailed instructions, see WINDOWS_SETUP.md
echo.
pause
