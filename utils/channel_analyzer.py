"""
Channel Analyzer Module

This module provides functionality for analyzing WiFi channel usage and congestion,
detecting overlapping channels, and recommending optimal channels.
"""

import logging
from typing import Dict, List, Tuple, Optional
import statistics

logger = logging.getLogger(__name__)

# Channel width in MHz for 2.4 GHz
CHANNEL_WIDTH_2_4GHZ = 22

# Non-overlapping channels in 2.4 GHz band
NON_OVERLAPPING_2_4GHZ = [1, 6, 11]

# Channel characteristics by band
CHANNELS_2_4GHZ = list(range(1, 15))  # Channels 1-14
CHANNELS_5GHZ = [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 149, 153, 157, 161, 165]

# Channel center frequencies (in MHz)
CHANNEL_FREQUENCIES = {
    # 2.4 GHz band
    1: 2412, 2: 2417, 3: 2422, 4: 2427, 5: 2432,
    6: 2437, 7: 2442, 8: 2447, 9: 2452, 10: 2457,
    11: 2462, 12: 2467, 13: 2472, 14: 2484,
    # 5 GHz band
    36: 5180, 40: 5200, 44: 5220, 48: 5240,
    52: 5260, 56: 5280, 60: 5300, 64: 5320,
    100: 5500, 104: 5520, 108: 5540, 112: 5560,
    116: 5580, 120: 5600, 124: 5620, 128: 5640,
    132: 5660, 136: 5680, 140: 5700, 144: 5720,
    149: 5745, 153: 5765, 157: 5785, 161: 5805, 165: 5825
}

# DFS channels (require Dynamic Frequency Selection)
DFS_CHANNELS = [52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140]

