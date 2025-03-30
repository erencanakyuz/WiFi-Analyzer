"""
Custom Button Widgets Module

This module provides custom button implementations for the application.
"""

from PyQt6.QtWidgets import QPushButton, QGraphicsDropShadowEffect, QSizePolicy
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont, QColor

class ActionButton(QPushButton):
    """
    A stylized action button with icon and text.
    """
    
    def __init__(self, text, icon_path=None, parent=None):
        """
        Initialize the action button.
        
        Args:
            text: Button text
            icon_path: Path to icon image (optional)
            parent: Parent widget
        """
        super().__init__(text, parent)
        
        # Set button properties
        self.setObjectName("actionButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        
        # Set font
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.setFont(font)
        
        # Set fixed height
        self.setFixedHeight(36)
        
        # Set icon if provided
        if icon_path:
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(20, 20))
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)