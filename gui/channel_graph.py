"""
Channel Graph Module

This module provides visualization components for displaying WiFi channel usage
and congestion information using Matplotlib.
"""
import logging
import numpy as np
import matplotlib
# Set the backend before importing pyplot
matplotlib.use('QtAgg')  # This works with both PyQt5 and PyQt6

from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.animation import FuncAnimation
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel, QFrame

from utils.channel_analyzer import ChannelAnalyzer, CHANNELS_2_4GHZ, CHANNELS_5GHZ, NON_OVERLAPPING_2_4GHZ, DFS_CHANNELS

logger = logging.getLogger(__name__)

class ChannelGraphCanvas(FigureCanvas):
    """
    Canvas for rendering channel graphs using Matplotlib.
    """
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        """
        Initialize the channel graph canvas.
        
        Args:
            parent: Parent widget
            width: Width of the figure in inches
            height: Height of the figure in inches
            dpi: Dots per inch
        """
        self.fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        self.axes = self.fig.add_subplot(111)
        
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Configure for interactive mode
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_hover)
        
        # Store data
        self.hover_annotation = None
        self.bar_containers = {}
        self.recommended_channel_line = None
        self.current_band = '2.4GHz'
        self.network_data = None
        
    def update_graph(self, visualization_data, band='2.4GHz'):
        """
        Update the graph with new visualization data.
        
        Args:
            visualization_data: Data for visualization from ChannelAnalyzer
            band: Frequency band to display ('2.4GHz' or '5GHz')
        """
        self.current_band = band
        self.network_data = visualization_data[band]
        
        # Clear previous graph
        self.axes.clear()
        
        # Get data for the current band
        channels = self.network_data['channels']
        network_counts = self.network_data['network_counts']
        congestion_scores = self.network_data['congestion_scores']
        recommended_channel = self.network_data['recommended_channel']
        
        # Create bar chart for network counts
        bars = self.axes.bar(channels, network_counts, alpha=0.7, color='steelblue')
        self.bar_containers['networks'] = bars
        
        # Create a second y-axis for congestion scores
        ax2 = self.axes.twinx()
        congestion_line = ax2.plot(channels, congestion_scores, 'r-', marker='o', label='Congestion Score')
        
        # Highlight recommended channel
        if recommended_channel in channels:
            index = channels.index(recommended_channel)
            self.recommended_channel_line = self.axes.axvline(
                x=recommended_channel, color='green', linestyle='--', alpha=0.7,
                label=f'Recommended: CH {recommended_channel}'
            )
        
        # Highlight special channels
        if band == '2.4GHz':
            # Highlight non-overlapping channels
            for ch in NON_OVERLAPPING_2_4GHZ:
                self.axes.axvline(x=ch, color='gray', linestyle=':', alpha=0.3)
        else:
            # Highlight DFS channels
            for i, ch in enumerate(channels):
                if ch in DFS_CHANNELS:
                    bars[i].set_color('lightsteelblue')
                    self.axes.text(ch, network_counts[i] + 0.1, 'DFS', 
                                 ha='center', va='bottom', fontsize=8, alpha=0.7)
        
        # Set labels and title
        self.axes.set_xlabel('Channel')
        self.axes.set_ylabel('Number of Networks')
        ax2.set_ylabel('Congestion Score')
        
        title = f'{band} WiFi Channel Usage'
        self.axes.set_title(title)
        
        # Set x-axis to show integer channel numbers
        self.axes.set_xticks(channels)
        
        # Set y-axis limits with some padding
        max_networks = max(network_counts) if network_counts else 1
        self.axes.set_ylim(0, max_networks * 1.2)
        ax2.set_ylim(0, 100)  # Congestion score is 0-100
        
        # Add legend
        lines, labels = self.axes.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        self.axes.legend(lines + lines2, labels + labels2, loc='upper right')
        
        # Update canvas
        self.draw()
    
    def _on_hover(self, event):
        """Handle mouse hover event to show channel details."""
        if not event.inaxes:
            if self.hover_annotation:
                self.hover_annotation.set_visible(False)
                self.draw_idle()
            return

        if not hasattr(self, 'network_data') or not self.network_data:
            return

        # Get x value (channel)
        x_mouse = event.xdata
        channels = self.network_data['channels']
        
        if not channels:
            return
            
        # Find closest channel
        closest_channel_idx = min(range(len(channels)), 
                                 key=lambda i: abs(channels[i] - x_mouse))
        closest_channel = channels[closest_channel_idx]
        
        # Get data for this channel
        network_count = self.network_data['network_counts'][closest_channel_idx]
        congestion_score = self.network_data['congestion_scores'][closest_channel_idx]
        
        # Create annotation text
        text = f"Channel: {closest_channel}\nNetworks: {network_count}\nCongestion: {congestion_score:.1f}%"
        
        # Add special indicators
        if self.current_band == '2.4GHz' and closest_channel in NON_OVERLAPPING_2_4GHZ:
            text += "\n(Non-overlapping)"
        elif self.current_band == '5GHz' and closest_channel in DFS_CHANNELS:
            text += "\n(DFS channel)"
        
        if closest_channel == self.network_data['recommended_channel']:
            text += "\n*** RECOMMENDED ***"
        
        # Update or create annotation
        if self.hover_annotation:
            # Instead of removing, update the existing annotation
            self.hover_annotation.set_visible(True)
            self.hover_annotation.set_text(text)
            self.hover_annotation.xy = (closest_channel, network_count)
        else:
            # Create new annotation
            self.hover_annotation = self.axes.annotate(
                text,
                xy=(closest_channel, network_count),
                xytext=(15, 15),
                textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
            )
        
        self.draw_idle()


