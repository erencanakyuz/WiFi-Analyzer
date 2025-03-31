"""
Data models for WiFi network information.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import json
import time
from datetime import datetime


@dataclass
class NetworkBSSID:
    """
    Represents a single BSSID (Basic Service Set Identifier) entry for a WiFi network.
    """
    bssid: str
    signal_percent: int = 0
    signal_dbm: float = -100.0
    channel: int = 1
    band: str = "2.4 GHz"
    
    # Additional optional fields
    channel_width: Optional[int] = None  # in MHz
    encryption: Optional[str] = None
    
    def __post_init__(self):
        """Validate inputs after initialization."""
        # Channel validation (0 or 1-196)
        if self.channel != 0 and not 1 <= self.channel <= 196:
            raise ValueError(f"Invalid channel number: {self.channel}")
        if not 0 <= self.signal_percent <= 100:
            raise ValueError(f"Invalid signal percentage: {self.signal_percent}")
    
    def __eq__(self, other):
        """Compare BSSIDs for equality."""
        if not isinstance(other, NetworkBSSID):
            return False
        return self.bssid == other.bssid
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "bssid": self.bssid,
            "signal_percent": self.signal_percent,
            "signal_dbm": self.signal_dbm,
            "channel": self.channel,
            "band": self.band,
            "channel_width": self.channel_width,
            "encryption": self.encryption,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NetworkBSSID':
        """Create a NetworkBSSID from a dictionary."""
        return cls(
            bssid=data["bssid"],
            signal_percent=data["signal_percent"],
            signal_dbm=data["signal_dbm"],
            channel=data["channel"],
            band=data["band"],
            channel_width=data.get("channel_width"),
            encryption=data.get("encryption")
        )


class WiFiNetwork:
    def __init__(self, ssid, bssids=None, security_type="Unknown"):
        self.ssid = ssid
        self.bssids = bssids or []  # Ensure bssids is never None
        self.security_type = security_type
    
    @property
    def signal_dbm(self):
        """Get the signal strength in dBm of the strongest BSSID."""
        if not self.bssids:
            return -100
        return max((b.signal_dbm for b in self.bssids if hasattr(b, 'signal_dbm')), default=-100)
    
    @property
    def bssid(self):
        """Get the BSSID of the strongest signal."""
        if not self.bssids:
            return ""
        strongest = max(self.bssids, key=lambda b: b.signal_dbm if hasattr(b, 'signal_dbm') else -100)
        return strongest.bssid
    
    @property
    def signal_percent(self):
        """Get the signal percentage of the strongest BSSID."""
        if not self.bssids:
            return 0
        strongest = max(self.bssids, key=lambda b: b.signal_dbm if hasattr(b, 'signal_dbm') else -100)
        return strongest.signal_percent
    
    # Essential compatibility properties
    @property
    def strongest_signal(self):
        """Compatibility property for the signal strength in dBm."""
        return self.signal_dbm
    
    @property
    def channel(self):
        """Get the channel of the strongest BSSID."""
        if not self.bssids:
            return 0
        strongest = max(self.bssids, key=lambda b: b.signal_dbm if hasattr(b, 'signal_dbm') else -100)
        return strongest.channel
    
    @property
    def band(self):
        """Get the frequency band of the strongest BSSID."""
        if not self.bssids:
            return "Unknown"
        strongest = max(self.bssids, key=lambda b: b.signal_dbm if hasattr(b, 'signal_dbm') else -100)
        return strongest.band
    
    # Additional compatibility aliases needed by dashboard
    @property
    def primary_channel(self):
        """Alias for channel property."""
        return self.channel
        
    @property
    def primary_band(self):
        """Alias for band property."""
        return self.band
        
    @property
    def primary_bssid(self):
        """Alias for bssid property."""
        return self.bssid


@dataclass
class ScanResult:
    """
    Represents the result of a single WiFi scan operation.
    """
    timestamp: float
    networks: List[WiFiNetwork]
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp,
            "success": self.success,
            "error_message": self.error_message,
            "networks": [n.to_dict() for n in self.networks],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanResult':
        """Create a ScanResult from a dictionary."""
        result = cls(
            timestamp=data["timestamp"],
            networks=[],
            success=data.get("success", True),
            error_message=data.get("error_message")
        )
        
        result.networks = [WiFiNetwork.from_dict(n) for n in data.get("networks", [])]
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ScanResult':
        """Create a ScanResult from a JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def get_timestamp_str(self, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Return the scan timestamp as a formatted string."""
        dt = datetime.fromtimestamp(self.timestamp)
        return dt.strftime(format_str)
