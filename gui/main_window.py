"""
Main Window Module

This module provides the main application window for the WiFi Analyzer application.
It serves as the central component that integrates all UI elements and core functionality.

Key Components:
    - MainWindow: Main application window with menu, toolbar, and status bar
    - ScanWorker: Background worker for network scanning
    - NetworkDetailsDialog: Dialog for showing detailed network information
    - ChannelAnalysisDialog: Dialog for channel analysis and recommendations
    - TestWorker: Background worker for network testing
    - NetworkTest: Mixin class for network testing functionality

The module coordinates:
    - Network scanning and analysis
    - Channel visualization
    - Network testing
    - User interface management
    - Settings persistence
    - Error handling and logging
"""

# Standard library imports
import os
import sys
import logging
import time
import json
import csv
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable, Tuple

# Third-party imports - Qt
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QStatusBar, QProgressBar, QMenuBar, QMenu, QMessageBox, 
    QDialog, QFileDialog, QSplitter, QToolBar, QComboBox, QCheckBox, 
    QApplication, QStyleOptionViewItem, QFrame, QGridLayout, QGroupBox, 
    QDialogButtonBox, QScrollArea
)
from PyQt6.QtCore import (
    Qt, QTimer, QSettings, QSize, QDir, pyqtSignal, QThread, QObject,
    QCoreApplication, QEvent
)
from PyQt6.QtGui import (
    QIcon, QKeySequence, QPixmap, QFont, QAction, QColor, QPalette,
    QCloseEvent
)

# Application imports - GUI components
from gui.network_table import NetworkTableView
from gui.dashboard import DashboardView
from gui.channel_graph import ChannelGraphWidget
from gui.theme_manager import apply_theme

# Application imports - Core functionality
from scanner.models import WiFiNetwork, ScanResult, NetworkBSSID
from scanner.windows_scanner import WindowsWiFiScanner
from utils.channel_analyzer import (
    ChannelAnalyzer, CHANNELS_2_4GHZ, CHANNELS_5GHZ, 
    NON_OVERLAPPING_2_4GHZ, DFS_CHANNELS
)
from utils.network_tester import NetworkTester

# Application imports - Configuration
from config.settings import (
    APP_NAME, APP_VERSION, ORGANIZATION_NAME, SCAN_INTERVAL_MS,
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT
)

# Initialize logger
logger = logging.getLogger(__name__)

class ScanWorker(QThread):
    """
    Worker thread for performing WiFi scanning in the background.
    """
    scan_complete = pyqtSignal(object)  # Emits ScanResult
    scan_progress = pyqtSignal(int)     # Emits progress percentage
    
    def __init__(self, scanner):
        super().__init__()
        self.scanner = scanner
        self.is_running = False
    
    def run(self):
        """Execute the scan operation in a separate thread."""
        self.is_running = True
        try:
            self.scan_progress.emit(10)
            
            scan_result = self.scanner.scan_networks_sync()
            
            self.scan_progress.emit(90)
            self.scan_complete.emit(scan_result)
            self.scan_progress.emit(100)
            
        except Exception as e:
            logger.error(f"Scan failed with exception: {str(e)}", exc_info=True)
            self.scan_complete.emit(ScanResult(
                timestamp=time.time(),
                networks=[],
                success=False,
                error_message=str(e)
            ))
            self.scan_progress.emit(100)
        finally:
            self.is_running = False
    
    def stop(self):
        """Stop the worker thread."""
        self.is_running = False
        self.wait()

class TestWorker(QObject):
    """
    Background worker for network testing.
    
    This class runs network tests in a separate thread to prevent UI freezing.
    It emits signals with test results when completed.
    """
    result_ready = pyqtSignal(dict)
    
    def __init__(self, test_function):
        super().__init__()
        self.test_function = test_function
        
    def run(self):
        """Run the test function and emit results."""
        try:
            result = self.test_function()
            self.result_ready.emit(result)
        except Exception as e:
            logger.error(f"Error in test worker: {e}", exc_info=True)
            self.result_ready.emit({
                'success': False,
                'error': str(e)
            })

