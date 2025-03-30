"""
Card widget for modern UI look and feel.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QFrame, QSizePolicy)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

class Card(QFrame):
    """
    Modern card widget with title and content area.
    """
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.setStyleSheet("""
            #card {
                background-color: white;
                border-radius: 10px;
                border: none;
            }
        """)
        
        # Create shadow effect for card
        from gui.theme_manager import create_shadow_effect
        self.setGraphicsEffect(create_shadow_effect())
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Title area
        self.title_widget = QWidget()
        self.title_widget.setObjectName("cardTitle")
        self.title_widget.setStyleSheet("""
            #cardTitle {
                background-color: #f5f5f5;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                padding: 10px;
            }
        """)
        
        title_layout = QHBoxLayout(self.title_widget)
        title_layout.setContentsMargins(15, 10, 15, 10)
        
        # Title label
        self.title_label = QLabel(title)
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.title_label.setFont(font)
        title_layout.addWidget(self.title_label)
        
        self.main_layout.addWidget(self.title_widget)
        
        # Separator
        self.separator = QFrame()
        self.separator.setObjectName("cardSeparator")
        self.separator.setFrameShape(QFrame.Shape.HLine)
        self.separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.separator.setFixedHeight(1)
        self.main_layout.addWidget(self.separator)
        
        # Content area
        self.content_widget = QWidget()
        self.content_widget.setObjectName("cardContent")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(15, 15, 15, 15)
        
        self.main_layout.addWidget(self.content_widget)
    
    def setContentWidget(self, widget):
        """Set the content widget of the card."""
        # Clear existing content
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        # Add new content
        self.content_layout.addWidget(widget)
    
    def setTitle(self, title):
        """Set the card title."""
        self.title_label.setText(title)

DashboardCard = Card  # Create an alias for backward compatibility