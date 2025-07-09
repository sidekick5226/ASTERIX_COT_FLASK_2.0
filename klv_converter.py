"""
KLV (Key-Length-Value) Metadata Converter
Converts surveillance track data to/from KLV metadata format according to MISB standards.
"""

import struct
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple, Union
import math

class KLVConverter:
    """
    Converts track data to/from KLV (Key-Length-Value) metadata format.
    Supports MISB ST 0601 (UAS Datalink Local Set) and ST 0902 (VMTi Local Set) standards.
    """
    
    def __init__(self):
        # MISB ST 0601 UAS Datalink Local Set Universal Key
        self.UAS_DATALINK_LS_UL = bytes([
            0x06, 0x0E, 0x2B, 0x34, 0x02, 0x0B, 0x01, 0x01,
            0x0E, 0x01, 0x03, 0x01, 0x01, 0x00, 0x00, 0x00
        ])
        
        # MISB ST 0902 VMTi Local Set Universal Key
        self.VMTI_LS_UL = bytes([
            0x06, 0x0E, 0x2B, 0x34, 0x02, 0x0B, 0x01, 0x01,
            0x0E, 0x01, 0x03, 0x03, 0x06, 0x00, 0x00, 0x00
        ])
        
        # ST 0601 Data Elements (Key definitions)
        self.ST0601_ELEMENTS = {
            1: {"name": "Checksum", "type": "uint16", "units": None},
            2: {"name": "UNIX Time Stamp", "type": "uint64", "units": "microseconds"},
            3: {"name": "Mission ID", "type": "string", "units": None},
            4: {"name": "Platform Tail Number", "type": "string", "units": None},
            5: {"name": "Platform Heading Angle", "type": "uint16", "units": "degrees"},
            6: {"name": "Platform Pitch Angle", "type": "int16", "units": "degrees"},
            7: {"name": "Platform Roll Angle", "type": "int16", "units": "degrees"},
            13: {"name": "Sensor Latitude", "type": "int32", "units": "degrees"},
            14: {"name": "Sensor Longitude", "type": "int32", "units": "degrees"},
            15: {"name": "Sensor True Altitude", "type": "uint16", "units": "meters"},
            16: {"name": "Sensor Horizontal Field of View", "type": "uint16", "units": "degrees"},
            17: {"name": "Sensor Vertical Field of View", "type": "uint16", "units": "degrees"},
            18: {"name": "Sensor Relative Azimuth Angle", "type": "uint32", "units": "degrees"},
            19: {"name": "Sensor Relative Elevation Angle", "type": "int32", "units": "degrees"},
            20: {"name": "Sensor Relative Roll Angle", "type": "uint32", "units": "degrees"},
            21: {"name": "Slant Range", "type": "uint32", "units": "meters"},
            22: {"name": "Target Width", "type": "uint16", "units": "meters"},
            23: {"name": "Frame Center Latitude", "type": "int32", "units": "degrees"},
            24: {"name": "Frame Center Longitude", "type": "int32", "units": "degrees"},
            25: {"name": "Frame Center Elevation", "type": "uint16", "units": "meters"},
            40: {"name": "Target Location Latitude", "type": "int32", "units": "degrees"},
            41: {"name": "Target Location Longitude", "type": "int32", "units": "degrees"},
            42: {"name": "Target Location Elevation", "type": "uint16", "units": "meters"},
            65: {"name": "UAS LDS Version Number", "type": "uint8", "units": None},
        }
        
        # ST 0902 VMTi Elements
        self.ST0902_ELEMENTS = {
            1: {"name": "Checksum", "type": "uint16", "units": None},
            2: {"name": "UNIX Time Stamp", "type": "uint64", "units": "microseconds"},
            3: {"name": "Mission ID", "type": "string", "units": None},
            4: {"name": "Platform Designation", "type": "string", "units": None},
            5: {"name": "Image Source Sensor", "type": "string", "units": None},
            6: {"name": "Image Coordinate System", "type": "string", "units": None},
            7: {"name": "System Name", "type": "string", "units": None},
            8: {"name": "System Short Name", "type": "string", "units": None},
            9: {"name": "Number of Detected Targets", "type": "uint16", "units": None},
            10: {"name": "Number of Reported Targets", "type": "uint16", "units": None},
            11: {"name": "Frame Number", "type": "uint32", "units": None},
            12: {"name": "Frame Width", "type": "uint16", "units": "pixels"},
            13: {"name": "Frame Height", "type": "uint16", "units": "pixels"},
            14: {"name": "Source Sensor Latitude", "type": "int32", "units": "degrees"},
            15: {"name": "Source Sensor Longitude", "type": "int32", "units": "degrees"},
            16: {"name": "Source Sensor True Altitude", "type": "uint16", "units": "meters"},
            101: {"name": "VMTi Data Set", "type": "local_set", "units": None},
        }
        
        # VMTi Target Data Elements
        self.VMTI_TARGET_ELEMENTS = {
            1: {"name": "Target Centroid Pixel Number", "type": "uint16", "units": "pixels"},
            2: {"name": "Target Centroid Pixel Row", "type": "uint16", "units": "pixels"},
            3: {"name": "Target Width", "type": "uint8", "units": "pixels"},
            4: {"name": "Target Height", "type": "uint8", "units": "pixels"},
            5: {"name": "Target Location Latitude", "type": "int32", "units": "degrees"},
            6: {"name": "Target Location Longitude", "type": "int32", "units": "degrees"},
            7: {"name": "Target Location Elevation", "type": "uint16", "units": "meters"},
            8: {"name": "Bounding Box Top Left Pixel Number", "type": "uint16", "units": "pixels"},
            9: {"name": "Bounding Box Top Left Pixel Row", "type": "uint16", "units": "pixels"},
            10: {"name": "Bounding Box Bottom Right Pixel Number", "type": "uint16", "units": "pixels"},
            11: {"name": "Bounding Box Bottom Right Pixel Row", "type": "uint16", "units": "pixels"},
            12: {"name": "Target Priority", "type": "uint8", "units": None},
            13: {"name": "Target Confidence Level", "type": "uint8", "units": "percent"},
            14: {"name": "Target History", "type": "uint8", "units": None},
            15: {"name": "Percentage of Target Pixels", "type": "uint8", "units": "percent"},
            16: {"name": "Target Color", "type": "uint24", "units": "RGB"},
            17: {"name": "Target Intensity", "type": "uint8", "units": None},
            18: {"name": "Target Location Covariance Matrix", "type": "bytes", "units": None},
            19: {"name": "Target Velocity North", "type": "int16", "units": "m/s"},
            20: {"name": "Target Velocity East", "type": "int16", "units": "m/s"},
        }
    
    def track_to_klv_packet(self, track: Dict[str, Any], 
                           standard: str = "ST0601") -> bytes:
        """
        Convert track data to KLV metadata packet.
        
        Args:
            track: Track dictionary containing position and metadata
            standard: KLV standard to use ("ST0601" or "ST0902")
            
        Returns:
            KLV packet as bytes
        """
        try:
            if standard == "ST0601":
                return self._create_st0601_packet(track)
            elif standard == "ST0902":
                return self._create_st0902_packet(track)
            else:
                raise ValueError(f"Unsupported KLV standard: {standard}")
                
        except Exception as e:
            print(f"Error creating KLV packet: {e}")
            return b''
    
    def _create_st0601_packet(self, track: Dict[str, Any]) -> bytes:
        """
        Create MISB ST 0601 UAS Datalink Local Set packet.
        
        Args:
            track: Track dictionary
            
        Returns:
            ST 0601 KLV packet bytes
        """
        try:
            packet_data = bytearray()
            
            # Add Universal Key
            packet_data.extend(self.UAS_DATALINK_LS_UL)
            
            # Prepare Local Set data
            local_set = bytearray()
            
            # Add UNIX Time Stamp (Key 2)
            timestamp = int(datetime.utcnow().timestamp() * 1000000)  # microseconds
            local_set.extend(self._encode_klv_item(2, struct.pack('>Q', timestamp)))
            
            # Add Mission ID (Key 3) if available
            mission_id = track.get('mission_id', f"MISSION-{track['track_id']}")
            local_set.extend(self._encode_klv_item(3, mission_id.encode('utf-8')))
            
            # Add Platform Tail Number (Key 4)
            platform_id = track.get('platform_id', track.get('callsign', track['track_id']))
            local_set.extend(self._encode_klv_item(4, platform_id.encode('utf-8')))
            
            # Add Platform Heading (Key 5) if available
            if 'heading' in track and track['heading'] is not None:
                heading = int((track['heading'] % 360) * 65536 / 360)
                local_set.extend(self._encode_klv_item(5, struct.pack('>H', heading)))
            
            # Add Sensor/Target Location (Keys 40, 41, 42)
            if 'latitude' in track and 'longitude' in track:
                # Target Location Latitude (Key 40)
                lat_encoded = int(track['latitude'] * (2**31 - 1) / 90)
                local_set.extend(self._encode_klv_item(40, struct.pack('>i', lat_encoded)))
                
                # Target Location Longitude (Key 41)
                lon_encoded = int(track['longitude'] * (2**31 - 1) / 180)
                local_set.extend(self._encode_klv_item(41, struct.pack('>i', lon_encoded)))
                
                # Target Location Elevation (Key 42) if available
                if 'altitude' in track and track['altitude'] is not None:
                    elevation = int(max(0, track['altitude'] * 0.3048))  # ft to meters
                    local_set.extend(self._encode_klv_item(42, struct.pack('>H', min(65535, elevation))))
            
            # Add UAS LDS Version Number (Key 65)
            local_set.extend(self._encode_klv_item(65, struct.pack('B', 16)))  # Version 16
            
            # Calculate and add checksum (Key 1) - must be first in local set
            checksum = self._calculate_checksum(self.UAS_DATALINK_LS_UL + local_set)
            checksum_item = self._encode_klv_item(1, struct.pack('>H', checksum))
            local_set = checksum_item + local_set
            
            # Add length and local set data
            length = self._encode_ber_length(len(local_set))
            packet_data.extend(length)
            packet_data.extend(local_set)
            
            return bytes(packet_data)
            
        except Exception as e:
            print(f"Error creating ST 0601 packet: {e}")
            return b''
    
    def _create_st0902_packet(self, track: Dict[str, Any]) -> bytes:
        """
        Create MISB ST 0902 VMTi Local Set packet.
        
        Args:
            track: Track dictionary
            
        Returns:
            ST 0902 KLV packet bytes
        """
        try:
            packet_data = bytearray()
            
            # Add Universal Key
            packet_data.extend(self.VMTI_LS_UL)
            
            # Prepare Local Set data
            local_set = bytearray()
            
            # Add UNIX Time Stamp (Key 2)
            timestamp = int(datetime.utcnow().timestamp() * 1000000)
            local_set.extend(self._encode_klv_item(2, struct.pack('>Q', timestamp)))
            
            # Add Mission ID (Key 3)
            mission_id = track.get('mission_id', f"VMTI-{track['track_id']}")
            local_set.extend(self._encode_klv_item(3, mission_id.encode('utf-8')))
            
            # Add Platform Designation (Key 4)
            platform = track.get('platform_id', 'UAV-001')
            local_set.extend(self._encode_klv_item(4, platform.encode('utf-8')))
            
            # Add System Name (Key 7)
            system_name = track.get('system_name', 'Surveillance System')
            local_set.extend(self._encode_klv_item(7, system_name.encode('utf-8')))
            
            # Add Number of Detected Targets (Key 9)
            local_set.extend(self._encode_klv_item(9, struct.pack('>H', 1)))
            
            # Add Number of Reported Targets (Key 10)
            local_set.extend(self._encode_klv_item(10, struct.pack('>H', 1)))
            
            # Add Frame Number (Key 11)
            frame_num = track.get('frame_number', int(datetime.utcnow().timestamp()))
            local_set.extend(self._encode_klv_item(11, struct.pack('>I', frame_num)))
            
            # Add Source Sensor Position (Keys 14, 15, 16) if available
            if 'sensor_latitude' in track:
                lat_encoded = int(track['sensor_latitude'] * (2**31 - 1) / 90)
                local_set.extend(self._encode_klv_item(14, struct.pack('>i', lat_encoded)))
            
            if 'sensor_longitude' in track:
                lon_encoded = int(track['sensor_longitude'] * (2**31 - 1) / 180)
                local_set.extend(self._encode_klv_item(15, struct.pack('>i', lon_encoded)))
            
            if 'sensor_altitude' in track:
                altitude = int(max(0, track['sensor_altitude']))
                local_set.extend(self._encode_klv_item(16, struct.pack('>H', min(65535, altitude))))
            
            # Add VMTi Data Set (Key 101) - contains target information
            vmti_data = self._create_vmti_target_data(track)
            local_set.extend(self._encode_klv_item(101, vmti_data))
            
            # Calculate and add checksum (Key 1)
            checksum = self._calculate_checksum(self.VMTI_LS_UL + local_set)
            checksum_item = self._encode_klv_item(1, struct.pack('>H', checksum))
            local_set = checksum_item + local_set
            
            # Add length and local set data
            length = self._encode_ber_length(len(local_set))
            packet_data.extend(length)
            packet_data.extend(local_set)
            
            return bytes(packet_data)
            
        except Exception as e:
            print(f"Error creating ST 0902 packet: {e}")
            return b''
    
    def _create_vmti_target_data(self, track: Dict[str, Any]) -> bytes:
        """
        Create VMTi target data set for a single target.
        
        Args:
            track: Track dictionary
            
        Returns:
            VMTi target data bytes
        """
        try:
            target_data = bytearray()
            
            # Target Location Latitude (Key 5)
            if 'latitude' in track:
                lat_encoded = int(track['latitude'] * (2**31 - 1) / 90)
                target_data.extend(self._encode_klv_item(5, struct.pack('>i', lat_encoded)))
            
            # Target Location Longitude (Key 6)
            if 'longitude' in track:
                lon_encoded = int(track['longitude'] * (2**31 - 1) / 180)
                target_data.extend(self._encode_klv_item(6, struct.pack('>i', lon_encoded)))
            
            # Target Location Elevation (Key 7)
            if 'altitude' in track and track['altitude'] is not None:
                elevation = int(max(0, track['altitude'] * 0.3048))  # ft to meters
                target_data.extend(self._encode_klv_item(7, struct.pack('>H', min(65535, elevation))))
            
            # Target Priority (Key 12)
            priority = track.get('priority', 1)
            target_data.extend(self._encode_klv_item(12, struct.pack('B', priority)))
            
            # Target Confidence Level (Key 13)
            confidence = int(track.get('confidence', 0.8) * 100)  # Convert to percentage
            target_data.extend(self._encode_klv_item(13, struct.pack('B', min(100, confidence))))
            
            # Target Velocity North (Key 19) and East (Key 20)
            if 'speed' in track and 'heading' in track:
                speed_ms = track['speed'] * 0.514444  # knots to m/s
                heading_rad = math.radians(track['heading'])
                
                velocity_north = int(speed_ms * math.cos(heading_rad))
                velocity_east = int(speed_ms * math.sin(heading_rad))
                
                target_data.extend(self._encode_klv_item(19, struct.pack('>h', velocity_north)))
                target_data.extend(self._encode_klv_item(20, struct.pack('>h', velocity_east)))
            
            return bytes(target_data)
            
        except Exception as e:
            print(f"Error creating VMTi target data: {e}")
            return b''
    
    def parse_klv_packet(self, klv_data: bytes) -> Dict[str, Any]:
        """
        Parse KLV packet and extract metadata.
        
        Args:
            klv_data: KLV packet bytes
            
        Returns:
            Dictionary containing parsed metadata
        """
        try:
            if len(klv_data) < 16:
                return {}
            
            # Extract Universal Key
            ul_key = klv_data[:16]
            
            # Determine standard based on Universal Key
            if ul_key == self.UAS_DATALINK_LS_UL:
                return self._parse_st0601_packet(klv_data)
            elif ul_key == self.VMTI_LS_UL:
                return self._parse_st0902_packet(klv_data)
            else:
                print(f"Unknown Universal Key: {ul_key.hex()}")
                return {}
                
        except Exception as e:
            print(f"Error parsing KLV packet: {e}")
            return {}
    
    def _parse_st0601_packet(self, klv_data: bytes) -> Dict[str, Any]:
        """
        Parse MISB ST 0601 packet.
        
        Args:
            klv_data: KLV packet bytes
            
        Returns:
            Parsed metadata dictionary
        """
        try:
            metadata = {
                'standard': 'ST0601',
                'universal_key': klv_data[:16].hex()
            }
            
            # Parse length and get local set data
            length, length_bytes = self._decode_ber_length(klv_data[16:])
            local_set_data = klv_data[16 + length_bytes:16 + length_bytes + length]
            
            # Parse local set items
            offset = 0
            while offset < len(local_set_data):
                try:
                    key, value, item_length = self._decode_klv_item(local_set_data[offset:])
                    if key in self.ST0601_ELEMENTS:
                        element_info = self.ST0601_ELEMENTS[key]
                        decoded_value = self._decode_value(value, element_info['type'])
                        metadata[element_info['name']] = decoded_value
                    
                    offset += item_length
                except Exception as e:
                    print(f"Error parsing item at offset {offset}: {e}")
                    break
            
            return metadata
            
        except Exception as e:
            print(f"Error parsing ST 0601 packet: {e}")
            return {}
    
    def _parse_st0902_packet(self, klv_data: bytes) -> Dict[str, Any]:
        """
        Parse MISB ST 0902 packet.
        
        Args:
            klv_data: KLV packet bytes
            
        Returns:
            Parsed metadata dictionary
        """
        try:
            metadata = {
                'standard': 'ST0902',
                'universal_key': klv_data[:16].hex()
            }
            
            # Parse length and get local set data
            length, length_bytes = self._decode_ber_length(klv_data[16:])
            local_set_data = klv_data[16 + length_bytes:16 + length_bytes + length]
            
            # Parse local set items
            offset = 0
            while offset < len(local_set_data):
                try:
                    key, value, item_length = self._decode_klv_item(local_set_data[offset:])
                    if key in self.ST0902_ELEMENTS:
                        element_info = self.ST0902_ELEMENTS[key]
                        if key == 101:  # VMTi Data Set
                            metadata['targets'] = self._parse_vmti_targets(value)
                        else:
                            decoded_value = self._decode_value(value, element_info['type'])
                            metadata[element_info['name']] = decoded_value
                    
                    offset += item_length
                except Exception as e:
                    print(f"Error parsing item at offset {offset}: {e}")
                    break
            
            return metadata
            
        except Exception as e:
            print(f"Error parsing ST 0902 packet: {e}")
            return {}
    
    def _parse_vmti_targets(self, vmti_data: bytes) -> List[Dict[str, Any]]:
        """
        Parse VMTi target data.
        
        Args:
            vmti_data: VMTi data bytes
            
        Returns:
            List of target dictionaries
        """
        try:
            targets = []
            target = {}
            
            offset = 0
            while offset < len(vmti_data):
                try:
                    key, value, item_length = self._decode_klv_item(vmti_data[offset:])
                    if key in self.VMTI_TARGET_ELEMENTS:
                        element_info = self.VMTI_TARGET_ELEMENTS[key]
                        decoded_value = self._decode_value(value, element_info['type'])
                        target[element_info['name']] = decoded_value
                    
                    offset += item_length
                except Exception as e:
                    print(f"Error parsing VMTi target at offset {offset}: {e}")
                    break
            
            if target:
                targets.append(target)
            
            return targets
            
        except Exception as e:
            print(f"Error parsing VMTi targets: {e}")
            return []
    
    def _encode_klv_item(self, key: int, value: bytes) -> bytes:
        """
        Encode a single KLV item.
        
        Args:
            key: Item key
            value: Item value bytes
            
        Returns:
            Encoded KLV item bytes
        """
        try:
            item = bytearray()
            
            # Encode key (BER OID encoding for keys > 127)
            if key <= 127:
                item.append(key)
            else:
                # Multi-byte key encoding
                item.extend(self._encode_ber_oid(key))
            
            # Encode length
            length_bytes = self._encode_ber_length(len(value))
            item.extend(length_bytes)
            
            # Add value
            item.extend(value)
            
            return bytes(item)
            
        except Exception as e:
            print(f"Error encoding KLV item: {e}")
            return b''
    
    def _decode_klv_item(self, data: bytes) -> Tuple[int, bytes, int]:
        """
        Decode a single KLV item from data.
        
        Args:
            data: Data bytes starting with KLV item
            
        Returns:
            Tuple of (key, value, total_length)
        """
        try:
            offset = 0
            
            # Decode key
            if data[0] <= 127:
                key = data[0]
                offset = 1
            else:
                key, key_bytes = self._decode_ber_oid(data)
                offset = key_bytes
            
            # Decode length
            length, length_bytes = self._decode_ber_length(data[offset:])
            offset += length_bytes
            
            # Extract value
            value = data[offset:offset + length]
            
            return key, value, offset + length
            
        except Exception as e:
            print(f"Error decoding KLV item: {e}")
            return 0, b'', 0
    
    def _encode_ber_length(self, length: int) -> bytes:
        """
        Encode length using BER (Basic Encoding Rules).
        
        Args:
            length: Length value to encode
            
        Returns:
            BER encoded length bytes
        """
        if length <= 127:
            return bytes([length])
        else:
            # Long form
            length_bytes = []
            temp_length = length
            while temp_length > 0:
                length_bytes.insert(0, temp_length & 0xFF)
                temp_length >>= 8
            
            return bytes([0x80 | len(length_bytes)]) + bytes(length_bytes)
    
    def _decode_ber_length(self, data: bytes) -> Tuple[int, int]:
        """
        Decode BER encoded length.
        
        Args:
            data: Data bytes starting with length
            
        Returns:
            Tuple of (length, bytes_consumed)
        """
        if data[0] <= 127:
            return data[0], 1
        else:
            # Long form
            num_octets = data[0] & 0x7F
            if num_octets == 0:
                raise ValueError("Indefinite length not supported")
            
            length = 0
            for i in range(1, num_octets + 1):
                length = (length << 8) | data[i]
            
            return length, num_octets + 1
    
    def _encode_ber_oid(self, oid: int) -> bytes:
        """
        Encode OID using BER.
        
        Args:
            oid: OID value to encode
            
        Returns:
            BER encoded OID bytes
        """
        if oid <= 127:
            return bytes([oid])
        
        result = []
        temp = oid
        result.append(temp & 0x7F)
        temp >>= 7
        
        while temp > 0:
            result.insert(0, (temp & 0x7F) | 0x80)
            temp >>= 7
        
        return bytes(result)
    
    def _decode_ber_oid(self, data: bytes) -> Tuple[int, int]:
        """
        Decode BER encoded OID.
        
        Args:
            data: Data bytes starting with OID
            
        Returns:
            Tuple of (oid, bytes_consumed)
        """
        oid = 0
        offset = 0
        
        while offset < len(data):
            byte = data[offset]
            oid = (oid << 7) | (byte & 0x7F)
            offset += 1
            
            if (byte & 0x80) == 0:
                break
        
        return oid, offset
    
    def _decode_value(self, value: bytes, value_type: str) -> Any:
        """
        Decode value based on its type.
        
        Args:
            value: Raw value bytes
            value_type: Type specification
            
        Returns:
            Decoded value
        """
        try:
            if value_type == "uint8":
                return struct.unpack('B', value)[0] if len(value) >= 1 else 0
            elif value_type == "uint16":
                return struct.unpack('>H', value)[0] if len(value) >= 2 else 0
            elif value_type == "uint24":
                # 24-bit unsigned integer
                if len(value) >= 3:
                    return (value[0] << 16) | (value[1] << 8) | value[2]
                return 0
            elif value_type == "uint32":
                return struct.unpack('>I', value)[0] if len(value) >= 4 else 0
            elif value_type == "uint64":
                return struct.unpack('>Q', value)[0] if len(value) >= 8 else 0
            elif value_type == "int16":
                return struct.unpack('>h', value)[0] if len(value) >= 2 else 0
            elif value_type == "int32":
                return struct.unpack('>i', value)[0] if len(value) >= 4 else 0
            elif value_type == "string":
                return value.decode('utf-8', errors='ignore')
            elif value_type == "bytes":
                return value.hex()
            else:
                return value.hex()
                
        except Exception as e:
            print(f"Error decoding value of type {value_type}: {e}")
            return None
    
    def _calculate_checksum(self, data: bytes) -> int:
        """
        Calculate 16-bit checksum for KLV packet.
        
        Args:
            data: Data to calculate checksum for
            
        Returns:
            16-bit checksum value
        """
        checksum = 0
        for i in range(0, len(data), 2):
            if i + 1 < len(data):
                word = (data[i] << 8) | data[i + 1]
            else:
                word = data[i] << 8
            checksum = (checksum + word) & 0xFFFF
        
        return (0x10000 - checksum) & 0xFFFF
    
    def tracks_to_klv_stream(self, tracks: List[Dict[str, Any]], 
                            standard: str = "ST0601") -> bytes:
        """
        Convert multiple tracks to a KLV stream.
        
        Args:
            tracks: List of track dictionaries
            standard: KLV standard to use
            
        Returns:
            KLV stream bytes containing all tracks
        """
        try:
            stream = bytearray()
            
            for track in tracks:
                packet = self.track_to_klv_packet(track, standard)
                if packet:
                    stream.extend(packet)
            
            return bytes(stream)
            
        except Exception as e:
            print(f"Error creating KLV stream: {e}")
            return b''
    
    def validate_klv_packet(self, klv_data: bytes) -> bool:
        """
        Validate KLV packet structure and checksum.
        
        Args:
            klv_data: KLV packet bytes to validate
            
        Returns:
            True if packet is valid, False otherwise
        """
        try:
            if len(klv_data) < 16:
                return False
            
            # Check Universal Key
            ul_key = klv_data[:16]
            if ul_key not in [self.UAS_DATALINK_LS_UL, self.VMTI_LS_UL]:
                return False
            
            # Parse and validate length
            length, length_bytes = self._decode_ber_length(klv_data[16:])
            expected_total_length = 16 + length_bytes + length
            
            if len(klv_data) != expected_total_length:
                return False
            
            # TODO: Validate checksum if present
            
            return True
            
        except Exception:
            return False
    
    def get_supported_standards(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about supported KLV standards.
        
        Returns:
            Dictionary containing standard information
        """
        return {
            'ST0601': {
                'name': 'UAS Datalink Local Set',
                'description': 'MISB Standard 0601 for UAS metadata',
                'universal_key': self.UAS_DATALINK_LS_UL.hex(),
                'elements': len(self.ST0601_ELEMENTS)
            },
            'ST0902': {
                'name': 'VMTi Local Set',
                'description': 'MISB Standard 0902 for Video Moving Target Indicator',
                'universal_key': self.VMTI_LS_UL.hex(),
                'elements': len(self.ST0902_ELEMENTS)
            }
        }
    
    def extract_track_from_klv(self, klv_metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract track data from parsed KLV metadata.
        
        Args:
            klv_metadata: Parsed KLV metadata dictionary
            
        Returns:
            Track dictionary or None
        """
        try:
            track = {
                'source': 'KLV',
                'klv_standard': klv_metadata.get('standard', 'Unknown')
            }
            
            # Extract common fields based on standard
            if klv_metadata.get('standard') == 'ST0601':
                # Extract from ST0601 format
                if 'Platform Tail Number' in klv_metadata:
                    track['track_id'] = klv_metadata['Platform Tail Number']
                    track['callsign'] = klv_metadata['Platform Tail Number']
                
                if 'Target Location Latitude' in klv_metadata:
                    # Decode latitude from ST0601 format
                    lat_raw = klv_metadata['Target Location Latitude']
                    track['latitude'] = lat_raw * 90.0 / (2**31 - 1)
                
                if 'Target Location Longitude' in klv_metadata:
                    # Decode longitude from ST0601 format  
                    lon_raw = klv_metadata['Target Location Longitude']
                    track['longitude'] = lon_raw * 180.0 / (2**31 - 1)
                
                if 'Target Location Elevation' in klv_metadata:
                    track['altitude'] = klv_metadata['Target Location Elevation'] * 3.28084  # m to ft
                
                if 'Platform Heading Angle' in klv_metadata:
                    heading_raw = klv_metadata['Platform Heading Angle']
                    track['heading'] = heading_raw * 360.0 / 65536
                
                track['type'] = 'Aircraft'  # Default for ST0601
            
            elif klv_metadata.get('standard') == 'ST0902':
                # Extract from ST0902 format
                if 'Platform Designation' in klv_metadata:
                    track['track_id'] = klv_metadata['Platform Designation']
                    track['callsign'] = klv_metadata['Platform Designation']
                
                # Extract target information if available
                if 'targets' in klv_metadata and klv_metadata['targets']:
                    target_data = klv_metadata['targets'][0]  # Use first target
                    
                    if 'Target Location Latitude' in target_data:
                        lat_raw = target_data['Target Location Latitude']
                        track['latitude'] = lat_raw * 90.0 / (2**31 - 1)
                    
                    if 'Target Location Longitude' in target_data:
                        lon_raw = target_data['Target Location Longitude']
                        track['longitude'] = lon_raw * 180.0 / (2**31 - 1)
                    
                    if 'Target Location Elevation' in target_data:
                        track['altitude'] = target_data['Target Location Elevation'] * 3.28084
                    
                    # Calculate speed and heading from velocity components
                    if 'Target Velocity North' in target_data and 'Target Velocity East' in target_data:
                        vel_north = target_data['Target Velocity North']
                        vel_east = target_data['Target Velocity East']
                        
                        speed_ms = math.sqrt(vel_north**2 + vel_east**2)
                        track['speed'] = speed_ms / 0.514444  # m/s to knots
                        
                        heading_rad = math.atan2(vel_east, vel_north)
                        track['heading'] = (math.degrees(heading_rad) + 360) % 360
                    
                    if 'Target Confidence Level' in target_data:
                        track['confidence'] = target_data['Target Confidence Level'] / 100.0
                
                track['type'] = 'Vehicle'  # Default for ST0902
            
            # Set default values
            track['status'] = 'Active'
            track['last_updated'] = datetime.utcnow().isoformat()
            
            # Ensure required fields are present
            if 'track_id' not in track:
                track['track_id'] = f"KLV-{int(datetime.utcnow().timestamp())}"
            
            if 'latitude' in track and 'longitude' in track:
                return track
            else:
                print("KLV metadata does not contain sufficient position information")
                return None
                
        except Exception as e:
            print(f"Error extracting track from KLV: {e}")
            return None
