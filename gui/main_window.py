"""
Main Window Module

This module provides the main application window for the WiFi Analyzer application,
integrating all UI components, scanner functionality, and visualization.
"""

import os
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import webbrowser
import subprocess
from gui.network_table import NetworkTableView
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStatusBar, QProgressBar, QMenuBar, QMenu, QMessageBox, QDialog, QFileDialog,
    QSplitter, QToolBar, QComboBox, QCheckBox, QApplication, QStyleOptionViewItem,
    QFrame, QGridLayout, QGroupBox, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QTimer, QSettings, QSize, QDir, pyqtSignal, QThread, QObject
from PyQt6.QtGui import QIcon, QKeySequence, QPixmap, QFont, QAction, QColor, QPalette
from gui.channel_graph import ChannelGraphWidget
from scanner.models import WiFiNetwork, ScanResult
from scanner.windows_scanner import WindowsWiFiScanner
from utils.channel_analyzer import ChannelAnalyzer
from utils.network_tester import NetworkTester
from config.settings import (
    APP_NAME, APP_VERSION, ORGANIZATION_NAME, SCAN_INTERVAL_MS,
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT
)


logger = logging.getLogger(__name__)

class ScanWorker(QThread):
    """
    Worker thread for performing WiFi scanning in the background.
    
    This class prevents the GUI from freezing during scan operations.
    """
    scan_complete = pyqtSignal(object, bool, str)
    scan_progress = pyqtSignal(int)
    
    def __init__(self, scanner: WindowsWiFiScanner):
        super().__init__()
        self.scanner = scanner
        self.is_running = True
    
    def run(self):
        """Execute the scan operation in a separate thread."""
        try:
            # Emit initial progress
            self.scan_progress.emit(10)
            logger.debug("Starting network scan in worker thread")
            
            # Perform the scan
            scan_result = self.scanner.scan_networks_sync()
            self.scan_progress.emit(90)
            
            logger.debug(f"Scan completed with success={scan_result.success}, found {len(scan_result.networks)} networks")
            if not scan_result.success:
                logger.error(f"Scan error: {scan_result.error_message}")
            
            # Emit results - pass the ScanResult object directly
            self.scan_complete.emit(scan_result, scan_result.success, scan_result.error_message)
            self.scan_progress.emit(100)
            
        except Exception as e:
            logger.error(f"Scan failed with exception: {str(e)}", exc_info=True)
            self.scan_complete.emit([], False, str(e))
            self.scan_progress.emit(100)
    
    def stop(self):
        """Stop the worker thread."""
        self.is_running = False
        self.wait()

class NetworkDetailsDialog(QDialog):
    """Dialog for displaying detailed information about a network."""
    
    def __init__(self, network, parent=None):
        super().__init__(parent)
        self.network = network
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle(f"Network Details: {self.network.ssid}")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Network details
        details_frame = QFrame()
        details_frame.setFrameShape(QFrame.Shape.StyledPanel)
        details_frame.setFrameShadow(QFrame.Shadow.Sunken)
        details_layout = QGridLayout(details_frame)
        
        # Create details grid
        row = 0
        for label, value in [
            ("SSID", self.network.ssid if self.network.ssid else "<Hidden Network>"),
            ("BSSID", self.network.bssid),
            ("Channel", str(self.network.channel)),
            ("Band", self.network.band),
            ("Signal", f"{self.network.signal_dbm} dBm"),
            ("Security", self.network.security_type),
            # Fix datetime conversion for timestamps
            ("First Seen", datetime.fromtimestamp(self.network.first_seen).strftime("%Y-%m-%d %H:%M:%S") if self.network.first_seen else "Unknown"),
            ("Last Seen", datetime.fromtimestamp(self.network.last_seen).strftime("%Y-%m-%d %H:%M:%S") if self.network.last_seen else "Unknown"),
        ]:
            details_layout.addWidget(QLabel(f"{label}:"), row, 0)
            details_layout.addWidget(QLabel(value), row, 1)
            row += 1
        
        layout.addWidget(details_frame)
        
        # BSSIDs section if the network has multiple BSSIDs
        if len(self.network.bssids) > 1:
            bssids_group = QGroupBox("All BSSIDs")
            bssids_layout = QVBoxLayout(bssids_group)
            
            for bssid_obj in self.network.bssids:
                bssid_info = QLabel(f"{bssid_obj.bssid}: Ch {bssid_obj.channel} ({bssid_obj.band}), {bssid_obj.signal_dbm} dBm")
                bssids_layout.addWidget(bssid_info)
            
            layout.addWidget(bssids_group)
        
        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

