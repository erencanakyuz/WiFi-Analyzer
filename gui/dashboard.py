"""
Dashboard view for WiFi analyzer.

Provides a modern overview of the WiFi environment.
"""
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QScrollArea, QSizePolicy, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from gui.widgets.card import Card as DashboardCard
from gui.widgets.signal_indicator import SignalIndicator
from gui.widgets.network_tile import NetworkTile
from scanner.models import WiFiNetwork

logger = logging.getLogger(__name__)

class DashboardView(QWidget):
    """
    Modern dashboard view for WiFi analyzer.
    """
    # Signal emitted when a network is selected
    network_selected = pyqtSignal(object)
    # Signal emitted when refresh is requested
    refresh_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.networks = []
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        
        # Top row with summary cards
        top_row = QHBoxLayout()
        top_row.setSpacing(20)
        
        # Networks count card
        self.networks_card = DashboardCard("Networks")
        networks_widget = QWidget()
        networks_layout = QVBoxLayout(networks_widget)
        
        self.networks_count = QLabel("0")
        font = self.networks_count.font()
        font.setPointSize(24)
        font.setBold(True)
        self.networks_count.setFont(font)
        self.networks_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        networks_layout.addWidget(self.networks_count)
        networks_layout.addWidget(QLabel("Total WiFi Networks"))
        self.networks_card.setContentWidget(networks_widget)
        
        # Channel utilization card
        self.channel_card = DashboardCard("Channel Utilization")
        channel_widget = QWidget()
        channel_layout = QVBoxLayout(channel_widget)
        
        self.channel_24_label = QLabel("2.4 GHz: Not available")
        self.channel_5_label = QLabel("5 GHz: Not available")
        
        channel_layout.addWidget(self.channel_24_label)
        channel_layout.addWidget(self.channel_5_label)
        self.channel_card.setContentWidget(channel_widget)
        
        # Strongest network card
        self.strongest_card = DashboardCard("Strongest Network")
        strongest_widget = QWidget()
        strongest_layout = QHBoxLayout(strongest_widget)
        
        # Signal indicator
        self.signal_indicator = SignalIndicator()
        strongest_layout.addWidget(self.signal_indicator)
        
        # Network details
        details_layout = QVBoxLayout()
        self.strongest_ssid = QLabel("No networks found")
        font = self.strongest_ssid.font()
        font.setPointSize(14)
        font.setBold(True)
        self.strongest_ssid.setFont(font)
        
        self.strongest_details = QLabel("")
        
        details_layout.addWidget(self.strongest_ssid)
        details_layout.addWidget(self.strongest_details)
        details_layout.addStretch()
        
        strongest_layout.addLayout(details_layout)
        self.strongest_card.setContentWidget(strongest_widget)
        
        # Add cards to top row
        top_row.addWidget(self.networks_card, 1)
        top_row.addWidget(self.channel_card, 1)
        top_row.addWidget(self.strongest_card, 2)
        
        # Add top row to main layout
        main_layout.addLayout(top_row)
        
        # Networks list card
        networks_list_card = DashboardCard("All Networks")
        networks_list_widget = QWidget()
        networks_list_layout = QVBoxLayout(networks_list_widget)
        
        # Scroll area for network tiles
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Container for network tiles
        self.networks_container = QWidget()
        self.networks_container_layout = QVBoxLayout(self.networks_container)
        self.networks_container_layout.setSpacing(10)
        
        scroll_area.setWidget(self.networks_container)
        networks_list_layout.addWidget(scroll_area)
        
        networks_list_card.setContentWidget(networks_list_widget)
        main_layout.addWidget(networks_list_card, 1)
    
    def set_networks(self, networks):
        """
        Update the dashboard with new network data.
        
        Args:
            networks: List of WiFiNetwork objects
        """
        self.networks = networks
        
        # Update networks count
        self.networks_count.setText(str(len(networks)))
        
        # Update strongest network info
        if networks:
            # Find strongest network by signal strength
            strongest = max(networks, key=lambda n: n.signal_dbm)
            
            # Update signal indicator
            self.signal_indicator.setSignalWithAnimation(strongest.signal_dbm)
            
            # Update labels
            self.strongest_ssid.setText(strongest.ssid if strongest.ssid else "<Hidden Network>")
            self.strongest_details.setText(
                f"Channel: {strongest.channel} • Band: {strongest.band} • "
                f"Security: {strongest.security_type}"
            )
        else:
            self.signal_indicator.setSignalWithAnimation(-100)  # Weakest signal
            self.strongest_ssid.setText("No networks found")
            self.strongest_details.setText("")
        
        # Update channel utilization
        ch_24ghz = [n for n in networks if n.band == "2.4 GHz"]
        ch_5ghz = [n for n in networks if n.band == "5 GHz"]
        
        if ch_24ghz:
            channels_24 = {}
            for net in ch_24ghz:
                channels_24[net.channel] = channels_24.get(net.channel, 0) + 1
            
            most_crowded_24 = max(channels_24.items(), key=lambda x: x[1]) if channels_24 else (0, 0)
            self.channel_24_label.setText(
                f"2.4 GHz: {len(ch_24ghz)} networks, Channel {most_crowded_24[0]} most crowded ({most_crowded_24[1]} networks)"
            )
        else:
            self.channel_24_label.setText("2.4 GHz: No networks found")
        
        if ch_5ghz:
            channels_5 = {}
            for net in ch_5ghz:
                channels_5[net.channel] = channels_5.get(net.channel, 0) + 1
            
            most_crowded_5 = max(channels_5.items(), key=lambda x: x[1]) if channels_5 else (0, 0)
            self.channel_5_label.setText(
                f"5 GHz: {len(ch_5ghz)} networks, Channel {most_crowded_5[0]} most crowded ({most_crowded_5[1]} networks)"
            )
        else:
            self.channel_5_label.setText("5 GHz: No networks found")
        
        # Clear old network tiles
        for i in range(self.networks_container_layout.count()):
            item = self.networks_container_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        
        # Sort networks by signal strength (strongest first)
        sorted_networks = sorted(networks, key=lambda n: n.signal_dbm, reverse=True)
        
        # Add tiles for networks
        for network in sorted_networks:
            tile = NetworkTile(network, self)
            tile.selected.connect(self._on_network_selected)
            self.networks_container_layout.addWidget(tile)
        
        # Add stretch to push tiles to top
        self.networks_container_layout.addStretch()
    
    def _on_network_selected(self, network):
        """Handle network selection."""
        # Update UI to show selection
        for i in range(self.networks_container_layout.count() - 1):  # -1 to skip stretch
            widget = self.networks_container_layout.itemAt(i).widget()
            if isinstance(widget, NetworkTile):
                widget.setSelected(widget.network == network)
        
        # Emit signal
        self.network_selected.emit(network)