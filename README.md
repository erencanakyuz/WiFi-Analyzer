# WiFi Analyzer

A comprehensive desktop Pyhton Windows application for analyzing WiFi networks, visualizing channel congestion, diagnosing connection issues finding best channel in both 5GHZ and 2.4 GHZ

## Overview

WiFi Analyzer scans for nearby wireless networks and provides detailed information and analytics to help users optimize their WiFi setup. The application features a modern PyQt-based GUI with interactive visualizations of WiFi channels, signal strength, and network characteristics.

## Features

- **Network Scanning**: Automatically detects and displays information about nearby WiFi networks
- **Detailed Network Information**: View SSID, BSSID, signal strength, channel, band, and security types
- **Channel Analysis**: Analyze channel congestion and receive recommendations for optimal channels
- **Signal Visualization**:
  - Interactive channel usage graphs
  - Real-time signal strength waterfall charts
  - Network signal quality indicators
- **Exporting**: Export scan results to CSV, JSON, or text formats
- **Network Diagnostics**: Tools to diagnose WiFi connectivity issues
- **Customization**: Configurable UI with theme options (dark mode, high contrast)

## Requirements

- Python 3.8 or higher
- Windows operating system (for full functionality)
- The following Python packages:PyQt6 (or PyQt5) matplotlib numpy
- 
## Installation

1. Clone the repository:git clone https://github.com/yourusername/WiFi-Analyzer.git cd WiFi-Analyzer
   
2. Install required dependencies:pip install -r requirements.txt
   
3. Run the application:python main.py
   
## Usage

### Scanning for Networks

Launch the application and it will automatically scan for nearby WiFi networks. You can manually refresh the scan by clicking the refresh button or using the keyboard shortcut (F5).

### Analyzing Channel Congestion

1. Go to Tools → Analyze Channel Congestion
2. The dialog will display analysis for both 2.4 GHz and 5 GHz bands
3. Review the congestion levels and recommendations for optimal channel selection

### Visualizing Channel Usage

The Channel Graph tab provides:
- Bar charts showing network distribution across channels
- Congestion score indicators
- Waterfall charts showing signal strength history
- Recommended channels highlighted for easy identification

### Exporting Data

1. Go to File → Export Networks
2. Choose your preferred format (CSV, JSON, or text)
3. Select a location to save the export file

## Project Structure

- **gui/**: User interface components
  - **main_window.py**: Main application window
  - **channel_graph.py**: Channel visualization components
  - **network_table.py**: Network list display
  - **widgets/**: Reusable UI components
- **scanner/**: Network scanning functionality
  - **windows_scanner.py**: Windows-specific scanning implementation
  - **models.py**: Data models for networks and scan results
  - **parser.py**: Parsing utilities for netsh output
- **utils/**: Utility functions
  - **channel_analyzer.py**: Channel analysis algorithms
  - **signal_utils.py**: Signal processing utilities
- **config/**: Application configuration



## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