class NetworkTestMixin:
    """
    Mixin class providing network testing functionality for MainWindow.
    
    This mixin adds methods for running various network tests and displaying
    their results in the application UI. It requires the main class to have:
    - network_tester attribute (NetworkTester instance)
    - test_results_label attribute (QLabel for showing results)
    - status_bar attribute (QStatusBar for status messages)
    """
    
    def run_test_in_thread(self, test_function: Callable[..., Dict[str, Any]], 
                          callback: Callable[[Dict[str, Any]], None],
                          status_message: str) -> None:
        """
        Run a network test in a background thread.
        
        Args:
            test_function: Test function to execute
            callback: Function to handle test results
            status_message: Message to show in status bar while testing
        """
        try:
            self.status_bar.showMessage(status_message)
            
            test_thread = QThread()
            worker = TestWorker(test_function)
            worker.moveToThread(test_thread)
            worker.result_ready.connect(callback)
            test_thread.started.connect(worker.run)
            test_thread.start()
            
        except Exception as e:
            logger.error(f"Error starting test thread: {e}", exc_info=True)
            self.status_bar.showMessage(f"Failed to start test: {str(e)}", 3000)
    
    def run_ping_test(self) -> None:
        """Run ping test to check network latency and packet loss."""
        def callback(result: Dict[str, Any]) -> None:
            try:
                if result['success']:
                    report = (
                        f"<b>Ping Test Results:</b><br>"
                        f"Target: 8.8.8.8<br>"
                        f"Minimum Latency: {result['min_latency']} ms<br>"
                        f"Average Latency: {result['avg_latency']} ms<br>"
                        f"Maximum Latency: {result['max_latency']} ms<br>"
                        f"Packet Loss: {result['packet_loss']}%<br>"
                        f"Jitter: {result['jitter']} ms"
                    )
                else:
                    report = (
                        f"<b>Ping Test Failed:</b><br>"
                        f"Error: {result['error']}"
                    )
                
                self.test_results_label.setText(report)
                self.status_bar.showMessage("Ping test complete", 3000)
                
            except Exception as e:
                logger.error(f"Error processing ping results: {e}", exc_info=True)
                self.status_bar.showMessage("Error processing ping results", 3000)
        
        self.run_test_in_thread(
            self.network_tester.ping_test,
            callback,
            "Running ping test..."
        )
    
    def run_dns_test(self) -> None:
        """Run DNS resolution test to check name server responsiveness."""
        def callback(result: Dict[str, Any]) -> None:
            try:
                if result.get('avg_time') is not None:
                    report = (
                        f"<b>DNS Resolution Test Results:</b><br>"
                        f"Average Time: {result['avg_time']:.2f} ms<br>"
                        f"Success Rate: {result['success_rate']}%<br><br>"
                        f"<b>Details:</b><br>"
                    )
                    
                    for host_result in result['results']:
                        status = "Success" if host_result['success'] else "Failed"
                        time_ms = (f"{host_result['time_ms']:.2f} ms" 
                                 if host_result['time_ms'] else "N/A")
                        report += f"{host_result['hostname']}: {status} ({time_ms})<br>"
                else:
                    report = (
                        f"<b>DNS Resolution Test Failed:</b><br>"
                        f"No successful resolutions."
                    )
                
                self.test_results_label.setText(report)
                self.status_bar.showMessage("DNS test complete", 3000)
                
            except Exception as e:
                logger.error(f"Error processing DNS results: {e}", exc_info=True)
                self.status_bar.showMessage("Error processing DNS results", 3000)
        
        self.run_test_in_thread(
            self.network_tester.dns_resolution_test,
            callback,
            "Testing DNS resolution..."
        )
    
    def run_throughput_test(self) -> None:
        """Run throughput test to estimate network speed."""
        def callback(result: Dict[str, Any]) -> None:
            try:
                if result['success']:
                    report = (
                        f"<b>Throughput Test Results:</b><br>"
                        f"Download Speed: {result['speed_mbps']} Mbps<br>"
                        f"Downloaded: {result['size_bytes'] / 1024:.1f} KB<br>"
                        f"Time: {result['time_seconds']} seconds"
                    )
                else:
                    report = (
                        f"<b>Throughput Test Failed:</b><br>"
                        f"Error: {result['error']}"
                    )
                
                self.test_results_label.setText(report)
                self.status_bar.showMessage("Throughput test complete", 3000)
                
            except Exception as e:
                logger.error(f"Error processing throughput results: {e}", exc_info=True)
                self.status_bar.showMessage("Error processing throughput results", 3000)
        
        self.run_test_in_thread(
            self.network_tester.throughput_test,
            callback,
            "Estimating network throughput..."
        )