class MainWindow(QMainWindow):
    """
    Main application window for the WiFi Analyzer.
    
    This class integrates all the UI components and handles the application logic.
    """
    def __init__(self, scanner: WindowsWiFiScanner):
        super().__init__()
        self.scanner = scanner
        self.networks = []
        self.scan_worker = None
        self.network_tester = NetworkTester()
        self.channel_analyzer = ChannelAnalyzer()
        self.last_scan_time = None
        self.auto_refresh_timer = None
        
        # Initialize UI
        self.setup_ui()
        self.load_settings()
        
        # Initial scan
        self.refresh_networks()
        
        # Set up auto-refresh if enabled
        if SCAN_INTERVAL_MS > 0:
            self.auto_refresh_timer = QTimer(self)
            self.auto_refresh_timer.timeout.connect(self.refresh_networks)
            self.auto_refresh_timer.start(SCAN_INTERVAL_MS)
            logger.info(f"Auto-refresh enabled: scanning every {SCAN_INTERVAL_MS/1000} seconds")
    
    def setup_ui(self):
        """Set up the user interface components."""
        # Configure main window
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create scan progress bar and add it to the layout
        self.scan_progress_bar = QProgressBar(self)
        self.scan_progress_bar.setMaximum(100)
        self.scan_progress_bar.setValue(0)
        self.scan_progress_bar.setVisible(False)
        main_layout.addWidget(self.scan_progress_bar)
        
        # Create splitter for resizable sections
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Create tab widget for main views
        self.tabs = QTabWidget()
        
        # Create and add dashboard view
        from gui.dashboard import DashboardView
        self.dashboard = DashboardView()
        self.dashboard.network_selected.connect(self.show_network_details)
        self.dashboard.refresh_requested.connect(self.refresh_networks)
        self.tabs.addTab(self.dashboard, "Dashboard")
        
        # Create network table view
        self.network_table = NetworkTableView()
        self.network_table.network_selected.connect(self.show_network_details)
        self.tabs.addTab(self.network_table, "Networks")
        
        # Create channel graph view (passing the analyzer)
        self.channel_graph = ChannelGraphWidget(analyzer=self.channel_analyzer, parent=self)
        self.channel_graph.refresh_requested.connect(self.refresh_networks)
        self.tabs.addTab(self.channel_graph, "Channel Usage")
            
        # Add network test tab
        self.network_test_widget = self.create_network_test_widget()
        self.tabs.addTab(self.network_test_widget, "Network Tests")
        
        # Add tabs to splitter
        self.main_splitter.addWidget(self.tabs)
            
        # Add splitter to main layout
        main_layout.addWidget(self.main_splitter)
        
        # Create status bar
        self.status_bar = self.statusBar()

        # Add permanent widgets to status bar
        self.status_networks_label = QLabel("No networks found")
        self.status_bar.addPermanentWidget(self.status_networks_label)

        self.status_last_scan_label = QLabel("Last scan: Never")
        self.status_bar.addPermanentWidget(self.status_last_scan_label)

        # Add a progress bar for scanning
        self.scan_progress_bar = QProgressBar()
        self.scan_progress_bar.setRange(0, 100)
        self.scan_progress_bar.setValue(100)
        self.scan_progress_bar.setVisible(False)
        self.scan_progress_bar.setMaximumWidth(200)
        self.status_bar.addWidget(self.scan_progress_bar)
    
    def create_menus(self):
        """Create the application menu bar and menus."""
        # Create menu bar
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        
        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut(QKeySequence.StandardKey.Refresh)
        refresh_action.triggered.connect(self.refresh_networks)
        file_menu.addAction(refresh_action)
        
        export_action = QAction("&Export Networks...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_networks)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menu_bar.addMenu("&View")
        
        toggle_toolbar_action = QAction("&Toolbar", self)
        toggle_toolbar_action.setCheckable(True)
        toggle_toolbar_action.setChecked(True)
        toggle_toolbar_action.toggled.connect(self.toggle_toolbar)
        view_menu.addAction(toggle_toolbar_action)
        
        toggle_statusbar_action = QAction("&Status Bar", self)
        toggle_statusbar_action.setCheckable(True)
        toggle_statusbar_action.setChecked(True)
        toggle_statusbar_action.toggled.connect(self.toggle_statusbar)
        view_menu.addAction(toggle_statusbar_action)
        
        view_menu.addSeparator()
        
        theme_menu = view_menu.addMenu("&Theme")
        
        light_theme_action = QAction("&Light", self)
        light_theme_action.triggered.connect(lambda: self.set_theme("light"))
        theme_menu.addAction(light_theme_action)
        
        dark_theme_action = QAction("&Dark", self)
        dark_theme_action.triggered.connect(lambda: self.set_theme("dark"))
        theme_menu.addAction(dark_theme_action)
        
        high_contrast_action = QAction("&High Contrast", self)
        high_contrast_action.triggered.connect(lambda: self.set_theme("high_contrast"))
        theme_menu.addAction(high_contrast_action)
        
        # Tools menu
        tools_menu = menu_bar.addMenu("&Tools")
        
        run_tests_action = QAction("Run &Network Tests", self)
        run_tests_action.triggered.connect(self.run_network_tests)
        tools_menu.addAction(run_tests_action)
        
        analyze_channels_action = QAction("Analyze Channel &Congestion", self)
        analyze_channels_action.triggered.connect(self.analyze_channels)
        tools_menu.addAction(analyze_channels_action)
        
        diagnose_wifi_action = QAction("Diagnose WiFi Issues", self)
        diagnose_wifi_action.triggered.connect(self.diagnose_wifi_issues)
        tools_menu.addAction(diagnose_wifi_action)
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """Create the application toolbar."""
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        
        # Add refresh action
        refresh_action = QAction("Refresh", self)
        refresh_action.setStatusTip("Scan for networks")
        refresh_action.triggered.connect(self.refresh_networks)
        self.toolbar.addAction(refresh_action)
        
        # Add diagnostic button
        diagnose_action = QAction("Diagnose", self)
        diagnose_action.setStatusTip("Run WiFi diagnostics")
        diagnose_action.triggered.connect(self.diagnose_wifi_issues)
        self.toolbar.addAction(diagnose_action)
        
        self.toolbar.addSeparator()
        
        # Add band filter
        self.toolbar.addWidget(QLabel("Band:"))
        band_combo = QComboBox()
        band_combo.addItem("All Bands")
        band_combo.addItem("2.4 GHz")
        band_combo.addItem("5 GHz")
        band_combo.currentTextChanged.connect(self.on_band_filter_changed)
        self.toolbar.addWidget(band_combo)
        
        self.toolbar.addSeparator()
        
        # Add auto-refresh toggle
        auto_refresh_checkbox = QCheckBox("Auto-refresh")
        auto_refresh_checkbox.setChecked(SCAN_INTERVAL_MS > 0)
        auto_refresh_checkbox.toggled.connect(self.toggle_auto_refresh)
        self.toolbar.addWidget(auto_refresh_checkbox)
    
    def create_network_test_widget(self):
        """Create the network test tab widget."""
        test_widget = QWidget()
        test_layout = QVBoxLayout(test_widget)
        
        # Simple layout with buttons to run various tests
        button_layout = QHBoxLayout()
        
        ping_button = QPushButton("Run Ping Test")
        ping_button.clicked.connect(self.run_ping_test)
        button_layout.addWidget(ping_button)
        
        dns_button = QPushButton("Test DNS Resolution")
        dns_button.clicked.connect(self.run_dns_test)
        button_layout.addWidget(dns_button)
        
        throughput_button = QPushButton("Estimate Throughput")
        throughput_button.clicked.connect(self.run_throughput_test)
        button_layout.addWidget(throughput_button)
        
        comprehensive_button = QPushButton("Run All Tests")
        comprehensive_button.clicked.connect(self.run_network_tests)
        button_layout.addWidget(comprehensive_button)
        
        test_layout.addLayout(button_layout)
        
        # Results area
        self.test_results_label = QLabel("No test results available. Click one of the buttons above to run a test.")
        self.test_results_label.setWordWrap(True)
        self.test_results_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        test_layout.addWidget(self.test_results_label)
        
        return test_widget
    
    def refresh_networks(self):
        """Refresh the network list by performing a new scan."""
        # Only start a new scan if we're not already scanning
        if self.scan_worker and self.scan_worker.isRunning():
            logger.debug("Scan already in progress, ignoring refresh request")
            return
        
        # Show progress bar
        self.scan_progress_bar.setValue(0)
        self.scan_progress_bar.setVisible(True)
        self.status_bar.showMessage("Scanning for networks...")
        
        # Create and start worker thread
        self.scan_worker = ScanWorker(self.scanner)
        self.scan_worker.scan_complete.connect(self.on_scan_complete)
        self.scan_worker.scan_progress.connect(self.on_scan_progress)
        self.scan_worker.start()
    
    def on_scan_progress(self, progress):
        """Update scan progress in the UI."""
        self.scan_progress_bar.setValue(progress)
        if progress >= 100:
            self.scan_progress_bar.setVisible(False)
    
    def on_scan_complete(self, scan_result, success, error):
        """Handle completion of network scanning."""
        # Update UI
        self.scan_progress_bar.setVisible(False)
        
        # Handle different types of scan_result
        if isinstance(scan_result, ScanResult):
            networks = scan_result.networks
        else:
            # For backward compatibility
            networks = scan_result
        
        if success:
            # Store networks
            self.networks = networks
            
            # Update timestamp
            self.last_scan_time = datetime.now()
            self.status_last_scan_label.setText(f"Last scan: {self.last_scan_time.strftime('%H:%M:%S')}")
            
            # Update status bar
            self.status_networks_label.setText(f"{len(networks)} networks found")
            self.status_bar.showMessage("Scan complete", 3000)
            
            # Update all UI components
            self.network_table.set_networks(networks)
            
            # Make sure dashboard is updated
            if hasattr(self, 'dashboard'):
                self.dashboard.set_networks(networks)
                logger.debug(f"Dashboard updated with {len(networks)} networks")
            
            # Update channel graphs
            try:
                self.channel_graph.update_graphs(networks)
            except Exception as e:
                logger.error(f"Error updating channel graphs: {str(e)}", exc_info=True)
            
            logger.info(f"Scan completed successfully: {len(networks)} networks found")
        else:
            # Handle error
            self.status_bar.showMessage(f"Scan failed: {error}", 5000)
            logger.error(f"Scan failed: {error}")
            
            # Show a more user-friendly message
            QMessageBox.warning(
                self, 
                "Scan Failed",
                f"Failed to scan for networks: {error}\n\n"
                "This may be caused by:\n"
                "1. Your WiFi adapter is disabled\n"
                "2. You need administrator privileges\n"
                "3. The wireless service is not running\n\n"
                "You can use Tools > Diagnose WiFi Issues for more details."
            )
    
    def show_network_details(self, network):
        """
        Display detailed information about a selected network in a dialog.
        
        Args:
            network: The WiFiNetwork object to display details for
        """
        try:
            dialog = NetworkDetailsDialog(network, self)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error showing network details: {str(e)}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Could not show network details: {str(e)}")
    
    def on_band_filter_changed(self, band_text):
        """Handle changes in the band filter combo box."""
        # Pass the filter to the network table
        if band_text == "All Bands":
            self.network_table.proxy_model.set_band_filter(None)
        else:
            self.network_table.proxy_model.set_band_filter(band_text)
        
        # Also update the channel graph view to focus on the selected band
        if band_text == "All Bands":
            self.channel_graph.band_both_radio.setChecked(True)
        elif band_text == "2.4 GHz":
            self.channel_graph.band_24ghz_radio.setChecked(True)
        elif band_text == "5 GHz":
            self.channel_graph.band_5ghz_radio.setChecked(True)
        
        # Update the channel graph
        self.channel_graph.update_band_view()
    
    def toggle_auto_refresh(self, enabled):
        """Toggle automatic refresh of network scans."""
        if enabled and (self.auto_refresh_timer is None or not self.auto_refresh_timer.isActive()):
            # Start auto-refresh
            self.auto_refresh_timer = QTimer(self)
            self.auto_refresh_timer.timeout.connect(self.refresh_networks)
            self.auto_refresh_timer.start(SCAN_INTERVAL_MS)
            logger.info(f"Auto-refresh enabled: scanning every {SCAN_INTERVAL_MS/1000} seconds")
        elif not enabled and self.auto_refresh_timer and self.auto_refresh_timer.isActive():
            # Stop auto-refresh
            self.auto_refresh_timer.stop()
            logger.info("Auto-refresh disabled")
    
    def toggle_toolbar(self, visible):
        """Toggle visibility of the toolbar."""
        self.toolbar.setVisible(visible)
    
    def toggle_statusbar(self, visible):
        """Toggle visibility of the status bar."""
        self.status_bar.setVisible(visible)
    
    def set_theme(self, theme):
        """Set the application theme."""
        from gui.theme_manager import apply_theme
        
        # Apply the theme using the theme manager
        apply_theme(theme)
        
        # Save the theme preference
        settings = QSettings(ORGANIZATION_NAME, APP_NAME)
        settings.setValue("theme", theme)
        
        logger.info(f"Set {theme} theme")
    
    def run_ping_test(self):
        """Run a ping test and display the results."""
        self.status_bar.showMessage("Running ping test...")
        
        # Run the test in the background
        def ping_callback(result):
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
        
        # Execute test in a separate thread
        test_thread = QThread()
        worker = TestWorker(self.network_tester.ping_test)
        worker.moveToThread(test_thread)
        worker.result_ready.connect(ping_callback)
        test_thread.started.connect(worker.run)
        test_thread.start()
    
    def run_dns_test(self):
        """Run a DNS resolution test and display the results."""
        self.status_bar.showMessage("Testing DNS resolution...")
        
        # Run the test in the background
        def dns_callback(result):
            if result['avg_time'] is not None:
                report = (
                    f"<b>DNS Resolution Test Results:</b><br>"
                    f"Average Resolution Time: {result['avg_time']:.2f} ms<br>"
                    f"Minimum Resolution Time: {result['min_time']:.2f} ms<br>"
                    f"Maximum Resolution Time: {result['max_time']:.2f} ms<br>"
                    f"Success Rate: {result['success_rate']}%<br><br>"
                    f"<b>Details:</b><br>"
                )
                
                for host_result in result['results']:
                    status = "Success" if host_result['success'] else "Failed"
                    time_ms = f"{host_result['time_ms']:.2f} ms" if host_result['time_ms'] else "N/A"
                    report += f"{host_result['hostname']}: {status} ({time_ms})<br>"
            else:
                report = (
                    f"<b>DNS Resolution Test Failed:</b><br>"
                    f"No successful resolutions."
                )
            
            self.test_results_label.setText(report)
            self.status_bar.showMessage("DNS test complete", 3000)
        
        # Execute test in a separate thread
        test_thread = QThread()
        worker = TestWorker(self.network_tester.dns_resolution_test)
        worker.moveToThread(test_thread)
        worker.result_ready.connect(dns_callback)
        test_thread.started.connect(worker.run)
        test_thread.start()
    
    def run_throughput_test(self):
        """Run a throughput estimation test and display the results."""
        self.status_bar.showMessage("Estimating network throughput...")
        
        # Run the test in the background
        def throughput_callback(result):
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
        
        # Execute test in a separate thread
        test_thread = QThread()
        worker = TestWorker(self.network_tester.throughput_test)
        worker.moveToThread(test_thread)
        worker.result_ready.connect(throughput_callback)
        test_thread.started.connect(worker.run)
        test_thread.start()
    
    def run_network_tests(self):
        """Run a comprehensive set of network tests."""
        self.status_bar.showMessage("Running comprehensive network tests...")
        
        # Run the tests in the background
        def tests_callback(result):
            report = "<b>Comprehensive Network Test Results:</b><br><br>"
            
            # Ping results
            ping = result['ping']
            if ping['success']:
                report += (
                    f"<b>Ping Test:</b><br>"
                    f"Average Latency: {ping['avg_latency']} ms<br>"
                    f"Packet Loss: {ping['packet_loss']}%<br>"
                    f"Jitter: {ping['jitter']} ms<br><br>"
                )
            else:
                report += f"<b>Ping Test:</b> Failed - {ping['error']}<br><br>"
            
            # DNS results
            dns = result['dns']
            if dns['avg_time'] is not None:
                report += (
                    f"<b>DNS Resolution:</b><br>"
                    f"Average Time: {dns['avg_time']:.2f} ms<br>"
                    f"Success Rate: {dns['success_rate']}%<br><br>"
                )
            else:
                report += "<b>DNS Resolution:</b> Failed - No successful resolutions<br><br>"
            
            # Gateway results
            gateway = result['gateway']
            if gateway['reachable']:
                report += (
                    f"<b>Gateway Connectivity:</b><br>"
                    f"Gateway IP: {gateway['gateway_ip']}<br>"
                    f"Latency: {gateway['latency']} ms<br><br>"
                )
            else:
                report += f"<b>Gateway Connectivity:</b> Failed - {gateway['error'] or 'Unreachable'}<br><br>"
            
            # Throughput results
            throughput = result['throughput']
            if throughput['success']:
                report += (
                    f"<b>Throughput Estimation:</b><br>"
                    f"Download Speed: {throughput['speed_mbps']} Mbps<br>"
                )
            else:
                report += f"<b>Throughput Estimation:</b> Failed - {throughput['error']}<br>"
            
            self.test_results_label.setText(report)
            self.status_bar.showMessage("Network tests complete", 3000)
        
        # Execute tests in a separate thread
        test_thread = QThread()
        worker = TestWorker(self.network_tester.run_comprehensive_test)
        worker.moveToThread(test_thread)
        worker.result_ready.connect(tests_callback)
        test_thread.started.connect(worker.run)
        test_thread.start()
    
    def analyze_channels(self):
        """Analyze channel congestion and recommendations."""
        if not self.networks:
            QMessageBox.information(self, "No Networks", 
                                  "No networks available for analysis. Please scan for networks first.")
            return
        
        # Create and show the channel analysis dialog
        dialog = ChannelAnalysisDialog(self.channel_analyzer, self.networks, self)
        dialog.exec()
    
    def export_networks(self):
        """Export the network list to a file."""
        if not self.networks:
            QMessageBox.information(self, "No Networks", 
                                  "No networks available to export. Please scan for networks first.")
            return
        
        # Show save dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Networks", "", "CSV Files (*.csv);;JSON Files (*.json);;Text Files (*.txt)"
        )
        
        if not file_path:
            return
        
        try:
            # Export based on file extension
            if file_path.endswith(".csv"):
                self.export_to_csv(file_path)
            elif file_path.endswith(".json"):
                self.export_to_json(file_path)
            else:
                self.export_to_text(file_path)
                
            self.status_bar.showMessage(f"Networks exported to {file_path}", 5000)
            logger.info(f"Networks exported to {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", 
                               f"Failed to export networks: {str(e)}")
            logger.error(f"Export failed: {str(e)}")
    
    def export_to_csv(self, file_path):
        """Export networks to CSV format."""
        import csv
        
        with open(file_path, 'w', newline='') as csvfile:
            fieldnames = ['SSID', 'BSSID', 'Signal (dBm)', 'Channel', 'Band', 
                         'Security', 'First Seen', 'Last Seen']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for network in self.networks:
                writer.writerow({
                    'SSID': network.ssid if network.ssid else '<Hidden>',
                    'BSSID': network.bssid,
                    'Signal (dBm)': network.signal_dbm,
                    'Channel': network.channel,
                    'Band': network.band,
                    'Security': network.security_type,
                    'First Seen': network.first_seen.strftime('%Y-%m-%d %H:%M:%S') if network.first_seen else 'Unknown',
                    'Last Seen': network.last_seen.strftime('%Y-%m-%d %H:%M:%S') if network.last_seen else 'Unknown'
                })
    
    def export_to_json(self, file_path):
        """Export networks to JSON format."""
        import json
        
        networks_data = []
        for network in self.networks:
            networks_data.append({
                'ssid': network.ssid if network.ssid else '<Hidden>',
                'bssid': network.bssid,
                'signal_dbm': network.signal_dbm,
                'channel': network.channel,
                'band': network.band,
                'security': network.security_type,
                'first_seen': network.first_seen.strftime('%Y-%m-%d %H:%M:%S') if network.first_seen else None,
                'last_seen': network.last_seen.strftime('%Y-%m-%d %H:%M:%S') if network.last_seen else None
            })
        
        with open(file_path, 'w') as jsonfile:
            json.dump({'networks': networks_data, 'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, 
                     jsonfile, indent=2)
    
    def export_to_text(self, file_path):
        """Export networks to plain text format."""
        with open(file_path, 'w') as textfile:
            textfile.write(f"WiFi Networks - Scanned on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            textfile.write("=" * 80 + "\n\n")
            
            for network in self.networks:
                textfile.write(f"SSID: {network.ssid if network.ssid else '<Hidden>'}\n")
                textfile.write(f"BSSID: {network.bssid}\n")
                textfile.write(f"Signal: {network.signal_dbm} dBm\n")
                textfile.write(f"Channel: {network.channel} ({network.band})\n")
                textfile.write(f"Security: {network.security_type}\n")
                textfile.write(f"First Seen: {network.first_seen.strftime('%Y-%m-%d %H:%M:%S') if network.first_seen else 'Unknown'}\n")
                textfile.write(f"Last Seen: {network.last_seen.strftime('%Y-%m-%d %H:%M:%S') if network.last_seen else 'Unknown'}\n")
                textfile.write("\n" + "-" * 40 + "\n\n")
    
    def show_about_dialog(self):
        """Show the About dialog with application information."""
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
            "<p>A WiFi analysis and channel visualization tool.</p>"
            "<p>This application allows you to scan for WiFi networks, "
            "visualize channel usage, and analyze network performance.</p>"
            "<p>© 2025 {ORGANIZATION_NAME}. All rights reserved.</p>"
        )
    
    def load_settings(self):
        """Load application settings."""
        settings = QSettings(ORGANIZATION_NAME, APP_NAME)
        
        # Restore window geometry if available
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # Restore window state if available
        state = settings.value("windowState")
        if state:
            self.restoreState(state)
        
        # Apply theme
        theme = settings.value("theme", "light")
        self.set_theme(theme)
    
    def save_settings(self):
        """Save application settings."""
        settings = QSettings(ORGANIZATION_NAME, APP_NAME)
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
    
    def closeEvent(self, event):
        """Handle application close event."""
        # Stop any ongoing scan
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.stop()
        
        # Stop monitoring if active
        if hasattr(self.network_tester, 'is_monitoring') and self.network_tester.is_monitoring():
            self.network_tester.stop_monitoring()
        
        # Save settings
        self.save_settings()
        
        # Accept the close event
        event.accept()
    
    def diagnose_wifi_issues(self):
        """Run diagnostics to troubleshoot WiFi issues."""
        self.status_bar.showMessage("Running WiFi diagnostics...")
        
        try:
            # Check if WiFi service is running
            wifi_service_check = subprocess.run(
                ['sc', 'query', 'wlansvc'], 
                capture_output=True,
                text=True
            )
            
            # Check WiFi adapter status
            adapter_check = subprocess.run(
                ['netsh', 'wlan', 'show', 'interfaces'],
                capture_output=True, 
                text=True
            )
            
            # Prepare report
            report = "<h3>WiFi Diagnostic Report</h3>"
            
            # Check WiFi service
            if "RUNNING" in wifi_service_check.stdout:
                report += "<p>✅ WiFi service (wlansvc) is running.</p>"
            else:
                report += "<p>❌ WiFi service (wlansvc) is NOT running. This will prevent scanning.</p>"
            
            # Check if there are any interfaces
            if "There is no wireless interface" in adapter_check.stdout:
                report += "<p>❌ No wireless interfaces detected. WiFi may be disabled or hardware issues.</p>"
            elif "Name" in adapter_check.stdout:
                report += "<p>✅ Wireless interface detected.</p>"
                
                # Check if interface is enabled
                if "State : connected" in adapter_check.stdout:
                    report += "<p>✅ WiFi adapter is connected.</p>"
                elif "State : disconnected" in adapter_check.stdout:
                    report += "<p>⚠️ WiFi adapter is disconnected but enabled.</p>"
                else:
                    report += "<p>⚠️ WiFi adapter status is unknown.</p>"
                    
            # Add netsh output for reference
            report += "<h4>WiFi Interfaces Info:</h4>"
            report += f"<pre>{adapter_check.stdout}</pre>"
            
            # Create a dialog to show the report
            dialog = QDialog(self)
            dialog.setWindowTitle("WiFi Diagnostics")
            dialog.setMinimumSize(600, 400)
            
            layout = QVBoxLayout(dialog)
            
            report_label = QLabel(report)
            report_label.setWordWrap(True)
            report_label.setTextFormat(Qt.TextFormat.RichText)
            
            layout.addWidget(report_label)
            
            close_button = QPushButton("Close")
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Diagnostics Failed", f"Failed to run diagnostics: {str(e)}")
            logger.error(f"Diagnostics failed: {str(e)}")


class TestWorker(QObject):
    """
    Worker class for running network tests in a separate thread.
    """
    result_ready = pyqtSignal(object)
    
    def __init__(self, test_function, *args, **kwargs):
        super().__init__()
        self.test_function = test_function
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        """Run the test function and emit results."""
        try:
            result = self.test_function(*self.args, **self.kwargs)
            self.result_ready.emit(result)
        except Exception as e:
            logger.error(f"Error in test worker: {str(e)}")
            self.result_ready.emit({"success": False, "error": str(e)})


class ChannelAnalysisDialog(QDialog):
    """
    Dialog for displaying detailed channel congestion analysis and recommendations.
    """
    def __init__(self, analyzer, networks, parent=None):
        super().__init__(parent)
        self.analyzer = analyzer
        self.networks = networks
        self.setup_ui()
        self.analyze()
    
    def setup_ui(self):
        """Set up the user interface components."""
        self.setWindowTitle("Channel Analysis")
        self.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Create tabs for 2.4 GHz and 5 GHz analysis
        self.tabs = QTabWidget()
        self.tab_24ghz = QWidget()
        self.tab_5ghz = QWidget()
        
        self.tabs.addTab(self.tab_24ghz, "2.4 GHz Band")
        self.tabs.addTab(self.tab_5ghz, "5 GHz Band")
        
        # Set up 2.4 GHz tab
        tab_24ghz_layout = QVBoxLayout(self.tab_24ghz)
        self.results_24ghz = QLabel("Analyzing 2.4 GHz channels...")
        self.results_24ghz.setWordWrap(True)
        tab_24ghz_layout.addWidget(self.results_24ghz)
        
        # Set up 5 GHz tab
        tab_5ghz_layout = QVBoxLayout(self.tab_5ghz)
        self.results_5ghz = QLabel("Analyzing 5 GHz channels...")
        self.results_5ghz.setWordWrap(True)
        tab_5ghz_layout.addWidget(self.results_5ghz)
        
        layout.addWidget(self.tabs)
        
        # Add close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
    
    def analyze(self):
        """Perform channel analysis and display results."""
        # Split networks by band
        networks_24ghz = [n for n in self.networks if n.channel <= 14]
        networks_5ghz = [n for n in self.networks if n.channel > 14]
        
        # Analyze 2.4 GHz band
        if networks_24ghz:
            congestion_24ghz = self.analyzer.calculate_channel_congestion_24ghz(networks_24ghz)
            recommendation_24ghz = self.analyzer.recommend_channel_24ghz(networks_24ghz)
            
            # Format results
            html = "<h3>2.4 GHz Band Analysis</h3>"
            html += f"<p><b>{len(networks_24ghz)} networks found on 2.4 GHz band</b></p>"
            
            html += "<h4>Channel Congestion:</h4><ul>"
            for channel, score in sorted(congestion_24ghz.items()):
                html += f"<li>Channel {channel}: "
                
                if score < 30:
                    html += f"<span style='color: green;'>Low</span> "
                elif score < 70:
                    html += f"<span style='color: orange;'>Medium</span> "
                else:
                    html += f"<span style='color: red;'>High</span> "
                
                html += f"({score:.1f}%)"
                
                # List networks on this channel
                networks_on_channel = [n for n in networks_24ghz if n.channel == channel]
                if networks_on_channel:
                    html += "<ul>"
                    for n in networks_on_channel:
                        html += f"<li>{n.ssid if n.ssid else '<Hidden>'} ({n.signal_dbm} dBm)</li>"
                    html += "</ul>"
                
                html += "</li>"
            html += "</ul>"
            
            # Add recommendation
            html += f"<h4>Recommendation:</h4><p>The least congested channel is <b>Channel {recommendation_24ghz}</b>."
            
            if recommendation_24ghz in [1, 6, 11]:
                html += " This is one of the standard non-overlapping channels (1, 6, 11)."
            else:
                html += " <i>Note: This is not one of the standard non-overlapping channels (1, 6, 11).</i>"
            
            html += "</p>"
            
            # Add explanation of overlapping channels
            html += (
                "<h4>About Channel Overlap:</h4>"
                "<p>In the 2.4 GHz band, each channel is 20 MHz wide but separated by only 5 MHz, "
                "causing significant overlap between adjacent channels. Channels 1, 6, and 11 "
                "are the only channels that don't overlap with each other.</p>"
            )
            
            self.results_24ghz.setText(html)
        else:
            self.results_24ghz.setText("<p>No networks found on 2.4 GHz band.</p>")
        
        # Analyze 5 GHz band
        if networks_5ghz:
            congestion_5ghz = self.analyzer.calculate_channel_congestion_5ghz(networks_5ghz)
            recommendation_5ghz = self.analyzer.recommend_channel_5ghz(networks_5ghz)
            
            # Format results
            html = "<h3>5 GHz Band Analysis</h3>"
            html += f"<p><b>{len(networks_5ghz)} networks found on 5 GHz band</b></p>"
            
            html += "<h4>Channel Congestion:</h4><ul>"
            for channel, score in sorted(congestion_5ghz.items()):
                html += f"<li>Channel {channel}: "
                
                if score < 30:
                    html += f"<span style='color: green;'>Low</span> "
                elif score < 70:
                    html += f"<span style='color: orange;'>Medium</span> "
                else:
                    html += f"<span style='color: red;'>High</span> "
                
                html += f"({score:.1f}%)"
                
                # List networks on this channel
                networks_on_channel = [n for n in networks_5ghz if n.channel == channel]
                if networks_on_channel:
                    html += "<ul>"
                    for n in networks_on_channel:
                        html += f"<li>{n.ssid if n.ssid else '<Hidden>'} ({n.signal_dbm} dBm)</li>"
                    html += "</ul>"
                
                html += "</li>"
            html += "</ul>"
            
            # Add recommendation
            if recommendation_5ghz:
                html += f"<h4>Recommendation:</h4><p>The least congested channel is <b>Channel {recommendation_5ghz}</b>.</p>"
            else:
                html += "<h4>Recommendation:</h4><p>No clear recommendation available.</p>"
            
            # Add explanation of 5 GHz channels
            html += (
                "<h4>About 5 GHz Channels:</h4>"
                "<p>The 5 GHz band has more available channels and less interference than 2.4 GHz. "
                "Channels in this band typically don't overlap with the standard 20 MHz width. "
                "Some channels may be subject to Dynamic Frequency Selection (DFS) requirements due to "
                "radar systems operating on the same frequencies.</p>"
            )
            
            self.results_5ghz.setText(html)
        else:
            self.results_5ghz.setText("<p>No networks found on 5 GHz band.</p>")
