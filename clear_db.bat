@echo off
echo Database Clear Utility
echo ======================
echo.
echo Available options:
echo   1. Clear surveillance data (tracks and events) [DEFAULT]
echo   2. Clear only tracks
echo   3. Clear only events  
echo   4. Clear all data except users (tracks, events, network config)
echo   5. Reset database completely (preserves users)
echo   6. Show help
echo.

set /p choice="Enter your choice (1-6) or press Enter for default: "

if "%choice%"=="" set choice=1
if "%choice%"=="1" python clear_db.py --surveillance
if "%choice%"=="2" python clear_db.py --tracks
if "%choice%"=="3" python clear_db.py --events
if "%choice%"=="4" python clear_db.py --all-data
if "%choice%"=="5" python clear_db.py --reset
if "%choice%"=="6" python clear_db.py --help

if "%choice%" gtr "6" (
    echo Invalid choice. Please run the script again.
)

pause