class MainWindow(QMainWindow, NetworkTestMixin):
    """
    Main application window for WiFi Analyzer.
    
    This class provides the primary user interface for the application, including
    menu, toolbar, status bar, and tabbed interface for different views.
    """
    
    def __init__(self, scanner: WindowsWiFiScanner):
        """
        Initialize the main window.
        
        Args:
            scanner: WiFi scanner instance for network discovery
        """
        super().__init__()
        
        # Create scan worker
        self.scan_worker = None
        
        # Store scanner reference
        self.scanner = scanner
        
        # Initialize other components
        self.channel_analyzer = ChannelAnalyzer()
        self.network_tester = NetworkTester()
        
        # Setup UI components
        self.setup_ui()
        
        # Load settings
        self.load_settings()
        
        # Set up auto-refresh timer
        self.setup_refresh_timer()
        
        # Begin initial scan if not disabled
        self.start_scan()
        
        # Log initialization
        logger.info("Main window initialized")
    
    def setup_ui(self):
        """Set up the user interface."""
        # Set window properties
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create dashboard tab
        self.dashboard_view = DashboardView()
        self.dashboard_view.refresh_requested.connect(self.start_scan)
        self.dashboard_view.network_selected.connect(self.on_network_selected)
        self.tab_widget.addTab(self.dashboard_view, "Dashboard")
        
        # Create networks tab
        self.network_table_view = NetworkTableView()
        self.network_table_view.network_selected.connect(self.on_network_selected)
        self.tab_widget.addTab(self.network_table_view, "Networks")
        
        # Create channel graph tab
        self.channel_graph = ChannelGraphWidget(self.channel_analyzer)
        self.channel_graph.refresh_requested.connect(self.start_scan)
        self.tab_widget.addTab(self.channel_graph, "Channel Graph")
        
        # Add tab widget to main layout
        self.main_layout.addWidget(self.tab_widget)
        
        # Create status bar
        self.status_bar = self.statusBar()
        
        # Create test results area
        self.test_results_frame = QFrame()
        self.test_results_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.test_results_frame.setFrameShadow(QFrame.Shadow.Sunken)
        self.test_results_layout = QVBoxLayout(self.test_results_frame)
        
        self.test_results_title = QLabel("Network Test Results")
        self.test_results_title.setStyleSheet("font-weight: bold;")
        self.test_results_label = QLabel("No tests run yet")
        
        self.test_results_layout.addWidget(self.test_results_title)
        self.test_results_layout.addWidget(self.test_results_label)
        
        # Create toolbar
        self.setup_toolbar()
        
        # Create menu bar
        self.setup_menu()
    
    def setup_toolbar(self):
        """Set up the application toolbar."""
        self.toolbar = self.addToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        
        # Scan action
        self.scan_action = QAction("Scan", self)
        self.scan_action.setShortcut(QKeySequence.StandardKey.Refresh)
        self.scan_action.triggered.connect(self.start_scan)
        self.toolbar.addAction(self.scan_action)
        
        self.toolbar.addSeparator()
        
        # Auto-refresh toggle
        self.auto_refresh_action = QAction("Auto Refresh", self)
        self.auto_refresh_action.setCheckable(True)
        self.auto_refresh_action.setChecked(True)
        self.auto_refresh_action.triggered.connect(self.toggle_auto_refresh)
        self.toolbar.addAction(self.auto_refresh_action)
    
    def setup_menu(self):
        """Set up the application menu bar."""
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        
        export_menu = file_menu.addMenu("&Export Networks")
        
        export_csv_action = QAction("Export as &CSV...", self)
        export_csv_action.triggered.connect(self.export_as_csv)
        export_menu.addAction(export_csv_action)
        
        export_json_action = QAction("Export as &JSON...", self)
        export_json_action.triggered.connect(self.export_as_json)
        export_menu.addAction(export_json_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Scan menu
        scan_menu = self.menuBar().addMenu("&Scan")
        
        scan_action = QAction("&Scan Now", self)
        scan_action.setShortcut(QKeySequence.StandardKey.Refresh)
        scan_action.triggered.connect(self.start_scan)
        scan_menu.addAction(scan_action)
        
        scan_menu.addSeparator()
        
        auto_refresh_action = QAction("&Auto Refresh", self)
        auto_refresh_action.setCheckable(True)
        auto_refresh_action.setChecked(True)
        auto_refresh_action.triggered.connect(self.toggle_auto_refresh)
        scan_menu.addAction(auto_refresh_action)
        
        # Test menu
        test_menu = self.menuBar().addMenu("&Tests")
        
        ping_action = QAction("&Ping Test", self)
        ping_action.triggered.connect(self.run_ping_test)
        test_menu.addAction(ping_action)
        
        dns_action = QAction("&DNS Resolution Test", self)
        dns_action.triggered.connect(self.run_dns_test)
        test_menu.addAction(dns_action)
        
        throughput_action = QAction("&Throughput Test", self)
        throughput_action.triggered.connect(self.run_throughput_test)
        test_menu.addAction(throughput_action)
        
        # Tools menu
        tools_menu = self.menuBar().addMenu("&Tools")
        
        analyze_channels_action = QAction("&Analyze Channel Congestion...", self)
        analyze_channels_action.triggered.connect(self.show_channel_analysis)
        tools_menu.addAction(analyze_channels_action)
        
        tools_menu.addSeparator()
        
        settings_action = QAction("&Settings...", self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        
        about_action = QAction("&About...", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_refresh_timer(self):
        """Set up the auto-refresh timer."""
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.start_scan)
        self.refresh_timer.start(SCAN_INTERVAL_MS)
    
    def toggle_auto_refresh(self, enabled: bool = None):
        """
        Toggle auto-refresh on/off.
        
        Args:
            enabled: If provided, set auto-refresh to this state. Otherwise toggle.
        """
        if enabled is None:
            enabled = not self.refresh_timer.isActive()
            
        if enabled:
            self.refresh_timer.start(SCAN_INTERVAL_MS)
            self.auto_refresh_action.setChecked(True)
            self.status_bar.showMessage("Auto-refresh enabled", 3000)
        else:
            self.refresh_timer.stop()
            self.auto_refresh_action.setChecked(False)
            self.status_bar.showMessage("Auto-refresh disabled", 3000)
            
        logger.info(f"Auto-refresh {'enabled' if enabled else 'disabled'}")
    

    def start_scan(self):
        """Start a new network scan."""
        try:
            # Check if scan is already running
            if hasattr(self, 'scan_worker') and self.scan_worker and self.scan_worker.is_running:
                logger.debug("Scan already in progress, ignoring request")
                return
            
            logger.info("Starting network scan")
            self.status_bar.showMessage("Scanning networks...")
            
            # Create and configure worker
            self.scan_worker = ScanWorker(self.scanner)
            self.scan_worker.scan_complete.connect(self.on_scan_complete)
            self.scan_worker.finished.connect(self._cleanup_worker)
            
            # Start the worker thread
            self.scan_worker.start()
            
        except Exception as e:
            logger.error(f"Error starting scan: {e}", exc_info=True)
            self.status_bar.showMessage("Error starting scan", 3000)
    
    def _cleanup_worker(self):
        """Clean up the scan worker after completion."""
        if hasattr(self, 'scan_worker') and self.scan_worker:
            self.scan_worker.deleteLater()
            self.scan_worker = None
    
    def on_scan_complete(self, result: ScanResult):
        """
        Handle scan completion.
        
        Args:
            result: Scan result object containing networks
        """
        # Ensure UI updates happen in the main thread
        if self.thread() != QThread.currentThread():
            # If called from another thread, re-emit to main thread
            QCoreApplication.instance().postEvent(self, 
                type=QEvent.Type.User,
                result=result
            )
            return

        if result.success:
            # Update network table
            self.network_table_view.set_networks(result.networks)
            
            # Update dashboard
            self.dashboard_view.set_networks(result.networks)
            
            # Update channel graph
            self.channel_graph.update_graphs(result.networks)
            
            # Log info
            logger.info(f"Scan completed: {len(result.networks)} networks found")
            self.status_bar.showMessage(f"Found {len(result.networks)} networks", 3000)
        else:
            logger.error(f"Scan failed: {result.error}")
            self.status_bar.showMessage(f"Scan failed: {result.error}", 5000)
    
    def event(self, event: QEvent) -> bool:
        """Handle custom events."""
        if event.type() == QEvent.Type.User:
            # Process scan results in main thread
            self.on_scan_complete(event.result)
            return True
        return super().event(event)

    def on_network_selected(self, network: WiFiNetwork):
        """
        Handle network selection.
        
        Args:
            network: Selected WiFiNetwork object
        """
        logger.debug(f"Network selected: {network.ssid}")
        # Other views should update to show this network if needed
    
    def export_as_csv(self):
        """Export networks to CSV file."""
        # Implementation for CSV export
        pass
        
    def export_as_json(self):
        """Export networks to JSON file."""
        # Implementation for JSON export
        pass
    
    def show_channel_analysis(self):
        """Show channel analysis dialog."""
        # Implementation for channel analysis dialog
        pass
        
    def show_settings(self):
        """Show settings dialog."""
        # Implementation for settings dialog
        pass
        
    def show_about(self):
        """Show about dialog."""
        # Implementation for about dialog
        pass
    
    def load_settings(self):
        """Load application settings."""
        # Implementation for loading settings
        pass
    
    def save_settings(self):
        """Save application settings."""
        # Implementation for saving settings
        pass
    
    def closeEvent(self, event: QCloseEvent):
        """Handle window close event."""
        self.save_settings()
        event.accept()
