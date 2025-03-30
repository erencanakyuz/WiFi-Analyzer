"""
Theme Manager Module

This module provides theming functionality for the WiFi Analyzer application.
It handles theme switching and provides color schemes for different UI components.

Available themes:
- Light: Default light theme
- Dark: Dark theme for low-light environments
- High Contrast: High contrast theme for accessibility
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QGraphicsDropShadowEffect

# Initialize logger
logger = logging.getLogger(__name__)

# Theme color definitions
THEMES = {
    'light': {
        'window': '#FFFFFF',
        'windowText': '#000000',
        'base': '#FFFFFF',
        'alternateBase': '#F5F5F5',
        'text': '#000000',
        'button': '#F0F0F0',
        'buttonText': '#000000',
        'brightText': '#FFFFFF',
        'highlight': '#0078D7',
        'highlightedText': '#FFFFFF',
        'link': '#0000FF',
        'linkVisited': '#800080',
        
        # Custom colors
        'cardBackground': '#FFFFFF',
        'cardBorder': '#E0E0E0',
        'graphBackground': '#FFFFFF',
        'graphGrid': '#CCCCCC',
        'graphLine': '#0078D7',
        'signalStrong': '#00A000',
        'signalMedium': '#FF8C00',
        'signalWeak': '#E60000',
        'tableBorder': '#E0E0E0',
        'tableHeader': '#F8F8F8',
        'tableAlternate': '#FAFAFA',
        'statusBar': '#F8F8F8',
        'toolBar': '#FFFFFF'
    },
    'dark': {
        'window': '#2D2D2D',
        'windowText': '#FFFFFF',
        'base': '#353535',
        'alternateBase': '#3D3D3D',
        'text': '#FFFFFF',
        'button': '#454545',
        'buttonText': '#FFFFFF',
        'brightText': '#FFFFFF',
        'highlight': '#0078D7',
        'highlightedText': '#FFFFFF',
        'link': '#3391FF',
        'linkVisited': '#B891F5',
        
        # Custom colors
        'cardBackground': '#353535',
        'cardBorder': '#454545',
        'graphBackground': '#2D2D2D',
        'graphGrid': '#404040',
        'graphLine': '#00A5FF',
        'signalStrong': '#00FF00',
        'signalMedium': '#FFB700',
        'signalWeak': '#FF4040',
        'tableBorder': '#454545',
        'tableHeader': '#404040',
        'tableAlternate': '#383838',
        'statusBar': '#252525',
        'toolBar': '#303030'
    },
    'high_contrast': {
        'window': '#000000',
        'windowText': '#FFFFFF',
        'base': '#000000',
        'alternateBase': '#202020',
        'text': '#FFFFFF',
        'button': '#000000',
        'buttonText': '#FFFFFF',
        'brightText': '#FFFFFF',
        'highlight': '#00FF00',
        'highlightedText': '#000000',
        'link': '#00FF00',
        'linkVisited': '#FFFF00',
        
        # Custom colors
        'cardBackground': '#000000',
        'cardBorder': '#FFFFFF',
        'graphBackground': '#000000',
        'graphGrid': '#404040',
        'graphLine': '#FFFF00',
        'signalStrong': '#00FF00',
        'signalMedium': '#FFFF00',
        'signalWeak': '#FF0000',
        'tableBorder': '#FFFFFF',
        'tableHeader': '#202020',
        'tableAlternate': '#101010',
        'statusBar': '#000000',
        'toolBar': '#000000'
    }
}

def create_shadow_effect() -> QGraphicsDropShadowEffect:
    """
    Create a themed shadow effect for cards and widgets.
    
    Returns:
        QGraphicsDropShadowEffect configured for the current theme
    """
    # QColor is already imported at the top level
    
    # Create shadow effect
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(20)
    
    # Use different shadow settings based on theme
    current_theme = get_current_theme() if 'get_current_theme' in globals() else 'dark'
    
    if current_theme == 'dark':
        shadow.setColor(QColor(0, 0, 0, 80))  # Darker shadow for dark theme
    elif current_theme == 'high_contrast':
        shadow.setColor(QColor(255, 255, 255, 100))  # White shadow for high contrast
    else:
        shadow.setColor(QColor(0, 0, 0, 60))  # Default shadow for light theme
        
    shadow.setOffset(0, 4)
    return shadow

class ThemeManager:
    """
    Manages application theming and provides color schemes.
    
    This class handles:
    - Theme switching
    - Color scheme access
    - Custom widget styling
    """
    
    _current_theme: str = 'light'
    _instance: Optional['ThemeManager'] = None
    
    @classmethod
    def instance(cls) -> 'ThemeManager':
        """Get singleton instance of ThemeManager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def apply_theme(self, theme_name: str) -> None:
        """
        Apply a theme to the application.

        Args:
            theme_name: Name of the theme to apply
            
        Raises:
            ValueError: If theme_name is not valid
        """
        if theme_name not in THEMES:
            raise ValueError(f"Invalid theme name: {theme_name}")
        
        try:
            self._current_theme = theme_name
            theme = THEMES[theme_name]
            
            # Create palette
            palette = QPalette()
            
            # Set standard colors
            palette.setColor(QPalette.ColorRole.Window, QColor(theme['window']))
            palette.setColor(QPalette.ColorRole.WindowText, QColor(theme['windowText']))
            palette.setColor(QPalette.ColorRole.Base, QColor(theme['base']))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(theme['alternateBase']))
            palette.setColor(QPalette.ColorRole.Text, QColor(theme['text']))
            palette.setColor(QPalette.ColorRole.Button, QColor(theme['button']))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme['buttonText']))
            palette.setColor(QPalette.ColorRole.BrightText, QColor(theme['brightText']))
            palette.setColor(QPalette.ColorRole.Highlight, QColor(theme['highlight']))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor(theme['highlightedText']))
            palette.setColor(QPalette.ColorRole.Link, QColor(theme['link']))
            palette.setColor(QPalette.ColorRole.LinkVisited, QColor(theme['linkVisited']))
            
            # Apply palette
            QApplication.instance().setPalette(palette)
            
            # Apply stylesheet for custom widgets
            self._apply_custom_styles(theme)
            
            # Notify observers of theme change
            ThemeObservable.notify_observers(theme_name)
            
            logger.info(f"Applied {theme_name} theme")
            
        except Exception as e:
            logger.error(f"Error applying theme {theme_name}: {e}", exc_info=True)
            raise
    
    def _apply_custom_styles(self, theme: Dict[str, str]) -> None:
        """Apply custom styles for widgets that need special handling."""
        stylesheet = f"""
            QToolBar {{
                background: {theme['toolBar']};
                border: none;
            }}
            
            QStatusBar {{
                background: {theme['statusBar']};
            }}
            
            QFrame[frameShape="4"] {{  /* QFrame.HLine */
                color: {theme['cardBorder']};
            }}
            
            QFrame[frameShape="5"] {{  /* QFrame.VLine */
                color: {theme['cardBorder']};
            }}
            
            QTableView {{
                gridline-color: {theme['tableBorder']};
                background-color: {theme['base']};
                alternate-background-color: {theme['tableAlternate']};
                selection-background-color: {theme['highlight']};
                selection-color: {theme['highlightedText']};
            }}
            
            QHeaderView::section {{
                background-color: {theme['tableHeader']};
                color: {theme['text']};
                padding: 4px;
                border: 1px solid {theme['tableBorder']};
            }}
            
            QScrollBar {{
                background: {theme['base']};
                width: 12px;
                height: 12px;
            }}
            
            QScrollBar::handle {{
                background: {theme['button']};
                border-radius: 6px;
            }}
            
            QScrollBar::add-line, QScrollBar::sub-line {{
                background: none;
            }}
        """
        QApplication.instance().setStyleSheet(stylesheet)
    
    def get_color(self, color_name: str) -> str:
        """
        Get a color value from the current theme.
        
        Args:
            color_name: Name of the color to retrieve
            
        Returns:
            Color value as hex string
            
        Raises:
            KeyError: If color_name is not found in theme
        """
        if color_name not in THEMES[self._current_theme]:
            raise KeyError(f"Color '{color_name}' not found in theme")
        
        return THEMES[self._current_theme][color_name]
    
    def get_current_theme(self) -> str:
        """Get the name of the current theme."""
        return self._current_theme

