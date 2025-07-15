"""
CoT (Cursor-on-Target) XML Converter
Converts surveillance track data to CoT XML format for military and emergency response systems.
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import uuid

class CoTConverter:
    """
    Converts track data to Cursor-on-Target (CoT) XML format.
    CoT is used for sharing situational awareness information in military and emergency response.
    """
    
    def __init__(self):
        self.cot_types = {
            'Aircraft': 'a-f-A',  # Air - Fixed Wing - Aircraft
            'Helicopter': 'a-f-H',  # Air - Fixed Wing - Helicopter  
            'Vessel': 'a-n-S',  # Air - Neutral - Sea Surface
            'Vehicle': 'a-f-G',  # Air - Fixed Wing - Ground
            'Person': 'a-f-G-I',  # Air - Fixed Wing - Ground - Infantry
            'Unknown': 'a-u-G'  # Air - Unknown - Ground
        }
        
        self.affiliation_codes = {
            'Friendly': 'f',
            'Hostile': 'h', 
            'Neutral': 'n',
            'Unknown': 'u'
        }
        
        self.dimension_codes = {
            'Air': 'A',
            'Ground': 'G',
            'Sea': 'S',
            'Subsurface': 'U'
        }
    
    def convert_track_to_cot(self, track: Dict[str, Any], affiliation: str = 'Unknown') -> str:
        """
        Convert a single track to CoT XML format.
        
        Args:
            track: Track dictionary containing position and metadata
            affiliation: Military affiliation (Friendly, Hostile, Neutral, Unknown)
            
        Returns:
            CoT XML string
        """
        try:
            # Create root event element
            event = ET.Element('event')
            
            # Set event attributes
            event.set('version', '2.0')
            event.set('uid', self._generate_uid(track))
            event.set('type', self._get_cot_type(track, affiliation))
            event.set('time', self._format_cot_time(datetime.utcnow()))
            event.set('start', self._format_cot_time(datetime.utcnow()))
            event.set('stale', self._format_cot_time(datetime.utcnow() + timedelta(minutes=5)))
            event.set('how', 'm-g')  # Machine - Generated
            
            # Add point element with coordinates
            point = ET.SubElement(event, 'point')
            point.set('lat', str(track['latitude']))
            point.set('lon', str(track['longitude']))
            point.set('hae', str(track.get('altitude', 0)))
            point.set('ce', '10')  # Circular Error (meters)
            point.set('le', '15')  # Linear Error (meters)
            
            # Add detail element
            detail = ET.SubElement(event, 'detail')
            
            # Add track information
            track_elem = ET.SubElement(detail, 'track')
            track_elem.set('course', str(track.get('heading', 0)))
            track_elem.set('speed', str(track.get('speed', 0)))
            
            # Add contact information
            contact = ET.SubElement(detail, 'contact')
            contact.set('callsign', track.get('callsign', track['track_id']))
            
            # Add remarks
            remarks = ET.SubElement(detail, 'remarks')
            remarks.text = f"Track {track['track_id']} - {track['type']} - Status: {track['status']}"
            
            # Add link information
            link = ET.SubElement(detail, 'link')
            link.set('uid', track['track_id'])
            link.set('type', 'a-f-G-U-C')  # Generic unit
            link.set('relation', 'p-p')  # Parent-child
            
            # Add precision location
            precisionlocation = ET.SubElement(detail, 'precisionlocation')
            precisionlocation.set('altsrc', 'DTED0')
            precisionlocation.set('geopointsrc', 'GPS')
            
            # Convert to string
            xml_str = ET.tostring(event, encoding='unicode')
            
            # Add XML declaration
            return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'
            
        except Exception as e:
            return ""
    
    def convert_multiple_tracks_to_cot(self, tracks: List[Dict[str, Any]], 
                                     affiliation: str = 'Unknown') -> str:
        """
        Convert multiple tracks to a CoT XML event collection.
        
        Args:
            tracks: List of track dictionaries
            affiliation: Military affiliation for all tracks
            
        Returns:
            CoT XML string containing all tracks
        """
        try:
            # Create root events element
            events = ET.Element('events')
            events.set('version', '2.0')
            
            for track in tracks:
                # Parse individual CoT XML
                track_xml = self.convert_track_to_cot(track, affiliation)
                if track_xml:
                    # Remove XML declaration and add to events
                    clean_xml = track_xml.split('\n', 1)[1] if '<?xml' in track_xml else track_xml
                    event_element = ET.fromstring(clean_xml)
                    events.append(event_element)
            
            # Convert to string
            xml_str = ET.tostring(events, encoding='unicode')
            
            # Add XML declaration
            return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'
            
        except Exception as e:
            return ""
    
    def _generate_uid(self, track: Dict[str, Any]) -> str:
        """
        Generate unique identifier for CoT event.
        
        Args:
            track: Track dictionary
            
        Returns:
            Unique identifier string
        """
        return f"SURV-{track['track_id']}-{int(datetime.utcnow().timestamp())}"
    
    def _get_cot_type(self, track: Dict[str, Any], affiliation: str = 'Unknown') -> str:
        """
        Determine CoT type code based on track type and affiliation.
        
        Args:
            track: Track dictionary
            affiliation: Military affiliation
            
        Returns:
            CoT type code string
        """
        base_type = self.cot_types.get(track['type'], 'a-u-G')
        affiliation_code = self.affiliation_codes.get(affiliation, 'u')
        
        # Replace affiliation code in type
        parts = base_type.split('-')
        if len(parts) >= 2:
            parts[1] = affiliation_code
            return '-'.join(parts)
        
        return base_type
    
    def _format_cot_time(self, dt: datetime) -> str:
        """
        Format datetime for CoT XML.
        
        Args:
            dt: Datetime object
            
        Returns:
            ISO formatted time string for CoT
        """
        return dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    
    def parse_cot_xml(self, cot_xml: str) -> List[Dict[str, Any]]:
        """
        Parse CoT XML back to track data.
        
        Args:
            cot_xml: CoT XML string
            
        Returns:
            List of track dictionaries
        """
        try:
            tracks = []
            
            # Parse XML
            if cot_xml.startswith('<?xml'):
                # Remove XML declaration for parsing
                cot_xml = cot_xml.split('\n', 1)[1]
            
            root = ET.fromstring(cot_xml)
            
            # Handle single event or multiple events
            if root.tag == 'event':
                events = [root]
            elif root.tag == 'events':
                events = root.findall('event')
            else:
                return tracks
            
            for event in events:
                track = self._parse_cot_event(event)
                if track:
                    tracks.append(track)
            
            return tracks
            
        except Exception as e:
            return []
    
    def _parse_cot_event(self, event: ET.Element) -> Optional[Dict[str, Any]]:
        """
        Parse individual CoT event element to track data.
        
        Args:
            event: XML event element
            
        Returns:
            Track dictionary or None
        """
        try:
            # Extract basic event attributes
            uid = event.get('uid', '')
            cot_type = event.get('type', '')
            
            # Extract position from point element
            point = event.find('point')
            if point is None:
                return None
            
            latitude = float(point.get('lat', 0))
            longitude = float(point.get('lon', 0))
            altitude = float(point.get('hae', 0))
            
            # Extract detail information
            detail = event.find('detail')
            
            # Initialize track data
            track = {
                'track_id': uid.split('-')[1] if '-' in uid else uid,
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude if altitude > 0 else None,
                'type': self._determine_track_type_from_cot(cot_type),
                'status': 'Active',
                'source': 'CoT',
                'cot_uid': uid,
                'cot_type': cot_type
            }
            
            if detail is not None:
                # Extract track information
                track_elem = detail.find('track')
                if track_elem is not None:
                    track['heading'] = float(track_elem.get('course', 0))
                    track['speed'] = float(track_elem.get('speed', 0))
                
                # Extract contact information
                contact = detail.find('contact')
                if contact is not None:
                    track['callsign'] = contact.get('callsign', track['track_id'])
                
                # Extract remarks
                remarks = detail.find('remarks')
                if remarks is not None and remarks.text:
                    track['remarks'] = remarks.text
            
            return track
            
        except Exception as e:
            return None
    
    def _determine_track_type_from_cot(self, cot_type: str) -> str:
        """
        Determine track type from CoT type code.
        
        Args:
            cot_type: CoT type code
            
        Returns:
            Track type string
        """
        # Simple mapping based on CoT type patterns
        if 'A' in cot_type:  # Air
            if 'H' in cot_type:
                return 'Helicopter'
            else:
                return 'Aircraft'
        elif 'S' in cot_type:  # Sea
            return 'Vessel'
        elif 'G' in cot_type:  # Ground
            return 'Vehicle'
        else:
            return 'Unknown'
    
    def create_cot_chat_message(self, sender: str, message: str, 
                               recipients: Optional[List[str]] = None) -> str:
        """
        Create CoT chat message XML.
        
        Args:
            sender: Message sender identifier
            message: Message text
            recipients: List of recipient identifiers (None for broadcast)
            
        Returns:
            CoT chat message XML string
        """
        try:
            # Create root event element
            event = ET.Element('event')
            
            # Set event attributes for chat
            event.set('version', '2.0')
            event.set('uid', f"GeoChat.{sender}.{uuid.uuid4()}")
            event.set('type', 'b-t-f')  # Bit - Text - Chat
            event.set('time', self._format_cot_time(datetime.utcnow()))
            event.set('start', self._format_cot_time(datetime.utcnow()))
            event.set('stale', self._format_cot_time(datetime.utcnow() + timedelta(hours=1)))
            event.set('how', 'h-g-i-g-o')  # Human generated
            
            # Add point element (sender location or default)
            point = ET.SubElement(event, 'point')
            point.set('lat', '0.0')
            point.set('lon', '0.0')
            point.set('hae', '0.0')
            point.set('ce', '9999999')
            point.set('le', '9999999')
            
            # Add detail element
            detail = ET.SubElement(event, 'detail')
            
            # Add __chat element
            chat = ET.SubElement(detail, '__chat')
            chat.set('chatroom', 'All Chat Rooms' if not recipients else 'Direct')
            chat.set('id', str(uuid.uuid4()))
            chat.set('senderCallsign', sender)
            
            # Add chatgrp element
            chatgrp = ET.SubElement(chat, 'chatgrp')
            chatgrp.set('uid0', sender)
            
            if recipients:
                for i, recipient in enumerate(recipients, 1):
                    chatgrp.set(f'uid{i}', recipient)
            else:
                chatgrp.set('uid1', 'All Chat Rooms')
            
            # Add message text
            remarks = ET.SubElement(detail, 'remarks')
            remarks.text = message
            
            # Convert to string
            xml_str = ET.tostring(event, encoding='unicode')
            
            # Add XML declaration
            return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'
            
        except Exception as e:
            return ""
    
    def get_supported_cot_types(self) -> Dict[str, str]:
        """
        Get dictionary of supported CoT types.
        
        Returns:
            Dictionary mapping track types to CoT type codes
        """
        return self.cot_types.copy()
    
    def validate_cot_xml(self, cot_xml: str) -> bool:
        """
        Validate CoT XML format.
        
        Args:
            cot_xml: CoT XML string to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Basic XML parsing validation
            if cot_xml.startswith('<?xml'):
                cot_xml = cot_xml.split('\n', 1)[1]
            
            root = ET.fromstring(cot_xml)
            
            # Check if it's a valid CoT structure
            if root.tag not in ['event', 'events']:
                return False
            
            # For single event, check required elements
            if root.tag == 'event':
                point = root.find('point')
                if point is None:
                    return False
                
                # Check required attributes
                required_attrs = ['lat', 'lon']
                for attr in required_attrs:
                    if point.get(attr) is None:
                        return False
            
            return True
            
        except Exception:
            return False
