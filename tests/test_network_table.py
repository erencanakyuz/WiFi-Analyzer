"""
Tests for the network table module.

Tests cover:
- Table model functionality
- Filtering and sorting
- Theme integration
- Signal strength rendering
- User interaction
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QModelIndex
from PyQt6.QtGui import QPainter, QColor

import sys
import os

# Add project root to sys.path to allow importing modules like 'gui'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from gui.network_table import (
    NetworkTableView, NetworkTableModel, NetworkFilterProxyModel,
    SignalStrengthDelegate
)
from scanner.models import WiFiNetwork, NetworkBSSID
from gui.theme_manager import ThemeUpdateEvent

# Sample test data
TEST_NETWORKS = [
    WiFiNetwork(
        ssid="Test Network 1",
        bssids=[NetworkBSSID(
            bssid="00:11:22:33:44:55",
            signal_percent=80,
            signal_dbm=-50,
            channel=1,
            band="2.4 GHz"
        )],
        security_type="WPA2",
        first_seen=datetime.now().timestamp(),
        last_seen=datetime.now().timestamp(),
    ),
    WiFiNetwork(
        ssid="Test Network 2",
        bssids=[NetworkBSSID(
            bssid="AA:BB:CC:DD:EE:FF",
            signal_percent=60,
            signal_dbm=-70,
            channel=36,
            band="5 GHz"
        )],
        security_type="WPA3",
        first_seen=datetime.now().timestamp(),
        last_seen=datetime.now().timestamp()
    ),
    WiFiNetwork(
        ssid=None,  # Hidden network
        bssids=[NetworkBSSID(
            bssid="FF:EE:DD:CC:BB:AA",
            signal_percent=40,
            signal_dbm=-85,
            channel=11,
            band="2.4 GHz"
        )],
        security_type="Open",
        first_seen=datetime.now().timestamp(),
        last_seen=datetime.now().timestamp()
    )
]

class TestNetworkTableModel(unittest.TestCase):
    """Test the network table model."""
    
    def setUp(self):
        """Set up test environment."""
        self.model = NetworkTableModel()
        self.model.update_networks(TEST_NETWORKS)
    
    def test_row_count(self):
        """Test row count calculation."""
        self.assertEqual(self.model.rowCount(), len(TEST_NETWORKS))
    
    def test_column_count(self):
        """Test column count."""
        self.assertEqual(self.model.columnCount(), len(self.model.COLUMNS))
    
    def test_header_data(self):
        """Test header data retrieval."""
        for i, column in enumerate(self.model.COLUMNS):
            self.assertEqual(
                self.model.headerData(i, Qt.Orientation.Horizontal),
                column
            )
    
    def test_data(self):
        """Test data retrieval."""
        # Test SSID display (including hidden network)
        ssid_col = self.model.COLUMNS.index('SSID')
        self.assertEqual(
            self.model.data(self.model.index(0, ssid_col)),
            "Test Network 1"
        )
        self.assertEqual(
            self.model.data(self.model.index(2, ssid_col)),
            "<Hidden Network>"
        )
        
        # Test signal strength
        signal_col = self.model.COLUMNS.index('Signal')
        self.assertEqual(
            self.model.data(self.model.index(0, signal_col)),
            -50
        )
    
    def test_tooltip(self):
        """Test tooltip generation."""
        signal_col = self.model.COLUMNS.index('Signal')
        tooltip = self.model.tooltip(0, signal_col)
        self.assertIn("-50 dBm", tooltip)
        self.assertIn("Excellent", tooltip)

class TestNetworkFilterProxy(unittest.TestCase):
    """Test the network filter proxy model."""
    
    def setUp(self):
        """Set up test environment."""
        self.source_model = NetworkTableModel()
        self.source_model.update_networks(TEST_NETWORKS)
        
        self.proxy = NetworkFilterProxyModel()
        self.proxy.setSourceModel(self.source_model)
    
    def test_no_filter(self):
        """Test with no filter applied."""
        self.assertEqual(self.proxy.rowCount(), len(TEST_NETWORKS))
    
    def test_band_filter(self):
        """Test band filtering."""
        self.proxy.set_band_filter("2.4 GHz")
        self.assertEqual(self.proxy.rowCount(), 2)  # Two 2.4 GHz networks
        
        self.proxy.set_band_filter("5 GHz")
        self.assertEqual(self.proxy.rowCount(), 1)  # One 5 GHz network
    
    def test_invalid_filter(self):
        """Test with invalid band filter."""
        self.proxy.set_band_filter("Invalid Band")
        self.assertEqual(self.proxy.rowCount(), 0)

class TestSignalStrengthDelegate(unittest.TestCase):
    """Test signal strength delegate."""
    
    @classmethod
    def setUpClass(cls):
        """Create QApplication instance for tests."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
    
    def setUp(self):
        """Set up test environment."""
        self.delegate = SignalStrengthDelegate()
        self.model = NetworkTableModel()
        self.model.update_networks(TEST_NETWORKS)
    
    def test_color_selection(self):
        """Test signal strength color selection."""
        # Mock painter and option
        painter = Mock(spec=QPainter)
        option = Mock()
        option.rect = Mock()
        option.palette = Mock()
        
        # Test strong signal
        index = self.model.index(0, self.model.COLUMNS.index('Signal'))
        self.delegate.paint(painter, option, index)
        
        # Verify color was set for strong signal
        painter.fillRect.assert_called()
        
        # Reset mock
        painter.reset_mock()
        
        # Test weak signal
        index = self.model.index(2, self.model.COLUMNS.index('Signal'))
        self.delegate.paint(painter, option, index)
        
        # Verify color was set for weak signal
        painter.fillRect.assert_called()

