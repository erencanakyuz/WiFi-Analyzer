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


@dataclass
class WiFiNetwork:
    """
    Represents a WiFi network with one or more BSSIDs.
    """
    ssid: str
    bssids: List[NetworkBSSID] = field(default_factory=list)
    security_type: Optional[str] = None
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    favorite: bool = False
    notes: str = ""

    def __post_init__(self):
        """Validate required fields."""
        pass  # Defer validation to validate() method

    def validate(self):
        """Validate network has required fields."""
        if not self.bssids:
            raise TypeError("At least one BSSID is required")

    def __eq__(self, other):
        """Compare WiFiNetworks for equality based on BSSIDs only."""
        if not isinstance(other, WiFiNetwork):
            return False
        return (sorted(self.bssids, key=lambda x: x.bssid) == 
                sorted(other.bssids, key=lambda x: x.bssid))

    def __str__(self):
        """Simple string representation showing SSID and strongest signal."""
        signal = f"{self.strongest_signal} dBm" if self.strongest_signal else "N/A"
        return f"{self.ssid} ({signal})"
    
    @property
    def strongest_signal(self) -> Optional[float]:
        """Return the strongest signal strength among all BSSIDs in dBm."""
        if not self.bssids:
            return None
        return max(bssid.signal_dbm for bssid in self.bssids)
    
    @property
    def signal_dbm(self):
        """Get the strongest signal strength among all BSSIDs."""
        if not self.bssids:
            return -100  # Default very weak signal if no BSSIDs
        return max(bssid.signal_dbm for bssid in self.bssids)
    
    @property
    def channel(self):
        """Get the channel of the BSSID with the strongest signal."""
        if not self.bssids:
            return 0
        strongest = max(self.bssids, key=lambda b: b.signal_dbm)
        return strongest.channel
        
    @property
    def band(self):
        """Get the frequency band of the BSSID with the strongest signal."""
        if not self.bssids:
            return "Unknown"
        strongest = max(self.bssids, key=lambda b: b.signal_dbm)
        return strongest.band
    
    @property
    def primary_channel(self):
        """Alias for channel property."""
        return self.channel
        
    @property
    def primary_band(self):
        """Alias for band property."""
        return self.band

    @property
    def bssid(self):
        """Get the BSSID of the strongest signal."""
        if not self.bssids:
            return ""
        strongest = max(self.bssids, key=lambda b: b.signal_dbm)
        return strongest.bssid
    
    def update_last_seen(self):
        """Update the last_seen timestamp to current time."""
        self.last_seen = time.time()
    
    def merged_with(self, other: 'WiFiNetwork') -> 'WiFiNetwork':
        """
        Merge this network with another network with the same SSID.
        Updates signal levels and adds any new BSSIDs.
        """
        if self.ssid != other.ssid:
            raise ValueError("Cannot merge networks with different SSIDs")
        
        result = WiFiNetwork(
            ssid=self.ssid,
            security_type=self.security_type,
            first_seen=min(self.first_seen, other.first_seen),
            last_seen=max(self.last_seen, other.last_seen),
            favorite=self.favorite,
            notes=self.notes
        )
        
        # Combine BSSIDs, keeping the most recent signal data
        existing_bssids = {b.bssid: b for b in self.bssids}
        
        for other_bssid in other.bssids:
            if other_bssid.bssid in existing_bssids:
                # Use the BSSID with the more recent data
                existing_bssids[other_bssid.bssid] = other_bssid
            else:
                # Add the new BSSID
                existing_bssids[other_bssid.bssid] = other_bssid
        
        result.bssids = list(existing_bssids.values())
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "ssid": self.ssid,
            "bssids": [b.to_dict() for b in self.bssids],
            "security_type": self.security_type,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "favorite": self.favorite,
            "notes": self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WiFiNetwork':
        """Create a WiFiNetwork from a dictionary."""
        network = cls(
            ssid=data["ssid"],
            security_type=data.get("security_type"),
            first_seen=data.get("first_seen", time.time()),
            last_seen=data.get("last_seen", time.time()),
            favorite=data.get("favorite", False),
            notes=data.get("notes", "")
        )
        
        network.bssids = [NetworkBSSID.from_dict(b) for b in data.get("bssids", [])]
        return network


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
