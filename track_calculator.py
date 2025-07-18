"""
Track Calculator for ASTERIX CAT-48 Surveillance System with IGMM Course Modeling
=================================================================================

This module processes surveillance plot data and performs multi-target tracking
using IGMM (Infinite Gaussian Mixture Model) course modeling for enhanced
plot-to-track association as described in IEEE research.

Features:
- IGMM-based course modeling for target tracking
- Enhanced plot-to-track association using course prediction
- Probabilistic association with course confidence weighting
- Dynamic gating based on course model confidence
- Multi-target tracking with advanced data association
- Kalman filtering with course-aware prediction
- Track quality assessment using course consistency

Based on: "Plot-to-Track Association Using IGMM Course Modeling 
for Target Tracking With Compact HFSWR"

Author: Generated for SurveillanceSentry
Date: 2024
"""

import numpy as np
import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict

# Import IGMM associator
from igmm_track_associator import IGMMPlotTrackAssociator, IGMMTrackData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrackState(Enum):
    """Track lifecycle states"""
    TENTATIVE = "tentative"      # New track candidate
    CONFIRMED = "confirmed"      # Established track
    COASTING = "coasting"        # Track without recent updates
    TERMINATED = "terminated"    # Dead track


@dataclass
class PlotData:
    """Individual radar plot/detection"""
    timestamp: datetime
    range_m: float              # Range in meters
    azimuth_deg: float          # Azimuth in degrees
    elevation_deg: float = 0.0  # Elevation (if available)
    latitude: float = 0.0       # Converted coordinates
    longitude: float = 0.0      # Converted coordinates
    rcs: float = 0.0           # Radar cross section
    plot_id: str = ""          # Unique plot identifier
    quality: float = 1.0       # Plot quality factor (0-1)
    track_type: str = "Aircraft"  # Target type: Aircraft, Vehicle, Vessel
    
    def __post_init__(self):
        if not self.plot_id:
            self.plot_id = f"plot_{int(self.timestamp.timestamp()*1000000)}"


@dataclass
class TrackData:
    """Consolidated track information"""
    track_id: str
    state: TrackState
    created_time: datetime
    last_update: datetime
    
    # Position and kinematics
    position_history: List[Tuple[float, float, datetime]] = field(default_factory=list)
    velocity_x: float = 0.0     # m/s
    velocity_y: float = 0.0     # m/s
    speed_ms: float = 0.0       # Speed in m/s
    heading_deg: float = 0.0    # Heading in degrees (0-360)
    
    # Track statistics
    plot_count: int = 0
    consecutive_misses: int = 0
    quality_score: float = 0.0
    
    # Track classification
    track_type: str = "Aircraft"  # Target type: Aircraft, Vehicle, Vessel
    
    # Kalman filter state
    state_vector: np.ndarray = field(default_factory=lambda: np.zeros(4))  # [x, y, vx, vy]
    covariance_matrix: np.ndarray = field(default_factory=lambda: np.eye(4) * 1000)
    
    # Associated plots
    associated_plots: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not hasattr(self, 'track_id') or not self.track_id:
            self.track_id = f"track_{int(self.created_time.timestamp()*1000000)}"


