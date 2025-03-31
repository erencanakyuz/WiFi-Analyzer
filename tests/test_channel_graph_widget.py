import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from pytestqt.qt_compat import qt_api

import sys
import os

# Add project root to sys.path to allow importing modules like 'gui'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from gui.channel_graph import ChannelGraphWidget, ChannelGraphCanvas, WaterfallGraphCanvas, NetworkGraphCanvas
from utils.channel_analyzer import ChannelAnalyzer
from scanner.models import WiFiNetwork, NetworkBSSID, ScanResult

# Sample data for testing
def create_sample_networks():
    net1_bssid1 = NetworkBSSID(bssid="AA:BB:CC:00:00:01", signal_dbm=-50, channel=6, band="2.4 GHz", encryption="WPA2")
    net1_bssid2 = NetworkBSSID(bssid="AA:BB:CC:00:00:02", signal_dbm=-55, channel=6, band="2.4 GHz", encryption="WPA2")
    net1 = WiFiNetwork(ssid="Network_2.4_1", bssids=[net1_bssid1, net1_bssid2], security_type="WPA2")
    
    net2_bssid1 = NetworkBSSID(bssid="AA:BB:CC:11:11:01", signal_dbm=-65, channel=11, band="2.4 GHz", encryption="WPA2")
    net2 = WiFiNetwork(ssid="Network_2.4_2", bssids=[net2_bssid1], security_type="WPA2")

    net3_bssid1 = NetworkBSSID(bssid="AA:BB:CC:22:22:01", signal_dbm=-60, channel=48, band="5 GHz", encryption="WPA2")
    net3 = WiFiNetwork(ssid="Network_5_1", bssids=[net3_bssid1], security_type="WPA2")

    net4_bssid1 = NetworkBSSID(bssid="AA:BB:CC:33:33:01", signal_dbm=-75, channel=149, band="5 GHz", encryption="WPA2")
    net4 = WiFiNetwork(ssid="Network_5_2", bssids=[net4_bssid1], security_type="WPA2")
    
    return [net1, net2, net3, net4]

@pytest.fixture
def channel_analyzer():
    return ChannelAnalyzer()

@pytest.fixture
def graph_widget(qtbot, channel_analyzer):
    """Fixture to create the ChannelGraphWidget."""
    # Ensure QApplication exists
    if QApplication.instance() is None:
        _app = QApplication([])
    
    widget = ChannelGraphWidget(analyzer=channel_analyzer)
    qtbot.addWidget(widget)
    widget.show()
    return widget

def test_widget_creation(graph_widget):
    """Test if the widget and its canvases are created."""
    assert graph_widget is not None
    assert graph_widget.tab_widget is not None
    assert graph_widget.channel_canvas is not None
    assert graph_widget.waterfall_canvas is not None
    assert graph_widget.network_canvas is not None
    assert isinstance(graph_widget.channel_canvas, ChannelGraphCanvas)
    assert isinstance(graph_widget.waterfall_canvas, WaterfallGraphCanvas)
    assert isinstance(graph_widget.network_canvas, NetworkGraphCanvas)

def test_update_graphs_with_data(qtbot, graph_widget):
    """Test updating graphs with sample data."""
    sample_networks = create_sample_networks()
    
    # Need to wait for events to process after update
    with qtbot.waitSignal(graph_widget.channel_canvas.draw_complete, timeout=2000):
        graph_widget.update_graphs(sample_networks)
    
    # Basic checks (more detailed checks would involve inspecting plot data)
    assert graph_widget.last_networks is not None
    assert len(graph_widget.last_networks) == len(sample_networks)
    
    # Check if network graph shows something (assuming 2.4GHz is default)
    # A more robust check would inspect graph_widget.network_canvas.G directly
    # For now, just check if the axes has content (lines/patches)
    assert len(graph_widget.network_canvas.axes.get_children()) > 1 # Should have more than just the background patch
    

def test_band_switching(qtbot, graph_widget):
    """Test switching bands and updating graphs."""
    sample_networks = create_sample_networks()
    graph_widget.update_graphs(sample_networks) # Initial update (2.4GHz)
    
    # Switch to 5GHz
    graph_widget.band_selector.setCurrentText('5GHz')
    qtbot.wait(100) # Allow time for signal processing and redraw
    
    assert graph_widget.current_band == '5GHz'
    # Add checks for graph content if necessary

def test_tab_switching(qtbot, graph_widget):
    """Test switching tabs and ensure graphs update/redraw correctly."""
    sample_networks = create_sample_networks()
    graph_widget.update_graphs(sample_networks)
    
    # Switch to Waterfall tab (index 1)
    graph_widget.tab_widget.setCurrentIndex(1)
    qtbot.wait(100)

    # Switch to Network Graph tab (index 2)
    graph_widget.tab_widget.setCurrentIndex(2)
    qtbot.wait(100)

    # Switch back to Channel Usage (index 0)
    graph_widget.tab_widget.setCurrentIndex(0)
    qtbot.wait(100)
    
    # Primarily testing that switching doesn't crash or block.
    # More specific assertions about graph state could be added.

# Potential future tests:
# - test_hover_annotation_after_resize
# - test_click_interaction
# - test_network_graph_layout_change
# - test specific plot data values on ChannelGraphCanvas/WaterfallGraphCanvas
