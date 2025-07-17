"""
Track Calculator for ASTERIX CAT-48 Surveillance System
====================================================

This module processes surveillance plot data and performs multi-target tracking
to correlate individual plots into coherent tracks. It implements data association
algorithms and calculates derived parameters like speed and heading.

Features:
- Multi-target tracking with data association
- Nearest neighbor and probabilistic data association
- Kalman filtering for track prediction and smoothing
- Speed and heading calculation from position data
- Track initiation, maintenance, and termination
- False alarm rejection and track quality assessment

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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrackState(Enum):
    """Track lifecycle states"""
    TENTATIVE = "tentative"      # New track candidate
    CONFIRMED = "confirmed"      # Established track
    COASTING = "coasting"        # Track without recent updates
    TERMINATED = "terminated"    # Dead track


class SensorType(Enum):
    """Sensor types for multi-sensor fusion"""
    RADAR = "radar"              # Primary radar
    ADSB = "adsb"               # ADS-B transponder
    SECONDARY = "secondary"      # Secondary surveillance radar
    OPTICAL = "optical"         # Electro-optical sensor
    UNKNOWN = "unknown"         # Unknown sensor type


class ManeuverState(Enum):
    """Maneuver detection states"""
    STRAIGHT = "straight"        # Straight line motion
    TURN = "turn"               # Turning maneuver
    ACCELERATION = "acceleration" # Speed change
    UNKNOWN = "unknown"         # Unknown maneuver state


@dataclass
class PlotData:
    """Individual radar plot/detection"""
    timestamp: datetime
    range_m: float              # Range in meters
    azimuth_deg: float          # Azimuth in degrees
    elevation_deg: float = 0.0  # Elevation (if available)
    latitude: float = 0.0       # Converted coordinates
    longitude: float = 0.0      # Converted coordinates
    altitude: Optional[float] = None  # Altitude in feet (if available)
    rcs: float = 0.0           # Radar cross section
    plot_id: str = ""          # Unique plot identifier
    quality: float = 1.0       # Plot quality factor (0-1)
    track_type: str = "Aircraft"  # Target type: Aircraft, Vehicle, Vessel
    sensor_type: SensorType = SensorType.RADAR  # Sensor type
    sensor_id: str = ""        # Sensor identifier
    doppler_velocity: float = 0.0  # Doppler velocity (if available)
    squawk: str = ""           # Transponder squawk code
    original_track_id: str = "" # Original track ID from database
    
    def __post_init__(self):
        if not self.plot_id:
            self.plot_id = f"plot_{int(self.timestamp.timestamp()*1000000)}"
        if not self.sensor_id:
            self.sensor_id = f"sensor_{self.sensor_type.value}"


@dataclass
class TrackData:
    """Consolidated track information"""
    track_id: str
    state: TrackState
    created_time: datetime
    last_update: datetime
    
    # Position and kinematics
    position_history: List[Tuple[float, float, datetime]] = field(default_factory=list)
    azimuth_history: List[Tuple[float, datetime]] = field(default_factory=list)  # Azimuth history
    last_azimuth: float = 0.0   # Last known azimuth in degrees
    velocity_x: float = 0.0     # m/s
    velocity_y: float = 0.0     # m/s
    speed_ms: float = 0.0       # Speed in m/s
    heading_deg: float = 0.0    # Heading in degrees (0-360)
    altitude: Optional[float] = None  # Altitude in feet from most recent associated plot
    
    # Track statistics
    plot_count: int = 0
    consecutive_misses: int = 0
    quality_score: float = 0.0
    
    # Track classification
    track_type: str = "Aircraft"  # Target type: Aircraft, Vehicle, Vessel
    original_track_id: str = ""   # Original track ID from database
    
    # Kalman filter state (extended for maneuver detection)
    state_vector: np.ndarray = field(default_factory=lambda: np.zeros(6))  # [x, y, vx, vy, ax, ay]
    covariance_matrix: np.ndarray = field(default_factory=lambda: np.eye(6) * 1000)
    
    # Associated plots
    associated_plots: List[str] = field(default_factory=list)
    
    # Maneuver detection
    maneuver_state: ManeuverState = ManeuverState.STRAIGHT
    maneuver_likelihood: float = 0.0
    acceleration_x: float = 0.0  # m/s²
    acceleration_y: float = 0.0  # m/s²
    
    # Multi-sensor fusion
    sensor_sources: Set[SensorType] = field(default_factory=set)
    sensor_weights: Dict[SensorType, float] = field(default_factory=dict)
    last_sensor_update: Dict[SensorType, datetime] = field(default_factory=dict)
    
    # Course modeling
    course_history: List[Tuple[float, datetime]] = field(default_factory=list)  # Recent courses
    predicted_course: float = 0.0   # Predicted course angle
    course_variance: float = 0.0    # Variance of course angles
    course_rate: float = 0.0        # Rate of change of course angle
    
    def __post_init__(self):
        if not hasattr(self, 'track_id') or not self.track_id:
            self.track_id = f"track_{int(self.created_time.timestamp()*1000000)}"


class TrackCalculator:
    """
    Main track calculator class implementing multi-target tracking algorithms
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize track calculator with configuration parameters
        
        Args:
            config: Configuration dictionary with tracking parameters
        """
        self.config = config or {}
        
        # Basic tracking parameters - increased for aircraft tracking
        self.max_association_distance = self.config.get('max_association_distance', 10000.0)  # 10km for aircraft
        self.max_azimuth_difference = self.config.get('max_azimuth_difference', 5.0)  # 5 degrees for aircraft
        self.use_azimuth_correlation = self.config.get('use_azimuth_correlation', True)  # Enable azimuth correlation
        self.use_course_modeling = self.config.get('use_course_modeling', True)  # Enable IGMM course modeling
        self.track_confirmation_threshold = self.config.get('track_confirmation_threshold', 3)
        self.track_termination_threshold = self.config.get('track_termination_threshold', 10)  # increased from 5
        self.coasting_threshold = self.config.get('coasting_threshold', 5)  # increased from 3
        self.min_speed_threshold = self.config.get('min_speed_threshold', 2.0)  # m/s
        self.max_speed_threshold = self.config.get('max_speed_threshold', 300.0)  # m/s
        
        # Kalman filter parameters (extended for maneuver detection)
        self.process_noise_std = self.config.get('process_noise_std', 5.0)
        self.measurement_noise_std = self.config.get('measurement_noise_std', 10.0)
        self.time_delta = self.config.get('time_delta', 1.0)  # seconds
        
        # Maneuver detection parameters
        self.maneuver_threshold = self.config.get('maneuver_threshold', 2.0)  # G force
        self.acceleration_noise_std = self.config.get('acceleration_noise_std', 2.0)
        
        # Multi-sensor fusion parameters
        self.sensor_fusion_enabled = self.config.get('sensor_fusion_enabled', True)
        self.sensor_time_threshold = self.config.get('sensor_time_threshold', 5.0)  # seconds
        
        # Probabilistic data association parameters - more permissive for aircraft
        self.pda_enabled = self.config.get('pda_enabled', True)
        self.pda_gate_threshold = self.config.get('pda_gate_threshold', 15.0)  # Increased from 9.21 for aircraft
        self.clutter_density = self.config.get('clutter_density', 1e-6)  # clutter per m²
        
        # Melbourne FL radar location (7800 Technology Drive)
        self.radar_lat = 28.0836  # degrees
        self.radar_lon = -80.6081  # degrees
        
        # Active tracks storage
        self.active_tracks: Dict[str, TrackData] = {}
        self.terminated_tracks: Dict[str, TrackData] = {}
        
        # Statistics
        self.stats = {
            'total_plots_processed': 0,
            'tracks_initiated': 0,
            'tracks_confirmed': 0,
            'tracks_terminated': 0,
            'association_success_rate': 0.0,
            'maneuver_detections': 0,
            'sensor_fusions': 0
        }
        
        logger.info(f"Enhanced track calculator initialized with {len(self.config)} parameters")
        logger.info(f"PDA enabled: {self.pda_enabled}, Sensor fusion: {self.sensor_fusion_enabled}")
    
    
    def process_plot_batch(self, plots: List[PlotData]) -> Dict[str, TrackData]:
        """
        Process a batch of plots and update tracks
        
        Args:
            plots: List of plot data to process
            
        Returns:
            Dictionary of updated tracks
        """
        logger.info(f"Processing batch of {len(plots)} plots")
        
        # Sort plots by timestamp
        plots.sort(key=lambda p: p.timestamp)
        
        # Track which tracks got updated in this batch
        updated_tracks = set()
        
        for plot in plots:
            associated_track = self._process_single_plot(plot)
            if associated_track:
                updated_tracks.add(associated_track.track_id)
        
        # Increment consecutive misses for tracks that weren't updated
        self._age_unassociated_tracks(updated_tracks)
        
        # Update track states and perform maintenance
        self._update_track_states()
        self._perform_track_maintenance()
        
        self.stats['total_plots_processed'] += len(plots)
        logger.info(f"Batch processing complete. Active tracks: {len(self.active_tracks)}")
        
        return self.active_tracks.copy()
    
    
    def _process_single_plot(self, plot: PlotData) -> Optional[TrackData]:
        """
        Process a single plot for track association with IGMM course modeling
        
        Args:
            plot: Individual plot data
            
        Returns:
            The track that was associated with this plot, or None if new track created
        """
        # Convert polar to cartesian coordinates
        x, y = self._polar_to_cartesian(plot.range_m, plot.azimuth_deg)
        
        # Use enhanced course-based association with IGMM modeling
        candidates = self._find_course_association_candidates(plot, x, y, plot.timestamp)
        
        # Fallback to traditional methods if no course candidates found
        if not candidates:
            if self.use_azimuth_correlation:
                candidates = self._find_azimuth_association_candidates(plot.azimuth_deg, plot.timestamp)
                # Convert azimuth candidates to course format
                candidates = [(track, 1.0 - (dist / self.max_azimuth_difference)) 
                             for track, dist in candidates]
            else:
                position_candidates = self._find_association_candidates(x, y, plot.timestamp)
                # Convert position candidates to course format  
                candidates = [(track, 1.0 - (dist / self.pda_gate_threshold)) 
                             for track, dist in position_candidates]
        
        if not candidates:
            # No suitable tracks found, initiate new track
            logger.debug(f"No association candidates found for plot at ({x:.1f}, {y:.1f}), creating new track")
            self._initiate_new_track(plot, x, y)
            return None
        else:
            # Associate with best candidate based on combined score
            logger.debug(f"Found {len(candidates)} association candidates for plot at ({x:.1f}, {y:.1f})")
            best_track = self._select_best_course_association(candidates, plot, x, y)
            if best_track:
                logger.debug(f"Associated plot with track {best_track.track_id}")
                self._associate_plot_to_track(plot, best_track, x, y)
                return best_track
            else:
                # No good association found, initiate new track
                logger.debug(f"No good association found among {len(candidates)} candidates, creating new track")
                self._initiate_new_track(plot, x, y)
                return None
    
    def _age_unassociated_tracks(self, updated_tracks: set):
        """
        Age tracks that weren't associated with any plots in this batch
        
        Args:
            updated_tracks: Set of track IDs that were updated in this batch
        """
        for track_id, track in self.active_tracks.items():
            if track.state == TrackState.TERMINATED:
                continue
                
            # If track wasn't updated in this batch, increment consecutive misses
            if track_id not in updated_tracks:
                track.consecutive_misses += 1
                logger.debug(f"Track {track_id} aged: {track.consecutive_misses} consecutive misses")
    
    
    def _find_track_by_original_id(self, original_track_id: str) -> Optional[TrackData]:
        """
        Find an existing track by its original track ID from the database
        
        Args:
            original_track_id: Original track ID from database
            
        Returns:
            Existing track or None
        """
        for track in self.active_tracks.values():
            if track.original_track_id == original_track_id:
                return track
        return None
    
    
    def _find_association_candidates(self, x: float, y: float, timestamp: datetime) -> List[Tuple[TrackData, float]]:
        """
        Find tracks that could be associated with the given plot using statistical gates
        
        Args:
            x, y: Cartesian coordinates of plot
            timestamp: Plot timestamp
            
        Returns:
            List of (track, distance) tuples for candidate tracks
        """
        candidates = []
        
        for track in self.active_tracks.values():
            if track.state == TrackState.TERMINATED:
                continue
                
            # Predict track position at plot timestamp
            predicted_pos = self._predict_track_position(track, timestamp)
            
            # Calculate Mahalanobis distance for statistical validation
            mahalanobis_dist = self._calculate_mahalanobis_distance(
                track, x, y, predicted_pos, timestamp
            )
            
            # Check if within statistical gate
            if self._is_within_statistical_gate(mahalanobis_dist):
                candidates.append((track, mahalanobis_dist))
        
        return candidates
    
    
    def _find_azimuth_association_candidates(self, azimuth_deg: float, timestamp: datetime) -> List[Tuple[TrackData, float]]:
        """
        Find tracks that could be associated with the given plot using azimuth correlation
        
        Args:
            azimuth_deg: Azimuth angle of plot in degrees
            timestamp: Plot timestamp
            
        Returns:
            List of (track, azimuth_difference) tuples for candidate tracks
        """
        candidates = []
        
        for track in self.active_tracks.values():
            if track.state == TrackState.TERMINATED:
                continue
            
            # Skip tracks with no azimuth history
            if not track.azimuth_history:
                continue
                
            # Calculate azimuth difference with track's last known azimuth
            azimuth_diff = self._calculate_azimuth_difference(azimuth_deg, track.last_azimuth)
            
            # Check if within azimuth correlation gate
            if azimuth_diff <= self.max_azimuth_difference:
                candidates.append((track, azimuth_diff))
        
        return candidates
    
    
    def _calculate_azimuth_difference(self, azimuth1: float, azimuth2: float) -> float:
        """
        Calculate the smallest angular difference between two azimuth angles
        
        Args:
            azimuth1, azimuth2: Azimuth angles in degrees (0-360)
            
        Returns:
            Smallest angular difference in degrees
        """
        # Normalize angles to 0-360 range
        azimuth1 = azimuth1 % 360
        azimuth2 = azimuth2 % 360
        
        # Calculate absolute difference
        diff = abs(azimuth1 - azimuth2)
        
        # Return the smallest angular difference (considering wrap-around)
        return min(diff, 360 - diff)


    def _select_best_association(self, candidates: List[Tuple[TrackData, float]], x: float, y: float, 
                               timestamp: datetime) -> Optional[TrackData]:
        """
        Select the best track for association using probabilistic data association
        
        Args:
            candidates: List of (track, distance) tuples
            x, y: Plot coordinates
            timestamp: Plot timestamp
            
        Returns:
            Best track for association or None
        """
        if not candidates:
            return None
            
        if not self.pda_enabled or len(candidates) == 1:
            # Use nearest neighbor if PDA disabled or only one candidate
            return min(candidates, key=lambda x: x[1])[0]
        
        # Calculate association probabilities for PDA
        association_probs = self._calculate_association_probabilities(candidates, x, y)
        
        # Select track with highest probability
        best_idx = np.argmax(association_probs)
        best_prob = association_probs[best_idx]
        
        # Only associate if probability is above threshold - more permissive for aircraft
        if best_prob > 0.3:  # Reduced from 0.5 to be more permissive
            return candidates[best_idx][0]
        
        return None
    
    
    def _select_best_course_association(self, candidates: List[Tuple[TrackData, float]], 
                                       plot: PlotData, x: float, y: float) -> Optional[TrackData]:
        """
        Select the best track for association using course-based scoring
        
        Args:
            candidates: List of (track, score) tuples
            plot: Plot data
            x, y: Plot coordinates
            
        Returns:
            Best track for association or None
        """
        if not candidates:
            return None
        
        # Sort by score (highest first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Take the best candidate if score is above threshold
        best_track, best_score = candidates[0]
        
        # Adaptive threshold based on track maturity and quality
        if len(best_track.course_history) >= 3 and best_track.quality_score > 0.7:
            threshold = 0.4  # Lower threshold for mature, good tracks to be more permissive  
        else:
            threshold = 0.2  # Much lower threshold for new or poor quality tracks
        
        if best_score >= threshold:
            return best_track
        
        return None
    
    
    def _associate_plot_to_track(self, plot: PlotData, track: TrackData, x: float, y: float):
        """
        Associate a plot with a track and update track state with sensor fusion
        
        Args:
            plot: Plot data
            track: Track to associate with
            x, y: Cartesian coordinates
        """
        # Calculate sensor fusion weight
        fusion_weight = self._fuse_sensor_data(track, plot)
        
        # Update Kalman filter with new measurement
        self._update_kalman_filter(track, x, y, plot.timestamp, fusion_weight)
        
        # Update track history
        track.position_history.append((x, y, plot.timestamp))
        if len(track.position_history) > 50:  # Keep last 50 positions
            track.position_history.pop(0)
        
        # Update azimuth history
        track.azimuth_history.append((plot.azimuth_deg, plot.timestamp))
        if len(track.azimuth_history) > 50:  # Keep last 50 azimuth readings
            track.azimuth_history.pop(0)
        track.last_azimuth = plot.azimuth_deg
        
        # Update altitude from most recent associated plot
        if plot.altitude is not None:
            track.altitude = plot.altitude
        
        # Update track statistics
        track.plot_count += 1
        track.consecutive_misses = 0
        track.last_update = plot.timestamp
        track.associated_plots.append(plot.plot_id)
        
        # Calculate speed and heading
        self._calculate_kinematics(track)
        
        # Update course modeling for IGMM-based association
        self._update_course_modeling(track, plot)
        
        # Detect maneuvers
        old_maneuver = track.maneuver_state
        track.maneuver_state = self._detect_maneuver(track)
        if track.maneuver_state != old_maneuver and track.maneuver_state != ManeuverState.STRAIGHT:
            self.stats['maneuver_detections'] += 1
            logger.info(f"Maneuver detected for track {track.track_id}: {track.maneuver_state.value}")
        
        # Update track quality
        self._update_track_quality(track)
        
        # Update sensor fusion statistics
        if len(track.sensor_sources) > 1:
            self.stats['sensor_fusions'] += 1
        
        # Update course modeling
        self._update_course_modeling(track, plot)
        
        logger.debug(f"Associated plot {plot.plot_id} with track {track.track_id} "
                    f"(sensor: {plot.sensor_type.value}, weight: {fusion_weight:.3f})")
    
    
    def _initiate_new_track(self, plot: PlotData, x: float, y: float):
        """
        Initiate a new track from unassociated plot
        
        Args:
            plot: Plot data
            x, y: Cartesian coordinates
        """
        # Generate new track ID instead of using original track ID
        # since database track IDs are individual detections, not correlated tracks
        track_id = f"track_{len(self.active_tracks) + len(self.terminated_tracks) + 1:06d}"
        
        track = TrackData(
            track_id=track_id,
            state=TrackState.TENTATIVE,
            created_time=plot.timestamp,
            last_update=plot.timestamp,
            track_type=plot.track_type,  # Use track type from plot
            original_track_id=plot.original_track_id,  # Keep for reference
            altitude=plot.altitude  # Initialize altitude from plot
        )
        
        # Initialize Kalman filter state (extended for maneuver detection)
        track.state_vector = np.array([x, y, 0.0, 0.0, 0.0, 0.0])  # [x, y, vx, vy, ax, ay]
        track.covariance_matrix = np.eye(6) * 1000  # Initial uncertainty
        
        # Add initial position
        track.position_history.append((x, y, plot.timestamp))
        track.plot_count = 1
        track.associated_plots.append(plot.plot_id)
        
        # Initialize azimuth history
        track.azimuth_history.append((plot.azimuth_deg, plot.timestamp))
        track.last_azimuth = plot.azimuth_deg
        
        # Initialize course modeling
        track.course_history = []
        track.course_variance = 0.0
        track.course_rate = 0.0
        track.predicted_course = 0.0
        
        self.active_tracks[track.track_id] = track
        self.stats['tracks_initiated'] += 1
        
        logger.info(f"Initiated new track {track.track_id} at ({x:.1f}, {y:.1f})")
        
        # Don't automatically confirm tracks - let them go through normal confirmation process
        # based on multiple associated plots
    
    
    def _update_kalman_filter(self, track: TrackData, x: float, y: float, timestamp: datetime, 
                             fusion_weight: float = 1.0):
        """
        Update track using extended Kalman filter with maneuver detection
        
        Args:
            track: Track to update
            x, y: Measured position
            timestamp: Measurement timestamp
            fusion_weight: Sensor fusion weight
        """
        # Time since last update
        if track.position_history:
            dt = (timestamp - track.position_history[-1][2]).total_seconds()
        else:
            dt = self.time_delta
        
        # State transition matrix (constant acceleration model)
        F = np.array([
            [1, 0, dt, 0, 0.5*dt**2, 0],
            [0, 1, 0, dt, 0, 0.5*dt**2],
            [0, 0, 1, 0, dt, 0],
            [0, 0, 0, 1, 0, dt],
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 1]
        ])
        
        # Process noise covariance (extended for acceleration)
        Q = np.array([
            [dt**4/4, 0, dt**3/2, 0, dt**2/2, 0],
            [0, dt**4/4, 0, dt**3/2, 0, dt**2/2],
            [dt**3/2, 0, dt**2, 0, dt, 0],
            [0, dt**3/2, 0, dt**2, 0, dt],
            [dt**2/2, 0, dt, 0, 1, 0],
            [0, dt**2/2, 0, dt, 0, 1]
        ]) * (self.process_noise_std ** 2)
        
        # Add acceleration noise
        Q[4:6, 4:6] += np.eye(2) * (self.acceleration_noise_std ** 2)
        
        # Measurement matrix (observe position only)
        H = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0]
        ])
        
        # Measurement noise covariance (weighted by fusion)
        R = np.eye(2) * (self.measurement_noise_std ** 2) / fusion_weight
        
        # Predict
        predicted_state = F @ track.state_vector
        predicted_covariance = F @ track.covariance_matrix @ F.T + Q
        
        # Update
        measurement = np.array([x, y])
        innovation = measurement - H @ predicted_state
        innovation_covariance = H @ predicted_covariance @ H.T + R
        
        try:
            kalman_gain = predicted_covariance @ H.T @ np.linalg.inv(innovation_covariance)
            track.state_vector = predicted_state + kalman_gain @ innovation
            track.covariance_matrix = (np.eye(6) - kalman_gain @ H) @ predicted_covariance
        except np.linalg.LinAlgError:
            # Fallback if inversion fails
            track.state_vector = predicted_state
            track.covariance_matrix = predicted_covariance
        
        # Update velocity and acceleration components
        track.velocity_x = track.state_vector[2]
        track.velocity_y = track.state_vector[3]
        track.acceleration_x = track.state_vector[4]
        track.acceleration_y = track.state_vector[5]
    
    
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
        Predict track position at given timestamp using constant acceleration model
        
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
        
        # Use extended Kalman filter state for prediction
        current_x, current_y = track.state_vector[0], track.state_vector[1]
        vx, vy = track.velocity_x, track.velocity_y
        ax, ay = track.acceleration_x, track.acceleration_y
        
        # Constant acceleration model
        predicted_x = current_x + vx * dt + 0.5 * ax * dt**2
        predicted_y = current_y + vy * dt + 0.5 * ay * dt**2
        
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
        
        # Adjust gate based on track quality and speed - more generous for aircraft
        quality_factor = max(track.quality_score, 0.2)  # More generous minimum
        speed_factor = min(track.speed_ms / 50.0, 5.0)  # Aircraft can be fast, allow larger gates
        
        # Make gate larger for coasting tracks to help re-acquire them
        coasting_factor = 2.0 if track.state == TrackState.COASTING else 1.0  # More generous for coasting
        
        gate_size = base_gate * (1.0 + speed_factor) * coasting_factor / quality_factor
        return min(gate_size, 15000.0)  # Cap at 15km for aircraft
    
    
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
            
            # Check for coasting (based on consecutive misses, not time)
            if (track.consecutive_misses >= self.coasting_threshold and 
                track.state == TrackState.CONFIRMED):
                track.state = TrackState.COASTING
                logger.debug(f"Track {track.track_id} coasting due to {track.consecutive_misses} consecutive misses")
    
    
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
                  track.consecutive_misses >= 7):  # increased from 3 to 7
                tracks_to_terminate.append(track_id)
        
        # Terminate selected tracks
        for track_id in tracks_to_terminate:
            track = self.active_tracks.pop(track_id)
            track.state = TrackState.TERMINATED
            self.terminated_tracks[track_id] = track
            self.stats['tracks_terminated'] += 1
            logger.info(f"Terminated track {track_id} (consecutive misses: {track.consecutive_misses}, state: {track.state.value})")
    
    
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
    
    
    def _calculate_mahalanobis_distance(self, track: TrackData, x: float, y: float, 
                                      predicted_pos: Tuple[float, float], timestamp: datetime) -> float:
        """
        Calculate Mahalanobis distance for statistical validation gate
        
        Args:
            track: Track data
            x, y: Measured position
            predicted_pos: Predicted position
            timestamp: Measurement timestamp
            
        Returns:
            Mahalanobis distance
        """
        # Innovation (measurement - prediction)
        innovation = np.array([x - predicted_pos[0], y - predicted_pos[1]])
        
        # Measurement covariance matrix
        R = np.eye(2) * (self.measurement_noise_std ** 2)
        
        # Predicted covariance (position only)
        H = np.array([[1, 0, 0, 0, 0, 0],
                      [0, 1, 0, 0, 0, 0]])  # Extract position from state
        
        innovation_cov = H @ track.covariance_matrix @ H.T + R
        
        # Calculate Mahalanobis distance
        try:
            inv_cov = np.linalg.inv(innovation_cov)
            mahalanobis_dist = innovation.T @ inv_cov @ innovation
            return float(mahalanobis_dist)
        except np.linalg.LinAlgError:
            # Fallback to Euclidean distance if covariance is singular
            return float(np.dot(innovation, innovation))
    
    
    def _is_within_statistical_gate(self, mahalanobis_distance: float) -> bool:
        """
        Check if measurement is within statistical validation gate
        
        Args:
            mahalanobis_distance: Mahalanobis distance
            
        Returns:
            True if within gate
        """
        # Use fixed threshold for 2D case (95% confidence level ≈ 5.99)
        threshold = self.pda_gate_threshold  # Default 9.21 is conservative
            
        return mahalanobis_distance <= threshold
    
    
    def _calculate_association_probabilities(self, candidates: List[Tuple[TrackData, float]], 
                                           x: float, y: float) -> np.ndarray:
        """
        Calculate association probabilities for probabilistic data association
        
        Args:
            candidates: List of (track, distance) tuples
            x, y: Plot coordinates
            
        Returns:
            Array of association probabilities
        """
        if not candidates:
            return np.array([])
        
        # Calculate likelihood for each candidate
        likelihoods = []
        for track, mahalanobis_dist in candidates:
            # Gaussian likelihood
            likelihood = np.exp(-0.5 * mahalanobis_dist)
            likelihoods.append(likelihood)
        
        # Add clutter likelihood
        clutter_likelihood = self.clutter_density
        total_likelihood = sum(likelihoods) + clutter_likelihood
        
        # Calculate probabilities
        probabilities = np.array(likelihoods) / total_likelihood
        
        return probabilities
    
    
    def _detect_maneuver(self, track: TrackData) -> ManeuverState:
        """
        Detect maneuver based on acceleration and track history
        
        Args:
            track: Track to analyze
            
        Returns:
            Detected maneuver state
        """
        if len(track.position_history) < 3:
            return ManeuverState.STRAIGHT
        
        # Calculate acceleration magnitude
        acceleration = math.sqrt(track.acceleration_x**2 + track.acceleration_y**2)
        
        # Maneuver detection thresholds (convert to m/s²)
        maneuver_threshold_ms2 = self.maneuver_threshold * 9.81
        
        if acceleration > maneuver_threshold_ms2:
            # Determine type of maneuver
            if abs(track.acceleration_x) > abs(track.acceleration_y):
                return ManeuverState.ACCELERATION
            else:
                return ManeuverState.TURN
        
        return ManeuverState.STRAIGHT
    
    
    def _fuse_sensor_data(self, track: TrackData, plot: PlotData) -> float:
        """
        Fuse data from multiple sensors using weighted average
        
        Args:
            track: Track to update
            plot: New plot data
            
        Returns:
            Fusion weight for this sensor
        """
        if not self.sensor_fusion_enabled:
            return 1.0
        
        # Update sensor sources
        track.sensor_sources.add(plot.sensor_type)
        track.last_sensor_update[plot.sensor_type] = plot.timestamp
        
        # Calculate sensor weights based on quality and recency
        base_weight = plot.quality
        
        # Adjust weight based on sensor type
        type_weights = {
            SensorType.RADAR: 1.0,
            SensorType.ADSB: 0.9,
            SensorType.SECONDARY: 0.8,
            SensorType.OPTICAL: 0.7,
            SensorType.UNKNOWN: 0.5
        }
        
        type_weight = type_weights.get(plot.sensor_type, 0.5)
        
        # Time decay factor
        if plot.sensor_type in track.last_sensor_update:
            last_update = track.last_sensor_update[plot.sensor_type]
            time_diff = (plot.timestamp - last_update).total_seconds()
            time_weight = np.exp(-time_diff / self.sensor_time_threshold)
        else:
            time_weight = 1.0
        
        # Combined weight
        fusion_weight = base_weight * type_weight * time_weight
        track.sensor_weights[plot.sensor_type] = fusion_weight
        
        return fusion_weight
    
    
    def _update_course_modeling(self, track: TrackData, plot: PlotData):
        """
        Update track course modeling for IGMM-based association
        
        Args:
            track: Track to update
            plot: New plot data
        """
        # Calculate current course from velocity components
        if track.speed_ms > self.min_speed_threshold:
            current_course = math.degrees(math.atan2(track.velocity_x, track.velocity_y))
            current_course = (current_course + 360) % 360
            
            # Update course history
            track.course_history.append((current_course, plot.timestamp))
            if len(track.course_history) > 20:  # Keep last 20 course readings
                track.course_history.pop(0)
            
            # Update course statistics
            if len(track.course_history) >= 2:
                # Calculate course variance
                courses = [c[0] for c in track.course_history]
                track.course_variance = self._calculate_angular_variance(courses)
                
                # Calculate course rate (rate of change)
                if len(track.course_history) >= 3:
                    recent_courses = courses[-3:]
                    recent_times = [c[1] for c in track.course_history[-3:]]
                    
                    # Simple linear regression for course rate
                    dt1 = (recent_times[1] - recent_times[0]).total_seconds()
                    dt2 = (recent_times[2] - recent_times[1]).total_seconds()
                    
                    if dt1 > 0 and dt2 > 0:
                        rate1 = self._angular_difference(recent_courses[1], recent_courses[0]) / dt1
                        rate2 = self._angular_difference(recent_courses[2], recent_courses[1]) / dt2
                        track.course_rate = (rate1 + rate2) / 2
        
        # Predict next course using IGMM
        track.predicted_course = self._predict_course_igmm(track)
    
    
    def _calculate_angular_variance(self, angles: List[float]) -> float:
        """
        Calculate variance for circular/angular data
        
        Args:
            angles: List of angles in degrees
            
        Returns:
            Angular variance
        """
        if len(angles) < 2:
            return 0.0
        
        # Convert to unit vectors and calculate circular variance
        x_sum = sum(math.cos(math.radians(a)) for a in angles)
        y_sum = sum(math.sin(math.radians(a)) for a in angles)
        
        n = len(angles)
        r_squared = (x_sum**2 + y_sum**2) / (n * n)
        r = math.sqrt(max(0.0, r_squared))  # Ensure non-negative for sqrt
        
        # Circular variance (1 - r), ensure non-negative result
        return max(0.0, 1.0 - r)
    
    
    def _angular_difference(self, angle1: float, angle2: float) -> float:
        """
        Calculate the smallest angular difference between two angles
        
        Args:
            angle1, angle2: Angles in degrees
            
        Returns:
            Smallest angular difference in degrees
        """
        diff = angle1 - angle2
        while diff > 180:
            diff -= 360
        while diff < -180:
            diff += 360
        return diff
    
    
    def _predict_course_igmm(self, track: TrackData) -> float:
        """
        Predict next course using Infinite Gaussian Mixture Model approach
        
        Args:
            track: Track to predict course for
            
        Returns:
            Predicted course in degrees
        """
        if len(track.course_history) < 3:
            return track.heading_deg
        
        # Simple IGMM approximation using weighted course prediction
        # In a full implementation, this would use Dirichlet Process Gaussian Mixture
        
        courses = [c[0] for c in track.course_history]
        times = [c[1] for c in track.course_history]
        
        # Weight recent courses more heavily
        weights = []
        current_time = times[-1]
        for t in times:
            age_seconds = (current_time - t).total_seconds()
            weight = math.exp(-age_seconds / 10.0)  # 10 second decay
            weights.append(weight)
        
        # Calculate weighted mean course
        x_weighted = sum(w * math.cos(math.radians(c)) for w, c in zip(weights, courses))
        y_weighted = sum(w * math.sin(math.radians(c)) for w, c in zip(weights, courses))
        weight_sum = sum(weights)
        
        if weight_sum > 0:
            x_weighted /= weight_sum
            y_weighted /= weight_sum
            
            predicted_course = math.degrees(math.atan2(y_weighted, x_weighted))
            predicted_course = (predicted_course + 360) % 360
            
            # Add course rate prediction
            if abs(track.course_rate) > 0.1:  # If turning
                dt = 1.0  # Predict 1 second ahead
                predicted_course += track.course_rate * dt
                predicted_course = (predicted_course + 360) % 360
            
            return predicted_course
        
        return track.heading_deg
    
    
    def _find_course_association_candidates(self, plot: PlotData, x: float, y: float, 
                                          timestamp: datetime) -> List[Tuple[TrackData, float]]:
        """
        Find association candidates using course modeling and IGMM approach
        
        Args:
            plot: Plot data
            x, y: Cartesian coordinates
            timestamp: Plot timestamp
            
        Returns:
            List of (track, combined_score) tuples for candidate tracks
        """
        candidates = []
        
        for track in self.active_tracks.values():
            if track.state == TrackState.TERMINATED:
                continue
            
            # Calculate position-based association score
            predicted_pos = self._predict_track_position(track, timestamp)
            position_distance = math.sqrt((x - predicted_pos[0])**2 + (y - predicted_pos[1])**2)
            
            # Skip if too far away
            if position_distance > self._get_association_gate(track):
                continue
            
            # Calculate course-based association score
            course_score = self._calculate_course_association_score(track, plot, x, y, timestamp)
            
            # Combine position and course scores
            # Normalize position distance to 0-1 scale
            max_distance = self._get_association_gate(track)
            position_score = 1.0 - (position_distance / max_distance)
            
            # Weighted combination (adjust weights based on track maturity)
            if len(track.course_history) >= 3:
                # Mature track - give more weight to course
                combined_score = 0.3 * position_score + 0.7 * course_score
            else:
                # New track - rely more on position
                combined_score = 0.7 * position_score + 0.3 * course_score
            
            candidates.append((track, combined_score))
        
        # Sort by combined score (higher is better)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return candidates
    
    
    def _calculate_course_association_score(self, track: TrackData, plot: PlotData, 
                                          x: float, y: float, timestamp: datetime) -> float:
        """
        Calculate course-based association score using IGMM modeling
        
        Args:
            track: Track to score
            plot: Plot data
            x, y: Plot coordinates
            timestamp: Plot timestamp
            
        Returns:
            Course association score (0-1, higher is better)
        """
        if len(track.course_history) < 2:
            return 0.5  # Neutral score for new tracks
        
        # Calculate observed course from track to plot
        last_pos = track.position_history[-1] if track.position_history else (0, 0, timestamp)
        dx = x - last_pos[0]
        dy = y - last_pos[1]
        
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            return 0.5  # No movement
        
        observed_course = math.degrees(math.atan2(dx, dy))
        observed_course = (observed_course + 360) % 360
        
        # Compare with predicted course
        predicted_course = track.predicted_course
        course_difference = abs(self._angular_difference(observed_course, predicted_course))
        
        # Calculate score based on course difference and track course variance
        # Use track's course variance to determine tolerance
        tolerance = max(15.0, 3.0 * math.sqrt(max(0.0, track.course_variance)) * 180.0 / math.pi)
        
        if course_difference <= tolerance:
            # Good match - calculate probability using Gaussian
            course_score = math.exp(-(course_difference**2) / (2 * tolerance**2))
        else:
            # Poor match
            course_score = 0.1
        
        # Boost score for consistent tracks
        if track.course_variance < 0.1:  # Very consistent course
            course_score *= 1.2
        
        return min(course_score, 1.0)
    
    
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
    
    
    def get_tracks_for_display(self, app=None) -> List[Dict]:
        """
        Get track data formatted for display
        
        Args:
            app: Flask app instance for database access (not used anymore)
            
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
                
                # Convert speed from m/s to knots and round
                speed_knots = round(track.speed_ms / 0.514444)
                
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
                    'altitude': track.altitude,      # Use altitude from most recent plot
                    'speed': speed_knots,            # Convert to knots and round
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
    Create default configuration for enhanced track calculator
    
    Returns:
        Default configuration dictionary
    """
    return {
        # Basic tracking parameters - optimized for aircraft
        'max_association_distance': 10000.0,    # meters (10km for aircraft)
        'max_azimuth_difference': 5.0,           # degrees (more permissive for aircraft)
        'use_azimuth_correlation': True,         # Enable azimuth correlation
        'use_course_modeling': True,             # Enable IGMM course modeling
        'track_confirmation_threshold': 2,       # plots (reduced for faster confirmation)
        'track_termination_threshold': 15,       # missed scans (increased for aircraft)
        'coasting_threshold': 8,                 # missed scans (increased for aircraft)
        'min_speed_threshold': 5.0,             # m/s (aircraft minimum speed)
        'max_speed_threshold': 400.0,           # m/s (increased for aircraft)
        'process_noise_std': 15.0,              # meters (increased for aircraft)
        'measurement_noise_std': 25.0,          # meters (increased for aircraft)
        'time_delta': 1.0,                      # seconds
        
        # Maneuver detection parameters
        'maneuver_threshold': 1.5,              # G force (more sensitive for aircraft)
        'acceleration_noise_std': 5.0,          # m/s² (increased for aircraft)
        
        # Multi-sensor fusion parameters
        'sensor_fusion_enabled': True,
        'sensor_time_threshold': 10.0,          # seconds (increased for aircraft)
        
        # Probabilistic data association parameters - more permissive for aircraft
        'pda_enabled': True,
        'pda_gate_threshold': 15.0,             # Increased from 9.21 for aircraft
        'clutter_density': 1e-7                 # Lower clutter density for airspace
    }


if __name__ == "__main__":
    # Example usage of enhanced track calculator
    config = create_default_config()
    
    # Enable all advanced features
    config['pda_enabled'] = True
    config['sensor_fusion_enabled'] = True
    config['maneuver_threshold'] = 1.5  # More sensitive maneuver detection
    
    tracker = TrackCalculator(config)
    
    # Create sample plots with different sensor types
    current_time = datetime.now()
    sample_plots = [
        # Radar plot
        PlotData(
            timestamp=current_time,
            range_m=5000,
            azimuth_deg=45,
            latitude=28.1,
            longitude=-80.6,
            sensor_type=SensorType.RADAR,
            quality=0.95
        ),
        # ADS-B plot at similar location
        PlotData(
            timestamp=current_time + timedelta(milliseconds=500),
            range_m=5020,
            azimuth_deg=45.1,
            latitude=28.101,
            longitude=-80.599,
            sensor_type=SensorType.ADSB,
            quality=0.98,
            squawk="1234"
        ),
        # Next radar plot showing maneuver
        PlotData(
            timestamp=current_time + timedelta(seconds=1),
            range_m=5100,
            azimuth_deg=47,  # Turning
            latitude=28.11,
            longitude=-80.59,
            sensor_type=SensorType.RADAR,
            quality=0.92
        ),
        # Corresponding ADS-B plot
        PlotData(
            timestamp=current_time + timedelta(seconds=1, milliseconds=200),
            range_m=5110,
            azimuth_deg=47.2,
            latitude=28.111,
            longitude=-80.588,
            sensor_type=SensorType.ADSB,
            quality=0.97,
            squawk="1234"
        )
    ]
    
    # Process plots
    tracks = tracker.process_plot_batch(sample_plots)
    
    # Print results
    print(f"Processed {len(sample_plots)} plots from {len(set(p.sensor_type for p in sample_plots))} sensor types")
    print(f"Active tracks: {len(tracks)}")
    
    for track in tracks.values():
        print(f"\nTrack {track.track_id}:")
        print(f"  State: {track.state.value}")
        print(f"  Speed: {track.speed_ms:.1f} m/s")
        print(f"  Heading: {track.heading_deg:.1f}°")
        print(f"  Acceleration: {math.sqrt(track.acceleration_x**2 + track.acceleration_y**2):.2f} m/s²")
        print(f"  Maneuver: {track.maneuver_state.value}")
        print(f"  Plots: {track.plot_count}")
        print(f"  Sensors: {[s.value for s in track.sensor_sources]}")
        print(f"  Quality: {track.quality_score:.3f}")
    
    # Print statistics
    stats = tracker.get_track_summary()
    print(f"\nTracking Statistics:")
    print(f"  Total plots processed: {stats['statistics']['total_plots_processed']}")
    print(f"  Tracks initiated: {stats['statistics']['tracks_initiated']}")
    print(f"  Maneuver detections: {stats['statistics']['maneuver_detections']}")
    print(f"  Sensor fusions: {stats['statistics']['sensor_fusions']}")
    print(f"  Active tracks by state: {stats['tracks_by_state']}")
    
    print(f"\nEnhanced features:")
    print(f"  ✓ Probabilistic Data Association (PDA)")
    print(f"  ✓ Multi-sensor fusion (Radar + ADS-B)")
    print(f"  ✓ Maneuver detection with acceleration estimation")
    print(f"  ✓ Extended Kalman filter (6-state: position, velocity, acceleration)")
