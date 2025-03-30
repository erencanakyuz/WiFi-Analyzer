"""
Dashboard view for WiFi analyzer.

Provides a modern overview of the WiFi environment with real-time statistics,
including:
- Total network count
- Channel utilization for both 2.4GHz and 5GHz bands
- Strongest network details
- Interactive list of all detected networks
"""

import logging
from typing import Dict, List, Optional, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QScrollArea, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from gui.widgets.card import Card as DashboardCard
from gui.widgets.signal_indicator import SignalIndicator
from gui.widgets.network_tile import NetworkTile
from scanner.models import WiFiNetwork

logger = logging.getLogger(__name__)

class DashboardView(QWidget):
    """
    Modern dashboard view for WiFi network analysis.
    
    Displays a comprehensive overview of the WiFi environment with:
    - Network statistics cards
    - Channel utilization information
    - Strongest network details with signal indicator
    - Scrollable list of all detected networks
    
    Signals:
        network_selected (WiFiNetwork): Emitted when a network is selected
        refresh_requested (): Emitted when a manual refresh is requested
    """
    network_selected = pyqtSignal(WiFiNetwork)  # Typed signal
    refresh_requested = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the dashboard view.
        
        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)
        self.networks: List[WiFiNetwork] = []
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """
        Set up the user interface components.
        
        Creates:
        - Network count summary card
        - Channel utilization card
        - Strongest network card
        - Scrollable network list
        """
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
    
    def set_networks(self, networks: List[WiFiNetwork]) -> None:
        """
        Update the dashboard with new network data.
        
        Args:
            networks: List of WiFiNetwork objects to display
            
        Note:
            Updates all dashboard components including:
            - Network count
            - Strongest network display
            - Channel utilization statistics
            - Network tile list
            
        Raises:
            Exception: If there's an error updating any component
        """
        try:
            self.networks = networks
            self._update_network_count(networks)
            self._update_strongest_network(networks)
            self._update_channel_stats(networks)
            self._update_network_tiles(networks)
        except Exception as e:
            logger.error(f"Error updating dashboard: {e}")
            self.networks_count.setText("Error")
            self.strongest_ssid.setText("Error updating dashboard")
            raise  # Re-raise for higher-level error handling
    
    def _update_network_count(self, networks: List[WiFiNetwork]) -> None:
        """Update the network count display."""
        try:
            self.networks_count.setText(str(len(networks)))
        except Exception as e:
            logger.error(f"Error updating network count: {e}")
            self.networks_count.setText("Error")

    def _update_strongest_network(self, networks: List[WiFiNetwork]) -> None:
        """Update the strongest network card display."""
        try:
            if networks:
                strongest = max(networks, key=lambda n: n.bssids[0].signal_dbm if n.bssids else -100)
                self.signal_indicator.setSignalWithAnimation(strongest.bssids[0].signal_dbm if strongest.bssids else -100)
                self.strongest_ssid.setText(strongest.ssid if strongest.ssid else "<Hidden Network>")
                self.strongest_details.setText(
                    f"Channel: {strongest.primary_channel} • Band: {strongest.primary_band} • "
                    f"Security: {strongest.security_type}"
                )
            else:
                self.signal_indicator.setSignalWithAnimation(-100)
                self.strongest_ssid.setText("No networks found")
                self.strongest_details.setText("")
        except Exception as e:
            logger.error(f"Error updating strongest network: {e}")
            self.strongest_ssid.setText("Error")
            self.strongest_details.setText("")

    def _update_channel_stats(self, networks: List[WiFiNetwork]) -> None:
        """Update channel utilization statistics."""
        try:
            ch_24ghz = [n for n in networks if n.band == "2.4 GHz"]
            ch_5ghz = [n for n in networks if n.band == "5 GHz"]
            
            self._update_band_stats(ch_24ghz, is_24ghz=True)
            self._update_band_stats(ch_5ghz, is_24ghz=False)
        except Exception as e:
            logger.error(f"Error updating channel stats: {e}")
            self.channel_24_label.setText("2.4 GHz: Error")
            self.channel_5_label.setText("5 GHz: Error")

    def _update_band_stats(self, networks: List[WiFiNetwork], is_24ghz: bool) -> None:
        """Update statistics for a specific frequency band."""
        label = self.channel_24_label if is_24ghz else self.channel_5_label
        band = "2.4 GHz" if is_24ghz else "5 GHz"
        
        if networks:
            channels: Dict[int, int] = {}
            for net in networks:
                channels[net.channel] = channels.get(net.channel, 0) + 1
            
            most_crowded = max(channels.items(), key=lambda x: x[1])
            label.setText(
                f"{band}: {len(networks)} networks, Channel {most_crowded[0]} "
                f"most crowded ({most_crowded[1]} networks)"
            )
        else:
            label.setText(f"{band}: No networks found")

    def _update_network_tiles(self, networks: List[WiFiNetwork]) -> None:
        """Update the network tiles display."""
        try:
            # Clear old tiles
            self._clear_network_tiles()
            
            # Add new tiles
            sorted_networks = sorted(networks, key=lambda n: n.signal_dbm, reverse=True)
            for network in sorted_networks:
                tile = NetworkTile(network, self)
                tile.selected.connect(self._on_network_selected)
                self.networks_container_layout.addWidget(tile)
            
            # Add stretch to push tiles to top
            self.networks_container_layout.addStretch()
        except Exception as e:
            logger.error(f"Error updating network tiles: {e}")

    def _clear_network_tiles(self) -> None:
        """Clear all network tiles from the container."""
        while self.networks_container_layout.count():
            item = self.networks_container_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    def _on_network_selected(self, network: WiFiNetwork) -> None:
        """
        Handle network selection.
        
        Args:
            network: Selected WiFiNetwork object
        """
        # Update UI to show selection
        for i in range(self.networks_container_layout.count() - 1):  # -1 to skip stretch
            widget = self.networks_container_layout.itemAt(i).widget()
            if isinstance(widget, NetworkTile):
                widget.setSelected(widget.network == network)
        
        # Emit signal
        self.network_selected.emit(network)
