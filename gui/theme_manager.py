"""
Theme Manager

Provides modern UI theming capabilities for the WiFi analyzer application.
"""
import logging
from PyQt6.QtGui import QPalette, QColor, QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QWidget
from PyQt6.QtCore import Qt, QSettings
import os

logger = logging.getLogger(__name__)

# Modern color schemes with Material Design inspiration
THEMES = {
    "light": {
        "primary": QColor(33, 150, 243),      # Blue
        "primaryDark": QColor(25, 118, 210),  # Darker blue
        "primaryLight": QColor(100, 181, 246),# Lighter blue
        "secondary": QColor(255, 152, 0),     # Orange
        "success": QColor(76, 175, 80),       # Green
        "warning": QColor(255, 193, 7),       # Amber
        "error": QColor(244, 67, 54),         # Red
        "background": QColor(245, 245, 245),  # Very light gray
        "surface": QColor(255, 255, 255),     # White
        "card": QColor(255, 255, 255),        # White
        "text": QColor(33, 33, 33),           # Almost black
        "textSecondary": QColor(117, 117, 117), # Medium gray
        "divider": QColor(224, 224, 224),     # Light gray
        "shadow": QColor(0, 0, 0, 40),        # Transparent black
    },
    "dark": {
        "primary": QColor(33, 150, 243),      # Blue
        "primaryDark": QColor(25, 118, 210),  # Darker blue
        "primaryLight": QColor(79, 195, 247), # Lighter blue
        "secondary": QColor(255, 167, 38),    # Orange
        "success": QColor(102, 187, 106),     # Green
        "warning": QColor(255, 202, 40),      # Amber
        "error": QColor(255, 82, 82),         # Red
        "background": QColor(18, 18, 18),     # Very dark gray
        "surface": QColor(30, 30, 30),        # Dark gray
        "card": QColor(35, 35, 35),           # Dark gray
        "text": QColor(255, 255, 255),        # White
        "textSecondary": QColor(185, 185, 185), # Light gray
        "divider": QColor(55, 55, 55),        # Medium dark gray
        "shadow": QColor(0, 0, 0, 80),        # Darker transparent black
    },
    "midnight": {
        "primary": QColor(86, 119, 252),      # Bright blue
        "primaryDark": QColor(63, 81, 181),   # Indigo
        "primaryLight": QColor(124, 179, 255),# Light blue
        "secondary": QColor(255, 135, 135),   # Salmon
        "success": QColor(100, 221, 100),     # Bright green
        "warning": QColor(255, 213, 79),      # Light amber
        "error": QColor(255, 95, 109),        # Bright red
        "background": QColor(13, 17, 23),     # Very dark blue-gray
        "surface": QColor(22, 27, 34),        # Dark blue-gray
        "card": QColor(30, 36, 47),           # Medium dark blue-gray
        "text": QColor(240, 246, 252),        # Off-white
        "textSecondary": QColor(139, 148, 158), # Blue-gray
        "divider": QColor(48, 54, 61),        # Medium blue-gray
        "shadow": QColor(0, 0, 0, 90),        # Deep shadow
    },
}

