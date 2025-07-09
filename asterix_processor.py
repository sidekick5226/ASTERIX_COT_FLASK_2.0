"""
ASTERIX (All Purpose Structured Eurocontrol Surveillance Information Exchange) Data Processor
Simulates processing of ASTERIX surveillance data from various sources.
"""

import json
import time
import struct
from datetime import datetime
from typing import Dict, List, Any, Optional

class AsterixProcessor:
    """
    Processes ASTERIX surveillance data and converts it to internal track format.
    This is a simplified implementation for demonstration purposes.
    """
    
    def __init__(self):
        self.category_definitions = {
            1: "Monoradar Target Reports",
            2: "Monoradar Target Reports", 
            8: "Monoradar Derived Weather Information",
            10: "Transmission of Monosensor Surface Movement Data",
            19: "Multilateration System Status Messages",
            20: "Multilateration Target Reports",
            21: "ADS-B Target Reports",
            23: "CNS/ATM Ground Station and Service Status Reports",
            34: "Transmission of Monoradar Service Messages",
            48: "Monoradar Target Reports",
            62: "System Track Data",
            65: "SDPS Service Status Messages"
        }
        
        self.data_items = {
            "I010/010": "Data Source Identifier",
            "I010/020": "Target Report Descriptor", 
            "I010/040": "Measured Position in Polar Coordinates",
            "I010/041": "Position in WGS-84 Coordinates",
            "I010/042": "Position in Cartesian Coordinates",
            "I010/090": "Flight Level in Binary Representation",
            "I010/091": "Measured Height",
            "I010/131": "Amplitude of Primary Plot",
            "I010/140": "Time of Day",
            "I010/161": "Track Number",
            "I010/170": "Track Status",
            "I010/200": "Calculated Track Velocity in Polar Coordinates",
            "I010/202": "Calculated Track Velocity in Cartesian Coordinates",
            "I010/210": "Calculated Acceleration",
            "I010/220": "Target Address",
            "I010/245": "Target Identification",
            "I010/250": "Mode S MB Data",
            "I010/270": "Target Size & Orientation",
            "I010/280": "Presence",
            "I010/300": "Vehicle Fleet Identification",
            "I010/310": "Pre-programmed Message"
        }
    
    def process_asterix_data(self, raw_data: bytes) -> List[Dict[str, Any]]:
        """
        Process raw ASTERIX data and extract track information.
        
        Args:
            raw_data: Raw ASTERIX data bytes
            
        Returns:
            List of processed track dictionaries
        """
        try:
            tracks = []
            
            # Simulate ASTERIX data parsing
            # In a real implementation, this would parse the actual ASTERIX format
            if len(raw_data) < 8:
                return tracks
            
            # Extract basic header information
            category = raw_data[0]
            length = struct.unpack('>H', raw_data[1:3])[0]
            
            if category not in self.category_definitions:
                print(f"Unknown ASTERIX category: {category}")
                return tracks
            
            # Simulate extracting multiple tracks from the data
            track_count = min(5, length // 20)  # Simulate multiple tracks
            
            for i in range(track_count):
                track = self._extract_track_from_data(raw_data, i, category)
                if track:
                    tracks.append(track)
            
            return tracks
            
        except Exception as e:
            print(f"Error processing ASTERIX data: {e}")
            return []
    
    def _extract_track_from_data(self, data: bytes, index: int, category: int) -> Optional[Dict[str, Any]]:
        """
        Extract individual track data from ASTERIX message.
        
        Args:
            data: Raw ASTERIX data
            index: Track index in the message
            category: ASTERIX category
            
        Returns:
            Extracted track dictionary or None
        """
        try:
            # Simulate track extraction based on category
            track_type = self._determine_track_type(category)
            
            # Generate simulated track data
            base_lat = 40.0 + (index * 0.1)
            base_lon = -74.0 + (index * 0.1)
            
            track = {
                'track_id': f"ASX{category:03d}{index:03d}",
                'callsign': f"TRK{index:03d}",
                'type': track_type,
                'latitude': base_lat,
                'longitude': base_lon,
                'altitude': 1000 + (index * 500) if track_type == 'Aircraft' else None,
                'heading': (index * 45) % 360,
                'speed': 100 + (index * 50),
                'status': 'Active',
                'source': 'ASTERIX',
                'category': category,
                'last_updated': datetime.utcnow().isoformat(),
                'quality_indicators': {
                    'detection_type': 'primary' if index % 2 == 0 else 'secondary',
                    'confidence': 0.8 + (index * 0.02),
                    'accuracy': 'high' if index < 3 else 'medium'
                }
            }
            
            return track
            
        except Exception as e:
            print(f"Error extracting track {index}: {e}")
            return None
    
    def _determine_track_type(self, category: int) -> str:
        """
        Determine track type based on ASTERIX category.
        
        Args:
            category: ASTERIX category number
            
        Returns:
            Track type string
        """
        if category in [1, 2, 19, 20, 21, 48]:
            return 'Aircraft'
        elif category in [10]:
            return 'Vehicle'
        elif category in [8]:
            return 'Weather'
        else:
            return 'Unknown'
    
    def validate_asterix_data(self, data: bytes) -> bool:
        """
        Validate ASTERIX data format and integrity.
        
        Args:
            data: Raw ASTERIX data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        try:
            if len(data) < 3:
                return False
            
            category = data[0]
            length = struct.unpack('>H', data[1:3])[0]
            
            # Basic validation checks
            if category not in self.category_definitions:
                return False
            
            if length > len(data):
                return False
            
            if length < 3:
                return False
            
            return True
            
        except Exception:
            return False
    
    def get_supported_categories(self) -> Dict[int, str]:
        """
        Get dictionary of supported ASTERIX categories.
        
        Returns:
            Dictionary mapping category numbers to descriptions
        """
        return self.category_definitions.copy()
    
    def create_asterix_message(self, tracks: List[Dict[str, Any]], category: int = 10) -> bytes:
        """
        Create a simulated ASTERIX message from track data.
        
        Args:
            tracks: List of track dictionaries
            category: ASTERIX category to use
            
        Returns:
            Simulated ASTERIX message bytes
        """
        try:
            # Simple ASTERIX message structure simulation
            message = bytearray()
            
            # Category (1 byte)
            message.append(category)
            
            # Length placeholder (2 bytes) - will be updated
            length_pos = len(message)
            message.extend([0, 0])
            
            # For each track, add simulated data
            for track in tracks:
                # Data Source Identifier (I010/010)
                message.extend([0x01, 0x02])  # SAC/SIC
                
                # Time of Day (I010/140) - 3 bytes
                time_of_day = int(time.time() % 86400 * 128)  # 1/128 seconds since midnight
                message.extend(struct.pack('>I', time_of_day)[1:])
                
                # Position in WGS-84 (I010/041) - 8 bytes
                lat = int(track['latitude'] * 8388608 / 90)  # Convert to ASTERIX format
                lon = int(track['longitude'] * 8388608 / 180)
                message.extend(struct.pack('>ii', lat, lon))
                
                # Track Number (I010/161) - 2 bytes
                track_num = int(track['track_id'][-3:]) if track['track_id'][-3:].isdigit() else 1
                message.extend(struct.pack('>H', track_num))
            
            # Update length field
            total_length = len(message)
            struct.pack_into('>H', message, length_pos, total_length)
            
            return bytes(message)
            
        except Exception as e:
            print(f"Error creating ASTERIX message: {e}")
            return b''
    
    def decode_data_item(self, item_code: str, data: bytes) -> Dict[str, Any]:
        """
        Decode specific ASTERIX data item.
        
        Args:
            item_code: ASTERIX data item code (e.g., "I010/010")
            data: Raw data for the item
            
        Returns:
            Decoded data dictionary
        """
        try:
            result = {
                'item_code': item_code,
                'description': self.data_items.get(item_code, 'Unknown'),
                'raw_data': data.hex(),
                'decoded_value': None
            }
            
            # Decode based on item type
            if item_code == "I010/010":  # Data Source Identifier
                if len(data) >= 2:
                    sac, sic = struct.unpack('BB', data[:2])
                    result['decoded_value'] = {'SAC': sac, 'SIC': sic}
            
            elif item_code == "I010/041":  # Position in WGS-84
                if len(data) >= 8:
                    lat_raw, lon_raw = struct.unpack('>ii', data[:8])
                    lat = lat_raw * 90.0 / 8388608
                    lon = lon_raw * 180.0 / 8388608
                    result['decoded_value'] = {'latitude': lat, 'longitude': lon}
            
            elif item_code == "I010/140":  # Time of Day
                if len(data) >= 3:
                    time_raw = struct.unpack('>I', b'\x00' + data[:3])[0]
                    seconds = time_raw / 128.0
                    result['decoded_value'] = {'seconds_since_midnight': seconds}
            
            elif item_code == "I010/161":  # Track Number
                if len(data) >= 2:
                    track_num = struct.unpack('>H', data[:2])[0]
                    result['decoded_value'] = {'track_number': track_num}
            
            return result
            
        except Exception as e:
            print(f"Error decoding data item {item_code}: {e}")
            return result
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about ASTERIX data processing.
        
        Returns:
            Dictionary containing processing statistics
        """
        return {
            'supported_categories': len(self.category_definitions),
            'supported_data_items': len(self.data_items),
            'last_processing_time': datetime.utcnow().isoformat(),
            'processor_version': '1.0.0',
            'capabilities': [
                'Track extraction',
                'Data validation', 
                'Message creation',
                'Item decoding'
            ]
        }
