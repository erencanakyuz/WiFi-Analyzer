"""
WiFi scanner implementation for Windows using netsh commands.
"""

import subprocess
import time
import threading
import logging
from typing import List, Dict, Optional, Callable, Tuple
import sys
import ctypes
import tempfile
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

from .models import WiFiNetwork, NetworkBSSID, ScanResult
from .parser import create_scan_result
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


class WindowsWiFiScanner:
    """
    A class to scan for WiFi networks on Windows using the netsh command.
    
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
        if not self.is_admin():
            logger.warning(
                "WiFi scanner initialized without admin privileges - some features may be limited:\n"
                "- May not detect all available networks\n"
                "- May not get complete signal strength information\n"
                "- May not be able to force fresh scans\n"
                "\n"
                "For full functionality, please run the application as Administrator."
            )
        else:
            logger.info("Windows WiFi scanner initialized with admin privileges")
    
    @staticmethod
    def is_admin() -> bool:
        """
        Check if the application is running with admin privileges.
        
        Returns:
            bool: True if running as admin, False otherwise
        """
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    
    @staticmethod
    def elevate_privileges():
        """
        Attempt to restart the application with admin privileges.
        """
        if not WindowsWiFiScanner.is_admin():
            # Re-run the program with admin rights
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit(0)
    
    def _check_wifi_adapter(self):
        """
        Check if WiFi adapter is enabled and available.
        
        Raises:
            AdapterDisabledError: If adapter is disabled or not available
        """
        try:
            result = subprocess.run(
                ['netsh', 'wlan', 'show', 'interfaces'],
                capture_output=True,
                text=True,
                timeout=SCAN_TIMEOUT_SECONDS
            )
            
            if "There is no wireless interface on the system" in result.stdout:
                raise AdapterDisabledError("No wireless interface found on this system")
            
            if "The Wireless AutoConfig Service (wlansvc) is not running" in result.stdout:
                raise AdapterDisabledError("Wireless service is not running")
                
            if "Hardware switch is off" in result.stdout or "Hardware radio status : Not ready" in result.stdout:
                raise AdapterDisabledError("WiFi hardware switch is turned off")
                
            # Check if any interface is in "connected" state
            if "State" in result.stdout and "disconnected" not in result.stdout.lower():
                return True
            
        except subprocess.TimeoutExpired:
            raise ScannerError("Command timed out while checking WiFi adapter")
        except subprocess.SubprocessError as e:
            if "Access denied" in str(e):
                logger.error("Permission denied when checking adapter status")
                if not self.is_admin():
                    raise ScannerError("Admin privileges required to check WiFi adapter")
            raise ScannerError(f"Error checking WiFi adapter: {str(e)}")
    
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
                
                # Try to force a rescan but don't fail if it doesn't work
                try:
                    logger.debug("Attempting to trigger fresh scan")
                    scan_result = subprocess.run(
                        ['netsh', 'wlan', 'scan'],
                        capture_output=True,
                        text=True,
                        timeout=SCAN_TIMEOUT_SECONDS
                    )
                    
                    if scan_result.returncode != 0:
                        logger.warning(f"Initial scan command failed with code {scan_result.returncode}, but continuing")
                        logger.warning(f"Error output: {scan_result.stderr}")
                    else:
                        # Short pause to allow scan to complete
                        time.sleep(1)
                except Exception as e:
                    logger.warning(f"Initial scan command failed: {str(e)}, but continuing with existing scan data")
                
                # Execute network scan command to get available networks
                logger.debug("Running netsh command to scan WiFi networks")
                result = subprocess.run(
                    ['netsh', 'wlan', 'show', 'networks', 'mode=Bssid'],
                    capture_output=True,
                    text=True,
                    timeout=SCAN_TIMEOUT_SECONDS
                )
                
                if result.returncode != 0:
                    logger.error(f"netsh command failed with return code {result.returncode}")
                    logger.error(f"Command output: {result.stderr}")
                    raise ScannerError(f"Scan command failed with return code {result.returncode}")
                
                # Log raw output for debugging
                logger.debug(f"netsh command completed successfully")
                logger.debug(f"Raw output length: {len(result.stdout)} characters")
                
                # Save output to file for inspection
                debug_dir = Path(app_dir, "debug")
                debug_dir.mkdir(exist_ok=True)
                output_path = debug_dir / "last_scan_output.txt"
                with open(output_path, "w") as f:
                    f.write(result.stdout)
                logger.debug(f"Raw netsh output saved to {output_path}")
                
                # Parse the output into structured data
                logger.debug("Parsing netsh output")
                scan_result = create_scan_result(result.stdout)
                
                # Store results and update timestamp
                with self._lock:
                    self._last_scan_result = scan_result
                    self._last_scan_time = scan_result.timestamp
                    self._scan_history.append(scan_result)
                    # Limit history size
                    if len(self._scan_history) > 10:
                        self._scan_history.pop(0)
                
                logger.info(f"Scan completed: {len(scan_result.networks)} networks found")
                if len(scan_result.networks) == 0:
                    logger.warning("No networks found - this may indicate a problem with WiFi or parsing")
                    
                return scan_result
                
            except AdapterDisabledError as e:
                # Don't retry for disabled adapter - it won't change on retry
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
                
            except subprocess.TimeoutExpired:
                logger.warning(f"Scan timed out (attempt {retry_count+1})")
                retry_count += 1
                time.sleep(1)  # Wait before retrying
                
            except ScannerError as e:
                if "Access denied" in str(e) and not self.is_admin():
                    # Permission issue
                    error_message = "Admin privileges required to scan networks"
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
                else:
                    # Other scanner error, try again
                    logger.warning(f"Scan error (attempt {retry_count+1}): {str(e)}")
                    retry_count += 1
                    time.sleep(1)
            
            except Exception as e:
                logger.error(f"Unexpected error during scan: {str(e)}")
                retry_count += 1
                time.sleep(1)
        
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
    
    def scan_networks_async(self, callback: Optional[Callable[[ScanResult], None]] = None) -> None:
        """
        Start an asynchronous WiFi scan.
        
        Args:
            callback: Function to call when scan completes.
                     Will receive the ScanResult object.
        """
        if self._scanning:
            logger.warning("Scan already in progress, ignoring new request")
            return
        
        self._callback = callback
        self._scanning = True
        
        def _scan_thread_func():
            try:
                scan_result = self.scan_networks_sync()
            finally:
                self._scanning = False
                if callback:
                    callback(scan_result)
        
        self._scan_thread = threading.Thread(target=_scan_thread_func)
        self._scan_thread.daemon = True
        self._scan_thread.start()
        logger.debug("Async scan started")
    
    def is_scanning(self) -> bool:
        """Check if a scan is currently in progress."""
        return self._scanning
    
    def get_last_scan_result(self) -> Optional[ScanResult]:
        """
        Get the most recent scan result.
        
        Returns:
            Optional[ScanResult]: The last scan result, or None if no scan has been performed
        """
        with self._lock:
            return self._last_scan_result
    
    def get_scan_history(self) -> List[ScanResult]:
        """
        Get the scan history.
        
        Returns:
            List[ScanResult]: List of historical scan results
        """
        with self._lock:
            return self._scan_history.copy()


class ScanWorker(QThread):
    """
    Worker thread for performing WiFi scanning in the background.
    """
    scan_complete = pyqtSignal(object, bool, str)
    scan_progress = pyqtSignal(int)
    
    def __init__(self, scanner):
        super().__init__()
        self.scanner = scanner
        self.is_running = False
    
    def run(self):
        """Execute the scan operation in a separate thread."""
        self.is_running = True
        try:
            # Emit initial progress
            self.scan_progress.emit(10)
            logger.debug("Starting network scan in worker thread")
            
            # Try scan_networks_sync first, fall back to scan_networks if needed
            try:
                if hasattr(self.scanner, 'scan_networks_sync'):
                    scan_result = self.scanner.scan_networks_sync()
                    success = scan_result.success
                    error = scan_result.error_message
                    networks = scan_result.networks
                else:
                    # Fall back to the original method
                    networks = self.scanner.scan_networks()
                    success = True
                    error = ""
                    # Create a ScanResult for consistency
                    scan_result = ScanResult(
                        timestamp=time.time(),
                        networks=networks,
                        success=True,
                        error_message=""
                    )
            except Exception as e:
                raise e
            
            self.scan_progress.emit(90)
            
            # Emit results
            self.scan_complete.emit(scan_result, success, error)
            self.scan_progress.emit(100)
            
        except Exception as e:
            logger.error(f"Scan failed with exception: {str(e)}", exc_info=True)
            self.scan_complete.emit([], False, str(e))
            self.scan_progress.emit(100)
        finally:
            self.is_running = False
    
    def stop(self):
        """Stop the worker thread."""
        self.is_running = False
        self.wait()