class TestNetworkTableView(unittest.TestCase):
    """Test network table view."""
    
    @classmethod
    def setUpClass(cls):
        """Create QApplication instance for tests."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
    
    def setUp(self):
        """Set up test environment."""
        self.view = NetworkTableView()
        self.view.set_networks(TEST_NETWORKS)
    
    def test_selection(self):
        """Test network selection."""
        # Select first row
        index = self.view.model.index(0, 0)
        self.view.setCurrentIndex(index)
        
        selected = self.view.get_selected_network()
        self.assertEqual(selected.ssid, TEST_NETWORKS[0].ssid)
    
    def test_theme_change(self):
        """Test theme change handling."""
        # Create mock theme event
        class TestNetworkTableModelExtended(unittest.TestCase):
            """Additional tests for NetworkTableModel."""
            
            def setUp(self):
                self.model = NetworkTableModel()
                self.model.update_networks(TEST_NETWORKS)
            
            def test_alignment_role(self):
                """Test text alignment role."""
                # Signal column should be center-aligned
                signal_col = self.model.COLUMNS.index('Signal')
                alignment = self.model.data(
                    self.model.index(0, signal_col), 
                    Qt.ItemDataRole.TextAlignmentRole
                )
                self.assertEqual(alignment, Qt.AlignmentFlag.AlignCenter)
                
                # SSID column should be left-aligned
                ssid_col = self.model.COLUMNS.index('SSID')
                alignment = self.model.data(
                    self.model.index(0, ssid_col),
                    Qt.ItemDataRole.TextAlignmentRole
                )
                self.assertEqual(alignment, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            
            def test_sort_role(self):
                """Test user role for sorting."""
                signal_col = self.model.COLUMNS.index('Signal')
                # Verify sort role returns numeric value for signal column
                sort_data = self.model.data(
                    self.model.index(0, signal_col),
                    Qt.ItemDataRole.UserRole
                )
                self.assertIsInstance(sort_data, int)
                self.assertEqual(sort_data, -50)
            
            def test_model_reset_on_update(self):
                """Test that model emits proper signals when updated."""
                # Using a signal spy would be better, but this simple approach works
                reset_called = [False, False]  # beginResetModel, endResetModel
                
                original_begin_reset = self.model.beginResetModel
                original_end_reset = self.model.endResetModel
                
                def mock_begin_reset():
                    reset_called[0] = True
                    original_begin_reset()
                    
                def mock_end_reset():
                    reset_called[1] = True
                    original_end_reset()
                
                self.model.beginResetModel = mock_begin_reset
                self.model.endResetModel = mock_end_reset
                
                # Update networks
                new_networks = TEST_NETWORKS.copy()
                self.model.update_networks(new_networks)
                
                # Verify both signals were emitted
                self.assertTrue(reset_called[0], "beginResetModel not called")
                self.assertTrue(reset_called[1], "endResetModel not called")
                
                # Restore original methods
                self.model.beginResetModel = original_begin_reset
                self.model.endResetModel = original_end_reset


        class TestNetworkFilterProxyAdvanced(unittest.TestCase):
            """Advanced tests for the network filter proxy model."""
            
            def setUp(self):
                self.source_model = NetworkTableModel()
                self.source_model.update_networks(TEST_NETWORKS)
                
                self.proxy = NetworkFilterProxyModel()
                self.proxy.setSourceModel(self.source_model)
            
            def test_dynamic_filter_change(self):
                """Test changing filters dynamically."""
                # Start with 2.4GHz filter
                self.proxy.set_band_filter("2.4 GHz")
                self.assertEqual(self.proxy.rowCount(), 2)
                
                # Change to 5GHz
                self.proxy.set_band_filter("5 GHz")
                self.assertEqual(self.proxy.rowCount(), 1)
                
                # Clear filter
                self.proxy.set_band_filter(None)
                self.assertEqual(self.proxy.rowCount(), len(TEST_NETWORKS))
            
            def test_source_mapping(self):
                """Test mapping between source and proxy indexes."""
                # Apply a filter so we have fewer rows
                self.proxy.set_band_filter("2.4 GHz")
                
                # Get a proxy index for the first visible row
                proxy_index = self.proxy.index(0, 0)
                self.assertTrue(proxy_index.isValid())
                
                # Map to source
                source_index = self.proxy.mapToSource(proxy_index)
                self.assertTrue(source_index.isValid())
                
                # Verify the source row has the expected band
                band_col = self.source_model.COLUMNS.index('Band')
                band_index = self.source_model.index(source_index.row(), band_col)
                band_data = self.source_model.data(band_index)
                self.assertEqual(band_data, "2.4 GHz")
            
            @patch('gui.network_table.logger')
            def test_invalid_source_model(self, mock_logger):
                """Test setting an invalid source model."""
                # Create a new proxy with a non-NetworkTableModel source
                proxy = NetworkFilterProxyModel()
                invalid_model = Mock()  # Not a NetworkTableModel
                
                proxy.setSourceModel(invalid_model)
                
                # Verify warning was logged
                mock_logger.warning.assert_called_with("Source model is not a NetworkTableModel!")


        class TestSignalStrengthDelegateAdvanced(unittest.TestCase):
            """Advanced tests for signal strength delegate."""
            
            @classmethod
            def setUpClass(cls):
                if not QApplication.instance():
                    cls.app = QApplication(sys.argv)
            
            def setUp(self):
                self.delegate = SignalStrengthDelegate()
                self.model = NetworkTableModel()
                self.model.update_networks(TEST_NETWORKS)
            
            def test_size_hint(self):
                """Test size hint calculation."""
                option = Mock()
                index = self.model.index(0, self.model.COLUMNS.index('Signal'))
                
                # Get size hint
                size = self.delegate.sizeHint(option, index)
                
                # Verify minimum width requirement
                self.assertGreaterEqual(size.width(), 70)
            
            def test_invalid_data_handling(self):
                """Test handling of invalid data."""
                painter = Mock(spec=QPainter)
                option = Mock()
                option.rect = Mock()
                option.palette = Mock()
                option.palette.highlight.return_value = QColor("blue")
                option.palette.highlightedText.return_value = Mock()
                option.palette.highlightedText().color.return_value = QColor("white")
                option.palette.base.return_value = QColor("white")
                option.palette.text.return_value = Mock()
                option.palette.text().color.return_value = QColor("black")
                option.state = 0  # Not selected
                
                # Create a model with invalid signal data
                model = NetworkTableModel()
                network = WiFiNetwork(
                    ssid="Invalid Signal",
                    bssids=[NetworkBSSID(
                        bssid="00:00:00:00:00:00",
                        signal_percent=None,
                        signal_dbm=None,  # Invalid signal
                        channel=1,
                        band="2.4 GHz"
                    )],
                    security_type="Unknown",
                    first_seen=datetime.now().timestamp(),
                    last_seen=datetime.now().timestamp()
                )
                model.update_networks([network])
                
                # Test with invalid signal data
                index = model.index(0, model.COLUMNS.index('Signal'))
                
                # This should not raise an exception
                self.delegate.paint(painter, option, index)
                
                # Verify base color was used (painter.setBrush was called)
                painter.setBrush.assert_called()


        class TestNetworkTableViewExtended(unittest.TestCase):
            """Extended tests for NetworkTableView."""
            
            @classmethod
            def setUpClass(cls):
                if not QApplication.instance():
                    cls.app = QApplication(sys.argv)
            
            def setUp(self):
                self.view = NetworkTableView()
                self.view.set_networks(TEST_NETWORKS)
            
            def test_context_menu(self):
                """Test context menu creation."""
                # Create a mock event with valid position
                event = Mock()
                event.pos.return_value = self.view.rect().center()
                event.globalPos.return_value = self.view.mapToGlobal(self.view.rect().center())
                
                # Get the index at that position (assuming it's valid)
                index = self.view.indexAt(event.pos())
                if not index.isValid():
                    # If no valid index, create a mock index and patch indexAt
                    index = Mock()
                    index.isValid.return_value = True
                    self.view.indexAt = Mock(return_value=index)
                    
                    # Mock proxy model mapping
                    source_index = Mock()
                    source_index.isValid.return_value = True
                    source_index.row.return_value = 0  # First row
                    self.view.proxy_model.mapToSource = Mock(return_value=source_index)
                
                # Create mocked QMenu
                with patch('PyQt6.QtWidgets.QMenu') as mock_menu:
                    # Make exec return None (as if no action was selected)
                    mock_menu_instance = Mock()
                    mock_menu.return_value = mock_menu_instance
                    mock_menu_instance.exec.return_value = None
                    
                    # Call context menu event
                    self.view.contextMenuEvent(event)
                    
                    # Verify menu was created and executed
                    mock_menu.assert_called_once()
