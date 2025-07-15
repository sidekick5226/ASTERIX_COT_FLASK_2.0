"""
Test Script for Track Calculator
===============================

This script demonstrates the track calculator functionality with sample data
and validates the tracking algorithms.

Author: Generated for SurveillanceSentry
Date: 2024
"""

import logging
import math
import random
from datetime import datetime, timedelta
from track_calculator import TrackCalculator, PlotData, create_default_config
from track_integrator import TrackIntegrator, create_database_schema

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_aircraft_trajectory(start_lat: float, start_lon: float, 
                               speed_ms: float, heading_deg: float,
                               duration_seconds: int, 
                               radar_lat: float = 28.0836, radar_lon: float = -80.6081) -> list:
    """
    Generate realistic aircraft trajectory
    
    Args:
        start_lat, start_lon: Starting position
        speed_ms: Speed in m/s
        heading_deg: Heading in degrees
        duration_seconds: Duration of trajectory
        radar_lat, radar_lon: Radar position
        
    Returns:
        List of PlotData objects
    """
    plots = []
    current_time = datetime.now()
    
    # Earth radius in meters
    R = 6378137.0
    
    # Current position
    lat, lon = start_lat, start_lon
    
    for t in range(0, duration_seconds, 1):  # 1 second intervals
        # Add some noise to simulate radar measurement errors
        noise_range = random.gauss(0, 5)  # 5m range noise
        noise_azimuth = random.gauss(0, 0.1)  # 0.1 degree azimuth noise
        
        # Calculate range and azimuth from radar
        dlat = lat - radar_lat
        dlon = lon - radar_lon
        
        # Convert to meters
        x = dlon * R * math.cos(math.radians(radar_lat)) * math.pi / 180
        y = dlat * R * math.pi / 180
        
        range_m = math.sqrt(x**2 + y**2) + noise_range
        azimuth_deg = (math.degrees(math.atan2(x, y)) + 360) % 360 + noise_azimuth
        
        # Create plot
        plot = PlotData(
            timestamp=current_time + timedelta(seconds=t),
            range_m=range_m,
            azimuth_deg=azimuth_deg,
            latitude=lat,
            longitude=lon,
            rcs=10.0,  # Typical aircraft RCS
            plot_id=f"sim_plot_{t}",
            quality=0.9 + random.uniform(-0.1, 0.1)
        )
        
        plots.append(plot)
        
        # Update position for next iteration
        heading_rad = math.radians(heading_deg)
        
        # Move aircraft
        distance_m = speed_ms * 1.0  # 1 second interval
        
        # Calculate new position
        dlat_new = distance_m * math.cos(heading_rad) / R * 180 / math.pi
        dlon_new = distance_m * math.sin(heading_rad) / (R * math.cos(math.radians(lat))) * 180 / math.pi
        
        lat += dlat_new
        lon += dlon_new
        
        # Add slight course variation
        heading_deg += random.gauss(0, 0.5)
    
    return plots


def generate_multiple_aircraft_scenario() -> list:
    """
    Generate a multi-aircraft scenario for testing
    
    Returns:
        List of all plots from multiple aircraft
    """
    all_plots = []
    
    # Aircraft 1: Commercial airliner
    aircraft1_plots = generate_aircraft_trajectory(
        start_lat=28.2, start_lon=-80.8,
        speed_ms=150,  # ~300 knots
        heading_deg=45,
        duration_seconds=120
    )
    all_plots.extend(aircraft1_plots)
    
    # Aircraft 2: General aviation
    aircraft2_plots = generate_aircraft_trajectory(
        start_lat=28.0, start_lon=-80.4,
        speed_ms=70,  # ~135 knots
        heading_deg=270,
        duration_seconds=150
    )
    all_plots.extend(aircraft2_plots)
    
    # Aircraft 3: Military jet
    aircraft3_plots = generate_aircraft_trajectory(
        start_lat=28.3, start_lon=-80.5,
        speed_ms=250,  # ~485 knots
        heading_deg=180,
        duration_seconds=90
    )
    all_plots.extend(aircraft3_plots)
    
    # Sort by timestamp
    all_plots.sort(key=lambda p: p.timestamp)
    
    return all_plots


