"""
Signal Utilities Module

This module provides functions for WiFi signal processing, conversion between different
signal strength representations, quality assessment, and trend analysis.
"""

import math
from typing import List, Tuple, Dict, Optional
import numpy as np
from datetime import datetime

# Constants for signal conversion and quality assessment
RSSI_MAX = -30.0  # Maximum expected RSSI value in dBm (very strong signal)
RSSI_MIN = -100.0  # Minimum expected RSSI value in dBm (very weak signal)

def percentage_to_dbm(percentage: float) -> float:
    """
    Convert signal strength percentage to dBm.
    
    Args:
        percentage: Signal strength as percentage (0-100)
        
    Returns:
        Signal strength in dBm
        
    Formula used: dBm = (percentage * 0.5) - 100
    """
    if not 0 <= percentage <= 100:
        raise ValueError(f"Percentage must be between 0 and 100, got {percentage}")
    
    return (percentage * 0.5) - 100

def dbm_to_percentage(dbm: float) -> float:
    """
    Convert signal strength in dBm to percentage.
    
    Args:
        dbm: Signal strength in dBm
        
    Returns:
        Signal strength as percentage (0-100)
    """
    # Ensure the result is clamped between 0-100
    percentage = (dbm + 100) * 2
    return max(0, min(100, percentage))

def dbm_to_quality(dbm: float) -> float:
    """
    Convert dBm signal strength to a quality score (0-100).
    
    This function provides a more nuanced mapping than a simple percentage
    by using a logarithmic scale to better represent how signal strength
    affects actual connection quality.
    
    Args:
        dbm: Signal strength in dBm
        
    Returns:
        Signal quality as percentage (0-100)
    """
    if dbm >= RSSI_MAX:
        return 100.0
    elif dbm <= RSSI_MIN:
        return 0.0
    else:
        # Logarithmic scale for more realistic quality representation
        return max(0, min(100, 
               (100.0 * (dbm - RSSI_MIN) / (RSSI_MAX - RSSI_MIN))**0.75))

def get_signal_quality_label(dbm: float) -> str:
    """
    Get a descriptive label for signal strength in dBm.
    
    Args:
        dbm: Signal strength in dBm
        
    Returns:
        String description of signal quality
    """
    if dbm >= -50:
        return "Excellent"
    elif dbm >= -60:
        return "Very Good"
    elif dbm >= -67:
        return "Good"
    elif dbm >= -70:
        return "Fair"
    elif dbm >= -80:
        return "Poor"
    else:
        return "Very Poor"

def calculate_snr(signal_dbm: float, noise_floor_dbm: float = -95) -> float:
    """
    Calculate Signal-to-Noise Ratio (SNR) in dB.
    
    Args:
        signal_dbm: Signal strength in dBm
        noise_floor_dbm: Noise floor in dBm, default is -95 dBm for typical environments
        
    Returns:
        SNR in dB
    """
    return signal_dbm - noise_floor_dbm

def get_expected_throughput(snr_db: float) -> float:
    """
    Estimate theoretical maximum throughput based on SNR.
    This is a simplified model and actual throughput will depend on many factors.
    
    Args:
        snr_db: Signal-to-Noise Ratio in dB
        
    Returns:
        Estimated throughput in Mbps
    """
    # Shannon capacity theorem simplified: C = B * log2(1 + SNR)
    # Assuming 20 MHz channel width for 2.4 GHz WiFi
    # This is simplified and doesn't account for protocol overhead
    channel_width_mhz = 20
    
    # Prevent math domain error with very low SNR
    if snr_db <= 0:
        return 0
    
    snr_linear = 10 ** (snr_db / 10)
    capacity_bits = channel_width_mhz * 1e6 * math.log2(1 + snr_linear)
    
    # Convert to Mbps and account for typical overhead (~40-60%)
    throughput_mbps = capacity_bits / 1e6 * 0.5  # 50% efficiency
    
    return round(throughput_mbps, 1)

def analyze_signal_trend(signal_history: List[Tuple[datetime, float]]) -> Dict[str, any]:
    """
    Analyze signal strength trend over time.
    
    Args:
        signal_history: List of tuples containing (timestamp, signal_dbm)
        
    Returns:
        Dictionary with trend analysis results including:
        - trend: overall trend direction ('improving', 'degrading', 'stable')
        - stability: signal stability measure (0-1)
        - min_signal: minimum signal value
        - max_signal: maximum signal value
        - avg_signal: average signal value
        - std_dev: standard deviation of signal
    """
    if not signal_history or len(signal_history) < 2:
        return {
            'trend': 'unknown',
            'stability': 0.0,
            'min_signal': None,
            'max_signal': None,
            'avg_signal': None,
            'std_dev': None
        }
    
    # Extract signal values
    signals = [s[1] for s in signal_history]
    
    # Calculate basic statistics
    min_signal = min(signals)
    max_signal = max(signals)
    avg_signal = sum(signals) / len(signals)
    
    # Standard deviation as a measure of stability
    std_dev = np.std(signals)
    stability = max(0, min(1, 1 - (std_dev / 20)))  # Normalize to 0-1 range
    
    # Determine trend by comparing first and last quartiles
    n = len(signals)
    first_quarter = signals[:n//4] if n >= 4 else signals[:1]
    last_quarter = signals[-n//4:] if n >= 4 else signals[-1:]
    
    first_avg = sum(first_quarter) / len(first_quarter)
    last_avg = sum(last_quarter) / len(last_quarter)
    
    trend = 'stable'
    if last_avg - first_avg > 3:  # More than 3 dBm improvement
        trend = 'improving'
    elif first_avg - last_avg > 3:  # More than 3 dBm degradation
        trend = 'degrading'
    
    return {
        'trend': trend,
        'stability': stability,
        'min_signal': min_signal,
        'max_signal': max_signal,
        'avg_signal': avg_signal,
        'std_dev': std_dev
    }

def get_channel_width_mhz(channel: int, width_code: Optional[str] = None) -> int:
    """
    Determine channel width in MHz based on channel number and optional width code.
    
    Args:
        channel: WiFi channel number
        width_code: Optional width code (e.g., '20', '40', '80')
        
    Returns:
        Channel width in MHz
    """
    # Default widths based on band
    if 1 <= channel <= 14:  # 2.4 GHz
        default_width = 20
    else:  # 5 GHz
        default_width = 20
    
    # If width code is provided, use it
    if width_code:
        try:
            return int(width_code)
        except (ValueError, TypeError):
            pass
    
    return default_width

def get_frequency_from_channel(channel: int) -> float:
    """
    Convert WiFi channel number to center frequency in GHz.
    
    Args:
        channel: WiFi channel number
        
    Returns:
        Center frequency in GHz
    """
    if 1 <= channel <= 14:  # 2.4 GHz band
        if channel == 14:  # Special case for Japan
            return 2.484
        else:
            return 2.407 + 0.005 * channel
    elif 36 <= channel <= 165:  # 5 GHz band
        return 5.0 + 0.005 * channel
    else:
        raise ValueError(f"Invalid channel number: {channel}")

def get_band_from_channel(channel: int) -> str:
    """
    Determine frequency band from channel number.
    
    Args:
        channel: WiFi channel number
        
    Returns:
        Frequency band label ("2.4 GHz" or "5 GHz")
    """
    if 1 <= channel <= 14:
        return "2.4 GHz"
    elif 36 <= channel <= 165:
        return "5 GHz"
    else:
        return "Unknown"