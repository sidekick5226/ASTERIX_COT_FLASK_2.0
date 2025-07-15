#!/usr/bin/env python3
"""
Comprehensive startup script for Surveillance Sentry
Includes options for PCAP replay integration
"""

import sys
import os
import time
import subprocess
import threading
import argparse
from datetime import datetime

def start_pcap_replay(pcap_file, host='127.0.0.1', port=8080, speed=1.0, delay=5):
    """Start PCAP replay in a separate thread"""
    def replay_thread():
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting {delay} seconds before starting PCAP replay...")
        time.sleep(delay)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting PCAP replay: {pcap_file}")
        try:
            subprocess.run([
                'python', 'pcap_parser.py', 'replay', pcap_file, host, str(port), str(speed)
            ], check=True)
        except subprocess.CalledProcessError as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] PCAP replay failed: {e}")
        except KeyboardInterrupt:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] PCAP replay stopped")
    
    thread = threading.Thread(target=replay_thread, daemon=True)
    thread.start()
    return thread

def main():
    parser = argparse.ArgumentParser(description='Start Surveillance Sentry with optional PCAP replay')
    parser.add_argument('--pcap', help='PCAP file to replay')
    parser.add_argument('--pcap-host', default='127.0.0.1', help='Host for PCAP replay (default: 127.0.0.1)')
    parser.add_argument('--pcap-port', type=int, default=8080, help='Port for PCAP replay (default: 8080)')
    parser.add_argument('--pcap-speed', type=float, default=1.0, help='PCAP replay speed multiplier (default: 1.0)')
    parser.add_argument('--pcap-delay', type=int, default=5, help='Delay before starting PCAP replay (default: 5 seconds)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔍 Surveillance Sentry - ASTERIX Processing System")
    print("=" * 60)
    
    # Start PCAP replay if requested
    if args.pcap:
        if not os.path.exists(args.pcap):
            print(f"❌ PCAP file not found: {args.pcap}")
            sys.exit(1)
        
        print(f"📡 PCAP replay configured:")
        print(f"   File: {args.pcap}")
        print(f"   Target: {args.pcap_host}:{args.pcap_port}")
        print(f"   Speed: {args.pcap_speed}x")
        print(f"   Delay: {args.pcap_delay} seconds")
        print()
        
        replay_thread = start_pcap_replay(
            args.pcap, args.pcap_host, args.pcap_port, args.pcap_speed, args.pcap_delay
        )
    
    # Start the main application
    print("🚀 Starting Flask application...")
    print("   Web interface: http://localhost:5000")
    print("   UDP receiver: 0.0.0.0:8080")
    print("   Press Ctrl+C to stop")
    print()
    
    try:
        # Import and run main
        from main import initialize_services
        from app import app, socketio
        
        # Initialize services
        initialize_services()
        
        # Start Flask app
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
