"""
Modern network tile widget for WiFi analyzer.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QFrame, QSizePolicy, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QPainterPath, QPalette

class NetworkTile(QFrame):
    """
    Modern tile view for a WiFi network.
    """
    # Signal emitted when tile is clicked
    selected = pyqtSignal(object)
    
    def __init__(self, network, parent=None):
        super().__init__(parent)
        
        self.network = network
        self.is_selected = False
        
        # Set up frame properties
        self.setObjectName("networkTile")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setContentsMargins(10, 10, 10, 10)
        
        # Add hover and shadow effects
        self.setAutoFillBackground(False)
        
        # Make it clickable
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Create layout
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Left side - Network info
        info_layout = QVBoxLayout()
        
        # SSID with security icon
        ssid_layout = QHBoxLayout()
        
        # SSID label
        ssid_text = self.network.ssid if self.network.ssid else "<Hidden Network>"
        self.ssid_label = QLabel(ssid_text)
        font = self.ssid_label.font()
        font.setPointSize(12)
        font.setBold(True)
        self.ssid_label.setFont(font)
        ssid_layout.addWidget(self.ssid_label)
        
        # Security icon (text for now, can be replaced with icon)
        security_color = self._get_security_color(self.network.security_type)
        self.security_label = QLabel(self.network.security_type)
        self.security_label.setStyleSheet(f"color: {security_color.name()}; font-weight: bold;")
        ssid_layout.addWidget(self.security_label)
        
        ssid_layout.addStretch()
        info_layout.addLayout(ssid_layout)
        
        # Details line - with safe attribute access
        try:
            channel = getattr(self.network, 'channel', '?')
            band = getattr(self.network, 'band', 'Unknown')
            bssid = getattr(self.network, 'bssid', 'Unknown')
            details = f"Channel {channel} • {band} • BSSID: {bssid}"
            self.details_label = QLabel(details)
        except Exception as e:
            self.details_label = QLabel("Details unavailable")
        
        font = self.details_label.font()
        font.setPointSize(9)
        self.details_label.setFont(font)
        self.details_label.setStyleSheet("color: #6c757d;")  # Secondary text color
        info_layout.addWidget(self.details_label)
        
        # Add the info layout to the main layout
        layout.addLayout(info_layout)
        
        # Right side - Signal strength
        signal_layout = QVBoxLayout()
        signal_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # Signal strength
        self.signal_label = QLabel(f"{self.network.signal_dbm} dBm")
        font = self.signal_label.font()
        font.setBold(True)
        font.setPointSize(12)
        self.signal_label.setFont(font)
        
        # Set color based on signal strength
        signal_color = self._get_signal_color(self.network.signal_dbm)
        self.signal_label.setStyleSheet(f"color: {signal_color.name()};")
        
        signal_layout.addWidget(self.signal_label)
        layout.addLayout(signal_layout)
    
    def _get_security_color(self, security_type):
        """Get color for security type."""
        if security_type == "WPA3":
            return QColor(0, 150, 0)  # Dark green - most secure
        elif security_type == "WPA2":
            return QColor(0, 200, 0)  # Green
        elif security_type == "WPA":
            return QColor(200, 200, 0)  # Yellow
        elif security_type == "WEP":
            return QColor(200, 100, 0)  # Orange
        elif security_type == "Open":
            return QColor(200, 0, 0)  # Red - insecure
        else:
            return QColor(150, 150, 150)  # Gray - unknown
    
    def _get_signal_color(self, signal_dbm):
        """Get color based on signal strength."""
        # Convert to percentage for easier threshold comparison
        min_dbm = -100
        max_dbm = -30
        percentage = min(100, max(0, (signal_dbm - min_dbm) / (max_dbm - min_dbm) * 100))
        
        if percentage > 70:
            return QColor(76, 175, 80)  # Green
        elif percentage > 40:
            return QColor(255, 193, 7)  # Amber
        else:
            return QColor(244, 67, 54)  # Red
    
    def setSelected(self, selected):
        """Set the selected state of the tile."""
        self.is_selected = selected
        self.update()
    
    def mousePressEvent(self, event):
        """Handle mouse press event."""
        self.selected.emit(self.network)
        super().mousePressEvent(event)
    
    def enterEvent(self, event):
        """Handle mouse hover enter event."""
        if not self.is_selected:
            # Add hover shadow effect
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(10)
            shadow.setColor(QColor(0, 0, 0, 50))
            shadow.setOffset(0, 3)
            self.setGraphicsEffect(shadow)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse hover leave event."""
        if not self.is_selected:
            self.setGraphicsEffect(None)
        super().leaveEvent(event)
    
    def paintEvent(self, event):
        """Custom paint event for rounded corners and selection effect."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get colors from palette
        if self.is_selected:
            bg_color = self.palette().color(QPalette.ColorRole.Highlight).lighter(130)
            text_color = self.palette().color(QPalette.ColorRole.HighlightedText)
            self.ssid_label.setStyleSheet(f"color: {text_color.name()};")
            self.details_label.setStyleSheet(f"color: {text_color.name().replace('#', '#88')};")
            
            # Add selected shadow effect
            if not self.graphicsEffect():
                shadow = QGraphicsDropShadowEffect(self)
                shadow.setBlurRadius(15)
                shadow.setColor(QColor(0, 0, 0, 70))
                shadow.setOffset(0, 4)
                self.setGraphicsEffect(shadow)
        else:
            bg_color = self.palette().color(QPalette.ColorRole.Base)
            text_color = self.palette().color(QPalette.ColorRole.Text)
            self.ssid_label.setStyleSheet("")
            self.details_label.setStyleSheet("color: #6c757d;")
        
        # Draw rounded rectangle for tile background
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 10, 10)
        
        # Draw background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawPath(path)
        
        # Draw border
        if self.is_selected:
            border_color = self.palette().color(QPalette.ColorRole.Highlight)
            painter.setPen(QPen(border_color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
        else:
            border_color = self.palette().color(QPalette.ColorRole.Mid)
            painter.setPen(QPen(border_color, 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
        
        super().paintEvent(event)
    
    def sizeHint(self):
        """Provide a default size hint."""
        return QSize(400, 80)