class TrackCalculator:
    """
    Main track calculator class implementing IGMM-based multi-target tracking
    """
    
    def __init__(self, config: Dict | None = None):
        """
        Initialize track calculator with IGMM course modeling
        
        Args:
            config: Configuration dictionary with tracking parameters
        """
        self.config = config or {}
        
        # IGMM Association parameters
        igmm_config = {
            'base_association_distance': self.config.get('max_association_distance', 500.0),
            'course_weight': self.config.get('course_weight', 0.3),
            'position_weight': self.config.get('position_weight', 0.7),
            'confirmation_threshold': self.config.get('track_confirmation_threshold', 3),
            'termination_threshold': self.config.get('track_termination_threshold', 5)
        }
        
        # Initialize IGMM associator
        self.igmm_associator = IGMMPlotTrackAssociator(igmm_config)
        
        # Legacy tracking parameters for compatibility
        self.max_association_distance = self.config.get('max_association_distance', 500.0)
        self.track_confirmation_threshold = self.config.get('track_confirmation_threshold', 3)
        self.track_termination_threshold = self.config.get('track_termination_threshold', 5)
        self.coasting_threshold = self.config.get('coasting_threshold', 3)
        self.min_speed_threshold = self.config.get('min_speed_threshold', 2.0)
        self.max_speed_threshold = self.config.get('max_speed_threshold', 300.0)
        
        # Kalman filter parameters (needed for legacy compatibility)
        self.process_noise_std = self.config.get('process_noise_std', 5.0)
        self.measurement_noise_std = self.config.get('measurement_noise_std', 10.0)
        self.time_delta = self.config.get('time_delta', 1.0)  # seconds
        
        # Melbourne FL radar location (7800 Technology Drive)
        self.radar_lat = 28.0836  # degrees
        self.radar_lon = -80.6081  # degrees
        
        # Legacy storage for compatibility
        self.active_tracks: Dict[str, TrackData] = {}
        self.terminated_tracks: Dict[str, TrackData] = {}
        
        # Statistics
        self.stats = {
            'total_plots_processed': 0,
            'tracks_initiated': 0,
            'tracks_confirmed': 0,
            'tracks_terminated': 0,
            'association_success_rate': 0.0
        }
        
        logger.info(f"IGMM Track calculator initialized with {len(self.config)} parameters")
    
    
    def process_plot_batch(self, plots: List[PlotData]) -> Dict[str, TrackData]:
        """
        Process a batch of plots using IGMM course modeling
        
        Args:
            plots: List of plot data to process
            
        Returns:
            Dictionary of updated tracks
        """
        logger.info(f"Processing batch of {len(plots)} plots")
        
        # Convert plots to IGMM format
        igmm_plots = []
        for plot in plots:
            # Convert polar to cartesian
            x, y = self._polar_to_cartesian(plot.range_m, plot.azimuth_deg)
            igmm_plots.append({
                'x': x,
                'y': y,
                'timestamp': plot.timestamp
            })
        
        # Process using IGMM associator
        igmm_tracks = self.igmm_associator.process_plots(igmm_plots)
        
        # Convert IGMM tracks back to legacy format for compatibility
        self.active_tracks = {}
        for igmm_track in igmm_tracks:
            if igmm_track.state in ["Confirmed", "Coasting"]:
                # Set track state
                if igmm_track.state == "Confirmed":
                    track_state = TrackState.CONFIRMED
                elif igmm_track.state == "Coasting":
                    track_state = TrackState.COASTING
                else:
                    track_state = TrackState.TENTATIVE
                
                # Convert back to legacy TrackData format
                track_data = TrackData(
                    track_id=igmm_track.track_id,
                    state=track_state,
                    created_time=igmm_track.timestamp,
                    last_update=igmm_track.timestamp,
                    speed_ms=igmm_track.speed,
                    heading_deg=igmm_track.heading,
                    plot_count=igmm_track.plot_count,
                    consecutive_misses=igmm_track.consecutive_misses,
                    quality_score=igmm_track.quality_score
                )
                
                # Set position in state vector [x, y, vx, vy]
                track_data.state_vector[0] = igmm_track.x
                track_data.state_vector[1] = igmm_track.y
                track_data.velocity_x = igmm_track.speed * math.cos(math.radians(igmm_track.heading))
                track_data.velocity_y = igmm_track.speed * math.sin(math.radians(igmm_track.heading))
                track_data.state_vector[2] = track_data.velocity_x
                track_data.state_vector[3] = track_data.velocity_y
                
                # Add to position history
                track_data.position_history.append((igmm_track.x, igmm_track.y, igmm_track.timestamp))
                
                self.active_tracks[igmm_track.track_id] = track_data
        
        # Update statistics
        self.stats['total_plots_processed'] += len(plots)
        logger.info(f"IGMM batch processing complete. Active tracks: {len(self.active_tracks)}")
        
        return self.active_tracks.copy()
    
    
    def _process_single_plot(self, plot: PlotData):
        """
        Process a single plot for track association
        
        Args:
            plot: Individual plot data
        """
        # Convert polar to cartesian coordinates
        x, y = self._polar_to_cartesian(plot.range_m, plot.azimuth_deg)
        
        # Find candidate tracks for association
        candidates = self._find_association_candidates(x, y, plot.timestamp)
        
        if not candidates:
            # No suitable tracks found, initiate new track
            self._initiate_new_track(plot, x, y)
        else:
            # Associate with best candidate track
            best_track = self._select_best_association(candidates, x, y, plot.timestamp)
            if best_track is not None:
                self._associate_plot_to_track(plot, best_track, x, y)
            else:
                # No suitable track found, initiate new track
                self._initiate_new_track(plot, x, y)
    
    
    def _find_association_candidates(self, x: float, y: float, timestamp: datetime) -> List[TrackData]:
        """
        Find tracks that could be associated with the given plot
        
        Args:
            x, y: Cartesian coordinates of plot
            timestamp: Plot timestamp
            
        Returns:
            List of candidate tracks
        """
        candidates = []
        
        for track in self.active_tracks.values():
            if track.state == TrackState.TERMINATED:
                continue
                
            # Predict track position at plot timestamp
            predicted_pos = self._predict_track_position(track, timestamp)
            
            # Calculate distance to predicted position
            distance = math.sqrt((x - predicted_pos[0])**2 + (y - predicted_pos[1])**2)
            
            # Check if within association gate
            if distance <= self._get_association_gate(track):
                candidates.append(track)
        
        return candidates
    
    
    def _select_best_association(self, candidates: List[TrackData], x: float, y: float, 
                               timestamp: datetime) -> TrackData | None:
        """
        Select the best track for association using nearest neighbor
        
        Args:
            candidates: List of candidate tracks
            x, y: Plot coordinates
            timestamp: Plot timestamp
            
        Returns:
            Best track for association or None if no suitable candidates
        """
        best_track = None
        min_distance = float('inf')
        
        for track in candidates:
            predicted_pos = self._predict_track_position(track, timestamp)
            distance = math.sqrt((x - predicted_pos[0])**2 + (y - predicted_pos[1])**2)
            
            # Weight by track quality
            weighted_distance = distance / max(track.quality_score, 0.1)
            
            if weighted_distance < min_distance:
                min_distance = weighted_distance
                best_track = track
        
        return best_track
    
    
    def _associate_plot_to_track(self, plot: PlotData, track: TrackData, x: float, y: float):
        """
        Associate a plot with a track and update track state
        
        Args:
            plot: Plot data
            track: Track to associate with
            x, y: Cartesian coordinates
        """
        # Update Kalman filter with new measurement
        self._update_kalman_filter(track, x, y, plot.timestamp)
        
        # Update track history
        track.position_history.append((x, y, plot.timestamp))
        if len(track.position_history) > 50:  # Keep last 50 positions
            track.position_history.pop(0)
        
        # Update track statistics
        track.plot_count += 1
        track.consecutive_misses = 0
        track.last_update = plot.timestamp
        track.associated_plots.append(plot.plot_id)
        
        # Calculate speed and heading
        self._calculate_kinematics(track)
        
        # Update track quality
        self._update_track_quality(track)
        
        logger.debug(f"Associated plot {plot.plot_id} with track {track.track_id}")
    
    
    def _initiate_new_track(self, plot: PlotData, x: float, y: float):
        """
        Initiate a new track from unassociated plot
        
        Args:
            plot: Plot data
            x, y: Cartesian coordinates
        """
        track = TrackData(
            track_id=f"track_{len(self.active_tracks) + len(self.terminated_tracks) + 1:06d}",
            state=TrackState.TENTATIVE,
            created_time=plot.timestamp,
            last_update=plot.timestamp,
            track_type=plot.track_type  # Use track type from plot
        )
        
        # Initialize Kalman filter state
        track.state_vector = np.array([x, y, 0.0, 0.0])  # [x, y, vx, vy]
        track.covariance_matrix = np.eye(4) * 1000  # Initial uncertainty
        
        # Add initial position
        track.position_history.append((x, y, plot.timestamp))
        track.plot_count = 1
        track.associated_plots.append(plot.plot_id)
        
        self.active_tracks[track.track_id] = track
        self.stats['tracks_initiated'] += 1
        
        logger.info(f"Initiated new track {track.track_id} at ({x:.1f}, {y:.1f})")
    
    
    def _update_kalman_filter(self, track: TrackData, x: float, y: float, timestamp: datetime):
        """
        Update track using Kalman filter
        
        Args:
            track: Track to update
            x, y: Measured position
            timestamp: Measurement timestamp
        """
        # Time since last update
        if track.position_history:
            dt = (timestamp - track.position_history[-1][2]).total_seconds()
        else:
            dt = self.time_delta
        
        # State transition matrix (constant velocity model)
        F = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        
        # Process noise covariance
        Q = np.array([
            [dt**4/4, 0, dt**3/2, 0],
            [0, dt**4/4, 0, dt**3/2],
            [dt**3/2, 0, dt**2, 0],
            [0, dt**3/2, 0, dt**2]
        ]) * (self.process_noise_std ** 2)
        
        # Measurement matrix
        H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ])
        
        # Measurement noise covariance
        R = np.eye(2) * (self.measurement_noise_std ** 2)
        
        # Predict
        predicted_state = F @ track.state_vector
        predicted_covariance = F @ track.covariance_matrix @ F.T + Q
        
        # Update
        measurement = np.array([x, y])
        innovation = measurement - H @ predicted_state
        innovation_covariance = H @ predicted_covariance @ H.T + R
        kalman_gain = predicted_covariance @ H.T @ np.linalg.inv(innovation_covariance)
        
        track.state_vector = predicted_state + kalman_gain @ innovation
        track.covariance_matrix = (np.eye(4) - kalman_gain @ H) @ predicted_covariance
        
        # Update velocity components
        track.velocity_x = track.state_vector[2]
        track.velocity_y = track.state_vector[3]
    
    
    def _calculate_kinematics(self, track: TrackData):
        """
        Calculate speed and heading from track data
        
        Args:
            track: Track to calculate kinematics for
        """
        if len(track.position_history) < 2:
            return
        
        # Calculate from Kalman filter velocity
        vx, vy = track.velocity_x, track.velocity_y
        
        # Calculate speed
        track.speed_ms = math.sqrt(vx**2 + vy**2)
        
        # Calculate heading (0-360 degrees, North=0)
        if track.speed_ms > self.min_speed_threshold:
            heading_rad = math.atan2(vx, vy)  # atan2(East, North)
            track.heading_deg = (math.degrees(heading_rad) + 360) % 360
        
        # Alternative calculation using position history for validation
        if len(track.position_history) >= 2:
            p1 = track.position_history[-2]
            p2 = track.position_history[-1]
            
            dt = (p2[2] - p1[2]).total_seconds()
            if dt > 0:
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                
                speed_check = math.sqrt(dx**2 + dy**2) / dt
                
                # Use position-based calculation if Kalman filter seems wrong
                if abs(speed_check - track.speed_ms) > 50:  # Large discrepancy
                    track.speed_ms = speed_check
                    if speed_check > self.min_speed_threshold:
                        heading_rad = math.atan2(dx, dy)
                        track.heading_deg = (math.degrees(heading_rad) + 360) % 360
    
    
    def _predict_track_position(self, track: TrackData, timestamp: datetime) -> Tuple[float, float]:
        """
        Predict track position at given timestamp
        
        Args:
            track: Track to predict
            timestamp: Target timestamp
            
        Returns:
            Predicted (x, y) position
        """
        if not track.position_history:
            return (0.0, 0.0)
        
        # Time since last update
        last_time = track.position_history[-1][2]
        dt = (timestamp - last_time).total_seconds()
        
        # Use Kalman filter state for prediction
        current_x, current_y = track.state_vector[0], track.state_vector[1]
        vx, vy = track.velocity_x, track.velocity_y
        
        predicted_x = current_x + vx * dt
        predicted_y = current_y + vy * dt
        
        return (predicted_x, predicted_y)
    
    
    def _get_association_gate(self, track: TrackData) -> float:
        """
        Get association gate size for track
        
        Args:
            track: Track to get gate for
            
        Returns:
            Gate size in meters
        """
        base_gate = self.max_association_distance
        
        # Adjust gate based on track quality and speed
        quality_factor = max(track.quality_score, 0.1)
        speed_factor = min(track.speed_ms / 50.0, 2.0)  # Larger gate for faster targets
        
        return base_gate * (1.0 + speed_factor) / quality_factor
    
    
    def _update_track_quality(self, track: TrackData):
        """
        Update track quality score
        
        Args:
            track: Track to update quality for
        """
        # Base quality from plot count
        plot_quality = min(track.plot_count / 10.0, 1.0)
        
        # Consistency quality (low consecutive misses)
        consistency_quality = max(0.0, 1.0 - track.consecutive_misses / 10.0)
        
        # Speed reasonableness
        speed_quality = 1.0
        if track.speed_ms > self.max_speed_threshold:
            speed_quality = 0.5
        elif track.speed_ms < self.min_speed_threshold and track.plot_count > 3:
            speed_quality = 0.7
        
        # Combine qualities
        track.quality_score = plot_quality * consistency_quality * speed_quality
        
        # Ensure minimum quality
        track.quality_score = max(track.quality_score, 0.1)
    
    
    def _update_track_states(self):
        """
        Update track states based on recent activity
        """
        current_time = datetime.now()
        
        for track in self.active_tracks.values():
            if track.state == TrackState.TERMINATED:
                continue
            
            # Check for track confirmation
            if (track.state == TrackState.TENTATIVE and 
                track.plot_count >= self.track_confirmation_threshold):
                track.state = TrackState.CONFIRMED
                self.stats['tracks_confirmed'] += 1
                logger.info(f"Track {track.track_id} confirmed")
            
            # Check for coasting
            time_since_update = (current_time - track.last_update).total_seconds()
            if (time_since_update > self.coasting_threshold * self.time_delta and 
                track.state == TrackState.CONFIRMED):
                track.state = TrackState.COASTING
                track.consecutive_misses += 1
                logger.debug(f"Track {track.track_id} coasting")
    
    
    def _perform_track_maintenance(self):
        """
        Perform track maintenance - terminate old tracks
        """
        tracks_to_terminate = []
        
        for track_id, track in self.active_tracks.items():
            # Terminate tracks with too many consecutive misses
            if track.consecutive_misses >= self.track_termination_threshold:
                tracks_to_terminate.append(track_id)
            
            # Terminate tentative tracks that haven't been confirmed
            elif (track.state == TrackState.TENTATIVE and 
                  track.plot_count < self.track_confirmation_threshold and
                  track.consecutive_misses >= 3):
                tracks_to_terminate.append(track_id)
        
        # Terminate selected tracks
        for track_id in tracks_to_terminate:
            track = self.active_tracks.pop(track_id)
            track.state = TrackState.TERMINATED
            self.terminated_tracks[track_id] = track
            self.stats['tracks_terminated'] += 1
            logger.info(f"Terminated track {track_id}")
    
    
    def _polar_to_cartesian(self, range_m: float, azimuth_deg: float) -> Tuple[float, float]:
        """
        Convert polar coordinates to cartesian
        
        Args:
            range_m: Range in meters
            azimuth_deg: Azimuth in degrees
            
        Returns:
            (x, y) coordinates in meters
        """
        azimuth_rad = math.radians(azimuth_deg)
        x = range_m * math.sin(azimuth_rad)  # East
        y = range_m * math.cos(azimuth_rad)  # North
        return (x, y)
    
    
    def get_track_summary(self) -> Dict:
        """
        Get summary of current tracking state
        
        Returns:
            Dictionary with tracking statistics
        """
        active_by_state = defaultdict(int)
        for track in self.active_tracks.values():
            active_by_state[track.state.value] += 1
        
        return {
            'active_tracks': len(self.active_tracks),
            'terminated_tracks': len(self.terminated_tracks),
            'tracks_by_state': dict(active_by_state),
            'statistics': self.stats.copy()
        }
    
    
    def get_tracks_for_display(self) -> List[Dict]:
        """
        Get track data formatted for display
        
        Returns:
            List of track dictionaries for display
        """
        display_tracks = []
        
        for track in self.active_tracks.values():
            if track.state == TrackState.TERMINATED:
                continue
            
            # Get latest position
            if track.position_history:
                latest_pos = track.position_history[-1]
                
                # Convert back to lat/lon for display
                lat, lon = self._cartesian_to_latlon(latest_pos[0], latest_pos[1])
                
                display_tracks.append({
                    'track_id': track.track_id,
                    'state': track.state.value,
                    'latitude': lat,
                    'longitude': lon,
                    'speed_ms': track.speed_ms,
                    'heading_deg': track.heading_deg,
                    'plot_count': track.plot_count,
                    'quality_score': track.quality_score,
                    'last_update': track.last_update.isoformat(),
                    'created_time': track.created_time.isoformat(),
                    # Add fields expected by dashboard
                    'track_type': track.track_type,  # Use actual track type
                    'type': track.track_type,        # Alias for track_type
                    'status': 'Active',              # All displayed tracks are active
                    'callsign': None,                # Not available from radar tracks
                    'altitude': None,                # Not available from 2D radar
                    'speed': track.speed_ms,         # Alias for speed_ms
                    'heading': track.heading_deg     # Alias for heading_deg
                })
        
        return display_tracks
    
    
    def _cartesian_to_latlon(self, x: float, y: float) -> Tuple[float, float]:
        """
        Convert cartesian coordinates back to lat/lon
        
        Args:
            x, y: Cartesian coordinates in meters
            
        Returns:
            (latitude, longitude) in degrees
        """
        # Earth radius in meters
        R = 6378137.0
        
        # Convert to lat/lon offset
        lat_offset = y / R * 180.0 / math.pi
        lon_offset = x / (R * math.cos(math.radians(self.radar_lat))) * 180.0 / math.pi
        
        return (self.radar_lat + lat_offset, self.radar_lon + lon_offset)


