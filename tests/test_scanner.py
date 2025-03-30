"""
Test Scanner Module

This module contains unit tests for the WiFi scanning and parsing functionality.
"""

import unittest
import os
import sys
import logging
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add project root to path to ensure imports work correctly
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanner.windows_scanner import WindowsWiFiScanner
from scanner.parser import parse_netsh_output
from scanner.models import WiFiNetwork, NetworkBSSID, ScanResult
from utils.signal_utils import percentage_to_dbm

# Sample netsh output for testing
SAMPLE_NETSH_OUTPUT = """
Interface name : Wi-Fi
There are 4 networks currently visible.

SSID 1 : TestNetwork1
    Network type            : Infrastructure
    Authentication          : WPA2-Personal
    Encryption              : CCMP
    BSSID 1                 : aa:bb:cc:dd:ee:ff
         Signal             : 70%
         Radio type         : 802.11n
         Channel            : 6
         Basic rates (Mbps) : 1 2 5.5 11
         Other rates (Mbps) : 6 9 12 18 24 36 48 54
    BSSID 2                 : ff:ee:dd:cc:bb:aa
         Signal             : 65%
         Radio type         : 802.11n
         Channel            : 6
         Basic rates (Mbps) : 1 2 5.5 11
         Other rates (Mbps) : 6 9 12 18 24 36 48 54

SSID 2 : TestNetwork2
    Network type            : Infrastructure
    Authentication          : WPA2-Personal
    Encryption              : CCMP
    BSSID 1                 : 11:22:33:44:55:66
         Signal             : 85%
         Radio type         : 802.11ac
         Channel            : 36
         Basic rates (Mbps) : 6 12 24
         Other rates (Mbps) : 9 18 36 48 54

SSID 3 : 
    Network type            : Infrastructure
    Authentication          : Open
    Encryption              : None
    BSSID 1                 : aa:aa:aa:aa:aa:aa
         Signal             : 30%
         Radio type         : 802.11g
         Channel            : 11
         Basic rates (Mbps) : 极速 2 5.5 11
         Other rates (Mbps) : 6 9 12 18 24 36 48 54

SSID 4 : TestNetwork4
    Network type            : Infrastructure
    Authentication          : WPA3-Personal
    Encryption              : CCMP
    BSSID 1                 : bb:bb:bb:bb:bb:bb
         Signal             : 50%
         Radio type         : 802.11ax
         Channel            : 149
         Basic rates (Mbps) : 6 12 24
         Other rates (Mbps) : 9 18 36 48 54
"""

EMPTY_NETSH_OUTPUT = """
Interface name : Wi-Fi
There are 0 networks currently visible.
"""

ERROR_NETSH_OUTPUT = """
There is no wireless interface on the system.
"""

