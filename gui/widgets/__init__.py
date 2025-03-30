"""
Custom widgets for WiFi Analyzer application.

This package contains custom widgets used in the WiFi Analyzer application,
including dashboard cards, progress indicators, and specialized visualizations.
"""

import os
import logging
from pathlib import Path
from PyQt6.QtGui import QFontDatabase, QFont
from PyQt6.QtWidgets import QApplication

# Configure logging
logger = logging.getLogger(__name__)

# Try to load custom fonts
def load_fonts():
    """Attempt to load custom fonts with fallback to system fonts."""
    # First check if QApplication exists
    if not QApplication.instance():
        logger.warning("QApplication not created yet - deferring font loading")
        return QFont('Arial', 10)  # Return a default font
        
    font_paths = {
        'Roboto-Regular': [':/fonts/Roboto-VariableFont_wdth,wght.ttf', 'fonts/Roboto-VariableFont_wdth,wght.ttf'],
        'Roboto-Italic': [':/fonts/Roboto-Italic-VariableFont_wdth,wght.ttf', 'fonts/Roboto-Italic-VariableFont_wdth,wght.ttf']
    }
    
    loaded_fonts = {}
    
    for font_name, paths in font_paths.items():
        font_loaded = False
        
        for path in paths:
            try:
                # Check if it's a resource path or file path
                if path.startswith(':/'):
                    # Try to load from Qt resources
                    font_id = QFontDatabase.addApplicationFont(path)
                    if font_id != -1:
                        font_loaded = True
                        logger.info(f"Loaded font {font_name} from resource")
                        break
                else:
                    # Try to load from file system
                    if os.path.exists(path):
                        font_id = QFontDatabase.addApplicationFont(path)
                        if font_id != -1:
                            font_loaded = True
                            logger.info(f"Loaded font {font_name} from file: {path}")
                            break
            except Exception as e:
                logger.warning(f"Failed to load font {font_name} from {path}: {str(e)}")
        
        if not font_loaded:
            logger.warning(f"Could not load font {font_name}, will use system fallback")
    
    # Return the best available font
    if 'Roboto' in QFontDatabase.families():
        return QFont('Roboto', 10)
    else:
        # Use a standard system font as fallback
        return QFont('Arial', 10)

# Load application font
APP_FONT = load_fonts()

# Import custom widgets
try:
    from .card import DashboardCard
    from .progress import CircularProgressIndicator
    from .network_stats import NetworkStatsWidget
    from .network_list import TopNetworkListWidget
    from .buttons import ActionButton
    from .toggle import AnimatedToggle  # Importing your toggle class
    
    __all__ = [
        'DashboardCard',
        'CircularProgressIndicator',
        'NetworkStatsWidget',
        'TopNetworkListWidget',
        'ActionButton',
        'AnimatedToggle',  # Making it available for import
        'APP_FONT'
    ]
    
except ImportError as e:
    logger.error(f"Failed to import widget components: {str(e)}")
    # Define fallback widgets if needed
    # This allows the application to start even if some widgets fail to import