def load_fonts():
    """Load custom fonts for the application."""
    # Define multiple possible locations for fonts
    base_paths = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "fonts"),
        os.path.join(os.path.dirname(__file__), "fonts"),
        "fonts"
    ]
    
    # Qt resource paths
    qt_paths = [
        ":/fonts/Roboto-Regular.ttf",
        ":/fonts/Roboto-Medium.ttf", 
        ":/fonts/Roboto-Bold.ttf"
    ]
    
    font_files = {
        "Roboto-Regular": "Roboto-Regular.ttf",
        "Roboto-Medium": "Roboto-Medium.ttf",
        "Roboto-Bold": "Roboto-Bold.ttf"
    }
    
    loaded_fonts = []
    
    # Try Qt resources first
    for qt_path in qt_paths:
        try:
            font_id = QFontDatabase.addApplicationFont(qt_path)
            if font_id != -1:
                logger.info(f"Loaded font from Qt resource: {qt_path}")
                loaded_fonts.append(os.path.basename(qt_path).split('.')[0])
        except Exception as e:
            logger.debug(f"Could not load Qt resource font {qt_path}: {str(e)}")
    
    # Then try file paths
    for name, filename in font_files.items():
        if name in loaded_fonts:
            continue  # Already loaded from Qt resources
            
        for base_path in base_paths:
            try:
                path = os.path.join(base_path, filename)
                if os.path.exists(path):
                    font_id = QFontDatabase.addApplicationFont(path)
                    if font_id != -1:
                        loaded_fonts.append(name)
                        logger.info(f"Loaded font: {name} from {path}")
                        break
            except Exception as e:
                logger.debug(f"Failed loading font {name} from {base_path}: {str(e)}")
    
    if not loaded_fonts:
        logger.warning("No custom fonts could be loaded, using system fallbacks")
    
    return loaded_fonts

def get_default_font(size=10, bold=False):
    """Get the default application font."""
    # Try to use Roboto if available
    families = QFontDatabase.families()
    
    if "Roboto" in families:
        font = QFont("Roboto", size)
    elif "Segoe UI" in families:  # Windows default
        font = QFont("Segoe UI", size)
    elif "SF Pro Text" in families:  # macOS default
        font = QFont("SF Pro Text", size)
    elif "Ubuntu" in families:  # Ubuntu default
        font = QFont("Ubuntu", size)
    else:
        font = QFont("Arial", size)
    
    if bold:
        font.setBold(True)
    
    return font

def create_shadow_effect(color=QColor(0, 0, 0, 50), blur_radius=15, offset_x=0, offset_y=5):
    """Create a shadow effect for widgets."""
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur_radius)
    shadow.setColor(color)
    shadow.setOffset(offset_x, offset_y)
    return shadow

def apply_modern_styles():
    """Apply additional modern UI styles."""
    return """
    #navBar {
        background-color: #2196F3;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    
    #appTitle {
        color: white;
        padding-left: 15px;
    }
    
    #navButton {
        background-color: transparent;
        color: white;
        border: none;
        font-weight: bold;
        padding: 12px 20px;
        border-radius: 4px;
        min-width: 100px;
    }
    
    #navButton:checked {
        background-color: rgba(255, 255, 255, 0.2);
    }
    
    #navButton:hover {
        background-color: rgba(255, 255, 255, 0.1);
    }
    
    #actionButton {
        background-color: white;
        color: #2196F3;
        font-weight: bold;
        border: none;
        border-radius: 4px;
        padding: 8px 15px;
        margin: 0 15px;
    }
    
    #actionButton:hover {
        background-color: #e0e0e0;
    }
    
    #cardContent {
        background-color: transparent;
    }
    
    #cardSeparator {
        background-color: #e0e0e0;
    }
    
    QProgressBar {
        border: none;
        border-radius: 4px;
        background-color: #f0f0f0;
        text-align: center;
        height: 10px;
    }
    
    QProgressBar::chunk {
        background-color: #2196F3;
        border-radius: 4px;
    }
    """

