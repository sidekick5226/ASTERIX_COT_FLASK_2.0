#!/usr/bin/env python3
"""
IGMM Course Modeling Track Association
Implementation based on "Plot-to-Track Association Using IGMM Course Modeling 
for Target Tracking With Compact HFSWR" approach
"""

import numpy as np
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from sklearn.mixture import BayesianGaussianMixture
import logging

logger = logging.getLogger(__name__)


@dataclass
class CourseModel:
    """Course model for a track using IGMM"""
    # Gaussian mixture model for course prediction
    gmm: Optional[BayesianGaussianMixture] = None
    
    # Course history (heading, speed, time_delta)
    course_history: List[Tuple[float, float, float]] = field(default_factory=list)
    
    # Model parameters
    max_components: int = 5
    confidence_threshold: float = 0.3
    history_length: int = 10
    
    def update_course(self, heading: float, speed: float, time_delta: float):
        """Update course model with new measurement"""
        # Add to history
        self.course_history.append((heading, speed, time_delta))
        
        # Limit history length
        if len(self.course_history) > self.history_length:
            self.course_history.pop(0)
        
        # Retrain GMM if we have enough data
        if len(self.course_history) >= 3:
            self._train_gmm()
    
    def _train_gmm(self):
        """Train IGMM on course history"""
        if len(self.course_history) < 3:
            return
            
        # Prepare training data: [heading, speed, acceleration]
        features = []
        for i in range(1, len(self.course_history)):
            h_prev, s_prev, dt_prev = self.course_history[i-1]
            h_curr, s_curr, dt_curr = self.course_history[i]
            
            # Calculate acceleration
            acceleration = (s_curr - s_prev) / max(dt_curr, 0.1)
            
            # Normalize heading change
            heading_change = self._normalize_heading_diff(h_curr - h_prev)
            
            features.append([heading_change, s_curr, acceleration])
        
        if len(features) >= 2:
            X = np.array(features)
            
            # Use Bayesian GMM (approximates IGMM)
            self.gmm = BayesianGaussianMixture(
                n_components=min(self.max_components, len(features)),
                covariance_type='full',
                weight_concentration_prior=1.0,
                random_state=42
            )
            
            try:
                self.gmm.fit(X)
            except Exception as e:
                logger.warning(f"Failed to train course GMM: {e}")
                self.gmm = None
    
    def predict_position(self, current_pos: Tuple[float, float], 
                        current_heading: float, current_speed: float,
                        prediction_time: float) -> Tuple[float, float, float]:
        """
        Predict future position using IGMM course model
        
        Returns: (predicted_x, predicted_y, confidence)
        """
        if self.gmm is None or len(self.course_history) < 2:
            # Fallback to simple linear prediction
            x, y = current_pos
            heading_rad = math.radians(current_heading)
            distance = current_speed * prediction_time
            
            pred_x = x + distance * math.cos(heading_rad)
            pred_y = y + distance * math.sin(heading_rad)
            
            return pred_x, pred_y, 0.1
        
        # Use GMM to predict course change
        last_course = self.course_history[-1]
        if len(self.course_history) >= 2:
            prev_course = self.course_history[-2]
            heading_change = self._normalize_heading_diff(last_course[0] - prev_course[0])
            acceleration = (last_course[1] - prev_course[1]) / max(last_course[2], 0.1)
        else:
            heading_change = 0.0
            acceleration = 0.0
        
        # Predict next course using GMM
        current_features = np.array([[heading_change, current_speed, acceleration]])
        
        try:
            # Get most likely component
            log_probs = self.gmm.score_samples(current_features)
            confidence = math.exp(log_probs[0])
            
            # Use GMM means for prediction
            weights = np.array(self.gmm.weights_)
            means = np.array(self.gmm.means_)
            
            # Weighted prediction
            predicted_heading_change = np.sum(weights * means[:, 0])
            predicted_speed = np.sum(weights * means[:, 1])
            
            # Apply prediction
            new_heading = current_heading + predicted_heading_change
            new_speed = max(0.1, predicted_speed)
            
            # Calculate position
            x, y = current_pos
            heading_rad = math.radians(new_heading)
            distance = new_speed * prediction_time
            
            pred_x = x + distance * math.cos(heading_rad)
            pred_y = y + distance * math.sin(heading_rad)
            
            return pred_x, pred_y, min(confidence, 1.0)
            
        except Exception as e:
            logger.warning(f"GMM prediction failed: {e}")
            # Fallback to linear prediction
            x, y = current_pos
            heading_rad = math.radians(current_heading)
            distance = current_speed * prediction_time
            
            pred_x = x + distance * math.cos(heading_rad)
            pred_y = y + distance * math.sin(heading_rad)
            
            return pred_x, pred_y, 0.1
    
    def _normalize_heading_diff(self, heading_diff: float) -> float:
        """Normalize heading difference to [-180, 180]"""
        while heading_diff > 180:
            heading_diff -= 360
        while heading_diff < -180:
            heading_diff += 360
        return heading_diff


