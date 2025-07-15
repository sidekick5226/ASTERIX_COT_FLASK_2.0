"""
ASTERIX CAT-48 and Lower Categories Consolidated Processor
Handles ASTERIX Categories 10, 21, and 48 in a single comprehensive processor.
Based on EUROCONTROL ASTERIX specifications and Cambridge Pixel implementation guidance.
"""

import struct
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import math
import logging

logger = logging.getLogger(__name__)

class AsterixConsolidatedProcessor:
    """
    Consolidated processor for ASTERIX Categories 10, 21, and 48.
    Handles all lower categories in a single efficient processor.
    """
    
    def __init__(self):
        self.supported_categories = [10, 21, 48]
        
        # Category descriptions
        self.category_descriptions = {
            10: "Transmission of Monosensor Surface Movement Data",
            21: "ADS-B Target Reports", 
            48: "Monoradar Target Reports"
        }
        
        # Processing statistics
        self.processing_stats = {
            'total_messages': 0,
            'messages_by_category': {},
            'processing_errors': 0,
            'last_processing_time': None
        }
        
        # Initialize category-specific configurations
        self._init_cat10_config()
        self._init_cat21_config()
        self._init_cat48_config()
    
    def _init_cat10_config(self):
        """Initialize CAT-10 specific configuration."""
        self.cat10_data_items = {
            "I010/010": "Data Source Identifier",
            "I010/020": "Target Report Descriptor",
            "I010/040": "Measured Position in Polar Coordinates",
            "I010/041": "Position in WGS-84 Coordinates",
            "I010/042": "Position in Cartesian Coordinates",
            "I010/060": "Mode-3/A Code in Octal Representation",
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
            "I010/310": "Pre-programmed Message",
            "I010/500": "Standard Deviation of Position",
            "I010/550": "System Status",
            "I010/RE": "Reserved Expansion Field",
            "I010/SP": "Special Purpose Field"
        }
        
        # CAT-10 FSPEC mapping (UAP order)
        self.cat10_fspec_mapping = [
            # First octet (bits 7-1, bit 0 is FX)
            ["I010/010", "I010/020", "I010/040", "I010/041", "I010/042", "I010/200", "I010/202"],
            # Second octet
            ["I010/161", "I010/170", "I010/060", "I010/220", "I010/245", "I010/250", "I010/300"],
            # Third octet  
            ["I010/090", "I010/091", "I010/270", "I010/550", "I010/310", "I010/500", "I010/280"],
            # Fourth octet
            ["I010/131", "I010/210", "I010/140", "I010/RE", "I010/SP", "", ""]
        ]
    
    def _init_cat21_config(self):
        """Initialize CAT-21 specific configuration."""
        self.cat21_data_items = {
            "I021/010": "Data Source Identifier",
            "I021/020": "Target Report Descriptor",
            "I021/030": "Time of Day",
            "I021/032": "Time of Day Accuracy",
            "I021/040": "Target Position in WGS-84",
            "I021/041": "Position Accuracy",
            "I021/070": "Time Stamp",
            "I021/071": "Time of Applicability for Position",
            "I021/072": "Time of Applicability for Velocity",
            "I021/080": "Target Address",
            "I021/090": "Quality Indicators",
            "I021/095": "Velocity Accuracy",
            "I021/110": "Trajectory Intent",
            "I021/130": "Position in WGS-84 Co-ordinates",
            "I021/131": "Signal Amplitude",
            "I021/140": "Geometric Height",
            "I021/145": "Flight Level",
            "I021/146": "Selected Altitude",
            "I021/150": "Air Speed",
            "I021/151": "True Air Speed",
            "I021/152": "Magnetic Heading",
            "I021/155": "Barometric Vertical Rate",
            "I021/157": "Geometric Vertical Rate",
            "I021/160": "Airborne Ground Vector",
            "I021/161": "Track Number",
            "I021/165": "Track Angle Rate",
            "I021/170": "Target Identification",
            "I021/200": "Target Status",
            "I021/210": "MOPS Version",
            "I021/220": "Met Information",
            "I021/230": "Roll Angle",
            "I021/RE": "Reserved Expansion Field",
            "I021/SP": "Special Purpose Field"
        }
        
        # CAT-21 FSPEC mapping
        self.cat21_fspec_mapping = [
            # First octet
            ["I021/010", "I021/040", "I021/030", "I021/130", "I021/080", "I021/140", "I021/090"],
            # Second octet
            ["I021/210", "I021/230", "I021/145", "I021/150", "I021/151", "I021/152", "I021/155"],
            # Third octet
            ["I021/157", "I021/160", "I021/165", "I021/170", "I021/095", "I021/032", "I021/200"],
            # Fourth octet
            ["I021/020", "I021/220", "I021/146", "I021/148", "I021/110", "I021/016", "I021/008"]
        ]
    
    def _init_cat48_config(self):
        """Initialize CAT-48 specific configuration."""
        self.cat48_data_items = {
            "I048/010": "Data Source Identifier",
            "I048/020": "Target Report Descriptor",
            "I048/030": "Warning/Error Conditions",
            "I048/040": "Measured Position in Polar Coordinates",
            "I048/042": "Calculated Position in Cartesian Coordinates",
            "I048/050": "Mode-2 Code in Octal Representation",
            "I048/055": "Mode-1 Code in Octal Representation",
            "I048/060": "Mode-2 Code Confidence Indicator",
            "I048/065": "Mode-1 Code Confidence Indicator",
            "I048/070": "Mode-3/A Code in Octal Representation",
            "I048/080": "Mode-3/A Code Confidence Indicator",
            "I048/090": "Flight Level in Binary Representation",
            "I048/100": "Mode-C Code and Code Confidence Indicator",
            "I048/110": "Height Measured by 3D Radar",
            "I048/120": "Radial Doppler Speed",
            "I048/130": "Radar Plot Characteristics",
            "I048/140": "Time of Day",
            "I048/161": "Track Number",
            "I048/170": "Track Status",
            "I048/200": "Calculated Track Velocity in Polar Coordinates",
            "I048/210": "Track Quality",
            "I048/220": "Aircraft Address",
            "I048/230": "Communications/ACAS Capability and Flight Status",
            "I048/240": "Aircraft Identification",
            "I048/250": "Mode S MB Data",
            "I048/260": "ACAS Resolution Advisory Report",
            "I048/RE": "Reserved Expansion Field",
            "I048/SP": "Special Purpose Field"
        }
        
        # CAT-48 FSPEC mapping (correct UAP order)
        self.cat48_fspec_mapping = [
            # First octet (bits 7-1, bit 0 is FX)
            ["I048/010", "I048/140", "I048/020", "I048/040", "I048/070", "I048/090", "I048/130"],
            # Second octet  
            ["I048/220", "I048/240", "I048/250", "I048/161", "I048/042", "I048/200", "I048/170"],
            # Third octet
            ["I048/210", "I048/030", "I048/080", "I048/100", "I048/110", "I048/120", "I048/230"],
            # Fourth octet
            ["I048/260", "I048/055", "I048/050", "I048/065", "I048/060", "I048/SP", "I048/RE"]
        ]
        
        # CAT-48 specific definitions
        self.cat48_target_types = {
            0: 'No detection',
            1: 'Single PSR detection',
            2: 'Single SSR detection', 
            3: 'SSR + PSR detection',
            4: 'Single ModeS All-Call',
            5: 'Single ModeS Roll-Call',
            6: 'ModeS All-Call + PSR',
            7: 'ModeS Roll-Call + PSR'
        }
        
        self.cat48_flight_status = {
            0: 'No alert, no SPI, aircraft airborne',
            1: 'No alert, no SPI, aircraft on ground',
            2: 'Alert, no SPI, aircraft airborne',
            3: 'Alert, no SPI, aircraft on ground',
            4: 'No alert, SPI, aircraft airborne or on ground',
            5: 'No alert, SPI, aircraft on ground',
            6: 'Alert, SPI, aircraft airborne or on ground',
            7: 'Alert, SPI, aircraft on ground'
        }
    
    def process_asterix_message(self, raw_data: bytes) -> List[Dict[str, Any]]:
        """
        Process ASTERIX message of any supported category.
        
        Args:
            raw_data: Raw ASTERIX message bytes
            
        Returns:
            List of processed target reports
        """
        try:
            if len(raw_data) < 3:
                return []
            
            # Extract category and length
            category = raw_data[0]
            length = struct.unpack('>H', raw_data[1:3])[0]
            
            if length > len(raw_data):
                logger.warning(f"Message length {length} exceeds data length {len(raw_data)}")
                return []
            
            # Update statistics
            self.processing_stats['total_messages'] += 1
            self.processing_stats['messages_by_category'][category] = \
                self.processing_stats['messages_by_category'].get(category, 0) + 1
            self.processing_stats['last_processing_time'] = datetime.utcnow().isoformat()
            
            # Route to appropriate category processor
            if category == 10:
                return self._process_cat10_message(raw_data)
            elif category == 21:
                return self._process_cat21_message(raw_data)
            elif category == 48:
                return self._process_cat48_message(raw_data)
            else:
                logger.warning(f"Unsupported ASTERIX category: {category}")
                return []
                
        except Exception as e:
            self.processing_stats['processing_errors'] += 1
            logger.error(f"Error processing ASTERIX message: {e}")
            return []
    
    def _process_cat48_message(self, raw_data: bytes) -> List[Dict[str, Any]]:
        """Process CAT-48 message using Cambridge Pixel methodology."""
        try:
            # Parse header
            category = raw_data[0]
            length = struct.unpack('>H', raw_data[1:3])[0]
            
            # Parse data record
            position = 3
            
            # Extract FSPEC
            fspec, fspec_length = self._extract_fspec(raw_data[position:])
            position += fspec_length
            
            # Decode which data items are present
            items_present = self._decode_fspec(fspec, self.cat48_fspec_mapping)
            
            # Parse each data item
            target = {
                'category': 48,
                'message_type': 'Monoradar Target Report',
                'timestamp': datetime.utcnow().isoformat(),
                'data_items': {},
                'track_id': None,
                'callsign': None,
                'latitude': None,
                'longitude': None,
                'altitude': None,
                'ground_speed': None,
                'heading': None,
                'range': None,
                'azimuth': None,
                'mode_3a': None,
                'aircraft_address': None,
                'detection_type': None,
                'time_of_day': None,
                'track_number': None,
                'flight_level': None,
                'radial_doppler_speed': None,
                'warning_conditions': []
            }
            
            # Parse each present data item
            for item_code in items_present:
                if position >= len(raw_data):
                    break
                    
                item_data, item_length = self._parse_cat48_data_item(item_code, raw_data[position:])
                if item_data:
                    target['data_items'][item_code] = item_data
                    self._apply_cat48_item_to_target(target, item_code, item_data)
                
                position += item_length
            
            # Generate track ID
            target['track_id'] = self._generate_track_id(target, 48)
            
            return [target]
            
        except Exception as e:
            logger.error(f"Error processing CAT-48 message: {e}")
            return []
    
    def _process_cat21_message(self, raw_data: bytes) -> List[Dict[str, Any]]:
        """Process CAT-21 message."""
        try:
            # Similar structure to CAT-48 but with CAT-21 specific parsing
            category = raw_data[0]
            length = struct.unpack('>H', raw_data[1:3])[0]
            
            position = 3
            fspec, fspec_length = self._extract_fspec(raw_data[position:])
            position += fspec_length
            
            items_present = self._decode_fspec(fspec, self.cat21_fspec_mapping)
            
            target = {
                'category': 21,
                'message_type': 'ADS-B Target Report',
                'timestamp': datetime.utcnow().isoformat(),
                'data_items': {},
                'track_id': None,
                'callsign': None,
                'latitude': None,
                'longitude': None,
                'altitude': None,
                'ground_speed': None,
                'heading': None,
                'aircraft_address': None,
                'time_of_day': None,
                'track_number': None,
                'flight_level': None,
                'geometric_height': None,
                'selected_altitude': None,
                'air_speed': None,
                'true_air_speed': None,
                'magnetic_heading': None,
                'vertical_rate': None
            }
            
            for item_code in items_present:
                if position >= len(raw_data):
                    break
                    
                item_data, item_length = self._parse_cat21_data_item(item_code, raw_data[position:])
                if item_data:
                    target['data_items'][item_code] = item_data
                    self._apply_cat21_item_to_target(target, item_code, item_data)
                
                position += item_length
            
            target['track_id'] = self._generate_track_id(target, 21)
            
            return [target]
            
        except Exception as e:
            logger.error(f"Error processing CAT-21 message: {e}")
            return []
    
    def _process_cat10_message(self, raw_data: bytes) -> List[Dict[str, Any]]:
        """Process CAT-10 message."""
        try:
            category = raw_data[0]
            length = struct.unpack('>H', raw_data[1:3])[0]
            
            position = 3
            fspec, fspec_length = self._extract_fspec(raw_data[position:])
            position += fspec_length
            
            items_present = self._decode_fspec(fspec, self.cat10_fspec_mapping)
            
            target = {
                'category': 10,
                'message_type': 'Surface Movement Data',
                'timestamp': datetime.utcnow().isoformat(),
                'data_items': {},
                'track_id': None,
                'callsign': None,
                'latitude': None,
                'longitude': None,
                'altitude': None,
                'ground_speed': None,
                'heading': None,
                'range': None,
                'azimuth': None,
                'mode_3a': None,
                'aircraft_address': None,
                'time_of_day': None,
                'track_number': None,
                'flight_level': None,
                'measured_height': None,
                'target_size': None,
                'vehicle_fleet': None,
                'surface_type': None
            }
            
            for item_code in items_present:
                if position >= len(raw_data):
                    break
                    
                item_data, item_length = self._parse_cat10_data_item(item_code, raw_data[position:])
                if item_data:
                    target['data_items'][item_code] = item_data
                    self._apply_cat10_item_to_target(target, item_code, item_data)
                
                position += item_length
            
            target['track_id'] = self._generate_track_id(target, 10)
            
            return [target]
            
        except Exception as e:
            logger.error(f"Error processing CAT-10 message: {e}")
            return []
    
    def _extract_fspec(self, data: bytes) -> Tuple[bytes, int]:
        """Extract FSPEC bytes from message data."""
        fspec = bytearray()
        position = 0
        
        for i in range(4):  # Maximum 4 FSPEC bytes
            if position >= len(data):
                break
                
            byte = data[position]
            fspec.append(byte)
            position += 1
            
            # Check FX bit (bit 0)
            if (byte & 0x01) == 0:
                break
        
        return bytes(fspec), position
    
    def _decode_fspec(self, fspec: bytes, mapping: List[List[str]]) -> List[str]:
        """Decode FSPEC to determine present data items."""
        items = []
        
        for octet_idx, octet in enumerate(fspec):
            if octet_idx >= len(mapping):
                break
            
            for bit_idx in range(7):  # Skip FX bit (bit 0)
                if (octet & (1 << (7 - bit_idx))) and bit_idx < len(mapping[octet_idx]):
                    item = mapping[octet_idx][bit_idx]
                    if item:  # Skip empty strings
                        items.append(item)
        
        return items
    
    def _parse_cat48_data_item(self, item_code: str, data: bytes) -> Tuple[Optional[Dict[str, Any]], int]:
        """Parse CAT-48 specific data items."""
        try:
            if item_code == "I048/010":  # Data Source Identifier
                if len(data) < 2:
                    return None, 0
                sac, sic = struct.unpack('BB', data[:2])
                return {'SAC': sac, 'SIC': sic}, 2
            
            elif item_code == "I048/020":  # Target Report Descriptor
                if len(data) < 1:
                    return None, 0
                return self._decode_cat48_target_descriptor(data), self._get_variable_length(data)
            
            elif item_code == "I048/030":  # Warning/Error Conditions
                if len(data) < 1:
                    return None, 0
                return self._decode_warning_conditions(data), self._get_variable_length(data)
            
            elif item_code == "I048/040":  # Measured Position in Polar Coordinates
                if len(data) < 4:
                    return None, 0
                rho_raw, theta_raw = struct.unpack('>HH', data[:4])
                rho = rho_raw / 256.0  # 1/256 NM LSB
                theta = theta_raw * 360.0 / 65536.0  # 360/2^16 degrees LSB
                return {'range': rho, 'azimuth': theta}, 4
            
            elif item_code == "I048/070":  # Mode-3/A Code
                if len(data) < 2:
                    return None, 0
                mode_3a_raw = struct.unpack('>H', data[:2])[0]
                mode_3a = self._decode_mode_3a(mode_3a_raw)
                return {'mode_3a': mode_3a, 'raw_value': mode_3a_raw}, 2
            
            elif item_code == "I048/090":  # Flight Level
                if len(data) < 2:
                    return None, 0
                fl_raw = struct.unpack('>h', data[:2])[0]
                flight_level = fl_raw / 4.0  # 1/4 FL LSB
                return {'flight_level': flight_level}, 2
            
            elif item_code == "I048/120":  # Radial Doppler Speed
                if len(data) < 2:
                    return None, 0
                speed_raw = struct.unpack('>h', data[:2])[0]
                speed = speed_raw  # 1 kt LSB
                return {'radial_doppler_speed': speed}, 2
            
            elif item_code == "I048/140":  # Time of Day
                if len(data) < 3:
                    return None, 0
                time_raw = struct.unpack('>I', b'\x00' + data[:3])[0]
                time_seconds = time_raw / 128.0  # 1/128 seconds LSB
                return {'time_of_day': time_seconds}, 3
            
            elif item_code == "I048/161":  # Track Number
                if len(data) < 2:
                    return None, 0
                track_num = struct.unpack('>H', data[:2])[0]
                return {'track_number': track_num}, 2
            
            elif item_code == "I048/170":  # Track Status
                if len(data) < 1:
                    return None, 0
                return self._decode_track_status(data), self._get_variable_length(data)
            
            elif item_code == "I048/200":  # Calculated Track Velocity
                if len(data) < 4:
                    return None, 0
                speed_raw, heading_raw = struct.unpack('>HH', data[:4])
                speed = speed_raw  # 1 kt LSB
                heading = heading_raw * 360.0 / 65536.0  # 360/2^16 degrees LSB
                return {'ground_speed': speed, 'heading': heading}, 4
            
            elif item_code == "I048/220":  # Aircraft Address
                if len(data) < 3:
                    return None, 0
                address = struct.unpack('>I', b'\x00' + data[:3])[0]
                return {'aircraft_address': f"{address:06X}"}, 3
            
            elif item_code == "I048/240":  # Aircraft Identification
                if len(data) < 6:
                    return None, 0
                callsign = self._decode_callsign(data[:6])
                return {'callsign': callsign}, 6
            
            else:
                # For other items, return minimal data
                return {'raw_data': data[:min(8, len(data))].hex()}, min(8, len(data))
                
        except Exception as e:
            logger.error(f"Error parsing CAT-48 item {item_code}: {e}")
            return None, 0
    
    def _parse_cat21_data_item(self, item_code: str, data: bytes) -> Tuple[Optional[Dict[str, Any]], int]:
        """Parse CAT-21 specific data items."""
        try:
            if item_code == "I021/010":  # Data Source Identifier
                if len(data) < 2:
                    return None, 0
                sac, sic = struct.unpack('BB', data[:2])
                return {'SAC': sac, 'SIC': sic}, 2
            
            elif item_code == "I021/040":  # Target Position in WGS-84
                if len(data) < 6:
                    return None, 0
                lat_raw, lon_raw = struct.unpack('>II', data[:6])
                latitude = lat_raw * 180.0 / (2**23)  # 180/2^23 degrees LSB
                longitude = lon_raw * 180.0 / (2**23)  # 180/2^23 degrees LSB
                return {'latitude': latitude, 'longitude': longitude}, 6
            
            elif item_code == "I021/080":  # Target Address
                if len(data) < 3:
                    return None, 0
                address = struct.unpack('>I', b'\x00' + data[:3])[0]
                return {'aircraft_address': f"{address:06X}"}, 3
            
            elif item_code == "I021/145":  # Flight Level
                if len(data) < 2:
                    return None, 0
                fl_raw = struct.unpack('>h', data[:2])[0]
                flight_level = fl_raw / 4.0  # 1/4 FL LSB
                return {'flight_level': flight_level}, 2
            
            elif item_code == "I021/170":  # Target Identification
                if len(data) < 6:
                    return None, 0
                callsign = self._decode_callsign(data[:6])
                return {'callsign': callsign}, 6
            
            else:
                # For other items, return minimal data
                return {'raw_data': data[:min(8, len(data))].hex()}, min(8, len(data))
                
        except Exception as e:
            logger.error(f"Error parsing CAT-21 item {item_code}: {e}")
            return None, 0
    
    def _parse_cat10_data_item(self, item_code: str, data: bytes) -> Tuple[Optional[Dict[str, Any]], int]:
        """Parse CAT-10 specific data items."""
        try:
            if item_code == "I010/010":  # Data Source Identifier
                if len(data) < 2:
                    return None, 0
                sac, sic = struct.unpack('BB', data[:2])
                return {'SAC': sac, 'SIC': sic}, 2
            
            elif item_code == "I010/040":  # Measured Position in Polar Coordinates
                if len(data) < 4:
                    return None, 0
                rho_raw, theta_raw = struct.unpack('>HH', data[:4])
                rho = rho_raw / 256.0  # 1/256 NM LSB
                theta = theta_raw * 360.0 / 65536.0  # 360/2^16 degrees LSB
                return {'range': rho, 'azimuth': theta}, 4
            
            elif item_code == "I010/220":  # Target Address
                if len(data) < 3:
                    return None, 0
                address = struct.unpack('>I', b'\x00' + data[:3])[0]
                return {'aircraft_address': f"{address:06X}"}, 3
            
            elif item_code == "I010/245":  # Target Identification
                if len(data) < 6:
                    return None, 0
                callsign = self._decode_callsign(data[:6])
                return {'callsign': callsign}, 6
            
            else:
                # For other items, return minimal data
                return {'raw_data': data[:min(8, len(data))].hex()}, min(8, len(data))
                
        except Exception as e:
            logger.error(f"Error parsing CAT-10 item {item_code}: {e}")
            return None, 0
    
    def _get_variable_length(self, data: bytes) -> int:
        """Get length of variable-length data item."""
        length = 0
        for i, byte in enumerate(data):
            length += 1
            if (byte & 0x01) == 0:  # FX bit not set
                break
            if i >= 10:  # Prevent infinite loop
                break
        return length
    
    def _decode_cat48_target_descriptor(self, data: bytes) -> Dict[str, Any]:
        """Decode CAT-48 Target Report Descriptor."""
        if len(data) < 1:
            return {}
        
        descriptor = data[0]
        typ = descriptor & 0x07
        
        return {
            'TYP': typ,
            'type_description': self.cat48_target_types.get(typ, 'Unknown'),
            'SIM': (descriptor >> 3) & 0x01,
            'RDP': (descriptor >> 4) & 0x01,
            'SPI': (descriptor >> 5) & 0x01,
            'RAB': (descriptor >> 6) & 0x01,
            'TST': (descriptor >> 7) & 0x01,
            'raw_value': descriptor
        }
    
    def _decode_warning_conditions(self, data: bytes) -> Dict[str, Any]:
        """Decode Warning/Error Conditions."""
        warnings = []
        warning_bits = 0
        
        for i, byte in enumerate(data):
            warning_bits |= (byte & 0xFE) << (i * 7)  # Exclude FX bit
            if (byte & 0x01) == 0:  # FX bit not set
                break
        
        # Check each warning bit
        warning_names = ['Garbled reply', 'Reflection', 'Sidelobe reply', 'Split plot',
                        'Second time around reply', 'Angels', 'Slow moving target']
        
        for bit in range(7):
            if warning_bits & (1 << bit):
                warnings.append(warning_names[bit] if bit < len(warning_names) else f"Warning {bit+1}")
        
        return {'warnings': warnings, 'raw_value': warning_bits}
    
    def _decode_track_status(self, data: bytes) -> Dict[str, Any]:
        """Decode Track Status."""
        if len(data) < 1:
            return {}
        
        status = {}
        byte = data[0]
        
        status['CNF'] = (byte >> 7) & 0x01  # Confirmed/Tentative
        status['TRE'] = (byte >> 6) & 0x01  # Track End
        status['CST'] = (byte >> 5) & 0x01  # Coast
        status['MAH'] = (byte >> 4) & 0x01  # Maneuver
        status['TCC'] = (byte >> 3) & 0x01  # CDTI/Raw mode
        status['STH'] = (byte >> 2) & 0x01  # Smoothed/Measured
        status['TOM'] = (byte >> 1) & 0x01  # Type of Movement
        
        return status
    
    def _decode_mode_3a(self, mode_3a_raw: int) -> str:
        """Decode Mode 3/A code to octal string."""
        code = mode_3a_raw & 0x0FFF
        return f"{code:04o}"
    
    def _decode_callsign(self, data: bytes) -> str:
        """Decode 6-bit encoded callsign."""
        charset = " ABCDEFGHIJKLMNOPQRSTUVWXYZ????? ???????????????0123456789??????"
        
        callsign = ""
        for i in range(0, len(data), 3):
            if i + 2 < len(data):
                val = struct.unpack('>I', b'\x00' + data[i:i+3])[0]
                callsign += charset[(val >> 18) & 0x3F]
                callsign += charset[(val >> 12) & 0x3F]
                callsign += charset[(val >> 6) & 0x3F]
                callsign += charset[val & 0x3F]
        
        return callsign.rstrip()
    
    def _apply_cat48_item_to_target(self, target: Dict[str, Any], item_code: str, item_data: Dict[str, Any]):
        """Apply CAT-48 parsed data item to target dictionary."""
        if item_code == "I048/020":
            target['detection_type'] = item_data.get('type_description', 'Unknown')
        elif item_code == "I048/030":
            target['warning_conditions'] = item_data.get('warnings', [])
        elif item_code == "I048/040":
            target['range'] = item_data.get('range')
            target['azimuth'] = item_data.get('azimuth')
            if target['range'] and target['azimuth']:
                lat, lon = self._convert_polar_to_latlon(target['range'], target['azimuth'])
                target['latitude'] = lat
                target['longitude'] = lon
        elif item_code == "I048/070":
            target['mode_3a'] = item_data.get('mode_3a')
        elif item_code == "I048/090":
            target['flight_level'] = item_data.get('flight_level')
        elif item_code == "I048/120":
            target['radial_doppler_speed'] = item_data.get('radial_doppler_speed')
        elif item_code == "I048/140":
            target['time_of_day'] = item_data.get('time_of_day')
        elif item_code == "I048/161":
            target['track_number'] = item_data.get('track_number')
        elif item_code == "I048/200":
            target['ground_speed'] = item_data.get('ground_speed')
            target['heading'] = item_data.get('heading')
        elif item_code == "I048/220":
            target['aircraft_address'] = item_data.get('aircraft_address')
        elif item_code == "I048/240":
            target['callsign'] = item_data.get('callsign')
    
    def _apply_cat21_item_to_target(self, target: Dict[str, Any], item_code: str, item_data: Dict[str, Any]):
        """Apply CAT-21 parsed data item to target dictionary."""
        if item_code == "I021/040":
            target['latitude'] = item_data.get('latitude')
            target['longitude'] = item_data.get('longitude')
        elif item_code == "I021/080":
            target['aircraft_address'] = item_data.get('aircraft_address')
        elif item_code == "I021/145":
            target['flight_level'] = item_data.get('flight_level')
        elif item_code == "I021/170":
            target['callsign'] = item_data.get('callsign')
    
    def _apply_cat10_item_to_target(self, target: Dict[str, Any], item_code: str, item_data: Dict[str, Any]):
        """Apply CAT-10 parsed data item to target dictionary."""
        if item_code == "I010/040":
            target['range'] = item_data.get('range')
            target['azimuth'] = item_data.get('azimuth')
            if target['range'] and target['azimuth']:
                lat, lon = self._convert_polar_to_latlon(target['range'], target['azimuth'])
                target['latitude'] = lat
                target['longitude'] = lon
        elif item_code == "I010/220":
            target['aircraft_address'] = item_data.get('aircraft_address')
        elif item_code == "I010/245":
            target['callsign'] = item_data.get('callsign')
    
    def _convert_polar_to_latlon(self, range_nm: float, azimuth_deg: float, 
                                 radar_lat: float = 28.0836, radar_lon: float = -80.6081) -> Tuple[float, float]:
        """Convert polar coordinates to latitude/longitude."""
        # Convert to radians
        azimuth_rad = math.radians(azimuth_deg)
        
        # Earth radius in nautical miles
        earth_radius_nm = 3443.92
        
        # Calculate delta lat/lon
        delta_lat = (range_nm / earth_radius_nm) * math.cos(azimuth_rad)
        delta_lon = (range_nm / earth_radius_nm) * math.sin(azimuth_rad) / math.cos(math.radians(radar_lat))
        
        # Convert to degrees
        delta_lat_deg = math.degrees(delta_lat)
        delta_lon_deg = math.degrees(delta_lon)
        
        # Calculate final position
        lat = radar_lat + delta_lat_deg
        lon = radar_lon + delta_lon_deg
        
        return lat, lon
    
    def _generate_track_id(self, target: Dict[str, Any], category: int) -> str:
        """Generate a unique track ID for the target."""
        prefix = f"CAT{category:02d}"
        
        # Try aircraft address first
        if target.get('aircraft_address'):
            return f"{prefix}_{target['aircraft_address']}"
        
        # Try Mode 3A code
        if target.get('mode_3a'):
            return f"{prefix}_3A_{target['mode_3a']}"
        
        # Try track number
        if target.get('track_number'):
            return f"{prefix}_TN_{target['track_number']}"
        
        # Use position-based ID
        if target.get('range') and target.get('azimuth'):
            return f"{prefix}_{int(target['range']*10):04d}_{int(target['azimuth']*10):04d}"
        
        # Fallback to hash-based ID
        return f"{prefix}_{hash(str(target)) % 100000:05d}"
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return self.processing_stats.copy()
    
    def reset_statistics(self):
        """Reset processing statistics."""
        self.processing_stats = {
            'total_messages': 0,
            'messages_by_category': {},
            'processing_errors': 0,
            'last_processing_time': None
        }
    
    def create_cat48_message(self, targets: List[Dict[str, Any]]) -> bytes:
        """Create a CAT-48 message from target data."""
        return self._create_asterix_message(targets, 48)
    
    def create_cat21_message(self, targets: List[Dict[str, Any]]) -> bytes:
        """Create a CAT-21 message from target data."""
        return self._create_asterix_message(targets, 21)
    
    def create_cat10_message(self, targets: List[Dict[str, Any]]) -> bytes:
        """Create a CAT-10 message from target data."""
        return self._create_asterix_message(targets, 10)
    
    def _create_asterix_message(self, targets: List[Dict[str, Any]], category: int) -> bytes:
        """Create an ASTERIX message for the specified category."""
        message = bytearray()
        
        # Category
        message.append(category)
        
        # Length placeholder
        length_pos = len(message)
        message.extend([0, 0])
        
        # Simple target encoding (basic implementation)
        for target in targets:
            # Basic FSPEC (simplified)
            if category == 48:
                message.append(0xE0)  # First octet
                message.append(0x00)  # Second octet with FX=0
                
                # Data Source Identifier (I048/010)
                message.extend([0x01, 0x02])
                
                # Target Report Descriptor (I048/020)
                message.append(0x02)  # Single SSR detection
                
                # Measured Position in Polar Coordinates (I048/040)
                if target.get('range') and target.get('azimuth'):
                    rho = int(target['range'] * 256)
                    theta = int(target['azimuth'] * 65536 / 360)
                    message.extend(struct.pack('>HH', rho, theta))
            
            elif category == 21:
                # Basic CAT-21 encoding
                message.append(0xC0)  # First octet
                message.append(0x00)  # Second octet with FX=0
                
                # Data Source Identifier (I021/010)
                message.extend([0x01, 0x02])
                
                # Target Position in WGS-84 (I021/040)
                if target.get('latitude') and target.get('longitude'):
                    lat = int(abs(target['latitude']) * (2**23) / 180.0)
                    lon = int(abs(target['longitude']) * (2**23) / 180.0)
                    # Pack as 3 bytes each
                    lat_bytes = struct.pack('>I', lat)[1:]  # 3 bytes
                    lon_bytes = struct.pack('>I', lon)[1:]  # 3 bytes
                    message.extend(lat_bytes + lon_bytes)
            
            elif category == 10:
                # Basic CAT-10 encoding
                message.append(0xA0)  # First octet
                message.append(0x00)  # Second octet with FX=0
                
                # Data Source Identifier (I010/010)
                message.extend([0x01, 0x02])
                
                # Measured Position in Polar Coordinates (I010/040)
                if target.get('range') and target.get('azimuth'):
                    rho = int(target['range'] * 256)
                    theta = int(target['azimuth'] * 65536 / 360)
                    message.extend(struct.pack('>HH', rho, theta))
        
        # Update length
        total_length = len(message)
        struct.pack_into('>H', message, length_pos, total_length)
        
        return bytes(message)
    
    def get_message_statistics(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics from processed messages."""
        if not messages:
            return {}
        
        stats = {
            'total_messages': len(messages),
            'categories': {},
            'unique_addresses': len(set(msg.get('aircraft_address', '') for msg in messages if msg.get('aircraft_address'))),
            'detection_types': {},
            'warning_conditions': {},
            'altitude_range': {'min': float('inf'), 'max': float('-inf')},
            'range_stats': {'min': float('inf'), 'max': float('-inf')},
            'callsigns': set(),
            'track_numbers': set()
        }
        
        for msg in messages:
            # Category statistics
            category = msg.get('category', 'Unknown')
            stats['categories'][category] = stats['categories'].get(category, 0) + 1
            
            # Detection type statistics
            det_type = msg.get('detection_type', 'Unknown')
            stats['detection_types'][det_type] = stats['detection_types'].get(det_type, 0) + 1
            
            # Warning conditions
            for warning in msg.get('warning_conditions', []):
                stats['warning_conditions'][warning] = stats['warning_conditions'].get(warning, 0) + 1
            
            # Altitude statistics
            if msg.get('altitude'):
                alt = msg['altitude']
                stats['altitude_range']['min'] = min(stats['altitude_range']['min'], alt)
                stats['altitude_range']['max'] = max(stats['altitude_range']['max'], alt)
            
            # Range statistics
            if msg.get('range'):
                rng = msg['range']
                stats['range_stats']['min'] = min(stats['range_stats']['min'], rng)
                stats['range_stats']['max'] = max(stats['range_stats']['max'], rng)
            
            # Callsigns
            if msg.get('callsign'):
                stats['callsigns'].add(msg['callsign'])
            
            # Track numbers
            if msg.get('track_number'):
                stats['track_numbers'].add(msg['track_number'])
        
        # Convert sets to lists for JSON serialization
        stats['callsigns'] = list(stats['callsigns'])
        stats['track_numbers'] = list(stats['track_numbers'])
        
        return stats
