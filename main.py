#!/usr/bin/env python
"""
WiFi Analysis and Channel Visualization Application

Main Entry Point

This script initializes the application, sets up logging, and launches the GUI.
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Ensure the application can be run from any directory
app_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(app_dir))

# Import required application modules
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings, Qt

from config.settings import (
    APP_NAME, APP_VERSION, ORGANIZATION_NAME,
    LOG_LEVEL, LOG_ROTATION_SIZE, LOG_ROTATION_COUNT
)
from gui.main_window import MainWindow
from scanner.windows_scanner import WindowsWiFiScanner
from gui.theme_manager import apply_theme, get_theme_colors


def setup_logging():
    """Configure the application logging system with rotation to prevent log file growth."""
    # Create logs directory if it doesn't exist
    log_dir = Path(app_dir, "logs")
    log_dir.mkdir(exist_ok=True)
    
    # Set up log file path with timestamp
    log_filename = f"{APP_NAME.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.log"
    log_path = Path(log_dir, log_filename)
    
    # Configure logging with rotation
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Create console handler for debugging
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO if LOG_LEVEL == "DEBUG" else getattr(logging, LOG_LEVEL))
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Create file handler with rotation
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=LOG_ROTATION_SIZE,
        backupCount=LOG_ROTATION_COUNT
    )
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Log application startup
    logging.info(f"Starting {APP_NAME} v{APP_VERSION}")
    logging.debug(f"Log file: {log_path}")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=f"{APP_NAME} v{APP_VERSION}")
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--no-scan', action='store_true', help='Skip initial network scan')
    parser.add_argument('--test-adapter', action='store_true', help='Test WiFi adapter only and exit')
    return parser.parse_args()


def check_windows_platform():
    """Check that application is running on a Windows platform."""
    if sys.platform != 'win32':
        logging.error("This application is designed for Windows operating systems only.")
        print("Error: This application requires Windows to run.")
        sys.exit(1)


def check_admin_permissions():
    """Check if application has the necessary permissions and warn if not."""
    # This is a simple check, not fool-proof
    try:
        # Try to access a directory that typically requires admin permissions
        test_path = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Temp')
        test_file = os.path.join(test_path, f"{APP_NAME}_admin_test.tmp")
        
        with open(test_file, 'w') as f:
            f.write("admin test")
        os.remove(test_file)
        
        logging.debug("Application has sufficient permissions")
    except (IOError, PermissionError):
        logging.warning("Application may need elevated permissions for some features")
        print("Warning: Some features may require running as administrator")


def main():
    """Main application entry point."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up logging
    setup_logging()
    
    # Platform-specific checks
    check_windows_platform()
    check_admin_permissions()
    
    # Set application properties
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QApplication.setApplicationName(APP_NAME)
    QApplication.setApplicationVersion(APP_VERSION)
    QApplication.setOrganizationName(ORGANIZATION_NAME)
    
    # Create the QApplication instance
    app = QApplication(sys.argv)
    
    try:
        # Apply modern theme from theme_manager
        theme_name = "dark"  # or get from settings
        theme = apply_theme(theme_name)

        # Initialize scanner
        scanner = WindowsWiFiScanner()
        logging.info("WindowsWiFiScanner initialized")
        
        # Create main window without passing theme_colors
        main_window = MainWindow(scanner)
        main_window.show()
        
        # If no-scan option was specified, disable auto-refresh
        if args.no_scan:
            main_window.toggle_auto_refresh(False)
            logging.info("Initial scan skipped due to --no-scan flag")
        
        # If debug mode is enabled, log more verbose information
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logging.debug("Debug mode enabled")
        
        # Start the application event loop
        exit_code = app.exec()
        
        # Clean up and exit
        logging.info(f"{APP_NAME} shutting down with exit code {exit_code}")
        return exit_code
        
    except Exception as e:
        logging.exception(f"Unhandled exception: {e}")
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())