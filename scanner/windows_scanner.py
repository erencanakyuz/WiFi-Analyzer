"""
WiFi scanner implementation using pywifi library instead of netsh commands.
"""

import time
import threading
import logging
from typing import List, Dict, Optional, Callable
from pathlib import Path
import json

import pywifi
from pywifi import PyWiFi, const
from PyQt6.QtCore import QThread, pyqtSignal

from .models import WiFiNetwork, NetworkBSSID, ScanResult
from config.settings import MAX_SCAN_RETRIES, SCAN_TIMEOUT_SECONDS

# Define application directory for debug files
app_dir = Path(__file__).parent.parent  # Root directory of the application

logger = logging.getLogger(__name__)


class ScannerError(Exception):
    """Base exception for scanner errors."""
    pass


class AdapterDisabledError(ScannerError):
    """Exception raised when WiFi adapter is disabled or not present."""
    pass


class WiFiScanner:
    """
    A class to scan for WiFi networks using the pywifi library.
    
    Attributes:
        _scanning (bool): Flag indicating if scan is in progress
        _scan_thread (threading.Thread): Thread for background scanning
        _callback (Optional[Callable]): Function to call when scan completes
        _last_scan_time (float): Timestamp of the last successful scan
        _scan_history (List[ScanResult]): History of scan results
        _lock (threading.Lock): Lock for thread safety
    """
    
    def __init__(self):
        """Initialize the WiFi scanner."""
        self._scanning = False
        self._scan_thread = None
        self._callback = None
        self._last_scan_time = 0
        self._last_scan_result = None
        self._scan_history = []
        self._lock = threading.Lock()
        
        # Initialize pywifi
        try:
            self.wifi = PyWiFi()
            self.iface = self.wifi.interfaces()[0]  # Get the first wireless interface
            logger.info(f"WiFi scanner initialized using interface: {self.iface.name()}")
        except Exception as e:
            logger.error(f"Error initializing WiFi interface: {e}")
            raise ScannerError(f"Could not initialize WiFi interface: {e}")

    def is_scanning(self) -> bool:
        """Check if a scan is currently in progress."""
        with self._lock:
            return self._scanning
    
    def _check_wifi_adapter(self):
        """
        Check if WiFi adapter is enabled and available.
        
        Raises:
            AdapterDisabledError: If adapter is disabled or not available
        """
        try:
            # Check if we have a valid interface
            if not self.iface:
                raise AdapterDisabledError("No wireless interface found on this system")
            
            # Check if the interface is active
            status = self.iface.status()
            if status == const.IFACE_DISCONNECTED:
                logger.info("WiFi interface is disconnected but available")
            elif status == const.IFACE_INACTIVE:
                raise AdapterDisabledError("WiFi interface is inactive")
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking WiFi adapter: {e}")
            raise AdapterDisabledError(f"Error checking WiFi adapter: {e}")
    
    def scan_networks_sync(self) -> ScanResult:
        """
        Perform a synchronous WiFi scan.
        
        Returns:
            ScanResult: Result of the scan operation
        """
        retry_count = 0
        
        while retry_count < MAX_SCAN_RETRIES:
            try:
                # First check if WiFi adapter is enabled
                logger.debug("Checking WiFi adapter status")
                self._check_wifi_adapter()
                logger.debug("WiFi adapter is enabled")
                
                # Scan for networks
                logger.debug("Scanning for networks")
                self.iface.scan()
                
                # Get scan results (wait a bit to ensure scan completes)
                time.sleep(2)
                networks = self.iface.scan_results()
                
                # Convert to our data model
                wifi_networks = self._convert_scan_results(networks)
                
                # Create successful scan result
                scan_result = ScanResult(
                    timestamp=time.time(),
                    networks=wifi_networks,
                    success=True,
                    error_message=""
                )
                
                # Save debug info
                self._save_debug_info(networks)
                
                # Store results and update timestamp
                with self._lock:
                    self._last_scan_result = scan_result
                    self._last_scan_time = scan_result.timestamp
                    self._scan_history.append(scan_result)
                    # Limit history size
                    if len(self._scan_history) > 10:
                        self._scan_history.pop(0)
                
                logger.info(f"Scan completed: {len(scan_result.networks)} networks found")
                return scan_result
                
            except AdapterDisabledError as e:
                # Don't retry for disabled adapter
                logger.error(f"WiFi adapter is disabled: {str(e)}")
                scan_result = ScanResult(
                    timestamp=time.time(),
                    networks=[],
                    success=False,
                    error_message=str(e)
                )
                with self._lock:
                    self._last_scan_result = scan_result
                return scan_result
                
            except Exception as e:
                logger.warning(f"Scan error (attempt {retry_count+1}): {str(e)}")
                retry_count += 1
                time.sleep(1)  # Wait before retrying
        
        # If we get here, all retries failed
        error_message = f"Scan failed after {MAX_SCAN_RETRIES} attempts"
        logger.error(error_message)
        scan_result = ScanResult(
            timestamp=time.time(),
            networks=[],
            success=False,
            error_message=error_message
        )
        with self._lock:
            self._last_scan_result = scan_result
        return scan_result
    
    def _save_debug_info(self, networks):
        """Save debug information about the scan."""
        try:
            debug_dir = Path(app_dir, "debug")
            debug_dir.mkdir(exist_ok=True)
            
            # Convert scan results to a serializable format
            debug_data = []
            for network in networks:
                debug_data.append({
                    'ssid': network.ssid,
                    'bssid': network.bssid,
                    'signal': network.signal,
                    'freq': network.freq,
                    'akm': [akm for akm in network.akm],
                    'channel': self._frequency_to_channel(network.freq),
                })
            
            # Save as JSON
            output_path = debug_dir / "last_scan_output.json"
            with open(output_path, "w") as f:
                json.dump(debug_data, f, indent=2)
            
            logger.debug(f"Debug data saved to {output_path}")
            
        except Exception as e:
            logger.warning(f"Failed to save debug info: {e}")
    
    def _frequency_to_channel(self, freq):
        """Convert frequency to channel number."""
        if freq >= 2412 and freq <= 2484:
            # 2.4 GHz band
            if freq == 2484:
                return 14
            return (freq - 2412) // 5 + 1
        elif freq >= 5160 and freq <= 5885:
            # 5 GHz band
            return (freq - 5160) // 5 + 32
        else:
            # Unknown band
            return 0
    
    def _channel_width_to_text(self, width):
        """Convert channel width constant to text."""
        if width == const.AKM_TYPE_NONE:
            return "Unknown"
        elif width == const.AKM_TYPE_WPA:
            return "WPA"
        elif width == const.AKM_TYPE_WPA2:
            return "WPA2"
        elif width == const.AKM_TYPE_WPA2PSK:
            return "WPA2-PSK"
        else:
            return f"Other ({width})"

    def _band_from_frequency(self, freq):
        """Determine band from frequency."""
        if 2412 <= freq <= 2484:
            return "2.4 GHz"
        elif 5160 <= freq <= 5885:
            return "5 GHz"
        else:
            return "Unknown"
    
    def _signal_percentage(self, signal_dbm):
        """Convert signal dBm to percentage (0-100)."""
        # Signal is usually between -100 dBm (weak) and -30 dBm (strong)
        if signal_dbm >= -50:
            return 100
        elif signal_dbm <= -100:
            return 0
        return 2 * (signal_dbm + 100)
    
    def _convert_scan_results(self, networks) -> List[WiFiNetwork]:
        """
        Convert pywifi scan results to our WiFiNetwork model.
        
        Args:
            networks: List of pywifi networks
            
        Returns:
            List of WiFiNetwork objects
        """
        wifi_networks = {}
        
        for network in networks:
            try:
                ssid = network.ssid
                display_ssid = ssid if ssid else "<Hidden Network>"
                
                bssid = network.bssid
                signal_dbm = network.signal
                freq = network.freq
                channel = self._frequency_to_channel(freq)
                band = self._band_from_frequency(freq)
                
                # Security type detection
                # --- Prioritize AUTH_ALG_OPEN and AKM_TYPE_NONE for Open networks ---
                if network.auth and const.AUTH_ALG_OPEN in network.auth and (not network.akm or const.AKM_TYPE_NONE in network.akm):
                    security_type = "Open"
                elif network.akm:
                    if const.AKM_TYPE_WPA2PSK in network.akm:
                        security_type = "WPA2-Personal"
                    elif const.AKM_TYPE_WPA2 in network.akm:
                        security_type = "WPA2-Enterprise"
                    elif const.AKM_TYPE_WPAPSK in network.akm:
                        security_type = "WPA-Personal"
                    elif const.AKM_TYPE_WPA in network.akm:
                        security_type = "WPA-Enterprise"
                    else:
                        security_type = "Secured"
                
                # Create NetworkBSSID object
                network_bssid = NetworkBSSID(
                    bssid=bssid,
                    signal_percent=self._signal_percentage(signal_dbm),
                    signal_dbm=signal_dbm,
                    channel=channel,
                    band=band,
                    encryption=security_type
                )
                
                # Group by SSID for WiFiNetwork objects
                grouping_key = ssid if ssid else bssid # Use BSSID as key for hidden networks
                if grouping_key not in wifi_networks:
                    # Create new network entry using display_ssid
                    wifi_networks[grouping_key] = WiFiNetwork(
                        ssid=display_ssid, 
                        bssids=[],
                        security_type=security_type # Use initial security type
                    )
                
                # Append BSSID using the grouping_key
                wifi_networks[grouping_key].bssids.append(network_bssid)
                # Ensure the security type is updated if a BSSID provides more info
                # If the current BSSID has a stronger security than 'Open' 
                # and the grouped network currently shows 'Open', update it.
                if security_type != "Open" and wifi_networks[grouping_key].security_type == "Open":
                     wifi_networks[grouping_key].security_type = security_type
                
            except Exception as e:
                logger.warning(f"Error processing network: {e}")
                continue
        
        # Create list from the dictionary values
        return list(wifi_networks.values())
    
    def scan_networks_async(self, callback: Optional[Callable[[ScanResult], None]] = None) -> None:
        """
        Perform an asynchronous WiFi scan.
        
        Args:
            callback: Function to call with the scan result when complete
        """
        if self._scanning:
            logger.warning("Scan already in progress, ignoring request")
            return
        
        with self._lock:
            self._scanning = True
            self._callback = callback
        
        def scan_thread():
            try:
                result = self.scan_networks_sync()
                if self._callback:
                    self._callback(result)
            finally:
                with self._lock:
                    self._scanning = False
                    self._callback = None
        
        self._scan_thread = threading.Thread(target=scan_thread)
        self._scan_thread.daemon = True
        self._scan_thread.start()
    
    # Add alias for compatibility with previous code
    def scan_async(self, callback: Optional[Callable[[ScanResult], None]] = None) -> None:
        """Alias for scan_networks_async for backward compatibility."""
        return self.scan_networks_async(callback)


class ScanWorker(QThread):
    """
    Worker thread for scanning WiFi networks.
    
    This class allows scanning to be performed in a separate thread
    to avoid blocking the UI.
    """
    
    scan_complete = pyqtSignal(object)  # Emits ScanResult
    
    def __init__(self, scanner: WiFiScanner):
        """
        Initialize the scan worker.
        
        Args:
            scanner: WiFiScanner instance
        """
        super().__init__()
        self.scanner = scanner
        self.is_running = False
    
    def run(self):
        """Run the scan operation."""
        self.is_running = True
        try:
            result = self.scanner.scan_networks_sync()
            self.scan_complete.emit(result)
        except Exception as e:
            logger.error(f"Error in scan worker: {e}", exc_info=True)
            result = ScanResult(
                timestamp=time.time(),
                networks=[],
                success=False,
                error_message=str(e)
            )
            self.scan_complete.emit(result)
        finally:
            self.is_running = False
