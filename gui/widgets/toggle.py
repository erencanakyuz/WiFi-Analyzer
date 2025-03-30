"""
Toggle Switch Widget Module

This module provides a modern animated toggle switch widget.
"""

from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from ..theme_manager import get_theme_colors

class AnimatedToggle(QCheckBox):
    """
    A modern toggle switch with animation.
    """
    
    def __init__(self, parent=None):
        """
        Initialize the toggle switch.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Set checkbox properties
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Get theme colors
        theme = get_theme_colors()
        
        # Initialize animation properties
        self._track_color_on = theme["primary"]
        self._track_color_off = theme["textSecondary"]
        self._thumb_color_on = QColor(255, 255, 255)
        self._thumb_color_off = QColor(255, 255, 255)
        
        # Set size
        self.setFixedSize(QSize(60, 30))
        
        # Animation properties
        self._position = 0 if not self.isChecked() else 1
        self._animation = QPropertyAnimation(self, b"position")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
    
    def paintEvent(self, event):
        """Paint the toggle switch."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate dimensions
        track_width = self.width() - 4
        track_height = 20
        track_x = 2
        track_y = (self.height() - track_height) // 2
        
        thumb_radius = track_height
        thumb_x = track_x + self._position * (track_width - thumb_radius * 2) + 2
        thumb_y = (self.height() - thumb_radius * 2) // 2
        
        # Paint track
        track_color = QColor()
        track_color.setRedF(self._track_color_off.redF() * (1 - self._position) +
                          self._track_color_on.redF() * self._position)
        track_color.setGreenF(self._track_color_off.greenF() * (1 - self._position) +
                            self._track_color_on.greenF() * self._position)
        track_color.setBlueF(self._track_color_off.blueF() * (1 - self._position) +
                           self._track_color_on.blueF() * self._position)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(track_color))
        painter.drawRoundedRect(track_x, track_y, track_width, track_height, track_height // 2, track_height // 2)
        
        # Paint thumb
        thumb_color = QColor()
        thumb_color.setRedF(self._thumb_color_off.redF() * (1 - self._position) +
                          self._thumb_color_on.redF() * self._position)
        thumb_color.setGreenF(self._thumb_color_off.greenF() * (1 - self._position) +
                            self._thumb_color_on.greenF() * self._position)
        thumb_color.setBlueF(self._thumb_color_off.blueF() * (1 - self._position) +
                           self._thumb_color_on.blueF() * self._position)
        
        painter.setPen(QPen(QColor(180, 180, 180), 1))
        painter.setBrush(QBrush(thumb_color))
        painter.drawEllipse(QRectF(thumb_x, thumb_y, thumb_radius, thumb_radius))
    
    def hitButton(self, pos):
        """Determine if position is within the toggle switch."""
        return self.contentsRect().contains(pos)
    
    def mousePressEvent(self, event):
        """Handle mouse press event."""
        super().mousePressEvent(event)
        self.animate_position()
    
    def animate_position(self):
        """Animate the position change based on checked state."""
        target_position = 1.0 if self.isChecked() else 0.0
        
        # Set animation
        self._animation.stop()
        self._animation.setStartValue(self._position)
        self._animation.setEndValue(target_position)
        self._animation.start()
    
    def get_position(self):
        """Get the current position."""
        return self._position
    
    def set_position(self, position):
        """Set the current position and trigger repaint."""
        self._position = position
        self.update()
    
    # Property for animation
    position = pyqtProperty(float, get_position, set_position)