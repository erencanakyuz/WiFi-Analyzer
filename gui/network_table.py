"""
Network Table Module

This module provides a modern card-based view for displaying WiFi network information
with sorting, filtering, and visual signal strength indicators.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from PyQt6.QtWidgets import (
    QStyledItemDelegate, QStyleOptionViewItem, QWidget, 
    QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, 
    QMenu, QComboBox, QFrame, QSizePolicy, QStyle,
    QApplication, QScrollArea, QGridLayout, QGraphicsDropShadowEffect,
    QToolButton
)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QAction, QColor, QBrush, QPainter, QPen, QFont, QIcon, QPixmap

from scanner.models import WiFiNetwork
from gui.theme_manager import get_theme_colors

logger = logging.getLogger(__name__)


class NetworkCard(QFrame):
    """
    Modern card widget representing a single WiFi network.
    """
    clicked = pyqtSignal(WiFiNetwork)
    
    def __init__(self, network, parent=None):
        super().__init__(parent)
        self.network = network
        self.setup_ui()
        
    def setup_ui(self):
        # Get theme colors
        theme = get_theme_colors()
        
        # Set frame properties
        self.setObjectName("networkCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(theme["shadow"])
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        # Set style sheet
        self.setStyleSheet(f"""
            #networkCard {{
                background-color: {theme["card"].name()};
                border-radius: 10px;
                padding: 0px;
                margin: 5px;
            }}
            QLabel#ssidLabel {{
                font-size: 14px;
                font-weight: bold;
                color: {theme["text"].name()};
            }}
            QLabel#detailsLabel {{
                color: {theme["textSecondary"].name()};
                font-size: 12px;
            }}
            QLabel#securityLabel {{
                font-size: 11px;
                padding: 3px 6px;
                border-radius: 10px;
                background-color: {theme["primaryLight"].name()};
                color: white;
            }}
            QLabel#bandLabel {{
                font-size: 11px;
                padding: 3px 6px;
                border-radius: 10px;
                background-color: {theme["secondary"].name()};
                color: white;
            }}
        """)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Top section with SSID and signal strength
        top_layout = QHBoxLayout()
        
        # SSID section
        ssid_layout = QVBoxLayout()
        ssid_label = QLabel(self.network.ssid if self.network.ssid else "<Hidden Network>")
        ssid_label.setObjectName("ssidLabel")
        
        details_label = QLabel(f"{self.network.bssid} • Ch {self.network.channel}")
        details_label.setObjectName("detailsLabel")
        
        ssid_layout.addWidget(ssid_label)
        ssid_layout.addWidget(details_label)
        
        # Signal section
        signal_widget = QWidget()
        signal_layout = QVBoxLayout(signal_widget)
        signal_layout.setContentsMargins(0, 0, 0, 0)
        
        # Calculate signal quality percentage
        signal_quality = min(100, max(0, (self.network.signal_dbm + 100) * 2))
        
        # Signal strength circle indicator
        signal_indicator = QLabel()
        signal_indicator.setFixedSize(QSize(50, 50))
        
        # Create signal indicator pixmap
        pixmap = QPixmap(50, 50)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw outer circle
        painter.setPen(QPen(QColor(220, 220, 220), 3))
        painter.drawEllipse(2, 2, 46, 46)
        
        # Draw filled arc based on signal strength
        if signal_quality > 70:
            color = theme["success"]
        elif signal_quality > 40:
            color = theme["warning"]
        else:
            color = theme["error"]
            
        painter.setPen(QPen(color, 6))
        painter.drawArc(5, 5, 40, 40, 90*16, int(-(signal_quality/100 * 360)*16))
        
        # Draw signal value
        painter.setPen(theme["text"])
        font = QFont()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, f"{self.network.signal_dbm}")
        
        painter.end()
        
        signal_indicator.setPixmap(pixmap)
        signal_layout.addWidget(signal_indicator, 0, Qt.AlignmentFlag.AlignRight)
        
        # Add signal label
        signal_label = QLabel("dBm")
        signal_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        signal_layout.addWidget(signal_label, 0, Qt.AlignmentFlag.AlignRight)
        
        # Add to top layout
        top_layout.addLayout(ssid_layout, 1)
        top_layout.addWidget(signal_widget)
        
        # Add tag section
        tag_layout = QHBoxLayout()
        tag_layout.setSpacing(8)
        
        # Security tag
        security_label = QLabel(self.network.security_type)
        security_label.setObjectName("securityLabel")
        security_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Band tag
        band_label = QLabel(self.network.band)
        band_label.setObjectName("bandLabel")
        band_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        tag_layout.addWidget(security_label)
        tag_layout.addWidget(band_label)
        tag_layout.addStretch()
        
        # First seen / Last seen
        time_layout = QHBoxLayout()
        
        # Format timestamps
        first_seen = (datetime.fromtimestamp(self.network.first_seen).strftime("%Y-%m-%d %H:%M") 
                    if self.network.first_seen else "Unknown")
        last_seen = (datetime.fromtimestamp(self.network.last_seen).strftime("%Y-%m-%d %H:%M") 
                    if self.network.last_seen else "Unknown")
                    
        time_label = QLabel(f"First seen: {first_seen} • Last seen: {last_seen}")
        time_label.setObjectName("detailsLabel")
        time_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        time_layout.addWidget(time_label)
        time_layout.addStretch()
        
        # Add all sections to main layout
        main_layout.addLayout(top_layout)
        main_layout.addLayout(tag_layout)
        main_layout.addLayout(time_layout)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.network)
        super().mousePressEvent(event)


class NetworkTableView(QWidget):
    """
    Modern widget for displaying and interacting with WiFi network data.
    
    This widget uses cards instead of a traditional table for a modern look and feel.
    """
    network_selected = pyqtSignal(object)
    refresh_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.networks = []
        self.filtered_networks = []
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface components."""
        # Get theme colors
        theme = get_theme_colors()
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header section with title and refresh button
        header_layout = QHBoxLayout()
        
        # Title
        title_label = QLabel("WiFi Networks")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        
        # Refresh button
        self.refresh_button = QPushButton()
        self.refresh_button.setIcon(QIcon(":/icons/refresh.png"))
        self.refresh_button.setIconSize(QSize(20, 20))
        self.refresh_button.setToolTip("Scan for networks")
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_button.setFixedSize(40, 40)
        self.refresh_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme["primary"].name()};
                border-radius: 20px;
                border: none;
                color: white;
            }}
            QPushButton:hover {{
                background-color: {theme["primaryDark"].name()};
            }}
            QPushButton:pressed {{
                background-color: {theme["primaryLight"].name()};
            }}
        """)
        self.refresh_button.clicked.connect(self.on_refresh_clicked)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_button)
        
        # Search and filters section
        filter_frame = QFrame()
        filter_frame.setObjectName("filterFrame")
        filter_frame.setStyleSheet(f"""
            #filterFrame {{
                background-color: {theme["card"].name()};
                border-radius: 10px;
                padding: 10px;
            }}
        """)
        
        filter_layout = QVBoxLayout(filter_frame)
        filter_layout.setContentsMargins(15, 15, 15, 15)
        filter_layout.setSpacing(15)
        
        # Search row
        search_layout = QHBoxLayout()
        search_icon = QLabel()
        search_icon.setPixmap(QIcon(":/icons/search.png").pixmap(QSize(16, 16)))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search networks...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {theme["divider"].name()};
                border-radius: 5px;
                padding: 8px;
                background-color: {theme["surface"].name()};
                color: {theme["text"].name()};
            }}
            QLineEdit:focus {{
                border: 2px solid {theme["primary"].name()};
            }}
        """)
        self.search_edit.textChanged.connect(self.filter_networks)
        
        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_edit)
        
        # Filters row
        filters_layout = QHBoxLayout()
        
        # Band filter
        band_layout = QVBoxLayout()
        band_label = QLabel("Frequency Band")
        self.band_combo = QComboBox()
        self.band_combo.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {theme["divider"].name()};
                border-radius: 5px;
                padding: 6px;
                background-color: {theme["surface"].name()};
                color: {theme["text"].name()};
            }}
        """)
        self.band_combo.addItem("All Bands")
        self.band_combo.addItem("2.4 GHz")
        self.band_combo.addItem("5 GHz")
        self.band_combo.currentIndexChanged.connect(self.filter_networks)
        band_layout.addWidget(band_label)
        band_layout.addWidget(self.band_combo)
        
        # Security filter
        security_layout = QVBoxLayout()
        security_label = QLabel("Security")
        self.security_combo = QComboBox()
        self.security_combo.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {theme["divider"].name()};
                border-radius: 5px;
                padding: 6px;
                background-color: {theme["surface"].name()};
                color: {theme["text"].name()};
            }}
        """)
        self.security_combo.addItem("All Types")
        self.security_combo.addItem("WPA3")
        self.security_combo.addItem("WPA2")
        self.security_combo.addItem("WPA")
        self.security_combo.addItem("WEP")
        self.security_combo.addItem("Open")
        self.security_combo.currentIndexChanged.connect(self.filter_networks)
        security_layout.addWidget(security_label)
        security_layout.addWidget(self.security_combo)
        
        # Min signal filter
        signal_layout = QVBoxLayout()
        signal_label = QLabel("Minimum Signal")
        self.signal_combo = QComboBox()
        self.signal_combo.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {theme["divider"].name()};
                border-radius: 5px;
                padding: 6px;
                background-color: {theme["surface"].name()};
                color: {theme["text"].name()};
            }}
        """)
        self.signal_combo.addItem("All signals")
        self.signal_combo.addItem("Poor (-90 dBm)")
        self.signal_combo.addItem("Fair (-80 dBm)")
        self.signal_combo.addItem("Good (-70 dBm)")
        self.signal_combo.addItem("Excellent (-60 dBm)")
        self.signal_combo.currentIndexChanged.connect(self.filter_networks)
        signal_layout.addWidget(signal_label)
        signal_layout.addWidget(self.signal_combo)
        
        # Sort options
        sort_layout = QVBoxLayout()
        sort_label = QLabel("Sort by")
        self.sort_combo = QComboBox()
        self.sort_combo.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {theme["divider"].name()};
                border-radius: 5px;
                padding: 6px;
                background-color: {theme["surface"].name()};
                color: {theme["text"].name()};
            }}
        """)
        self.sort_combo.addItem("Signal (strongest first)")
        self.sort_combo.addItem("SSID (A-Z)")
        self.sort_combo.addItem("Channel")
        self.sort_combo.addItem("Security")
        self.sort_combo.currentIndexChanged.connect(self.filter_networks)
        sort_layout.addWidget(sort_label)
        sort_layout.addWidget(self.sort_combo)
        
        filters_layout.addLayout(band_layout)
        filters_layout.addLayout(security_layout)
        filters_layout.addLayout(signal_layout)
        filters_layout.addLayout(sort_layout)
        
        filter_layout.addLayout(search_layout)
        filter_layout.addLayout(filters_layout)
        
        # Set up network cards scroll area
        self.cards_area = QScrollArea()
        self.cards_area.setWidgetResizable(True)
        self.cards_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.cards_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.cards_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {theme["background"].name()};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {theme["primaryLight"].name()};
                border-radius: 5px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(5, 5, 5, 5)
        self.cards_layout.setSpacing(15)
        self.cards_layout.addStretch()
        
        self.cards_area.setWidget(self.cards_container)
        
        # Status area
        self.status_label = QLabel("No networks found")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_font = QFont()
        status_font.setItalic(True)
        self.status_label.setFont(status_font)
        
        # Add widgets to main layout
        main_layout.addLayout(header_layout)
        main_layout.addWidget(filter_frame)
        main_layout.addWidget(self.cards_area, 1)
        main_layout.addWidget(self.status_label)
        
        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    
    def set_networks(self, networks: List[WiFiNetwork]):
        """
        Update the view with new network data.
        
        Args:
            networks: List of WiFiNetwork objects to display
        """
        self.networks = networks
        self.filter_networks()
        self.status_label.setText(f"{len(networks)} networks found")
    
    def filter_networks(self):
        """Apply filters to the network list."""
        filtered = self.networks.copy()
        
        # Apply search filter
        search_text = self.search_edit.text().lower()
        if search_text:
            filtered = [n for n in filtered if 
                        search_text in n.ssid.lower() or 
                        search_text in n.bssid.lower() or
                        search_text in str(n.channel) or
                        search_text in n.security_type.lower()]
        
        # Apply band filter
        band_idx = self.band_combo.currentIndex()
        if band_idx == 1:  # 2.4 GHz
            filtered = [n for n in filtered if n.band == "2.4 GHz"]
        elif band_idx == 2:  # 5 GHz
            filtered = [n for n in filtered if n.band == "5 GHz"]
        
        # Apply security filter
        security_idx = self.security_combo.currentIndex()
        if security_idx > 0:
            security_type = self.security_combo.currentText()
            filtered = [n for n in filtered if n.security_type == security_type]
        
        # Apply signal filter
        signal_idx = self.signal_combo.currentIndex()
        if signal_idx == 1:  # Poor
            filtered = [n for n in filtered if n.signal_dbm >= -90]
        elif signal_idx == 2:  # Fair
            filtered = [n for n in filtered if n.signal_dbm >= -80]
        elif signal_idx == 3:  # Good
            filtered = [n for n in filtered if n.signal_dbm >= -70]
        elif signal_idx == 4:  # Excellent
            filtered = [n for n in filtered if n.signal_dbm >= -60]
        
        # Apply sort
        sort_idx = self.sort_combo.currentIndex()
        if sort_idx == 0:  # Signal
            filtered.sort(key=lambda n: n.signal_dbm, reverse=True)
        elif sort_idx == 1:  # SSID
            filtered.sort(key=lambda n: n.ssid.lower() if n.ssid else "zzzzzz")
        elif sort_idx == 2:  # Channel
            filtered.sort(key=lambda n: n.channel)
        elif sort_idx == 3:  # Security
            filtered.sort(key=lambda n: n.security_type)
        
        # Update the filtered_networks list
        self.filtered_networks = filtered
        
        # Clear existing widgets from the layout
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add network cards to the existing layout
        for network in self.filtered_networks:
            card = NetworkCard(network)
            card.clicked.connect(self.on_card_clicked)
            # Insert above the stretch that was added in setup_ui
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
        
        # Update status label
        visible_count = len(self.filtered_networks)
        total_count = len(self.networks)
        if visible_count == total_count:
            self.status_label.setText(f"{total_count} networks found")
        else:
            self.status_label.setText(f"{visible_count} of {total_count} networks shown")
    
    def on_card_clicked(self, network):
        """
        Handle card click event.
        
        Args:
            network: WiFiNetwork object associated with the clicked card
        """
        self.network_selected.emit(network)
    
    def on_refresh_clicked(self):
        """Handle refresh button click."""
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Scanning...")
        
        # Emit signal instead of calling parent method directly
        self.refresh_requested.emit()
    
    def refresh_complete(self):
        """Update the UI after a refresh operation completes."""
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh")