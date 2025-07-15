#!/usr/bin/env python3
"""
Test script for the consolidated ASTERIX processor
Tests CAT-48, CAT-21, and CAT-10 processing functionality
"""

import sys
import struct
from asterix_cat48_consolidated import AsterixConsolidatedProcessor
from asterix_converter import AsterixMultiCategoryConverter
from asterix_cat48 import AsterixCAT48Processor
from asterix_cat21 import AsterixCAT21Processor
from asterix_cat10 import AsterixCAT10Processor

def create_test_cat48_message():
    """Create a simple CAT-48 test message."""
    message = bytearray()
    
    # Category 48
    message.append(48)
    
    # Length placeholder
    length_pos = len(message)
    message.extend([0, 0])
    
    # FSPEC - First octet: I048/010, I048/140, I048/020, I048/040, I048/070
    message.append(0xF8)  # 11111000
    message.append(0x00)  # Second octet with FX=0
    
    # I048/010 - Data Source Identifier
    message.extend([0x01, 0x02])  # SAC=1, SIC=2
    
    # I048/140 - Time of Day (3 bytes)
    time_raw = int(12345.5 * 128)  # 12345.5 seconds since midnight
    message.extend(struct.pack('>I', time_raw)[1:])  # 3 bytes
    
    # I048/020 - Target Report Descriptor
    message.append(0x02)  # Single SSR detection
    
    # I048/040 - Measured Position in Polar Coordinates
    rho = int(10.5 * 256)  # 10.5 NM
    theta = int(90.0 * 65536 / 360)  # 90 degrees
    message.extend(struct.pack('>HH', rho, theta))
    
    # I048/070 - Mode-3/A Code
    mode_3a = 0x1234  # Example squawk code
    message.extend(struct.pack('>H', mode_3a))
    
    # Update length
    total_length = len(message)
    struct.pack_into('>H', message, length_pos, total_length)
    
    return bytes(message)

def create_test_cat21_message():
    """Create a simple CAT-21 test message."""
    message = bytearray()
    
    # Category 21
    message.append(21)
    
    # Length placeholder
    length_pos = len(message)
    message.extend([0, 0])
    
    # FSPEC - First octet: I021/010, I021/040, I021/080
    message.append(0xA8)  # 10101000
    message.append(0x00)  # Second octet with FX=0
    
    # I021/010 - Data Source Identifier
    message.extend([0x01, 0x02])  # SAC=1, SIC=2
    
    # I021/040 - Target Position in WGS-84 (6 bytes)
    lat = int(abs(28.0836) * (2**23) / 180.0)  # Example latitude (positive)
    lon = int(abs(-80.6081) * (2**23) / 180.0)  # Example longitude (positive)
    # Pack as 3 bytes each
    lat_bytes = struct.pack('>I', lat)[1:]  # 3 bytes
    lon_bytes = struct.pack('>I', lon)[1:]  # 3 bytes
    message.extend(lat_bytes + lon_bytes)
    
    # I021/080 - Target Address
    address = 0x123456  # Example aircraft address
    message.extend(struct.pack('>I', address)[1:])  # 3 bytes
    
    # Update length
    total_length = len(message)
    struct.pack_into('>H', message, length_pos, total_length)
    
    return bytes(message)

def create_test_cat10_message():
    """Create a simple CAT-10 test message."""
    message = bytearray()
    
    # Category 10
    message.append(10)
    
    # Length placeholder
    length_pos = len(message)
    message.extend([0, 0])
    
    # FSPEC - First octet: I010/010, I010/040, I010/220
    message.append(0xA4)  # 10100100
    message.append(0x00)  # Second octet with FX=0
    
    # I010/010 - Data Source Identifier
    message.extend([0x01, 0x02])  # SAC=1, SIC=2
    
    # I010/040 - Measured Position in Polar Coordinates
    rho = int(5.2 * 256)  # 5.2 NM
    theta = int(45.0 * 65536 / 360)  # 45 degrees
    message.extend(struct.pack('>HH', rho, theta))
    
    # I010/220 - Target Address
    address = 0x654321  # Example target address
    message.extend(struct.pack('>I', address)[1:])  # 3 bytes
    
    # Update length
    total_length = len(message)
    struct.pack_into('>H', message, length_pos, total_length)
    
    return bytes(message)

def test_consolidated_processor():
    """Test the consolidated processor directly."""
    print("=== Testing Consolidated Processor ===")
    
    processor = AsterixConsolidatedProcessor()
    
    # Test CAT-48
    print("\n1. Testing CAT-48 processing:")
    cat48_msg = create_test_cat48_message()
    print(f"CAT-48 message length: {len(cat48_msg)} bytes")
    
    results = processor.process_asterix_message(cat48_msg)
    print(f"Processed {len(results)} targets")
    
    if results:
        target = results[0]
        print(f"  Category: {target['category']}")
        print(f"  Message Type: {target['message_type']}")
        print(f"  Track ID: {target['track_id']}")
        print(f"  Range: {target.get('range', 'N/A')}")
        print(f"  Azimuth: {target.get('azimuth', 'N/A')}")
        print(f"  Mode 3A: {target.get('mode_3a', 'N/A')}")
        print(f"  Time of Day: {target.get('time_of_day', 'N/A')}")
        if target.get('latitude') and target.get('longitude'):
            print(f"  Position: {target['latitude']:.6f}, {target['longitude']:.6f}")
    
    # Test CAT-21
    print("\n2. Testing CAT-21 processing:")
    cat21_msg = create_test_cat21_message()
    print(f"CAT-21 message length: {len(cat21_msg)} bytes")
    
    results = processor.process_asterix_message(cat21_msg)
    print(f"Processed {len(results)} targets")
    
    if results:
        target = results[0]
        print(f"  Category: {target['category']}")
        print(f"  Message Type: {target['message_type']}")
        print(f"  Track ID: {target['track_id']}")
        print(f"  Aircraft Address: {target.get('aircraft_address', 'N/A')}")
        if target.get('latitude') and target.get('longitude'):
            print(f"  Position: {target['latitude']:.6f}, {target['longitude']:.6f}")
    
    # Test CAT-10
    print("\n3. Testing CAT-10 processing:")
    cat10_msg = create_test_cat10_message()
    print(f"CAT-10 message length: {len(cat10_msg)} bytes")
    
    results = processor.process_asterix_message(cat10_msg)
    print(f"Processed {len(results)} targets")
    
    if results:
        target = results[0]
        print(f"  Category: {target['category']}")
        print(f"  Message Type: {target['message_type']}")
        print(f"  Track ID: {target['track_id']}")
        print(f"  Aircraft Address: {target.get('aircraft_address', 'N/A')}")
        print(f"  Range: {target.get('range', 'N/A')}")
        print(f"  Azimuth: {target.get('azimuth', 'N/A')}")
        if target.get('latitude') and target.get('longitude'):
            print(f"  Position: {target['latitude']:.6f}, {target['longitude']:.6f}")
    
    # Test statistics
    print("\n4. Testing processing statistics:")
    stats = processor.get_processing_statistics()
    print(f"  Total messages: {stats['total_messages']}")
    print(f"  Messages by category: {stats['messages_by_category']}")
    print(f"  Processing errors: {stats['processing_errors']}")

def test_backward_compatibility():
    """Test that the wrapper classes still work."""
    print("\n=== Testing Backward Compatibility ===")
    
    # Test CAT-48 wrapper
    print("\n1. Testing CAT-48 wrapper:")
    cat48_processor = AsterixCAT48Processor()
    cat48_msg = create_test_cat48_message()
    
    results = cat48_processor.process_cat48_message(cat48_msg)
    print(f"CAT-48 wrapper processed {len(results)} targets")
    
    if results:
        target = results[0]
        print(f"  Category: {target['category']}")
        print(f"  Track ID: {target['track_id']}")
    
    # Test CAT-21 wrapper
    print("\n2. Testing CAT-21 wrapper:")
    cat21_processor = AsterixCAT21Processor()
    cat21_msg = create_test_cat21_message()
    
    results = cat21_processor.process_cat21_message(cat21_msg)
    print(f"CAT-21 wrapper processed {len(results)} targets")
    
    if results:
        target = results[0]
        print(f"  Category: {target['category']}")
        print(f"  Track ID: {target['track_id']}")
    
    # Test CAT-10 wrapper
    print("\n3. Testing CAT-10 wrapper:")
    cat10_processor = AsterixCAT10Processor()
    cat10_msg = create_test_cat10_message()
    
    results = cat10_processor.process_cat10_message(cat10_msg)
    print(f"CAT-10 wrapper processed {len(results)} targets")
    
    if results:
        target = results[0]
        print(f"  Category: {target['category']}")
        print(f"  Track ID: {target['track_id']}")

def test_converter_integration():
    """Test the updated converter."""
    print("\n=== Testing Converter Integration ===")
    
    converter = AsterixMultiCategoryConverter()
    
    # Test with different categories
    test_messages = [
        ("CAT-48", create_test_cat48_message()),
        ("CAT-21", create_test_cat21_message()),
        ("CAT-10", create_test_cat10_message())
    ]
    
    for name, msg in test_messages:
        print(f"\nTesting {name} through converter:")
        results = converter.process_asterix_message(msg)
        print(f"  Processed {len(results)} targets")
        
        if results:
            target = results[0]
            print(f"  Category: {target['category']}")
            print(f"  Message Type: {target['message_type']}")
            print(f"  Track ID: {target['track_id']}")

def test_message_creation():
    """Test message creation functionality."""
    print("\n=== Testing Message Creation ===")
    
    processor = AsterixConsolidatedProcessor()
    
    # Create test target data
    test_target = {
        'range': 10.5,
        'azimuth': 90.0,
        'latitude': 28.0836,
        'longitude': -80.6081,
        'aircraft_address': '123456'
    }
    
    # Test CAT-48 message creation
    cat48_msg = processor.create_cat48_message([test_target])
    print(f"Created CAT-48 message: {len(cat48_msg)} bytes")
    print(f"  Category: {cat48_msg[0]}")
    print(f"  Length: {struct.unpack('>H', cat48_msg[1:3])[0]}")
    
    # Test CAT-21 message creation
    cat21_msg = processor.create_cat21_message([test_target])
    print(f"Created CAT-21 message: {len(cat21_msg)} bytes")
    print(f"  Category: {cat21_msg[0]}")
    print(f"  Length: {struct.unpack('>H', cat21_msg[1:3])[0]}")
    
    # Test CAT-10 message creation
    cat10_msg = processor.create_cat10_message([test_target])
    print(f"Created CAT-10 message: {len(cat10_msg)} bytes")
    print(f"  Category: {cat10_msg[0]}")
    print(f"  Length: {struct.unpack('>H', cat10_msg[1:3])[0]}")

def main():
    """Run all tests."""
    print("ASTERIX Consolidated Processor Test Suite")
    print("=========================================")
    
    try:
        test_consolidated_processor()
        test_backward_compatibility()
        test_converter_integration()
        test_message_creation()
        
        print("\n=== All Tests Completed Successfully! ===")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
