"""
Progress Indicators Module

This module provides custom progress indicators for the application.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QPen

class CircularProgressIndicator(QWidget):
    """
    A circular loading/progress indicator with animation.
    """
    
    def __init__(self, parent=None, size=40, color=None):
        """
        Initialize the circular progress indicator.
        
        Args:
            parent: Parent widget
            size: Size of the indicator in pixels
            color: Color of the indicator (QColor)
        """
        super().__init__(parent)
        
        # Store properties
        self.size = size
        self.color = color or QColor(33, 150, 243)  # Default blue
        
        # Set widget size
        self.setFixedSize(size, size)
        
        # Animation properties
        self._angle = 0
        self._animation = QPropertyAnimation(self, b"angle")
        self._animation.setDuration(1000)
        self._animation.setStartValue(0)
        self._animation.setEndValue(360)
        self._animation.setLoopCount(-1)  # Loop forever
        self._animation.setEasingCurve(QEasingCurve.Type.Linear)
        
        # Start animation when visible
        self.setVisible(False)
    
    def showEvent(self, event):
        """Handle show event by starting animation."""
        self._animation.start()
        super().showEvent(event)
    
    def hideEvent(self, event):
        """Handle hide event by stopping animation."""
        self._animation.stop()
        super().hideEvent(event)
    
    def paintEvent(self, event):
        """Paint the circular progress indicator."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate center and radius
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(center_x, center_y) - 2
        
        # Configure pen
        pen = QPen(self.color)
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        # Draw arc
        rect = QRectF(center_x - radius, center_y - radius, 2 * radius, 2 * radius)
        
        # Draw 270 degrees arc, starting from the current angle
        start_angle = self._angle * 16
        span_angle = 270 * 16
        painter.drawArc(rect, start_angle, span_angle)
    
    def get_angle(self):
        """Get the current angle."""
        return self._angle
    
    def set_angle(self, angle):
        """Set the current angle and trigger repaint."""
        self._angle = angle
        self.update()
    
    # Property for animation
    angle = pyqtProperty(int, get_angle, set_angle)