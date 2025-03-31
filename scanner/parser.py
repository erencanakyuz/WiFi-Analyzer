import logging
import re
import time
from typing import List
from .models import WiFiNetwork, NetworkBSSID, ScanResult
from utils.signal_utils import percentage_to_dbm

# Configure logger
logger = logging.getLogger(__name__)

def create_scan_result(output_text: str) -> ScanResult:
    """
    Create a ScanResult object from netsh output.
    
    Args:
        output_text (str): Raw netsh command output text
        
    Returns:
        ScanResult: A ScanResult object containing parsed networks
    """
    try:
        # Check if output is empty
        if not output_text or output_text.strip() == "":
            logger.error("Received empty output from netsh command")
            return ScanResult(
                timestamp=time.time(),
                networks=[],
                success=False,
                error_message="Empty output from netsh command"
            )
            
        # Look for key patterns to detect common issues
        if "There is no wireless interface" in output_text:
            logger.error("No wireless interface detected")
            return ScanResult(
                timestamp=time.time(),
                networks=[],
                success=False,
                error_message="No wireless interface detected"
            )
            
        if "The Wireless AutoConfig Service (wlansvc) is not running" in output_text:
            logger.error("Wireless AutoConfig Service is not running")
            return ScanResult(
                timestamp=time.time(),
                networks=[],
                success=False,
                error_message="Wireless AutoConfig Service is not running"
            )
            
        if "There are 0 networks currently visible" in output_text:
            logger.warning("netsh reports 0 networks currently visible")
            # This is not an error, just no networks in range
            return ScanResult(
                timestamp=time.time(),
                networks=[],
                success=True,
                error_message=""
            )
        
        # Parse networks from the output
        logger.debug(f"Starting to parse network information from netsh output")
        networks = parse_netsh_output(output_text)
        
        # Create and return a successful scan result
        return ScanResult(
            timestamp=time.time(),
            networks=networks,
            success=True,
            error_message=""
        )
    except Exception as e:
        logger.error(f"Error parsing netsh output: {str(e)}", exc_info=True)
        # Return a failed scan result
        return ScanResult(
            timestamp=time.time(),
            networks=[],
            success=False,
            error_message=f"Error parsing scan results: {str(e)}"
        )