class ChannelAnalyzer:
    """
    A class for analyzing WiFi channels, detecting overlap, and recommending
    optimal channels.
    """
    
    def __init__(self):
        """Initialize the channel analyzer."""
        self.channel_usage = {}  # Tracks networks per channel
    
    def analyze_channel_usage(self, networks: List[Dict]) -> Dict:
        """
        Analyze channel usage based on networks list.
        
        Args:
            networks: List of network dictionaries with channel and signal information
            
        Returns:
            Dictionary with channel usage analysis
        """
        # Reset channel usage
        self.channel_usage = {
            '2.4GHz': {channel: [] for channel in CHANNELS_2_4GHZ},
            '5GHz': {channel: [] for channel in CHANNELS_5GHZ}
        }
        
        # Count networks per channel
        for network in networks:
            try:
                # Extract BSSID info (assuming networks have multiple BSSIDs)
                for bssid_info in network.get('bssids', []):
                    channel = bssid_info.get('channel')
                    signal_dbm = bssid_info.get('signal_dbm')
                    band = bssid_info.get('band')
                    
                    if channel and signal_dbm:
                        if band == '2.4 GHz' and channel in CHANNELS_2_4GHZ:
                            self.channel_usage['2.4GHz'][channel].append({
                                'ssid': network.get('ssid', 'Unknown'),
                                'bssid': bssid_info.get('bssid', 'Unknown'),
                                'signal_dbm': signal_dbm
                            })
                        elif band == '5 GHz' and channel in CHANNELS_5GHZ:
                            self.channel_usage['5GHz'][channel].append({
                                'ssid': network.get('ssid', 'Unknown'),
                                'bssid': bssid_info.get('bssid', 'Unknown'),
                                'signal_dbm': signal_dbm
                            })
            except (KeyError, TypeError) as e:
                logger.warning(f"Error processing network: {e}")
                continue
        
        # Analyze congestion
        analysis = {
            '2.4GHz': self._analyze_band_congestion('2.4GHz'),
            '5GHz': self._analyze_band_congestion('5GHz'),
            'recommendations': self._generate_recommendations()
        }
        
        return analysis
    
    def _analyze_band_congestion(self, band: str) -> Dict:
        """
        Analyze congestion for a specific frequency band.
        
        Args:
            band: Frequency band ('2.4GHz' or '5GHz')
            
        Returns:
            Dictionary with congestion analysis for the band
        """
        channels = self.channel_usage.get(band, {})
        congestion_scores = {}
        network_counts = {}
        signal_strengths = {}
        
        # Calculate basic metrics for each channel
        for channel, networks in channels.items():
            network_counts[channel] = len(networks)
            
            # Calculate average signal strength if networks exist
            if networks:
                signal_strengths[channel] = statistics.mean([n['signal_dbm'] for n in networks])
            else:
                signal_strengths[channel] = None
        
        # Calculate congestion scores based on network count and overlaps
        if band == '2.4GHz':
            congestion_scores = self._calculate_2_4ghz_congestion(network_counts, signal_strengths)
        else:  # 5GHz
            congestion_scores = self._calculate_5ghz_congestion(network_counts, signal_strengths)
        
        return {
            'network_counts': network_counts,
            'signal_strengths': signal_strengths,
            'congestion_scores': congestion_scores
        }
    
    def _calculate_2_4ghz_congestion(self, network_counts: Dict[int, int], 
                                    signal_strengths: Dict[int, float]) -> Dict[int, float]:
        """
        Calculate congestion scores for 2.4 GHz channels, considering overlap.
        
        Args:
            network_counts: Dictionary of channel to network count
            signal_strengths: Dictionary of channel to average signal strength
            
        Returns:
            Dictionary of channel to congestion score (0-100)
        """
        congestion_scores = {}
        
        for channel in CHANNELS_2_4GHZ:
            # Start with base score from network count on this channel
            if network_counts[channel] == 0:
                congestion_scores[channel] = 0
                continue
                
            base_score = min(100, network_counts[channel] * 20)  # Each network adds 20 points
            
            # Consider overlapping channels (channels within 4 of current channel overlap in 2.4GHz)
            overlap_factor = 0
            for other_channel in CHANNELS_2_4GHZ:
                if other_channel == channel:
                    continue
                    
                # Calculate overlap based on channel distance
                # 2.4 GHz channels are 5 MHz apart, with 22 MHz bandwidth
                channel_distance = abs(channel - other_channel)
                if channel_distance < 5:  # Significant overlap
                    overlap_percentage = max(0, (5 - channel_distance) / 5)
                    
                    # Weight by network count and signal strength
                    if network_counts[other_channel] > 0 and signal_strengths[other_channel]:
                        # Normalize signal strength from -100..-30 to 0..1
                        signal_factor = min(1.0, max(0.0, (signal_strengths[other_channel] + 100) / 70))
                        overlap_factor += (network_counts[other_channel] * overlap_percentage * signal_factor)
            
            # Add overlap factor to base score
            overlap_score = min(100, overlap_factor * 10)
            final_score = min(100, base_score + overlap_score)
            
            congestion_scores[channel] = round(final_score, 1)
        
        return congestion_scores
    
    def _calculate_5ghz_congestion(self, network_counts: Dict[int, int],
                                  signal_strengths: Dict[int, float]) -> Dict[int, float]:
        """
        Calculate congestion scores for 5 GHz channels.
        
        Args:
            network_counts: Dictionary of channel to network count
            signal_strengths: Dictionary of channel to average signal strength
            
        Returns:
            Dictionary of channel to congestion score (0-100)
        """
        congestion_scores = {}
        
        for channel in CHANNELS_5GHZ:
            if network_counts[channel] == 0:
                congestion_scores[channel] = 0
                continue
                
            # 5 GHz channels generally don't overlap with standard 20 MHz width
            # So congestion is mostly based on the number of networks
            base_score = min(100, network_counts[channel] * 20)  # Each network adds 20 points
            
            # Add penalty for DFS channels (less desirable)
            dfs_penalty = 10 if channel in DFS_CHANNELS else 0
            
            final_score = min(100, base_score + dfs_penalty)
            congestion_scores[channel] = round(final_score, 1)
        
        return congestion_scores
    
    def _generate_recommendations(self) -> Dict:
        """
        Generate channel recommendations based on congestion analysis.
        
        Returns:
            Dictionary with channel recommendations for each band
        """
        recommendations = {}
        
        # 2.4 GHz recommendation - prefer channels 1, 6, 11
        band_2_4 = self._analyze_band_congestion('2.4GHz')
        congestion_2_4 = band_2_4['congestion_scores']
        
        # First check non-overlapping channels
        non_overlapping_congestion = {ch: congestion_2_4.get(ch, 100) for ch in NON_OVERLAPPING_2_4GHZ}
        recommended_2_4 = min(non_overlapping_congestion.items(), key=lambda x: x[1])[0]
        
        # If all non-overlapping channels have high congestion, consider all channels
        if min(non_overlapping_congestion.values()) > 70:
            all_channels_congestion = {ch: score for ch, score in congestion_2_4.items() if ch in CHANNELS_2_4GHZ}
            if all_channels_congestion:
                recommended_2_4 = min(all_channels_congestion.items(), key=lambda x: x[1])[0]
        
        # 5 GHz recommendation
        band_5 = self._analyze_band_congestion('5GHz')
        congestion_5 = band_5['congestion_scores']
        
        # Prefer non-DFS channels first
        non_dfs_channels = [ch for ch in CHANNELS_5GHZ if ch not in DFS_CHANNELS]
        non_dfs_congestion = {ch: congestion_5.get(ch, 100) for ch in non_dfs_channels}
        
        if non_dfs_congestion and min(non_dfs_congestion.values()) < 50:
            # If we have good non-DFS channels, use them
            recommended_5 = min(non_dfs_congestion.items(), key=lambda x: x[1])[0]
        else:
            # Otherwise consider all 5 GHz channels
            all_channels_congestion = {ch: score for ch, score in congestion_5.items() if ch in CHANNELS_5GHZ}
            if all_channels_congestion:
                recommended_5 = min(all_channels_congestion.items(), key=lambda x: x[1])[0]
            else:
                recommended_5 = 36  # Default to a common channel if no data
        
        recommendations['2.4GHz'] = {
            'channel': recommended_2_4,
            'congestion': congestion_2_4.get(recommended_2_4, 0),
            'reason': "Least congested non-overlapping channel" if recommended_2_4 in NON_OVERLAPPING_2_4GHZ 
                     else "All standard non-overlapping channels are congested"
        }
        
        recommendations['5GHz'] = {
            'channel': recommended_5,
            'congestion': congestion_5.get(recommended_5, 0),
            'reason': "Least congested non-DFS channel" if recommended_5 not in DFS_CHANNELS
                     else "Least congested channel (requires DFS support)"
        }
        
        return recommendations
    
    def get_channel_overlap(self, channel: int, band: str = '2.4GHz') -> List[int]:
        """
        Get a list of channels that overlap with the given channel.
        
        Args:
            channel: The channel number to check
            band: The frequency band ('2.4GHz' or '5GHz')
            
        Returns:
            List of overlapping channel numbers
        """
        if band == '2.4GHz':
            # In 2.4 GHz, channels with numbers differing by less than 5 overlap
            return [ch for ch in CHANNELS_2_4GHZ if 0 < abs(ch - channel) < 5]
        else:
            # In 5 GHz with 20 MHz channels, there's generally no overlap
            return []
    
    def get_visualization_data(self) -> Dict:
        """
        Prepare data for channel usage visualization.
        
        Returns:
            Dictionary with data for visualization
        """
        # Analyze congestion for both bands
        analysis_2_4 = self._analyze_band_congestion('2.4GHz')
        analysis_5 = self._analyze_band_congestion('5GHz')
        
        # Get recommendations
        recommendations = self._generate_recommendations()
        
        # Prepare data for visualization
        visualization_data = {
            '2.4GHz': {
                'channels': CHANNELS_2_4GHZ,
                'network_counts': [analysis_2_4['network_counts'].get(ch, 0) for ch in CHANNELS_2_4GHZ],
                'signal_strengths': [analysis_2_4['signal_strengths'].get(ch) for ch in CHANNELS_2_4GHZ],
                'congestion_scores': [analysis_2_4['congestion_scores'].get(ch, 0) for ch in CHANNELS_2_4GHZ],
                'recommended_channel': recommendations['2.4GHz']['channel'],
                'non_overlapping': NON_OVERLAPPING_2_4GHZ
            },
            '5GHz': {
                'channels': CHANNELS_5GHZ,
                'network_counts': [analysis_5['network_counts'].get(ch, 0) for ch in CHANNELS_5GHZ],
                'signal_strengths': [analysis_5['signal_strengths'].get(ch) for ch in CHANNELS_5GHZ],
                'congestion_scores': [analysis_5['congestion_scores'].get(ch, 0) for ch in CHANNELS_5GHZ],
                'recommended_channel': recommendations['5GHz']['channel'],
                'dfs_channels': DFS_CHANNELS
            }
        }
        
        return visualization_data