def create_default_config() -> Dict:
    """
    Create default configuration for track calculator
    
    Returns:
        Default configuration dictionary
    """
    return {
        'max_association_distance': 500.0,      # meters
        'track_confirmation_threshold': 3,       # plots
        'track_termination_threshold': 5,        # missed scans
        'coasting_threshold': 3,                 # seconds
        'min_speed_threshold': 2.0,             # m/s
        'max_speed_threshold': 300.0,           # m/s
        'process_noise_std': 5.0,               # meters
        'measurement_noise_std': 10.0,          # meters
        'time_delta': 1.0                       # seconds
    }


if __name__ == "__main__":
    # Example usage
    config = create_default_config()
    tracker = TrackCalculator(config)
    
    # Create sample plots
    sample_plots = [
        PlotData(
            timestamp=datetime.now(),
            range_m=5000,
            azimuth_deg=45,
            latitude=28.1,
            longitude=-80.6
        ),
        PlotData(
            timestamp=datetime.now() + timedelta(seconds=1),
            range_m=5100,
            azimuth_deg=46,
            latitude=28.11,
            longitude=-80.59
        )
    ]
    
    # Process plots
    tracks = tracker.process_plot_batch(sample_plots)
    
    # Print results
    print(f"Processed {len(sample_plots)} plots")
    print(f"Active tracks: {len(tracks)}")
    
    for track in tracks.values():
        print(f"Track {track.track_id}: State={track.state.value}, "
              f"Speed={track.speed_ms:.1f} m/s, "
              f"Heading={track.heading_deg:.1f}°, "
              f"Plots={track.plot_count}")
