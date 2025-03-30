"""
Network List Widget

This module provides a widget for displaying a summary list of networks.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QFont, QIcon

class NetworkListItem(QFrame):
    """
    Widget representing a single network in the list.
    """
    
    def __init__(self, network, parent=None):
        """
        Initialize the network list item.
        
        Args:
            network: WiFiNetwork object
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Set frame properties
        self.setObjectName("networkListItem")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)
        
        # Signal strength indicator (using icon)
        strength = getattr(network, 'strongest_signal', -100)
        if strength >= -60:
            icon_path = ":/icons/signal_strong.png"
        elif strength >= -70:
            icon_path = ":/icons/signal_good.png"
        elif strength >= -80:
            icon_path = ":/icons/signal_fair.png"
        else:
            icon_path = ":/icons/signal_weak.png"
            
        signal_label = QLabel()
        signal_label.setPixmap(QIcon(icon_path).pixmap(QSize(24, 24)))
        
        # SSID label
        ssid_label = QLabel(network.ssid)
        ssid_label.setObjectName("networkSsid")
        ssid_font = QFont()
        ssid_font.setPointSize(10)
        ssid_font.setBold(True)
        ssid_label.setFont(ssid_font)
        
        # Signal strength and channel
        details_label = QLabel(f"{strength} dBm | Ch {getattr(network, 'primary_channel', 0)}")
        details_label.setObjectName("networkDetails")
        
        # Security type
        security_label = QLabel(getattr(network, 'security_type', ''))
        security_label.setObjectName("networkSecurity")
        security_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # Add widgets to layout
        layout.addWidget(signal_label)
        layout.addWidget(ssid_label, 1)
        layout.addWidget(details_label)
        layout.addWidget(security_label)


class TopNetworkListWidget(QFrame):
    """
    Widget for displaying a list of top networks.
    """
    
    def __init__(self, parent=None):
        """
        Initialize the top networks list widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Set frame properties
        self.setObjectName("networkListCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        
        # Setup UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Top Networks")
        title_label.setObjectName("cardTitle")
        title_font = QFont()
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        
        # Scroll area for network items
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Container for network items
        self.networks_container = QWidget()
        self.networks_layout = QVBoxLayout(self.networks_container)
        self.networks_layout.setContentsMargins(0, 0, 0, 0)
        self.networks_layout.setSpacing(10)
        self.networks_layout.addStretch()
        
        # Add container to scroll area
        scroll_area.setWidget(self.networks_container)
        
        # Add widgets to layout
        layout.addWidget(title_label)
        layout.addWidget(scroll_area)
    
    def set_networks(self, networks):
        """
        Update the list with new network data.
        
        Args:
            networks: List of WiFiNetwork objects
        """
        # Clear existing items
        for i in reversed(range(self.networks_layout.count())):
            item = self.networks_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        # Add new items
        for network in networks:
            item = NetworkListItem(network)
            self.networks_layout.insertWidget(0, item)  # Add at the top
        
        # Add stretch at the end
        self.networks_layout.addStretch()