def test_track_calculator():
    """
    Test the track calculator with simulated data
    """
    logger.info("Starting track calculator test")
    
    # Create tracker with default configuration
    config = create_default_config()
    tracker = TrackCalculator(config)
    
    # Generate test data
    logger.info("Generating multi-aircraft scenario")
    plots = generate_multiple_aircraft_scenario()
    logger.info(f"Generated {len(plots)} plots for testing")
    
    # Process plots in batches (simulate real-time processing)
    batch_size = 10
    for i in range(0, len(plots), batch_size):
        batch = plots[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1} with {len(batch)} plots")
        
        tracks = tracker.process_plot_batch(batch)
        
        # Log current state
        summary = tracker.get_track_summary()
        logger.info(f"Active tracks: {summary['active_tracks']}, "
                   f"Terminated: {summary['terminated_tracks']}")
    
    # Final results
    final_tracks = tracker.get_tracks_for_display()
    logger.info(f"Final tracking results: {len(final_tracks)} active tracks")
    
    for track in final_tracks:
        logger.info(f"Track {track['track_id']}: "
                   f"State={track['state']}, "
                   f"Speed={track['speed_ms']:.1f} m/s, "
                   f"Heading={track['heading_deg']:.1f}°, "
                   f"Plots={track['plot_count']}, "
                   f"Quality={track['quality_score']:.2f}")
    
    # Get final statistics
    stats = tracker.get_track_summary()
    logger.info(f"Final statistics: {stats}")
    
    return tracker, final_tracks


def test_track_integrator():
    """
    Test the track integrator with database
    """
    logger.info("Starting track integrator test")
    
    # Create database schema
    create_database_schema()
    
    # Initialize integrator
    integrator = TrackIntegrator()
    
    # Test processing (this would normally read from database)
    logger.info("Testing integrator functionality")
    
    # Get current tracks
    tracks = integrator.get_current_tracks()
    logger.info(f"Current tracks from integrator: {len(tracks)}")
    
    # Get statistics
    stats = integrator.get_track_statistics()
    logger.info(f"Integrator statistics: {stats}")
    
    return integrator


def validate_tracking_accuracy():
    """
    Validate tracking accuracy with known trajectories
    """
    logger.info("Starting tracking accuracy validation")
    
    # Create tracker
    tracker = TrackCalculator(create_default_config())
    
    # Generate single aircraft with known trajectory
    known_plots = generate_aircraft_trajectory(
        start_lat=28.1, start_lon=-80.7,
        speed_ms=100,  # Known speed
        heading_deg=90,  # Known heading (East)
        duration_seconds=60
    )
    
    # Process plots
    tracks = tracker.process_plot_batch(known_plots)
    
    # Validate results
    if tracks:
        track = list(tracks.values())[0]
        
        # Check speed accuracy
        speed_error = abs(track.speed_ms - 100)
        heading_error = abs(track.heading_deg - 90)
        if heading_error > 180:
            heading_error = 360 - heading_error
        
        logger.info(f"Validation results:")
        logger.info(f"  True speed: 100 m/s, Calculated: {track.speed_ms:.1f} m/s, Error: {speed_error:.1f} m/s")
        logger.info(f"  True heading: 90°, Calculated: {track.heading_deg:.1f}°, Error: {heading_error:.1f}°")
        
        # Pass/fail criteria
        speed_pass = speed_error < 10  # Within 10 m/s
        heading_pass = heading_error < 10  # Within 10 degrees
        
        logger.info(f"  Speed validation: {'PASS' if speed_pass else 'FAIL'}")
        logger.info(f"  Heading validation: {'PASS' if heading_pass else 'FAIL'}")
        
        return speed_pass and heading_pass
    
    logger.error("No tracks generated for validation")
    return False


def main():
    """
    Main test function
    """
    logger.info("=" * 60)
    logger.info("Track Calculator Test Suite")
    logger.info("=" * 60)
    
    try:
        # Test 1: Basic track calculator functionality
        logger.info("\n1. Testing Track Calculator")
        tracker, tracks = test_track_calculator()
        
        # Test 2: Track integrator functionality
        logger.info("\n2. Testing Track Integrator")
        integrator = test_track_integrator()
        
        # Test 3: Accuracy validation
        logger.info("\n3. Validating Tracking Accuracy")
        accuracy_pass = validate_tracking_accuracy()
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Track Calculator: {'PASS' if len(tracks) > 0 else 'FAIL'}")
        logger.info(f"Track Integrator: PASS")  # If no exception thrown
        logger.info(f"Accuracy Validation: {'PASS' if accuracy_pass else 'FAIL'}")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        raise


if __name__ == "__main__":
    main()