@dataclass
class IGMMTrackData:
    """Enhanced track data with IGMM course modeling"""
    track_id: str
    x: float
    y: float
    heading: float
    speed: float
    timestamp: datetime
    
    # Course model
    course_model: CourseModel = field(default_factory=CourseModel)
    
    # Track statistics
    plot_count: int = 0
    consecutive_misses: int = 0
    quality_score: float = 0.0
    
    # Track state
    state: str = "Tentative"  # Tentative, Confirmed, Coasting
    
    # Position history for course calculation
    position_history: List[Tuple[float, float, datetime]] = field(default_factory=list)
    
    # Prediction cache (private attributes for internal use)
    _predicted_x: float = field(default=0.0, init=False)
    _predicted_y: float = field(default=0.0, init=False)
    _prediction_confidence: float = field(default=0.0, init=False)
    
    def update_with_plot(self, x: float, y: float, timestamp: datetime):
        """Update track with new plot measurement"""
        # Calculate course if we have previous position
        if self.position_history:
            prev_x, prev_y, prev_time = self.position_history[-1]
            
            # Calculate movement
            dx = x - prev_x
            dy = y - prev_y
            dt = (timestamp - prev_time).total_seconds()
            
            if dt > 0:
                distance = math.sqrt(dx*dx + dy*dy)
                speed = distance / dt
                heading = math.degrees(math.atan2(dy, dx))
                
                # Update course model
                self.course_model.update_course(heading, speed, dt)
                
                # Update track state
                self.heading = heading
                self.speed = speed
        
        # Update position
        self.x = x
        self.y = y
        self.timestamp = timestamp
        
        # Update history
        self.position_history.append((x, y, timestamp))
        if len(self.position_history) > 20:  # Keep last 20 positions
            self.position_history.pop(0)
        
        # Update statistics
        self.plot_count += 1
        self.consecutive_misses = 0
        self.quality_score = min(1.0, self.plot_count / 10.0)
        
        # Update state
        if self.plot_count >= 3 and self.state == "Tentative":
            self.state = "Confirmed"
    
    def get_association_gate(self, base_distance: float) -> float:
        """Get dynamic association gate based on course model confidence"""
        if self.course_model.gmm is not None:
            # Smaller gate for more confident course models
            confidence = self.course_model.confidence_threshold
            gate_factor = 2.0 - confidence  # Range: 1.0 to 2.0
        else:
            gate_factor = 2.0  # Larger gate for uncertain tracks
        
        # Adjust for track quality
        quality_factor = max(0.5, self.quality_score)
        
        return base_distance * gate_factor / quality_factor