class TestWiFiScanner(unittest.TestCase):
    """Test cases for the WiFi scanning functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Configure logging to avoid polluting test output
        logging.basicConfig(level=logging.ERROR)
        
        # Create a scanner with mocked subprocess
        self.scanner = WindowsWiFiScanner()
        
    @patch('subprocess.run')
    def test_scan_successful(self, mock_run):
        """Test successful network scanning."""
        # Mock subprocess.run to return sample output
        mock_process = MagicMock()
        mock_process.stdout = SAMPLE_NETSH_OUTPUT
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        # Call scan method
        result = self.scanner.scan_networks_sync()
        
        # Check that networks were parsed correctly
        self.assertEqual(len(result.networks), 4)
        
        # Check properties of first network
        network = next(n for n in result.networks if n.ssid == "TestNetwork1")
        self.assertEqual(network.ssid, "TestNetwork1")
        self.assertEqual(network.bssids[0].bssid, "aa:bb:cc:dd:ee:ff")
        self.assertEqual(network.bssids[0].channel, 6)
        self.assertEqual(network.bssids[0].band, "2.4 GHz")
        self.assertEqual(network.security_type, "WPA2")
        self.assertEqual(network.bssids[0].signal_dbm, -65)  # 70% converted to dBm
        
        # Check 5 GHz network
        network = next(n for n in result.networks if n.ssid == "TestNetwork2")
        self.assertEqual(network.bssids[0].band, "5 GHz")
        self.assertEqual(network.bssids[0].channel, 36)
        
        # Check hidden network
        hidden_network = next(n for n in result.networks if n.ssid == "")
        self.assertEqual(hidden_network.security_type, "Open")
        self.assertEqual(hidden_network.bssids[0].channel, 11)
        
        # Check WPA3 network
        wpa3_network = next(n for n in result.networks if n.ssid == "TestNetwork4")
        self.assertEqual(wpa3_network.security_type, "WPA3")
        self.assertEqual(wpa3_network.bssids[0].channel, 149)
        self.assertEqual(wpa3_network.bssids[0].band, "5 GHz")
    
    @patch('subprocess.run')
    def test_scan_empty(self, mock_run):
        """Test scanning with no networks found."""
        # Mock subprocess.run to return empty output
        mock_process = MagicMock()
        mock_process.stdout = EMPTY_NETSH_OUTPUT
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        
        # Call scan method
        result = self.scanner.scan_networks_sync()
        
        # Check that an empty list was returned
        self.assertEqual(len(result.networks), 0)
    
    @patch('subprocess.run')
    def test_scan_error(self, mock_run):
        """Test scanning with an error."""
        # Mock subprocess.run to return error output
        mock_process = MagicMock()
        mock_process.stdout = ERROR_NETSH_OUTPUT
        mock_process.returncode = 1
        mock_run.return_value = mock_process
        
        # Call scan method
        result = self.scanner.scan_networks_sync()
        self.assertFalse(result.success)
    
    def test_parse_netsh_output(self):
        """Test parsing netsh output directly."""
        result = parse_netsh_output(SAMPLE_NETSH_OUTPUT)
        
        # Check that all networks were parsed
        self.assertEqual(len(result.networks), 4)
        
        # Check specific network details
        ssids = [n.ssid for n in result.networks]
        self.assertIn("TestNetwork1", ssids)
        self.assertIn("TestNetwork2", ssids)
        self.assertIn("", ssids)  # Hidden network
        self.assertIn("TestNetwork4", ssids)
    
    def test_signal_conversion(self):
        """Test conversion from percentage to dBm."""
        # From parser.py
        self.assertEqual(percentage_to_dbm(100), -50)
        self.assertEqual(percentage_to_dbm(0), -100)
        self.assertEqual(percentage_to_dbm(50), -75)
        self.assertEqual(percentage_to_dbm(70), -65)


class TestWiFiNetwork(unittest.TestCase):
    """Test cases for the WiFiNetwork model class."""
    
    def test_network_creation(self):
        """Test creating and manipulating WiFiNetwork objects."""
        # Create a network
        network = WiFiNetwork(
            ssid="TestSSID",
            bssids=[NetworkBSSID(
                bssid="00:11:22:33:44:55",
                signal_percent=70,
                signal_dbm=-70,
                channel=6,
                band="2.4 GHz"
            )],
            security_type="WPA2"
        )
        
        # Check properties
        self.assertEqual(network.ssid, "TestSSID")
        self.assertEqual(network.bssids[0].bssid, "00:11:22:33:44:55")
        self.assertEqual(network.bssids[0].signal_dbm, -70)
        self.assertEqual(network.bssids[0].channel, 6)
        self.assertEqual(network.bssids[0].band, "2.4 GHz")
        self.assertEqual(network.security_type, "WPA2")
        
        # Check that first_seen and last_seen were set automatically
        self.assertIsNotNone(network.first_seen)
        self.assertIsNotNone(network.last_seen)
        
        # Test string representation
        self.assertIn("TestSSID", str(network))
        self.assertIn("-70 dBm", str(network))
    
    def test_network_equality(self):
        """Test network equality comparison."""
        # Create two networks with the same BSSID but different properties
        network1 = WiFiNetwork(
            ssid="TestSSID",
            bssids=[NetworkBSSID(
                bssid="00:11:22:33:44:55",
                signal_percent=70,
                signal_dbm=-70,
                channel=6,
                band="2.4 GHz"
            )],
            security_type="WPA2"
        )
        
        network2 = WiFiNetwork(
            ssid="DifferentSSID",
            bssids=[NetworkBSSID(
                bssid="00:11:22:33:44:55",  # Same BSSID
                signal_percent=75,
                signal_dbm=-65,
                channel=6,
                band="2.4 GHz"
            )],
            security_type="WPA2"
        )
        
        # Networks with the same BSSID should be considered equal
        self.assertEqual(network1, network2)
        
        # Create a network with a different BSSID
        network3 = WiFiNetwork(
            ssid="TestSSID",
            bssids=[NetworkBSSID(
                bssid="AA:BB:CC:DD:EE:FF",  # Different BSSID
                signal_percent=70,
                signal_dbm=-70,
                channel=6,
                band="2.4 GHz"
            )],
            security_type="WPA2"
        )
        
        # Networks with different BSSIDs should not be equal
        self.assertNotEqual(network1, network3)


class TestEdgeCases(unittest.TestCase):
    """Test handling of edge cases and unusual input."""
    
    def test_special_characters_in_ssid(self):
        """Test handling of special characters in SSIDs."""
        # Create a network with special characters in SSID
        network = WiFiNetwork(
            ssid="Test\nNetwork\t\r\nWith「Special」Chars",
            bssids=[NetworkBSSID(
                bssid="00:11:22:33:44:55",
                signal_percent=70,
                signal_dbm=-70,
                channel=6,
                band="2.4 GHz"
            )],
            security_type="WPA2"
        )
        
        # Check that the SSID was stored correctly
        self.assertEqual(network.ssid, "Test\nNetwork\t\r\nWith「Special」Chars")
    
    def test_invalid_channel_numbers(self):
        """Test handling of invalid channel numbers."""
        # Create a network with invalid channel number
        with self.assertRaises(ValueError):
            network = WiFiNetwork(
                ssid="TestNetwork",
                bssids=[NetworkBSSID(
                    bssid="00:11:22:33:44:55",
                    signal_percent=70,
                    signal_dbm=-70,
                    channel=0,  # Invalid channel
                    band="2.4 GHz"
                )],
                security_type="WPA2"
            )
        
        # Too high channel number
        with self.assertRaises(ValueError):
            network = WiFiNetwork(
                ssid="TestNetwork",
                bssids=[NetworkBSSID(
                    bssid="00:11:22:33:44:55",
                    signal_percent=70,
                    signal_dbm=-70,
                    channel=200,  # Invalid channel
                    band="2.4 GHz"
                )],
                security_type="WPA2"
            )
    
    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        # Missing BSSID
        with self.assertRaises(TypeError):
            network = WiFiNetwork(
                ssid="TestNetwork",
                bssids=[],  # Empty bssids list
                security_type="WPA2"
            )


if __name__ == "__main__":
    unittest.main()