def parse_netsh_output(output_text: str) -> List[WiFiNetwork]:
    """
    Parse the raw output of 'netsh wlan show networks mode=Bssid' command.
    
    Args:
        output_text (str): The raw command output text
        
    Returns:
        List[WiFiNetwork]: List of parsed WiFi networks
    """
    networks = []
    current_network = None
    current_bssid = None
    
    # Split output into lines and process
    lines = output_text.split('\n')
    
    # Print raw output for debugging
    logger.debug(f"Processing {len(lines)} lines of netsh output")
    
    # Debug: Print first few lines to see the format
    if len(lines) > 5:
        logger.debug("First 5 lines of output:")
        for i in range(5):
            logger.debug(f"Line {i}: {lines[i]}")
    
    # Add a log to output all lines for extreme debugging
    # Uncomment this if still troubleshooting
    # for i, line in enumerate(lines):
    #     logger.debug(f"Line {i}: {line}")
    
    # Compile regex patterns for better performance
    ssid_pattern = re.compile(r'SSID \d+ : (.+)')
    bssid_pattern = re.compile(r'BSSID \d+\s*: (.+)')
    signal_pattern = re.compile(r'Signal\s*: (\d+)%')
    channel_pattern = re.compile(r'Channel\s*: (\d+)')
    auth_pattern = re.compile(r'Authentication\s*: (.+)')
    encryption_pattern = re.compile(r'Encryption\s*: (.+)')
    radio_type_pattern = re.compile(r'Radio type\s*: (.+)')
    band_pattern = re.compile(r'Band\s*: (.+)')  # Add pattern for Band field
    
    # Keep track of patterns matched for debugging
    pattern_matches = {
        "ssid": 0,
        "bssid": 0,
        "signal": 0,
        "channel": 0,
        "auth": 0,
        "encryption": 0,
        "radio_type": 0
    }
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        # New network section starts with SSID
        ssid_match = ssid_pattern.search(line)
        if ssid_match:
            pattern_matches["ssid"] += 1
            # Save previous network if exists
            if current_network and current_network.bssids:
                networks.append(current_network)
            
            # Create new network
            ssid = ssid_match.group(1).strip()
            # Handle hidden networks
            if ssid == "":
                ssid = "<Hidden Network>"
            current_network = WiFiNetwork(ssid=ssid)
            current_bssid = None
            logger.debug(f"Found network: {ssid}")
            continue
        
        # Skip processing if no current network
        if not current_network:
            continue
            
        # New BSSID section
        bssid_match = bssid_pattern.search(line)
        if bssid_match:
            pattern_matches["bssid"] += 1
            # Save previous BSSID if exists and has valid values
            if current_bssid and current_bssid.signal_percent > 0:
                current_network.bssids.append(current_bssid)
                logger.debug(f"Added BSSID: {current_bssid.bssid} to {current_network.ssid}")
            
            # Create new BSSID object
            bssid_value = bssid_match.group(1).strip()
            current_bssid = NetworkBSSID(
                bssid=bssid_value,
                signal_percent=0,
                signal_dbm=-100.0,
                channel=0,
                band="Unknown"
            )
            logger.debug(f"Found BSSID: {bssid_value}")
            continue
        
        # Skip processing if no current BSSID
        if not current_bssid:
            continue
            
        # Extract BSSID-specific information
        if "Signal" in line:
            signal_match = signal_pattern.search(line)
            if signal_match:
                pattern_matches["signal"] += 1
                signal_percent = int(signal_match.group(1))
                current_bssid.signal_percent = signal_percent
                # Convert percent to dBm
                current_bssid.signal_dbm = percentage_to_dbm(signal_percent)
                logger.debug(f"Signal for {current_bssid.bssid}: {signal_percent}% ({current_bssid.signal_dbm} dBm)")
        
        elif "Channel" in line:
            channel_match = channel_pattern.search(line)
            if channel_match:
                pattern_matches["channel"] += 1
                channel = int(channel_match.group(1))
                current_bssid.channel = channel
                # Determine frequency band based on channel
                if 1 <= channel <= 14:
                    current_bssid.band = "2.4 GHz"
                elif 36 <= channel <= 165:
                    current_bssid.band = "5 GHz"
                else:
                    current_bssid.band = "Unknown"
                logger.debug(f"Channel for {current_bssid.bssid}: {channel} ({current_bssid.band})")
        
        # Radio type can help determine band
        elif "Radio type" in line:
            radio_match = radio_type_pattern.search(line)
            if radio_match:
                pattern_matches["radio_type"] += 1
                radio_type = radio_match.group(1).strip()
                if "802.11n" in radio_type:
                    # Could be either 2.4 or 5GHz
                    pass
                elif "802.11ac" in radio_type or "802.11ax" in radio_type:
                    # These are 5GHz
                    current_bssid.band = "5 GHz"
                elif "802.11g" in radio_type or "802.11b" in radio_type:
                    # These are 2.4GHz
                    current_bssid.band = "2.4 GHz"
        
        elif "Band" in line:  # Add handling for Band field
            band_match = band_pattern.search(line)
            if band_match:
                band = band_match.group(1).strip()
                current_bssid.band = band
                logger.debug(f"Band for {current_bssid.bssid}: {band}")
        
        elif "Authentication" in line:
            auth_match = auth_pattern.search(line)
            if auth_match:
                pattern_matches["auth"] += 1
                auth_type = auth_match.group(1).strip()
                current_network.security_type = auth_type
                logger.debug(f"Authentication for {current_network.ssid}: {auth_type}")
        
        elif "Encryption" in line:
            encryption_match = encryption_pattern.search(line)
            if encryption_match:
                pattern_matches["encryption"] += 1
                encryption = encryption_match.group(1).strip()
                current_bssid.encryption = encryption

    # Don't forget to add the last network and BSSID
    if current_network:
        if current_bssid and current_bssid.signal_percent > 0:
            current_network.bssids.append(current_bssid)
        if current_network.bssids:  # Only add if it has valid BSSIDs
            networks.append(current_network)

    # Log pattern matching statistics
    logger.debug(f"Pattern matches: {pattern_matches}")    
    
    # Set network properties based on strongest BSSID
    for network in networks:
        if network.bssids:
            # Log strongest BSSID info (optional)
            strongest_bssid = max(network.bssids, key=lambda b: b.signal_percent)
            logger.debug(f"Network '{network.ssid}' - Strongest BSSID: {strongest_bssid.bssid} (Ch: {strongest_bssid.channel}, Signal: {strongest_bssid.signal_dbm} dBm)")
    
    logger.info(f"Parsed {len(networks)} networks with {sum(len(n.bssids) for n in networks)} BSSIDs")
    
    # If no networks found, log detailed info about the input
    if not networks:
        logger.warning("No networks parsed from netsh output")
        if pattern_matches["ssid"] == 0:
            logger.warning("No SSID patterns matched - may indicate unexpected netsh output format or empty scan.")
            return []
    
    return networks