def apply_theme(theme_name="light"):
    """Apply the specified theme to the application."""
    if theme_name not in THEMES:
        logger.warning(f"Unknown theme: {theme_name}, falling back to light theme")
        theme_name = "light"
    
    theme = THEMES[theme_name]
    logger.info(f"Applying theme: {theme_name}")
    
    # Load fonts before applying theme
    loaded_fonts = load_fonts()
    
    # Update the application palette
    palette = QPalette()
    
    # Basic application colors
    palette.setColor(QPalette.ColorRole.Window, theme["background"])
    palette.setColor(QPalette.ColorRole.WindowText, theme["text"])
    palette.setColor(QPalette.ColorRole.Base, theme["surface"])
    palette.setColor(QPalette.ColorRole.AlternateBase, 
                    QColor(theme["surface"].red() + 10, 
                          theme["surface"].green() + 10, 
                          theme["surface"].blue() + 10))
    palette.setColor(QPalette.ColorRole.ToolTipBase, theme["card"])
    palette.setColor(QPalette.ColorRole.ToolTipText, theme["text"])
    palette.setColor(QPalette.ColorRole.Text, theme["text"])
    palette.setColor(QPalette.ColorRole.Button, theme["surface"])
    palette.setColor(QPalette.ColorRole.ButtonText, theme["text"])
    palette.setColor(QPalette.ColorRole.BrightText, theme["secondary"])
    palette.setColor(QPalette.ColorRole.Link, theme["primary"])
    palette.setColor(QPalette.ColorRole.Highlight, theme["primary"])
    palette.setColor(QPalette.ColorRole.HighlightedText, 
                    QColor(255, 255, 255))  # Always white for highlighted text
    
    # Apply palette to application
    app = QApplication.instance()
    if app:
        app.setPalette(palette)
        
        # Complete the stylesheet with proper theme references
        stylesheet = f"""
        QMainWindow, QDialog {{
            background-color: {theme["background"].name()};
        }}
        
        QToolTip {{
            color: {theme["text"].name()};
            background-color: {theme["card"].name()};
            border: 1px solid {theme["divider"].name()};
        }}
        
        QLabel {{
            color: {theme["text"].name()};
        }}
        
        QPushButton {{
            background-color: {theme["primary"].name()};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
        }}
        
        QPushButton:hover {{
            background-color: {theme["primaryDark"].name()};
        }}
        
        QLineEdit, QComboBox, QSpinBox {{
            border: 1px solid {theme["divider"].name()};
            border-radius: 4px;
            padding: 8px;
            background-color: {theme["surface"].name()};
            color: {theme["text"].name()};
        }}
        """
        
        # Add additional modern styles
        stylesheet += apply_modern_styles()
        
        app.setStyleSheet(stylesheet)
        
        # Set default font
        default_font = get_default_font()
        app.setFont(default_font)
    else:
        logger.warning("No QApplication instance found, theme not applied")
    
    # Save theme preference
    settings = QSettings()
    settings.setValue("theme", theme_name)
    
    # Make theme colors available globally as a dictionary
    global current_theme
    current_theme = theme
    
    logger.info(f"Applied '{theme_name}' theme")
    
    return theme  # Return theme dict for direct use

# Add this global variable to store current theme colors
current_theme = None

# Function to get current theme colors
def get_theme_colors(theme_name=None):
    """Get the theme color dictionary.
    
    Args:
        theme_name: Optional name of theme to get colors for, or a theme dictionary
    
    Returns:
        Dictionary of theme colors
    """
    global current_theme
    
    # If the argument is already a dictionary, return it directly
    if isinstance(theme_name, dict):
        return theme_name
    
    if theme_name is not None and isinstance(theme_name, str):
        # Return specified theme by name
        if theme_name in THEMES:
            return THEMES[theme_name]
        else:
            logger.warning(f"Unknown theme name: {theme_name}, using current theme")
    
    if current_theme is None:
        # Load theme if not initialized
        theme_name = get_current_theme()
        current_theme = THEMES[theme_name]
    
    return current_theme

def get_current_theme():
    """Get the currently active theme name."""
    settings = QSettings()
    return settings.value("theme", "light")

# Example widget showing theme usage
class MyWidget(QWidget):
    """Example showing how to use theme colors in a widget."""
    def __init__(self):
        super().__init__()
        
        # Get current theme colors
        theme = get_theme_colors()
        
        # Use them directly
        self.setStyleSheet(f"background-color: {theme['background'].name()}")

# Inside MainWindow class
from gui.theme_manager import get_theme_colors

def some_method(self):
    theme = get_theme_colors()
    # Use theme colors directly
    self.some_widget.setStyleSheet(f"background-color: {theme['primary'].name()}")