class WaterfallGraphCanvas(FigureCanvas):
    """
    Canvas for rendering waterfall charts to show signal strength over time.
    """
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        """
        Initialize the waterfall graph canvas.
        
        Args:
            parent: Parent widget
            width: Width of the figure in inches
            height: Height of the figure in inches
            dpi: Dots per inch
        """
        self.fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        self.axes = self.fig.add_subplot(111)
        
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Create empty data structure for waterfall
        self.history_depth = 10  # Number of history rows to keep
        self.history_data = None
        self.current_channels = None
        self.im = None
        self.colorbar = None
        
    def initialize_data(self, channels):
        """
        Initialize the waterfall data structure for a set of channels.
        
        Args:
            channels: List of channel numbers
        """
        self.current_channels = channels
        self.history_data = np.zeros((self.history_depth, len(channels)))
        self.history_data.fill(np.nan)  # Fill with NaN to indicate no data
    
    def update_waterfall(self, signal_data, channels):
        """
        Update the waterfall chart with new signal data.
        
        Args:
            signal_data: List of signal strengths by channel
            channels: List of channel numbers
        """
        # Initialize data if needed or if channels changed
        if self.history_data is None or self.current_channels != channels:
            self.initialize_data(channels)
        
        # Roll the history data (shift older data down)
        self.history_data = np.roll(self.history_data, 1, axis=0)
        
        # Fill in the newest row with current data
        for i, ch in enumerate(channels):
            if i < len(signal_data) and signal_data[i] is not None:
                self.history_data[0, i] = signal_data[i]
            else:
                self.history_data[0, i] = np.nan
        
        # Clear previous graph
        self.axes.clear()
        
        # Create waterfall plot (pseudocolor plot)
        # vmin/vmax set the color scale boundaries for signal strength
        self.im = self.axes.imshow(
            self.history_data, 
            aspect='auto',
            cmap='jet',
            interpolation='nearest',
            extent=[min(channels)-0.5, max(channels)+0.5, self.history_depth-0.5, -0.5],
            vmin=-90,  # Min signal strength (dBm)
            vmax=-30   # Max signal strength (dBm)
        )
        
        # Add colorbar
        if self.colorbar is None:
            self.colorbar = self.fig.colorbar(self.im, ax=self.axes)
            self.colorbar.set_label('Signal Strength (dBm)')
        else:
            self.colorbar.update_normal(self.im)
        
        # Set labels and title
        self.axes.set_xlabel('Channel')
        self.axes.set_ylabel('Time (newest at top)')
        self.axes.set_title('Signal Strength History')
        
        # Set x-axis to show integer channel numbers
        self.axes.set_xticks(channels)
        
        # Hide y-tick labels (time axis)
        self.axes.set_yticks([])
        
        # Update canvas
        self.draw()


