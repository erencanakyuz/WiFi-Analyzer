"""
Application settings and configuration for the WiFi Analyzer.
"""

import os
import json
from PyQt6.QtCore import QSettings
from pathlib import Path

# Application information
APP_NAME = "WiFi Analyzer"
APP_VERSION = "1.0.0"
ORGANIZATION = "WiFiTools"
ORGANIZATION_NAME = ORGANIZATION  # For compatibility with main.py

# Logging settings
LOG_LEVEL = "INFO"
LOG_ROTATION_SIZE = 5 * 1024 * 1024  # 5 MB
LOG_ROTATION_COUNT = 3

# File paths
APP_DIR = Path.home() / ".wifi_analyzer"
LOG_FILE = APP_DIR / "wifi_analyzer.log"
DB_FILE = APP_DIR / "wifi_history.db"
EXPORT_DIR = APP_DIR / "exports"

# Ensure directories exist
APP_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

# Scanning settings
SCAN_INTERVAL_SECONDS = 30  # Default scan interval in seconds
SCAN_INTERVAL_MS = SCAN_INTERVAL_SECONDS * 1000  # For compatibility with main.py
MAX_SCAN_RETRIES = 3        # Maximum number of scan retries on failure
SCAN_TIMEOUT_SECONDS = 10   # Timeout for scan operations

# Network frequency ranges
CHANNELS_2_4GHZ = list(range(1, 15))  # Channels 1-14
CHANNELS_5GHZ = list(range(36, 166))  # Channels 36-165

# Channel widths in MHz
CHANNEL_WIDTH_2_4GHZ = 22
CHANNEL_WIDTH_5GHZ_STANDARD = 20
CHANNEL_WIDTH_5GHZ_WIDE = 40
CHANNEL_WIDTH_5GHZ_ULTRA = 80
CHANNEL_WIDTH_5GHZ_SUPER = 160

# Non-overlapping channels for 2.4GHz
NON_OVERLAPPING_CHANNELS_2_4GHZ = [1, 6, 11]

# UI Settings
DARK_MODE = False  # Default to light mode
HIGH_CONTRAST = False
FONT_SIZE = 10  # Default font size
REFRESH_RATE_MS = 1000  # UI refresh rate in milliseconds

# Default window size
DEFAULT_WINDOW_WIDTH = 900
DEFAULT_WINDOW_HEIGHT = 700

# QSettings for persistent storage
settings = QSettings(ORGANIZATION, APP_NAME)


def load_settings():
    """Load application settings from QSettings."""
    global SCAN_INTERVAL_SECONDS, DARK_MODE, HIGH_CONTRAST, FONT_SIZE, REFRESH_RATE_MS
    
    SCAN_INTERVAL_SECONDS = int(settings.value("scanning/interval", SCAN_INTERVAL_SECONDS))
    DARK_MODE = bool(settings.value("ui/dark_mode", DARK_MODE))
    HIGH_CONTRAST = bool(settings.value("ui/high_contrast", HIGH_CONTRAST))
    FONT_SIZE = int(settings.value("ui/font_size", FONT_SIZE))
    REFRESH_RATE_MS = int(settings.value("ui/refresh_rate_ms", REFRESH_RATE_MS))


def save_settings():
    """Save current settings to persistent storage."""
    settings.setValue("scanning/interval", SCAN_INTERVAL_SECONDS)
    settings.setValue("ui/dark_mode", DARK_MODE)
    settings.setValue("ui/high_contrast", HIGH_CONTRAST)
    settings.setValue("ui/font_size", FONT_SIZE)
    settings.setValue("ui/refresh_rate_ms", REFRESH_RATE_MS)
    settings.sync()


def export_settings(filepath=None):
    """Export settings to a JSON file."""
    if filepath is None:
        filepath = EXPORT_DIR / "settings_export.json"
    
    settings_dict = {
        "scanning": {
            "interval": SCAN_INTERVAL_SECONDS
        },
        "ui": {
            "dark_mode": DARK_MODE,
            "high_contrast": HIGH_CONTRAST,
            "font_size": FONT_SIZE,
            "refresh_rate_ms": REFRESH_RATE_MS
        }
    }
    
    with open(filepath, 'w') as f:
        json.dump(settings_dict, f, indent=2)
    
    return filepath


def import_settings(filepath):
    """Import settings from a JSON file."""
    global SCAN_INTERVAL_SECONDS, DARK_MODE, HIGH_CONTRAST, FONT_SIZE, REFRESH_RATE_MS
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    try:
        SCAN_INTERVAL_SECONDS = int(data.get("scanning", {}).get("interval", SCAN_INTERVAL_SECONDS))
        DARK_MODE = bool(data.get("ui", {}).get("dark_mode", DARK_MODE))
        HIGH_CONTRAST = bool(data.get("ui", {}).get("high_contrast", HIGH_CONTRAST))
        FONT_SIZE = int(data.get("ui", {}).get("font_size", FONT_SIZE))
        REFRESH_RATE_MS = int(data.get("ui", {}).get("refresh_rate_ms", REFRESH_RATE_MS))
        
        # Save the imported settings
        save_settings()
        return True
    except (KeyError, ValueError) as e:
        return False


# Load settings on module import
load_settings()