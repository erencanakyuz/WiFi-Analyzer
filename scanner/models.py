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
    signal_percent: int
    signal_dbm: float
    channel: int
    band: str  # "2.4 GHz" or "5 GHz"
    
    # Additional optional fields
    channel_width: Optional[int] = None  # in MHz
    encryption: Optional[str] = None
    
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
    
    @property
    def strongest_signal(self) -> Optional[float]:
        """Return the strongest signal strength among all BSSIDs in dBm."""
        if not self.bssids:
            return None
        return max(bssid.signal_dbm for bssid in self.bssids)
    
    @property
    def primary_channel(self) -> Optional[int]:
        """Return the channel of the BSSID with the strongest signal."""
        if not self.bssids:
            return None
        strongest = max(self.bssids, key=lambda b: b.signal_dbm)
        return strongest.channel
    
    @property
    def primary_band(self) -> Optional[str]:
        """Return the frequency band of the BSSID with the strongest signal."""
        if not self.bssids:
            return None
        strongest = max(self.bssids, key=lambda b: b.signal_dbm)
        return strongest.band
    
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