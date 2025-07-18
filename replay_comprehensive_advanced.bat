@echo off
echo ================================
echo Advanced Comprehensive PCAP Replay
echo ================================
echo.

echo This will replay the comprehensive PCAP file containing:
echo - CAT-48: Primary surveillance radar plots
echo - CAT-34: Secondary surveillance radar
echo - CAT-8: Meteorological data  
echo - CAT-21: ADS-B target reports (with altitude data)
echo.

echo Target file: cat48--cat34-cat8-cat21-plot--psr-iff-track--adsb-weather--capture.pcap
echo Make sure the Flask app is running and UDP receiver is started!
echo.

echo Select replay speed:
echo 1. 0.5x (Slow - good for debugging)
echo 2. 1.0x (Normal speed)
echo 3. 2.0x (Fast)
echo 4. 5.0x (Very fast)
echo 5. Custom speed
echo.

set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" (
    set speed=0.5
    echo Selected: 0.5x speed
) else if "%choice%"=="2" (
    set speed=1.0
    echo Selected: 1.0x speed
) else if "%choice%"=="3" (
    set speed=2.0
    echo Selected: 2.0x speed
) else if "%choice%"=="4" (
    set speed=5.0
    echo Selected: 5.0x speed
) else if "%choice%"=="5" (
    set /p speed="Enter custom speed (e.g., 1.5): "
    echo Selected: %speed%x speed
) else (
    set speed=1.0
    echo Invalid choice, using default 1.0x speed
)

echo.
echo Starting replay at %speed%x speed...
echo Press Ctrl+C to stop
echo.

python pcap_parser.py replay cat48--cat34-cat8-cat21-plot--psr-iff-track--adsb-weather--capture.pcap 127.0.0.1 8080 %speed%

echo.
echo Replay session ended.
echo Check the surveillance dashboard for results.
echo.

pause
