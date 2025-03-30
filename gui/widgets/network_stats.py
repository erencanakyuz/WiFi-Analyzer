"""
Network Statistics Widget

This module provides a widget for displaying network statistics
and distribution information.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QPainter, QFont, QPen, QBrush

class NetworkStatsWidget(QFrame):
    """
    Widget for displaying network statistics with visualizations.
    """
    
    def __init__(self, parent=None):
        """
        Initialize the network stats widget.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Initialize data
        self.band_data = {'2.4 GHz': 0, '5 GHz': 0}
        self.security_data = {'Open': 0, 'WEP': 0, 'WPA': 0, 'WPA2': 0, 'WPA3': 0}
        
        # Setup UI
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface."""
        # Set frame properties
        self.setObjectName("statsCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Title
        title_label = QLabel("Network Statistics")
        title_label.setObjectName("cardTitle")
        title_font = QFont()
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        
        # Create charts
        self.band_chart = PieChart("Frequency Band Distribution")
        self.security_chart = PieChart("Security Type Distribution")
        
        # Add widgets to layout
        layout.addWidget(title_label)
        layout.addWidget(self.band_chart)
        layout.addWidget(self.security_chart)
    
    def update_stats(self, networks):
        """
        Update statistics based on network data.
        
        Args:
            networks: List of WiFiNetwork objects
        """
        # Reset data
        band_data = {'2.4 GHz': 0, '5 GHz': 0}
        security_data = {'Open': 0, 'WEP': 0, 'WPA': 0, 'WPA2': 0, 'WPA3': 0, 'Other': 0}
        
        # Count networks by band and security type
        for network in networks:
            # Count by band
            band = getattr(network, 'primary_band', None) or getattr(network, 'band', None)
            if band in band_data:
                band_data[band] += 1
            
            # Count by security type
            security = getattr(network, 'security_type', None)
            if security in security_data:
                security_data[security] += 1
            else:
                security_data['Other'] += 1
        
        # Update charts
        self.band_chart.update_data(band_data)
        self.security_chart.update_data(security_data)


class PieChart(QWidget):
    """
    Simple pie chart visualization widget.
    """
    
    COLORS = [
        QColor(33, 150, 243),    # Blue
        QColor(76, 175, 80),     # Green
        QColor(255, 152, 0),     # Orange
        QColor(233, 30, 99),     # Pink
        QColor(156, 39, 176),    # Purple
        QColor(0, 188, 212),     # Cyan
        QColor(255, 87, 34),     # Deep Orange
        QColor(121, 85, 72)      # Brown
    ]
    
    def __init__(self, title, parent=None):
        """
        Initialize the pie chart.
        
        Args:
            title: Chart title
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Store properties
        self.title = title
        self.data = {}
        
        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(120)
    
    def update_data(self, data):
        """
        Update chart data.
        
        Args:
            data: Dictionary of category -> value
        """
        self.data = data
        self.update()
    
    def paintEvent(self, event):
        """Paint the pie chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw title
        painter.setPen(QColor(200, 200, 200))
        title_font = QFont()
        title_font.setPointSize(10)
        painter.setFont(title_font)
        painter.drawText(10, 15, self.title)
        
        # Check if we have data
        total = sum(self.data.values())
        if total == 0:
            # No data, draw placeholder
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            painter.setBrush(QBrush(QColor(50, 50, 50)))
            
            # Draw empty circle
            rect = QRectF(10, 25, 80, 80)
            painter.drawEllipse(rect)
            
            # Draw "No Data" text
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No Data")
            return
        
        # Calculate chart dimensions
        chart_x = 10
        chart_y = 25
        chart_diameter = 80
        chart_rect = QRectF(chart_x, chart_y, chart_diameter, chart_diameter)
        
        # Draw pie segments
        start_angle = 0
        color_index = 0
        legend_y = chart_y
        
        for category, value in self.data.items():
            if value > 0:
                # Calculate angle for this segment (in 1/16 of a degree)
                angle = int(value / total * 360 * 16)
                
                # Set color
                color = self.COLORS[color_index % len(self.COLORS)]
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(color))
                
                # Draw segment
                painter.drawPie(chart_rect, start_angle, angle)
                
                # Draw legend item
                legend_x = chart_x + chart_diameter + 20
                legend_box_size = 10
                
                painter.fillRect(
                    legend_x, 
                    legend_y, 
                    legend_box_size, 
                    legend_box_size, 
                    color
                )
                
                # Draw legend text
                painter.setPen(QColor(200, 200, 200))
                text_font = QFont()
                text_font.setPointSize(9)
                painter.setFont(text_font)
                
                text = f"{category}: {value} ({int(value/total*100)}%)"
                painter.drawText(
                    legend_x + legend_box_size + 5,
                    legend_y + legend_box_size,
                    text
                )
                
                # Update start angle and colors
                start_angle += angle
                color_index += 1
                legend_y += legend_box_size + 5