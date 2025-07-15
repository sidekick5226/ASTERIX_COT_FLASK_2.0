@echo off
echo ================================
echo PCAP Replay Tool
echo ================================
echo.

echo This will replay your PCAP file to the UDP receiver
echo Make sure the Flask app is running and UDP receiver is started!
echo.

pause

echo Replaying PCAP file at 1x speed...
python pcap_parser.py replay cat48-only-plot-capture.pcap 127.0.0.1 8080 1.0

pause
