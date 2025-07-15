"""
ADSB to CoT (Cursor-on-Target) Converter
Specialized converter for ADSB aircraft data to CoT XML format for military and emergency response systems.
Handles ADSB-specific data fields and aviation-specific CoT types.
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid
import math
import json

class ADSBCoTConverter:
    """
    Converts ADSB aircraft data to Cursor-on-Target (CoT) XML format.
    Specialized for aviation surveillance with proper ADSB field handling.
    """
    
    def __init__(self):
        # ADSB-specific CoT types for aircraft
        self.adsb_cot_types = {
            'A0': 'a-f-A-C-F',      # Fixed Wing - Commercial - Fighter
            'A1': 'a-f-A-C-L',      # Fixed Wing - Commercial - Light
            'A2': 'a-f-A-C-M',      # Fixed Wing - Commercial - Medium
            'A3': 'a-f-A-C-H',      # Fixed Wing - Commercial - Heavy
            'A4': 'a-f-A-C-J',      # Fixed Wing - Commercial - Jet
            'A5': 'a-f-A-C-T',      # Fixed Wing - Commercial - Turboprop
            'A6': 'a-f-A-M',        # Fixed Wing - Military
            'A7': 'a-f-A-M-F',      # Fixed Wing - Military - Fighter
            'B0': 'a-f-H',          # Helicopter
            'B1': 'a-f-H-C',        # Helicopter - Commercial
            'B2': 'a-f-H-M',        # Helicopter - Military
            'B3': 'a-f-H-E',        # Helicopter - Emergency
            'B4': 'a-f-H-L',        # Helicopter - Law Enforcement
            'B5': 'a-f-H-S',        # Helicopter - Search and Rescue
            'B6': 'a-f-H-U',        # Helicopter - Utility
            'B7': 'a-f-H-N',        # Helicopter - News
            'C0': 'a-f-A-G',        # Glider
            'C1': 'a-f-A-B',        # Balloon
            'C2': 'a-f-A-D',        # Drone/UAV
            'C3': 'a-f-A-U',        # Ultralight
            'C4': 'a-f-A-S',        # Spacecraft
            'C5': 'a-f-A-P',        # Parachute
            'C6': 'a-f-A-O',        # Other
            'default': 'a-f-A'      # Generic aircraft
        }
        
        # ADSB emergency codes
        self.emergency_codes = {
            '7500': 'HIJACK',
            '7600': 'RADIO_FAILURE', 
            '7700': 'GENERAL_EMERGENCY',
            '7777': 'MILITARY_INTERCEPT'
        }
        
        # Flight status codes
        self.flight_status = {
            0: 'NO_INFO',
            1: 'GROUND',
            2: 'AIRBORNE',
            3: 'ALERT',
            4: 'SPI',
            5: 'RESERVED'
        }
        
        # Wake turbulence categories
        self.wake_categories = {
            0: 'UNKNOWN',
            1: 'LIGHT',
            2: 'SMALL',
            3: 'LARGE',
            4: 'HIGH_VORTEX',
            5: 'HEAVY',
            6: 'HIGHLY_MANEUVERABLE',
            7: 'ROTORCRAFT'
        }
    
    def convert_adsb_to_cot(self, adsb_data: Dict[str, Any], affiliation: str = 'Unknown') -> str:
        """
        Convert ADSB aircraft data to CoT XML format.
        
        Args:
            adsb_data: ADSB message dictionary
            affiliation: Military affiliation (Friendly, Hostile, Neutral, Unknown)
            
        Returns:
            CoT XML string
        """
        try:
            # Create root event element
            event = ET.Element('event')
            
            # Set event attributes
            event.set('version', '2.0')
            event.set('uid', self._generate_adsb_uid(adsb_data))
            event.set('type', self._get_adsb_cot_type(adsb_data, affiliation))
            event.set('time', self._format_cot_time(datetime.utcnow()))
            event.set('start', self._format_cot_time(datetime.utcnow()))
            event.set('stale', self._format_cot_time(datetime.utcnow() + timedelta(minutes=2)))  # ADSB updates frequently
            event.set('how', 'm-g-adsb')  # Machine - Generated - ADSB
            
            # Add point element with coordinates
            point = ET.SubElement(event, 'point')
            point.set('lat', str(adsb_data.get('latitude', 0)))
            point.set('lon', str(adsb_data.get('longitude', 0)))
            point.set('hae', str(adsb_data.get('altitude', 0)))
            point.set('ce', str(adsb_data.get('horizontal_accuracy', 25)))  # ADSB accuracy
            point.set('le', str(adsb_data.get('vertical_accuracy', 50)))
            
            # Add detail element
            detail = ET.SubElement(event, 'detail')
            
            # Add ADSB-specific track information
            track_elem = ET.SubElement(detail, 'track')
            track_elem.set('course', str(adsb_data.get('heading', 0)))
            track_elem.set('speed', str(adsb_data.get('ground_speed', 0)))
            
            # Add vertical rate if available
            if 'vertical_rate' in adsb_data:
                track_elem.set('climb', str(adsb_data['vertical_rate']))
            
            # Add contact information
            contact = ET.SubElement(detail, 'contact')
            contact.set('callsign', adsb_data.get('callsign', adsb_data.get('icao24', 'UNKNOWN')))
            
            # Add ADSB-specific details
            adsb_detail = ET.SubElement(detail, 'adsb')
            
            # ICAO 24-bit address
            if 'icao24' in adsb_data:
                adsb_detail.set('icao24', adsb_data['icao24'])
            
            # Squawk code
            if 'squawk' in adsb_data:
                adsb_detail.set('squawk', str(adsb_data['squawk']))
                # Check for emergency squawk codes
                if str(adsb_data['squawk']) in self.emergency_codes:
                    emergency = ET.SubElement(detail, 'emergency')
                    emergency.set('type', self.emergency_codes[str(adsb_data['squawk'])])
                    emergency.text = f"Emergency squawk: {adsb_data['squawk']}"
            
            # Flight status
            if 'flight_status' in adsb_data:
                status_code = adsb_data['flight_status']
                adsb_detail.set('flight_status', self.flight_status.get(status_code, 'UNKNOWN'))
            
            # Aircraft category
            if 'category' in adsb_data:
                adsb_detail.set('category', str(adsb_data['category']))
            
            # Wake turbulence category
            if 'wake_category' in adsb_data:
                wake_code = adsb_data['wake_category']
                adsb_detail.set('wake_turbulence', self.wake_categories.get(wake_code, 'UNKNOWN'))
            
            # Add aircraft information if available
            if any(key in adsb_data for key in ['aircraft_type', 'registration', 'operator']):
                aircraft = ET.SubElement(detail, 'aircraft')
                
                if 'aircraft_type' in adsb_data:
                    aircraft.set('type', adsb_data['aircraft_type'])
                
                if 'registration' in adsb_data:
                    aircraft.set('registration', adsb_data['registration'])
                
                if 'operator' in adsb_data:
                    aircraft.set('operator', adsb_data['operator'])
            
            # Add navigation information
            if any(key in adsb_data for key in ['nav_qnh', 'nav_altitude_mcp', 'nav_altitude_fms']):
                nav = ET.SubElement(detail, 'navigation')
                
                if 'nav_qnh' in adsb_data:
                    nav.set('qnh', str(adsb_data['nav_qnh']))
                
                if 'nav_altitude_mcp' in adsb_data:
                    nav.set('mcp_altitude', str(adsb_data['nav_altitude_mcp']))
                
                if 'nav_altitude_fms' in adsb_data:
                    nav.set('fms_altitude', str(adsb_data['nav_altitude_fms']))
            
            # Add sensor information
            sensor = ET.SubElement(detail, 'sensor')
            sensor.set('type', 'ADSB')
            sensor.set('range', str(adsb_data.get('range', 0)))
            sensor.set('azimuth', str(adsb_data.get('azimuth', 0)))
            
            if 'receiver_id' in adsb_data:
                sensor.set('receiver', adsb_data['receiver_id'])
            
            if 'rssi' in adsb_data:
                sensor.set('signal_strength', str(adsb_data['rssi']))
            
            # Add remarks with ADSB-specific information
            remarks = ET.SubElement(detail, 'remarks')
            remarks_text = f"ADSB Track {adsb_data.get('icao24', 'UNKNOWN')}"
            
            if 'callsign' in adsb_data:
                remarks_text += f" - {adsb_data['callsign']}"
            
            if 'squawk' in adsb_data:
                remarks_text += f" - Squawk: {adsb_data['squawk']}"
            
            if 'flight_status' in adsb_data:
                status = self.flight_status.get(adsb_data['flight_status'], 'UNKNOWN')
                remarks_text += f" - Status: {status}"
            
            remarks.text = remarks_text
            
            # Add link information
            link = ET.SubElement(detail, 'link')
            link.set('uid', adsb_data.get('icao24', 'UNKNOWN'))
            link.set('type', 'a-f-A')
            link.set('relation', 'p-p')
            
            # Add precision location with ADSB-specific source
            precisionlocation = ET.SubElement(detail, 'precisionlocation')
            precisionlocation.set('altsrc', 'BAROMETRIC')
            precisionlocation.set('geopointsrc', 'ADSB')
            
            # Convert to string
            return ET.tostring(event, encoding='unicode')
            
        except Exception as e:
            raise Exception(f"Error converting ADSB to CoT: {str(e)}")
    
    def convert_adsb_batch_to_cot(self, adsb_messages: List[Dict[str, Any]], 
                                 affiliation: str = 'Unknown') -> List[str]:
        """
        Convert multiple ADSB messages to CoT XML format.
        
        Args:
            adsb_messages: List of ADSB message dictionaries
            affiliation: Military affiliation
            
        Returns:
            List of CoT XML strings
        """
        cot_messages = []
        
        for adsb_data in adsb_messages:
            try:
                cot_xml = self.convert_adsb_to_cot(adsb_data, affiliation)
                cot_messages.append(cot_xml)
            except Exception as e:
                continue
        
        return cot_messages
    
    def _generate_adsb_uid(self, adsb_data: Dict[str, Any]) -> str:
        """Generate unique identifier for ADSB track."""
        icao24 = adsb_data.get('icao24', 'UNKNOWN')
        callsign = adsb_data.get('callsign', '')
        
        if callsign:
            return f"ADSB.{icao24}.{callsign}"
        else:
            return f"ADSB.{icao24}"
    
    def _get_adsb_cot_type(self, adsb_data: Dict[str, Any], affiliation: str) -> str:
        """
        Determine CoT type based on ADSB data.
        
        Args:
            adsb_data: ADSB message data
            affiliation: Military affiliation
            
        Returns:
            CoT type string
        """
        # Get affiliation code
        affiliation_code = 'u'  # Unknown default
        if affiliation.lower() == 'friendly':
            affiliation_code = 'f'
        elif affiliation.lower() == 'hostile':
            affiliation_code = 'h'
        elif affiliation.lower() == 'neutral':
            affiliation_code = 'n'
        
        # Determine aircraft type from category
        category = adsb_data.get('category', 'default')
        base_type = self.adsb_cot_types.get(category, self.adsb_cot_types['default'])
        
        # Replace affiliation in base type
        type_parts = base_type.split('-')
        if len(type_parts) >= 2:
            type_parts[1] = affiliation_code
            return '-'.join(type_parts)
        
        return base_type
    
    def _format_cot_time(self, dt: datetime) -> str:
        """Format datetime for CoT XML."""
        return dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    
    def create_adsb_filter_cot(self, filter_criteria: Dict[str, Any]) -> str:
        """
        Create a CoT message for ADSB filter criteria.
        Used to communicate filtering parameters to other systems.
        
        Args:
            filter_criteria: Dictionary containing filter parameters
            
        Returns:
            CoT XML string for filter
        """
        event = ET.Element('event')
        event.set('version', '2.0')
        event.set('uid', f"ADSB.FILTER.{uuid.uuid4()}")
        event.set('type', 'b-m-p-s-m')  # Battle - Management - Points - Sensors - Manager
        event.set('time', self._format_cot_time(datetime.utcnow()))
        event.set('start', self._format_cot_time(datetime.utcnow()))
        event.set('stale', self._format_cot_time(datetime.utcnow() + timedelta(hours=1)))
        event.set('how', 'm-g')
        
        # Add dummy point (filters don't have geographic location)
        point = ET.SubElement(event, 'point')
        point.set('lat', '0')
        point.set('lon', '0')
        point.set('hae', '0')
        point.set('ce', '0')
        point.set('le', '0')
        
        # Add detail with filter information
        detail = ET.SubElement(event, 'detail')
        
        adsb_filter = ET.SubElement(detail, 'adsb_filter')
        
        # Add filter criteria
        for key, value in filter_criteria.items():
            adsb_filter.set(key, str(value))
        
        remarks = ET.SubElement(detail, 'remarks')
        remarks.text = f"ADSB Filter Configuration: {json.dumps(filter_criteria)}"
        
        return ET.tostring(event, encoding='unicode')
    
    def validate_adsb_data(self, adsb_data: Dict[str, Any]) -> bool:
        """
        Validate ADSB data before conversion.
        
        Args:
            adsb_data: ADSB message data
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['latitude', 'longitude']
        
        # Check required fields
        for field in required_fields:
            if field not in adsb_data:
                return False
        
        # Validate coordinate ranges
        lat = adsb_data.get('latitude', 0)
        lon = adsb_data.get('longitude', 0)
        
        if not (-90 <= lat <= 90):
            return False
        
        if not (-180 <= lon <= 180):
            return False
        
        # Validate altitude if present
        if 'altitude' in adsb_data:
            alt = adsb_data['altitude']
            if not (-1000 <= alt <= 100000):  # Reasonable altitude range
                return False
        
        # Validate speed if present
        if 'ground_speed' in adsb_data:
            speed = adsb_data['ground_speed']
            if not (0 <= speed <= 1000):  # Reasonable speed range in knots
                return False
        
        return True
    
    def get_adsb_statistics(self, adsb_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate statistics from ADSB messages.
        
        Args:
            adsb_messages: List of ADSB messages
            
        Returns:
            Dictionary with statistics
        """
        if not adsb_messages:
            return {}
        
        stats = {
            'total_messages': len(adsb_messages),
            'unique_aircraft': len(set(msg.get('icao24', '') for msg in adsb_messages)),
            'aircraft_types': {},
            'altitude_range': {'min': float('inf'), 'max': float('-inf')},
            'speed_range': {'min': float('inf'), 'max': float('-inf')},
            'emergency_squawks': 0,
            'ground_aircraft': 0,
            'airborne_aircraft': 0
        }
        
        for msg in adsb_messages:
            # Count aircraft types
            category = msg.get('category', 'unknown')
            stats['aircraft_types'][category] = stats['aircraft_types'].get(category, 0) + 1
            
            # Track altitude range
            if 'altitude' in msg:
                alt = msg['altitude']
                stats['altitude_range']['min'] = min(stats['altitude_range']['min'], alt)
                stats['altitude_range']['max'] = max(stats['altitude_range']['max'], alt)
            
            # Track speed range
            if 'ground_speed' in msg:
                speed = msg['ground_speed']
                stats['speed_range']['min'] = min(stats['speed_range']['min'], speed)
                stats['speed_range']['max'] = max(stats['speed_range']['max'], speed)
            
            # Count emergency squawks
            if 'squawk' in msg and str(msg['squawk']) in self.emergency_codes:
                stats['emergency_squawks'] += 1
            
            # Count ground vs airborne
            if 'flight_status' in msg:
                if msg['flight_status'] == 1:  # Ground
                    stats['ground_aircraft'] += 1
                elif msg['flight_status'] == 2:  # Airborne
                    stats['airborne_aircraft'] += 1
        
        return stats
