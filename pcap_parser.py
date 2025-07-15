#!/usr/bin/env python3
"""
PCAP Parser for ASTERIX CAT-48 Data
Extracts UDP payloads from PCAP file and optionally sends them to UDP receiver
"""

import struct
import socket
import time
import sys
from datetime import datetime

class PCAPParser:
    """Simple PCAP file parser for extracting UDP payloads"""
    
    def __init__(self, filename):
        self.filename = filename
        self.file = None
        self.header = None
        
    def open(self):
        """Open and read PCAP header"""
        try:
            self.file = open(self.filename, 'rb')
            
            # Read global header (24 bytes)
            header_data = self.file.read(24)
            if len(header_data) < 24:
                raise ValueError("Invalid PCAP file: too short")
            
            # Parse header
            magic = struct.unpack('<I', header_data[0:4])[0]
            
            if magic == 0xa1b2c3d4:
                # Little endian
                self.endian = '<'
            elif magic == 0xd4c3b2a1:
                # Big endian
                self.endian = '>'
            else:
                raise ValueError(f"Invalid PCAP magic number: {magic:08x}")
            
            # Parse rest of header
            header_format = self.endian + 'HHIIII'
            header_values = struct.unpack(header_format, header_data[4:])
            
            self.header = {
                'version_major': header_values[0],
                'version_minor': header_values[1],
                'thiszone': header_values[2],
                'sigfigs': header_values[3],
                'snaplen': header_values[4],
                'network': header_values[5]
            }
            
            print(f"PCAP file opened: {self.filename}")
            print(f"Version: {self.header['version_major']}.{self.header['version_minor']}")
            print(f"Network type: {self.header['network']}")
            
            return True
            
        except Exception as e:
            print(f"Error opening PCAP file: {e}")
            return False
    
    def read_packet(self):
        """Read next packet from PCAP file"""
        if not self.file:
            return None
        
        # Read packet header (16 bytes)
        header_data = self.file.read(16)
        if len(header_data) < 16:
            return None  # End of file
        
        # Parse packet header
        header_format = self.endian + 'IIII'
        ts_sec, ts_usec, incl_len, orig_len = struct.unpack(header_format, header_data)
        
        # Read packet data
        packet_data = self.file.read(incl_len)
        if len(packet_data) < incl_len:
            return None  # Truncated packet
        
        return {
            'timestamp': ts_sec + ts_usec / 1000000.0,
            'length': orig_len,
            'data': packet_data
        }
    
    def extract_udp_payload(self, packet_data):
        """Extract UDP payload from Ethernet packet"""
        try:
            # Skip Ethernet header (14 bytes)
            if len(packet_data) < 14:
                return None
            
            # Check Ethernet type (should be 0x0800 for IPv4)
            eth_type = struct.unpack('>H', packet_data[12:14])[0]
            if eth_type != 0x0800:
                return None  # Not IPv4
            
            # Parse IP header
            ip_start = 14
            if len(packet_data) < ip_start + 20:
                return None
            
            ip_header = packet_data[ip_start:ip_start + 20]
            version_ihl = ip_header[0]
            ihl = (version_ihl & 0x0f) * 4  # Header length in bytes
            protocol = ip_header[9]
            
            if protocol != 17:  # Not UDP
                return None
            
            # Parse UDP header
            udp_start = ip_start + ihl
            if len(packet_data) < udp_start + 8:
                return None
            
            udp_header = packet_data[udp_start:udp_start + 8]
            src_port, dst_port, udp_length, checksum = struct.unpack('>HHHH', udp_header)
            
            # Extract UDP payload
            payload_start = udp_start + 8
            payload_length = udp_length - 8
            
            if len(packet_data) < payload_start + payload_length:
                return None
            
            payload = packet_data[payload_start:payload_start + payload_length]
            
            return {
                'src_port': src_port,
                'dst_port': dst_port,
                'payload': payload
            }
            
        except Exception as e:
            print(f"Error extracting UDP payload: {e}")
            return None
    
    def close(self):
        """Close PCAP file"""
        if self.file:
            self.file.close()
            self.file = None

