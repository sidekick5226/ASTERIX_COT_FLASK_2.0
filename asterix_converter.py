"""
ASTERIX Multi-Category Converter
Central coordinator for all ASTERIX category processors.
Routes messages to appropriate category-specific processors and provides unified interface.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import struct

# Import consolidated processor
from asterix_cat48_consolidated import AsterixConsolidatedProcessor

class AsterixMultiCategoryConverter:
    """
    Central converter that handles multiple ASTERIX categories.
    Uses consolidated processor for categories 10, 21, and 48.
    """
    
    def __init__(self):
        # Use consolidated processor for all supported categories
        self.consolidated_processor = AsterixConsolidatedProcessor()
        
        # Keep processors dict for backward compatibility
        self.processors = {
            10: self.consolidated_processor,
            21: self.consolidated_processor,
            48: self.consolidated_processor
        }
        
        self.category_descriptions = {
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
        
        self.processing_stats = {
            'total_messages': 0,
            'messages_by_category': {},
            'processing_errors': 0,
            'last_processing_time': None
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
            
            # Extract category from first byte
            category = raw_data[0]
            
            # Update statistics
            self.processing_stats['total_messages'] += 1
            self.processing_stats['messages_by_category'][category] = \
                self.processing_stats['messages_by_category'].get(category, 0) + 1
            self.processing_stats['last_processing_time'] = datetime.utcnow().isoformat()
            
            # Route to consolidated processor
            if category in self.processors:
                processor = self.processors[category]
                return processor.process_asterix_message(raw_data)
            else:
                # Fallback processing for unsupported categories
                return self._process_generic_asterix(raw_data)
                
        except Exception as e:
            self.processing_stats['processing_errors'] += 1
            return []
    
    def _process_generic_asterix(self, raw_data: bytes) -> List[Dict[str, Any]]:
        """
        Generic processing for unsupported ASTERIX categories.
        
        Args:
            raw_data: Raw ASTERIX message bytes
            
        Returns:
            List with basic message information
        """
        try:
            category = raw_data[0]
            length = struct.unpack('>H', raw_data[1:3])[0]
            
            # Create basic message info
            message_info = {
                'category': category,
                'message_type': self.category_descriptions.get(category, 'Unknown Category'),
                'length': length,
                'timestamp': datetime.utcnow().isoformat(),
                'raw_data': raw_data.hex(),
                'processing_status': 'unsupported_category',
                'warning': f'Category {category} not fully supported - basic info only'
            }
            
            return [message_info]
            
        except Exception as e:
            return []
    
    def process_asterix_batch(self, messages: List[bytes]) -> List[Dict[str, Any]]:
        """
        Process multiple ASTERIX messages.
        
        Args:
            messages: List of raw ASTERIX message bytes
            
        Returns:
            List of all processed target reports
        """
        all_targets = []
        
        for message in messages:
            targets = self.process_asterix_message(message)
            all_targets.extend(targets)
        
        return all_targets
    
    def get_supported_categories(self) -> Dict[int, str]:
        """
        Get list of supported ASTERIX categories.
        
        Returns:
            Dictionary of category numbers to descriptions
        """
        return {cat: desc for cat, desc in self.category_descriptions.items() 
                if cat in self.processors}
    
    def get_all_categories(self) -> Dict[int, str]:
        """
        Get list of all known ASTERIX categories.
        
        Returns:
            Dictionary of all category numbers to descriptions
        """
        return self.category_descriptions.copy()
    
    def get_category_processor(self, category: int) -> Optional[object]:
        """
        Get processor for specific category.
        
        Args:
            category: ASTERIX category number
            
        Returns:
            Category processor or None if not supported
        """
        return self.processors.get(category)
    
    def validate_asterix_message(self, raw_data: bytes) -> Dict[str, Any]:
        """
        Validate ASTERIX message format.
        
        Args:
            raw_data: Raw ASTERIX message bytes
            
        Returns:
            Validation result dictionary
        """
        validation = {
            'is_valid': False,
            'category': None,
            'length': None,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Check minimum length
            if len(raw_data) < 3:
                validation['errors'].append('Message too short (minimum 3 bytes)')
                return validation
            
            # Extract header
            category = raw_data[0]
            length = struct.unpack('>H', raw_data[1:3])[0]
            
            validation['category'] = category
            validation['length'] = length
            
            # Validate category
            if category not in self.category_descriptions:
                validation['warnings'].append(f'Unknown category {category}')
            
            # Validate length
            if length > len(raw_data):
                validation['errors'].append(f'Declared length {length} exceeds actual data length {len(raw_data)}')
                return validation
            
            if length < 3:
                validation['errors'].append(f'Invalid length {length} (minimum 3)')
                return validation
            
            # Category-specific validation
            if category in self.processors:
                processor = self.processors[category]
                # Add category-specific validation if available
                validation['warnings'].append(f'Category {category} processor available')
            else:
                validation['warnings'].append(f'Category {category} not fully supported')
            
            # If we get here, basic validation passed
            validation['is_valid'] = True
            
        except Exception as e:
            validation['errors'].append(f'Validation error: {str(e)}')
        
        return validation
    
    def create_asterix_message(self, targets: List[Dict[str, Any]], category: int = 21) -> bytes:
        """
        Create ASTERIX message from target data.
        
        Args:
            targets: List of target dictionaries
            category: ASTERIX category to create
            
        Returns:
            ASTERIX message bytes
        """
        try:
            if category in self.processors:
                processor = self.processors[category]
                
                if category == 10:
                    return processor.create_cat10_message(targets)
                elif category == 21:
                    return processor.create_cat21_message(targets)
                elif category == 48:
                    return processor.create_cat48_message(targets)
                else:
                    # Fallback if category is in processors but not handled above
                    return self._create_generic_message(targets, category)
            
            else:
                # Generic message creation
                return self._create_generic_message(targets, category)
                
        except Exception as e:
            return b''
    
    def _create_generic_message(self, targets: List[Dict[str, Any]], category: int) -> bytes:
        """
        Create generic ASTERIX message for unsupported categories.
        
        Args:
            targets: List of target dictionaries
            category: ASTERIX category
            
        Returns:
            Generic ASTERIX message bytes
        """
        message = bytearray()
        
        # Category
        message.append(category)
        
        # Length placeholder
        length_pos = len(message)
        message.extend([0, 0])
        
        # Simple generic data (for demonstration)
        for target in targets:
            # Add basic target information
            message.extend([0x01, 0x02])  # Basic SAC/SIC
            
            # Add timestamp if available
            if 'timestamp' in target:
                message.extend([0x00, 0x01, 0x02])  # Dummy time
        
        # Update length
        total_length = len(message)
        struct.pack_into('>H', message, length_pos, total_length)
        
        return bytes(message)
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary with processing statistics
        """
        stats = self.processing_stats.copy()
        
        # Add category information
        stats['supported_categories'] = len(self.processors)
        stats['total_known_categories'] = len(self.category_descriptions)
        
        # Add per-category stats
        for category, processor in self.processors.items():
            if hasattr(processor, 'get_message_statistics'):
                stats[f'category_{category}_info'] = {
                    'name': self.category_descriptions.get(category, 'Unknown'),
                    'processor_available': True
                }
        
        return stats
    
    def get_message_statistics(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate comprehensive statistics from processed messages.
        
        Args:
            messages: List of processed messages
            
        Returns:
            Dictionary with comprehensive statistics
        """
        if not messages:
            return {}
        
        stats = {
            'total_messages': len(messages),
            'categories': {},
            'message_types': {},
            'unique_tracks': set(),
            'timestamp_range': {'earliest': None, 'latest': None},
            'geographic_bounds': {
                'min_lat': float('inf'), 'max_lat': float('-inf'),
                'min_lon': float('inf'), 'max_lon': float('-inf')
            },
            'processing_summary': {}
        }
        
        for msg in messages:
            # Category statistics
            category = msg.get('category', 'Unknown')
            stats['categories'][category] = stats['categories'].get(category, 0) + 1
            
            # Message type statistics
            msg_type = msg.get('message_type', 'Unknown')
            stats['message_types'][msg_type] = stats['message_types'].get(msg_type, 0) + 1
            
            # Track statistics
            if msg.get('track_id'):
                stats['unique_tracks'].add(msg['track_id'])
            
            # Timestamp statistics
            if msg.get('timestamp'):
                if not stats['timestamp_range']['earliest']:
                    stats['timestamp_range']['earliest'] = msg['timestamp']
                    stats['timestamp_range']['latest'] = msg['timestamp']
                else:
                    if msg['timestamp'] < stats['timestamp_range']['earliest']:
                        stats['timestamp_range']['earliest'] = msg['timestamp']
                    if msg['timestamp'] > stats['timestamp_range']['latest']:
                        stats['timestamp_range']['latest'] = msg['timestamp']
            
            # Geographic bounds
            if msg.get('latitude') and msg.get('longitude'):
                lat, lon = msg['latitude'], msg['longitude']
                stats['geographic_bounds']['min_lat'] = min(stats['geographic_bounds']['min_lat'], lat)
                stats['geographic_bounds']['max_lat'] = max(stats['geographic_bounds']['max_lat'], lat)
                stats['geographic_bounds']['min_lon'] = min(stats['geographic_bounds']['min_lon'], lon)
                stats['geographic_bounds']['max_lon'] = max(stats['geographic_bounds']['max_lon'], lon)
        
        # Convert set to count
        stats['unique_tracks'] = len(stats['unique_tracks'])
        
        # Add category-specific statistics
        for category in stats['categories']:
            if category in self.processors:
                category_messages = [msg for msg in messages if msg.get('category') == category]
                processor = self.processors[category]
                
                if hasattr(processor, 'get_message_statistics'):
                    stats['processing_summary'][f'category_{category}'] = \
                        processor.get_message_statistics(category_messages)
        
        return stats
    
    def filter_messages_by_category(self, messages: List[Dict[str, Any]], 
                                   categories: List[int]) -> List[Dict[str, Any]]:
        """
        Filter messages by ASTERIX category.
        
        Args:
            messages: List of processed messages
            categories: List of category numbers to keep
            
        Returns:
            Filtered list of messages
        """
        return [msg for msg in messages if msg.get('category') in categories]
    
    def get_category_coverage(self) -> Dict[str, Any]:
        """
        Get information about category coverage and capabilities.
        
        Returns:
            Dictionary with category coverage information
        """
        coverage = {
            'total_categories': len(self.category_descriptions),
            'supported_categories': len(self.processors),
            'coverage_percentage': (len(self.processors) / len(self.category_descriptions)) * 100,
            'supported': [],
            'unsupported': [],
            'processor_info': {}
        }
        
        for category, description in self.category_descriptions.items():
            category_info = {
                'category': category,
                'description': description,
                'supported': category in self.processors
            }
            
            if category in self.processors:
                coverage['supported'].append(category_info)
                coverage['processor_info'][category] = {
                    'class_name': self.processors[category].__class__.__name__,
                    'capabilities': self._get_processor_capabilities(category)
                }
            else:
                coverage['unsupported'].append(category_info)
        
        return coverage
    
    def _get_processor_capabilities(self, category: int) -> List[str]:
        """
        Get capabilities of a specific processor.
        
        Args:
            category: ASTERIX category number
            
        Returns:
            List of processor capabilities
        """
        if category not in self.processors:
            return []
        
        processor = self.processors[category]
        capabilities = []
        
        # Check for common methods
        if hasattr(processor, 'process_cat' + str(category) + '_message'):
            capabilities.append('Message Processing')
        
        if hasattr(processor, 'create_cat' + str(category) + '_message'):
            capabilities.append('Message Creation')
        
        if hasattr(processor, 'get_message_statistics'):
            capabilities.append('Statistics Generation')
        
        # Category-specific capabilities
        if category == 10:
            capabilities.extend(['Surface Movement Tracking', 'Vehicle Fleet Identification'])
        elif category == 21:
            capabilities.extend(['ADS-B Processing', 'Emergency Detection', 'Quality Assessment'])
        elif category == 48:
            capabilities.extend(['Monoradar Processing', 'Mode S Handling', 'Plot Characteristics'])
        
        return capabilities
