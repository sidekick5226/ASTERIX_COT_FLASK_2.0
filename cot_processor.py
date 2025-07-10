"""
CoT (Cursor-on-Target) to Track Data Processor
Converts ASTERIX CAT048 data to CoT XML format and vice versa for advanced 3D visualization.
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid
import json


class CoTProcessor:
    """
    Processes CoT XML messages and converts track data to/from CoT format.
    Handles real-time position updates for advanced Cesium 3D visualization.
    """
    
    def __init__(self):
        self.active_tracks = {}
        self.cot_namespace = {
            'event': 'http://schemas.cot.org/2.0/cot',
            'detail': 'http://schemas.cot.org/2.0/detail'
        }
    
    def track_to_cot_xml(self, track: Dict[str, Any]) -> str:
        """
        Convert surveillance track to CoT XML format.
        
        Args:
            track: Track dictionary with position and metadata
            
        Returns:
            CoT XML string ready for WebSocket broadcast
        """
        # Generate unique CoT event ID
        uid = f"TRACK-{track.get('track_id', 'UNKNOWN')}"
        
        # Determine CoT type based on track type
        cot_type = self._get_cot_type(track.get('type', 'Unknown'))
        
        # Current time for CoT event
        now = datetime.now(timezone.utc)
        time_str = now.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        stale_time = (now.timestamp() + 300) * 1000  # 5 minutes from now
        
        # Create CoT event XML
        event = ET.Element('event')
        event.set('version', '2.0')
        event.set('uid', uid)
        event.set('type', cot_type)
        event.set('how', 'm-g')  # Machine generated
        event.set('time', time_str)
        event.set('start', time_str)
        event.set('stale', datetime.fromtimestamp(stale_time / 1000, timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        
        # Point element with coordinates
        point = ET.SubElement(event, 'point')
        point.set('lat', str(track.get('latitude', 0.0)))
        point.set('lon', str(track.get('longitude', 0.0)))
        point.set('hae', str(track.get('altitude', 0.0)))
        point.set('ce', '10.0')  # Circular error
        point.set('le', '5.0')   # Linear error
        
        # Detail element with track-specific information
        detail = ET.SubElement(event, 'detail')
        
        # Track details
        track_detail = ET.SubElement(detail, 'track')
        track_detail.set('callsign', track.get('callsign', track.get('track_id', 'UNKNOWN')))
        track_detail.set('course', str(track.get('heading', 0.0)))
        track_detail.set('speed', str(track.get('speed', 0.0)))
        
        # Contact information
        contact = ET.SubElement(detail, 'contact')
        contact.set('callsign', track.get('callsign', track.get('track_id', 'UNKNOWN')))
        
        # Tactical information for 3D rendering
        tactical = ET.SubElement(detail, 'tactical')
        tactical.set('type', track.get('type', 'Unknown'))
        tactical.set('status', track.get('status', 'Active'))
        
        # Remarks for additional information
        remarks = ET.SubElement(detail, 'remarks')
        remarks.text = f"Track {track.get('track_id')} - {track.get('type', 'Unknown')} unit"
        
        return ET.tostring(event, encoding='unicode')
    
    def cot_xml_to_track(self, cot_xml: str) -> Optional[Dict[str, Any]]:
        """
        Parse CoT XML and extract track data.
        
        Args:
            cot_xml: CoT XML string
            
        Returns:
            Track dictionary or None if parsing fails
        """
        try:
            root = ET.fromstring(cot_xml)
            
            # Extract basic event information
            uid = root.get('uid', '')
            cot_type = root.get('type', '')
            
            # Extract track ID from UID
            track_id = uid.replace('TRACK-', '') if uid.startswith('TRACK-') else uid
            
            # Extract position from point element
            point = root.find('point')
            if point is None:
                return None
                
            latitude = float(point.get('lat', 0.0))
            longitude = float(point.get('lon', 0.0))
            altitude = float(point.get('hae', 0.0))
            
            # Extract details
            detail = root.find('detail')
            track_info = {}
            
            if detail is not None:
                # Track details
                track_elem = detail.find('track')
                if track_elem is not None:
                    track_info['callsign'] = track_elem.get('callsign', track_id)
                    track_info['heading'] = float(track_elem.get('course', 0.0))
                    track_info['speed'] = float(track_elem.get('speed', 0.0))
                
                # Tactical information
                tactical = detail.find('tactical')
                if tactical is not None:
                    track_info['type'] = tactical.get('type', 'Unknown')
                    track_info['status'] = tactical.get('status', 'Active')
            
            # Create track dictionary
            track = {
                'track_id': track_id,
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude,
                'callsign': track_info.get('callsign', track_id),
                'type': track_info.get('type', self._cot_type_to_track_type(cot_type)),
                'heading': track_info.get('heading', 0.0),
                'speed': track_info.get('speed', 0.0),
                'status': track_info.get('status', 'Active'),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            return track
            
        except Exception as e:
            print(f"Error parsing CoT XML: {e}")
            return None
    
    def _get_cot_type(self, track_type: str) -> str:
        """
        Map track type to CoT type code.
        
        Args:
            track_type: Track type (Aircraft, Vessel, Vehicle, etc.)
            
        Returns:
            CoT type code string
        """
        type_mapping = {
            'Aircraft': 'a-f-A',      # Air - Fixed wing - Aircraft
            'Vessel': 's-v-N',        # Surface - Vessel - Naval
            'Vehicle': 'a-f-G-U-C',   # Ground - Unit - Combat
            'Unknown': 'a-u-G'        # Unknown - Ground
        }
        
        return type_mapping.get(track_type, 'a-u-G')
    
    def _cot_type_to_track_type(self, cot_type: str) -> str:
        """
        Map CoT type code to track type.
        
        Args:
            cot_type: CoT type code
            
        Returns:
            Track type string
        """
        if cot_type.startswith('a-f-A'):
            return 'Aircraft'
        elif cot_type.startswith('s-v'):
            return 'Vessel'
        elif cot_type.startswith('a-f-G') or cot_type.startswith('a-n-G'):
            return 'Vehicle'
        else:
            return 'Unknown'
    
    def batch_tracks_to_cot(self, tracks: List[Dict[str, Any]]) -> str:
        """
        Convert multiple tracks to CoT XML batch message.
        
        Args:
            tracks: List of track dictionaries
            
        Returns:
            CoT XML string containing all tracks
        """
        # Create root event for batch update
        root = ET.Element('events')
        root.set('version', '2.0')
        root.set('batch', 'true')
        
        for track in tracks:
            # Parse individual track CoT XML and append to batch
            track_cot = self.track_to_cot_xml(track)
            track_element = ET.fromstring(track_cot)
            root.append(track_element)
        
        return ET.tostring(root, encoding='unicode')
    
    def create_heartbeat_message(self) -> str:
        """
        Create CoT heartbeat message for connection health.
        
        Returns:
            CoT heartbeat XML string
        """
        uid = f"HEARTBEAT-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        time_str = now.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        event = ET.Element('event')
        event.set('version', '2.0')
        event.set('uid', uid)
        event.set('type', 't-x-c-h')  # Heartbeat type
        event.set('how', 'h-e')
        event.set('time', time_str)
        event.set('start', time_str)
        event.set('stale', time_str)
        
        point = ET.SubElement(event, 'point')
        point.set('lat', '0.0')
        point.set('lon', '0.0')
        point.set('hae', '0.0')
        point.set('ce', '999999.0')
        point.set('le', '999999.0')
        
        detail = ET.SubElement(event, 'detail')
        
        return ET.tostring(event, encoding='unicode')
    
    def validate_cot_xml(self, cot_xml: str) -> bool:
        """
        Validate CoT XML format and structure.
        
        Args:
            cot_xml: CoT XML string to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            root = ET.fromstring(cot_xml)
            
            # Check required attributes
            required_attrs = ['version', 'uid', 'type', 'time']
            for attr in required_attrs:
                if attr not in root.attrib:
                    return False
            
            # Check for point element
            point = root.find('point')
            if point is None:
                return False
            
            # Validate coordinate values
            try:
                float(point.get('lat', '0'))
                float(point.get('lon', '0'))
                float(point.get('hae', '0'))
            except ValueError:
                return False
            
            return True
            
        except ET.ParseError:
            return False
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about CoT processing.
        
        Returns:
            Dictionary containing processing statistics
        """
        return {
            'active_tracks': len(self.active_tracks),
            'supported_formats': ['CoT XML', 'ASTERIX CAT048'],
            'cot_types_supported': [
                'a-f-A (Aircraft)',
                's-v-N (Naval Vessel)', 
                'a-f-G-U-C (Ground Vehicle)',
                'a-u-G (Unknown)'
            ],
            'features': [
                'Real-time position updates',
                'WebSocket broadcasting',
                'glTF model positioning',
                'Camera follow modes'
            ]
        }


# Example usage and testing
if __name__ == "__main__":
    processor = CoTProcessor()
    
    # Example track data
    sample_track = {
        'track_id': 'TRK001',
        'callsign': 'HAWK01',
        'type': 'Aircraft',
        'latitude': 40.7128,
        'longitude': -74.0060,
        'altitude': 10000,
        'heading': 270.0,
        'speed': 250.0,
        'status': 'Active'
    }
    
    # Convert to CoT XML
    cot_xml = processor.track_to_cot_xml(sample_track)
    print("Generated CoT XML:")
    print(cot_xml)
    
    # Parse back to track
    parsed_track = processor.cot_xml_to_track(cot_xml)
    print("\nParsed track data:")
    print(json.dumps(parsed_track, indent=2))
    
    # Validation
    is_valid = processor.validate_cot_xml(cot_xml)
    print(f"\nCoT XML validation: {'Valid' if is_valid else 'Invalid'}")