def analyze_pcap(filename):
    """Analyze PCAP file and show UDP packet summary"""
    parser = PCAPParser(filename)
    
    if not parser.open():
        return
    
    packet_count = 0
    udp_count = 0
    asterix_count = 0
    
    print("\nAnalyzing packets...")
    print("-" * 60)
    
    while True:
        packet = parser.read_packet()
        if not packet:
            break
        
        packet_count += 1
        
        udp_data = parser.extract_udp_payload(packet['data'])
        if udp_data:
            udp_count += 1
            payload = udp_data['payload']
            
            # Check if this looks like ASTERIX data
            if len(payload) >= 3:
                category = payload[0]
                length = struct.unpack('>H', payload[1:3])[0]
                
                if category == 48 and length <= len(payload):
                    asterix_count += 1
                    timestamp = datetime.fromtimestamp(packet['timestamp'])
                    print(f"[{timestamp.strftime('%H:%M:%S.%f')[:-3]}] "
                          f"CAT-48 packet: {len(payload)} bytes, "
                          f"ports {udp_data['src_port']} → {udp_data['dst_port']}")
    
    parser.close()
    
    print("-" * 60)
    print(f"Total packets: {packet_count}")
    print(f"UDP packets: {udp_count}")
    print(f"ASTERIX CAT-48 packets: {asterix_count}")

def replay_pcap(filename, dest_host='127.0.0.1', dest_port=8080, speed=1.0):
    """Replay UDP packets from PCAP file"""
    parser = PCAPParser(filename)
    
    if not parser.open():
        return
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print(f"\nReplaying to {dest_host}:{dest_port} at {speed}x speed")
    print("Press Ctrl+C to stop")
    print("-" * 50)
    
    last_timestamp = None
    packet_count = 0
    sent_count = 0
    
    try:
        while True:
            packet = parser.read_packet()
            if not packet:
                break
            
            packet_count += 1
            
            # Extract UDP payload
            udp_data = parser.extract_udp_payload(packet['data'])
            if not udp_data:
                continue
            
            payload = udp_data['payload']
            
            # Check if this looks like ASTERIX CAT-48
            if len(payload) >= 3 and payload[0] == 48:
                # Calculate timing
                if last_timestamp:
                    delay = (packet['timestamp'] - last_timestamp) / speed
                    if delay > 0:
                        time.sleep(delay)
                
                # Send packet
                sock.sendto(payload, (dest_host, dest_port))
                sent_count += 1
                
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                print(f"[{timestamp}] Sent packet {sent_count}: {len(payload)} bytes")
                
                last_timestamp = packet['timestamp']
    
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error during replay: {e}")
    finally:
        sock.close()
        parser.close()
    
    print(f"\nReplay completed: {sent_count}/{packet_count} packets sent")

def main():
    if len(sys.argv) < 2:
        print("Usage: python pcap_parser.py <command> [options]")
        print("Commands:")
        print("  analyze <pcap_file> - Analyze PCAP file")
        print("  replay <pcap_file> [host] [port] [speed] - Replay packets")
        print("")
        print("Examples:")
        print("  python pcap_parser.py analyze cat48-only-plot-capture.pcap")
        print("  python pcap_parser.py replay cat48-only-plot-capture.pcap")
        print("  python pcap_parser.py replay cat48-only-plot-capture.pcap 127.0.0.1 8080 2.0")
        return
    
    command = sys.argv[1]
    
    if command == "analyze":
        if len(sys.argv) < 3:
            print("Error: PCAP filename required")
            return
        
        filename = sys.argv[2]
        analyze_pcap(filename)
        
    elif command == "replay":
        if len(sys.argv) < 3:
            print("Error: PCAP filename required")
            return
        
        filename = sys.argv[2]
        host = sys.argv[3] if len(sys.argv) > 3 else '127.0.0.1'
        port = int(sys.argv[4]) if len(sys.argv) > 4 else 8080
        speed = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
        
        replay_pcap(filename, host, port, speed)
        
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