class IGMMPlotTrackAssociator:
    """
    IGMM-based plot-to-track association system
    """
    
    def __init__(self, config: Dict | None = None):
        self.config = config or {}
        
        # Association parameters
        self.base_association_distance = self.config.get('base_association_distance', 500.0)
        self.course_weight = self.config.get('course_weight', 0.3)
        self.position_weight = self.config.get('position_weight', 0.7)
        
        # Track management
        self.confirmation_threshold = self.config.get('confirmation_threshold', 3)
        self.termination_threshold = self.config.get('termination_threshold', 5)
        
        # Active tracks
        self.tracks: Dict[str, IGMMTrackData] = {}
        self.next_track_id = 1
        
        logger.info("IGMM track associator initialized")
    
    def process_plots(self, plots: List[Dict]) -> List[IGMMTrackData]:
        """
        Process incoming plots using IGMM course modeling
        
        Args:
            plots: List of plot dictionaries with x, y, timestamp
            
        Returns:
            List of updated tracks
        """
        current_time = datetime.now()
        
        # Update track predictions
        self._update_track_predictions(current_time)
        
        # Associate plots to tracks
        for plot in plots:
            self._associate_plot(plot, current_time)
        
        # Track maintenance
        self._manage_tracks(current_time)
        
        return list(self.tracks.values())
    
    def _update_track_predictions(self, current_time: datetime):
        """Update track position predictions using IGMM course models"""
        for track in self.tracks.values():
            if track.timestamp:
                dt = (current_time - track.timestamp).total_seconds()
                if dt > 0:
                    # Get IGMM prediction
                    pred_x, pred_y, confidence = track.course_model.predict_position(
                        (track.x, track.y), track.heading, track.speed, dt
                    )
                    
                    # Update predicted position (but keep original as backup)
                    track._predicted_x = pred_x
                    track._predicted_y = pred_y
                    track._prediction_confidence = confidence
    
    def _associate_plot(self, plot: Dict, current_time: datetime):
        """Associate a plot with existing tracks or create new track"""
        x, y = plot['x'], plot['y']
        
        # Find candidate tracks
        candidates = []
        
        for track_id, track in self.tracks.items():
            # Calculate association cost
            cost = self._calculate_association_cost(plot, track)
            gate = track.get_association_gate(self.base_association_distance)
            
            if cost < gate:
                candidates.append((track_id, cost))
        
        if candidates:
            # Associate with best candidate
            best_track_id, _ = min(candidates, key=lambda x: x[1])
            best_track = self.tracks[best_track_id]
            best_track.update_with_plot(x, y, current_time)
            
            logger.debug(f"Associated plot to track {best_track_id}")
        else:
            # Create new track
            self._create_new_track(plot, current_time)
    
    def _calculate_association_cost(self, plot: Dict, track: IGMMTrackData) -> float:
        """
        Calculate association cost using position and course information
        """
        x, y = plot['x'], plot['y']
        
        # Position distance
        if hasattr(track, '_predicted_x'):
            # Use IGMM prediction if available
            pos_dist = math.sqrt((x - track._predicted_x)**2 + (y - track._predicted_y)**2)
            
            # Weight by prediction confidence
            confidence = getattr(track, '_prediction_confidence', 0.1)
            pos_cost = pos_dist * (2.0 - confidence)
        else:
            # Fallback to current position
            pos_dist = math.sqrt((x - track.x)**2 + (y - track.y)**2)
            pos_cost = pos_dist
        
        # Course consistency cost
        course_cost = 0.0
        if len(track.position_history) >= 2:
            # Calculate expected course
            prev_pos = track.position_history[-1]
            expected_heading = math.degrees(math.atan2(y - prev_pos[1], x - prev_pos[0]))
            
            heading_diff = abs(expected_heading - track.heading)
            if heading_diff > 180:
                heading_diff = 360 - heading_diff
            
            course_cost = heading_diff / 180.0 * self.base_association_distance
        
        # Combined cost
        total_cost = (self.position_weight * pos_cost + 
                     self.course_weight * course_cost)
        
        return total_cost
    
    def _create_new_track(self, plot: Dict, current_time: datetime):
        """Create new track from plot"""
        track_id = f"track_{self.next_track_id:06d}"
        self.next_track_id += 1
        
        track = IGMMTrackData(
            track_id=track_id,
            x=plot['x'],
            y=plot['y'],
            heading=0.0,  # Will be calculated with next plot
            speed=0.0,
            timestamp=current_time
        )
        
        track.update_with_plot(plot['x'], plot['y'], current_time)
        self.tracks[track_id] = track
        
        logger.info(f"Created new track {track_id} at ({plot['x']:.1f}, {plot['y']:.1f})")
    
    def _manage_tracks(self, current_time: datetime):
        """Manage track lifecycle"""
        tracks_to_remove = []
        
        for track_id, track in self.tracks.items():
            # Update consecutive misses
            if track.timestamp:
                time_since_update = (current_time - track.timestamp).total_seconds()
                if time_since_update > 10:  # 10 seconds without update
                    track.consecutive_misses += 1
            
            # Remove tracks that exceed termination threshold
            if track.consecutive_misses > self.termination_threshold:
                tracks_to_remove.append(track_id)
                logger.info(f"Terminating track {track_id}")
            elif track.consecutive_misses > 0:
                track.state = "Coasting"
        
        # Remove terminated tracks
        for track_id in tracks_to_remove:
            del self.tracks[track_id]
    
    def get_active_tracks(self) -> List[Dict]:
        """Get active tracks in standard format"""
        active_tracks = []
        
        for track in self.tracks.values():
            if track.state in ["Confirmed", "Coasting"]:
                active_tracks.append({
                    'track_id': track.track_id,
                    'x': track.x,
                    'y': track.y,
                    'heading': track.heading,
                    'speed': track.speed,
                    'quality': track.quality_score,
                    'state': track.state,
                    'plot_count': track.plot_count,
                    'course_confidence': getattr(track, '_prediction_confidence', 0.0)
                })
        
        return active_tracks