class ChannelGraphWidget(QWidget):
    """
    Widget for displaying WiFi channel graphs.
    """
    
    # Signal emitted when refresh is requested
    refresh_requested = pyqtSignal()
    
    def __init__(self, analyzer, parent=None):
        """Initialize the channel graph widget."""
        super().__init__(parent)
        
        # Store the channel analyzer
        self.channel_analyzer = analyzer
        
        # Create layout
        self.init_ui()
        
        # Setup auto-refresh timer
        self._setup_timer()
    
    def init_ui(self):
        """Initialize the UI components."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Controls layout
        controls_layout = QHBoxLayout()
        
        # Band selection
        self.band_label = QLabel("Frequency Band:")
        self.band_combo = QComboBox()
        self.band_combo.addItem("2.4 GHz", "2.4GHz")
        self.band_combo.addItem("5 GHz", "5GHz")
        self.band_combo.currentIndexChanged.connect(self._on_band_changed)
        
        # Add controls to layout
        controls_layout.addWidget(self.band_label)
        controls_layout.addWidget(self.band_combo)
        controls_layout.addStretch(1)
        
        # Add controls to main layout
        main_layout.addLayout(controls_layout)
        
        # Create channel graph canvas
        self.channel_graph = ChannelGraphCanvas(self, width=8, height=4)
        main_layout.addWidget(self.channel_graph)
        
        # Store reference to the figure from the channel graph canvas
        self.fig = self.channel_graph.fig
        
        # Create waterfall graph canvas
        self.waterfall_graph = WaterfallGraphCanvas(self, width=8, height=3)
        main_layout.addWidget(self.waterfall_graph)
        
        # Set initial state
        self.current_band = "2.4GHz"
        self.visualization_data = None
    
    def _setup_timer(self):
        """Setup auto-refresh timer."""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._on_refresh_clicked)
    
    def start_auto_refresh(self, interval_ms=5000):
        """
        Start auto-refresh timer.
        
        Args:
            interval_ms: Refresh interval in milliseconds
        """
        self.refresh_timer.start(interval_ms)
    
    def stop_auto_refresh(self):
        """Stop auto-refresh timer."""
        self.refresh_timer.stop()
    
    def _on_band_changed(self, index):
        """
        Handle band selection change.
        
        Args:
            index: Index of the selected item
        """
        self.current_band = self.band_combo.currentData()
        
        # Update graph if we have data
        if self.visualization_data:
            self.channel_graph.update_graph(self.visualization_data, self.current_band)
            
            # Update waterfall with current band's signal data
            if self.current_band == "2.4GHz":
                channels = CHANNELS_2_4GHZ
            else:
                channels = CHANNELS_5GHZ
                
            signals = self.visualization_data[self.current_band]['signal_strengths']
            self.waterfall_graph.update_waterfall(signals, channels)
    
    def _on_refresh_clicked(self):
        """Handle refresh button click."""
        # Emit signal to request fresh network data
        self.refresh_requested.emit()
    
    def update_graphs(self, networks):
        """
        Update graphs with new network data.
        
        Args:
            networks: List of network dictionaries
        """
        try:
            # Convert networks to the format expected by channel_analyzer
            analyzer_networks = []
            for network in networks:
                # Create dictionary representation of each network
                net_dict = {
                    'ssid': network.ssid,
                    'bssid': network.bssid,
                    'channel': network.channel,
                    'band': network.band,
                    'signal_dbm': network.signal_dbm,
                    'bssids': []
                }
                
                # Add all BSSIDs
                for bssid in network.bssids:
                    bssid_dict = {
                        'bssid': bssid.bssid,
                        'channel': bssid.channel,
                        'band': bssid.band,
                        'signal_dbm': bssid.signal_dbm
                    }
                    net_dict['bssids'].append(bssid_dict)
                    
                analyzer_networks.append(net_dict)
            
            # Analyze channel usage
            self.channel_analyzer.analyze_channel_usage(analyzer_networks)
            
            # Get visualization data
            self.visualization_data = self.channel_analyzer.get_visualization_data()
            
            # Update channel graph
            self.channel_graph.update_graph(self.visualization_data, self.current_band)
            
            # Update waterfall graph
            if self.current_band == "2.4GHz":
                channels = CHANNELS_2_4GHZ
            else:
                channels = CHANNELS_5GHZ
                
            signals = self.visualization_data[self.current_band]['signal_strengths']
            self.waterfall_graph.update_waterfall(signals, channels)
            
        except Exception as e:
            logger.error(f"Error updating channel graphs: {str(e)}")
    
    def take_snapshot(self):
        """
        Take a snapshot of the current graph.
        
        Returns:
            Figure object that can be saved as an image
        """
        return self.channel_graph.fig