def get_theme_colors(theme_name=None):
    """
    Get all color settings for a specific theme.
    
    Args:
        theme_name: Name of the theme to get colors for. If None, returns current theme.
        
    Returns:
        Dict with color settings for the theme
    """
    if theme_name is None:
        theme_name = get_current_theme()
        
    if theme_name not in THEMES:
        raise ValueError(f"Theme '{theme_name}' not found")
        
    return THEMES[theme_name]

class ThemeObservable:
    """Observable pattern implementation for theme changes."""
    
    _observers: List['ThemeObserver'] = []
    
    @classmethod
    def register_observer(cls, observer: 'ThemeObserver') -> None:
        """Register an observer to be notified of theme changes."""
        if observer not in cls._observers:
            cls._observers.append(observer)
    
    @classmethod
    def unregister_observer(cls, observer: 'ThemeObserver') -> None:
        """Unregister an observer to no longer receive notifications."""
        if observer in cls._observers:
            cls._observers.remove(observer)
    
    @classmethod
    def notify_observers(cls, theme_name: str) -> None:
        """Notify all registered observers of a theme change."""
        event = ThemeUpdateEvent(theme_name)
        for observer in cls._observers:
            observer.on_theme_changed(event)

def apply_theme(theme_name: str) -> None:
    """
    Apply a theme to the application (convenience function).
    
    Args:
        theme_name: Name of the theme to apply
    """
    ThemeManager.instance().apply_theme(theme_name)
    ThemeObservable.notify_observers(theme_name)

def get_color(color_name: str) -> str:
    """
    Get a color from the current theme (convenience function).
    
    Args:
        color_name: Name of the color to retrieve
        
    Returns:
        Color value as hex string
    """
    return ThemeManager.instance().get_color(color_name)

def get_current_theme() -> str:
    """Get the name of the current theme (convenience function)."""
    return ThemeManager.instance().get_current_theme()

def register_theme_observer(observer: 'ThemeObserver') -> None:
    """
    Register an observer to be notified of theme changes.
    
    Args:
        observer: Observer to register
    """
    ThemeObservable.register_observer(observer)

def unregister_theme_observer(observer: 'ThemeObserver') -> None:
    """
    Unregister an observer to no longer receive notifications.
    
    Args:
        observer: Observer to unregister
    """
    ThemeObservable.unregister_observer(observer)

class ThemeObserver:
    """Base class for theme change observers."""
    def on_theme_changed(self, event: 'ThemeUpdateEvent') -> None:
        """
        Handle theme change events.
        
        Args:
            event: Theme update event containing the new theme name
        """
        pass

class ThemeUpdateEvent:
    """Event representing a theme change."""
    def __init__(self, theme_name: str):
        self.theme_name = theme_name
