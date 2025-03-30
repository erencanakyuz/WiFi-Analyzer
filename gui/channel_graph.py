from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Union, Any, Tuple
import numpy as np
import matplotlib
import networkx as nx
from matplotlib.cm import get_cmap

# Set the backend before importing pyplot
matplotlib.use('QtAgg')  # This works with both PyQt5 and PyQt6

from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.artist import Artist
from matplotlib.text import Annotation
from matplotlib.container import BarContainer
from matplotlib.collections import LineCollection
from matplotlib.animation import FuncAnimation
from matplotlib.axes import Axes
from matplotlib.colorbar import Colorbar
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QComboBox, QLabel, QFrame, QTabWidget, QSplitter,
    QMainWindow, QStatusBar, QApplication, QSlider
)
from PyQt6.QtGui import QColor, QFont, QPalette

from utils.channel_analyzer import (
    ChannelAnalyzer, CHANNELS_2_4GHZ, CHANNELS_5GHZ, 
    NON_OVERLAPPING_2_4GHZ, DFS_CHANNELS
)
from scanner.models import WiFiNetwork, NetworkBSSID   # Alias for compatibility

logger = logging.getLogger(__name__)

# Type aliases
VisualizationData = Dict[str, Dict[str, Union[List[int], List[float], int]]]

# Modern dark theme colors
DARK_BG = "#2E2E2E"
LIGHT_TEXT = "#E0E0E0"
ACCENT_COLOR = "#5294E2"
SECONDARY_COLOR = "#8AB4F8"
GRID_COLOR = "#555555"
CHART_COLORS = ["#5294E2", "#FF7043", "#66BB6A", "#FFA726", "#AB47BC", "#26C6DA"]

def apply_dark_theme(app):
    """Apply dark theme to the entire application"""
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(DARK_BG))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(LIGHT_TEXT))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor("#353535"))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#2E2E2E"))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(DARK_BG))
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(LIGHT_TEXT))
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(LIGHT_TEXT))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(DARK_BG))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(LIGHT_TEXT))
    dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(ACCENT_COLOR))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT_COLOR))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(LIGHT_TEXT))
    
    app.setPalette(dark_palette)
    
    # Set stylesheet for additional controls
    app.setStyleSheet("""
        QComboBox, QPushButton, QTabBar::tab {
            background-color: #3C3C3C;
            color: #E0E0E0;
            border: 1px solid #555555;
            padding: 5px 10px;
            border-radius: 3px;
        }
        
        QComboBox:hover, QPushButton:hover, QTabBar::tab:hover {
            background-color: #444444;
        }
        
        QComboBox:pressed, QPushButton:pressed, QTabBar::tab:selected {
            background-color: #5294E2;
        }
        
        QSlider::groove:horizontal {
            background: #555555;
            height: 6px;
            border-radius: 3px;
        }
        
        QSlider::handle:horizontal {
            background: #5294E2;
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }
    """)


class ChannelGraphCanvas(FigureCanvas):
    """
    Canvas for rendering enhanced channel graphs using Matplotlib.
    """
    
    def __init__(
        self, 
        parent: Optional[QWidget] = None, 
        width: int = 5, 
        height: int = 4, 
        dpi: int = 100
    ) -> None:
        """
        Initialize the channel graph canvas.
        
        Args:
            parent: Parent widget
            width: Width of the figure in inches
            height: Height of the figure in inches
            dpi: Dots per inch (dots per inch)
        """
        self.fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        self.fig.patch.set_facecolor(DARK_BG)
        self.axes = self.fig.add_subplot(111)
        self.axes.set_facecolor("#353535")
        
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
        
        # Configure style for dark theme
        self._configure_style()
        
    def _configure_style(self):
        """Set up matplotlib style for dark theme"""
        self.axes.tick_params(colors=LIGHT_TEXT)
        for spine in self.axes.spines.values():
            spine.set_edgecolor(GRID_COLOR)
            
        self.axes.title.set_color(LIGHT_TEXT)
        self.axes.xaxis.label.set_color(LIGHT_TEXT)
        self.axes.yaxis.label.set_color(LIGHT_TEXT)
        
    def update_graph(self, visualization_data: VisualizationData, band: str = '2.4GHz') -> None:
        """
        Update the graph with new visualization data.
        
        Args:
            visualization_data: Data for visualization from ChannelAnalyzer
            band: Frequency band to display ('2.4GHz' or '5GHz')
            
        Raises:
            KeyError: If required data is missing from visualization_data
            ValueError: If data arrays have inconsistent lengths
        """
        try:
            self.current_band = band
            self.network_data = visualization_data[band]
            
            # Get data for the current band
            channels = self.network_data['channels']
            network_counts = self.network_data['network_counts']
            congestion_scores = self.network_data['congestion_scores']
            recommended_channel = self.network_data['recommended_channel']
            
            # Validate data arrays
            if len(network_counts) != len(channels) or len(congestion_scores) != len(channels):
                raise ValueError("Data arrays must have consistent lengths")
            
            # Clear previous graph
            self.axes.clear()
            
            # Create bar chart for network counts
            bars = self.axes.bar(channels, network_counts, alpha=0.8, color=ACCENT_COLOR, width=0.9)
            self.bar_containers['networks'] = bars
            
            # Create a second y-axis for congestion scores
            ax2 = self.axes.twinx()
            congestion_line = ax2.plot(channels, congestion_scores, color=SECONDARY_COLOR, 
                                     marker='o', linewidth=2, markersize=6,
                                     label='Congestion Score')
            
            # Add semi-transparent fill under the congestion line
            ax2.fill_between(channels, congestion_scores, alpha=0.2, color=SECONDARY_COLOR)
            
            # Highlight recommended channel
            if recommended_channel in channels:
                self.recommended_channel_line = self.axes.axvline(
                    x=recommended_channel, color='#66BB6A', linestyle='--', linewidth=2, alpha=0.8,
                    label=f'Recommended: CH {recommended_channel}'
                )
            
            # Highlight special channels
            if band == '2.4GHz':
                for ch in NON_OVERLAPPING_2_4GHZ:
                    self.axes.axvline(x=ch, color=GRID_COLOR, linestyle=':', alpha=0.4)
            else:
                for i, ch in enumerate(channels):
                    if ch in DFS_CHANNELS:
                        bars[i].set_color('#FFA726')  # Orange for DFS channels
                        self.axes.text(ch, network_counts[i] + 0.1, 'DFS', 
                                     ha='center', va='bottom', fontsize=8, color=LIGHT_TEXT)
            
            # Set up graph labels and styling
            self._configure_graph_appearance(ax2, channels, network_counts)
            
            # Set style for dark theme
            self._configure_style()
            ax2.tick_params(colors=LIGHT_TEXT)
            ax2.yaxis.label.set_color(LIGHT_TEXT)
            
            # Update canvas
            self.draw()
            
        except KeyError as e:
            logger.error(f"Missing required data in visualization_data: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid data format: {e}")
            raise
        except Exception as e:
            logger.error(f"Error updating graph: {e}")
            raise
            
    def _configure_graph_appearance(self, ax2: Axes, channels: List[int], 
                                  network_counts: List[int]) -> None:
        """Configure graph labels, title, and styling."""
        # Set labels and title
        self.axes.set_xlabel('Channel', fontsize=10, fontweight='bold')
        self.axes.set_ylabel('Number of Networks', fontsize=10, fontweight='bold')
        ax2.set_ylabel('Congestion Score', fontsize=10, fontweight='bold')
        
        title = f'{self.current_band} WiFi Channel Usage'
        self.axes.set_title(title, fontsize=12, fontweight='bold')
        
        # Set x-axis to show integer channel numbers
        self.axes.set_xticks(channels)
        
        # Set y-axis limits with some padding
        max_networks = max(network_counts) if network_counts else 0
        # Ensure we have a minimum range to avoid identical ylims
        y_max = max(max_networks * 1.2, 1)  # At least 1 when max_networks is 0
        self.axes.set_ylim(0, y_max)
        ax2.set_ylim(0, 100)  # Congestion score is 0-100
        
        # Add grid
        self.axes.grid(True, axis='y', linestyle='--', alpha=0.3, color=GRID_COLOR)
        
        # Add legend with custom styling
        lines, labels = self.axes.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        legend = self.axes.legend(lines + lines2, labels + labels2, 
                               loc='upper right', framealpha=0.8, facecolor="#353535", 
                               edgecolor=GRID_COLOR)
        for text in legend.get_texts():
            text.set_color(LIGHT_TEXT)
        

    def _on_hover(self, event: matplotlib.backend_bases.MouseEvent) -> None:
        """
        Handle mouse hover event to show channel details.
        
        Args:
            event: Mouse event containing coordinates and axis information
            
        Note:
            Updates the hover annotation with channel details when mouse
            moves over the graph. Hides annotation when mouse leaves axes.
        """
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
                bbox=dict(boxstyle='round,pad=0.5', fc='#444444', alpha=0.9, ec=ACCENT_COLOR),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color=ACCENT_COLOR),
                color=LIGHT_TEXT
            )
        
        self.draw_idle()


class WaterfallGraphCanvas(FigureCanvas):
    """
    Canvas for rendering enhanced waterfall charts to show signal strength over time.
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
        self.fig.patch.set_facecolor(DARK_BG)
        self.axes = self.fig.add_subplot(111)
        self.axes.set_facecolor("#353535")
        
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Create empty data structure for waterfall
        self.history_depth = 10  # Number of history rows to keep
        self.history_data = None
        self.current_channels = None
        self.im = None
        self.colorbar = None
        
        # Configure style for dark theme
        self._configure_style()
        
    def _configure_style(self):
        """Set up matplotlib style for dark theme"""
        self.axes.tick_params(colors=LIGHT_TEXT)
        for spine in self.axes.spines.values():
            spine.set_edgecolor(GRID_COLOR)
            
        self.axes.title.set_color(LIGHT_TEXT)
        self.axes.xaxis.label.set_color(LIGHT_TEXT)
        self.axes.yaxis.label.set_color(LIGHT_TEXT)
        
    def initialize_data(self, channels: List[int]) -> None:
        """
        Initialize the waterfall data structure for a set of channels.
        
        Args:
            channels: List of channel numbers to monitor
        """
        self.current_channels = channels
        self.history_data = np.zeros((self.history_depth, len(channels)))
        self.history_data.fill(np.nan)  # Fill with NaN to indicate no data
    
    def update_waterfall(self, signal_data: List[float], channels: List[int]) -> None:
        """
        Update the waterfall chart with new signal data.
        
        Args:
            signal_data: List of signal strengths by channel (in dBm)
            channels: List of channel numbers to display
            
        Note:
            Updates the waterfall display showing signal strength history over time.
            Newest data is shown at the top of the chart.
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
        # Using a more visually appealing colormap
        self.im = self.axes.imshow(
            self.history_data, 
            aspect='auto',
            cmap='viridis',  # Modern colormap
            interpolation='bilinear',  # Smoother interpolation
            extent=[min(channels)-0.5, max(channels)+0.5, self.history_depth-0.5, -0.5],
            vmin=-90,  # Min signal strength (dBm)
            vmax=-30   # Max signal strength (dBm)
        )
        
        # Add colorbar with custom styling
        if self.colorbar is None:
            self.colorbar = self.fig.colorbar(self.im, ax=self.axes)
            self.colorbar.set_label('Signal Strength (dBm)', color=LIGHT_TEXT)
            self.colorbar.ax.yaxis.set_tick_params(color=LIGHT_TEXT)
            for label in self.colorbar.ax.get_yticklabels():
                label.set_color(LIGHT_TEXT)
        else:
            self.colorbar.update_normal(self.im)
            self.colorbar.set_label('Signal Strength (dBm)', color=LIGHT_TEXT)
            
        # Set labels and title
        self.axes.set_xlabel('Channel', fontsize=10, fontweight='bold')
        self.axes.set_ylabel('Time (newest at top)', fontsize=10, fontweight='bold')
        self.axes.set_title('Signal Strength History', fontsize=12, fontweight='bold')
        
        # Set x-axis to show integer channel numbers
        self.axes.set_xticks(channels)
        
        # Hide y-tick labels (time axis)
        self.axes.set_yticks(range(self.history_depth))
        self.axes.set_yticklabels([f"{i} scans ago" if i > 0 else "Current" for i in range(self.history_depth)])
        
        # Configure style for dark theme
        self._configure_style()
        
        # Update canvas
        self.draw()


class NetworkGraphCanvas(FigureCanvas):
    """
    Canvas for rendering network relationship graphs using NetworkX.
    Shows relationships between networks, access points, and channels.
    """
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        """Initialize the network graph canvas."""
        self.fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        self.fig.patch.set_facecolor(DARK_BG)
        self.axes = self.fig.add_subplot(111)
        self.axes.set_facecolor("#353535")
        
        super().__init__(self.fig)
        self.setParent(parent)
        
        # Configure style
        self._configure_style()
        
        # Network graph setup
        self.G = nx.Graph()
        self.pos = None
        self.node_labels = {}
        self.edge_labels = {}

        
    def _configure_style(self):
        """Set up matplotlib style for dark theme"""
        self.axes.tick_params(colors=LIGHT_TEXT)
        for spine in self.axes.spines.values():
            spine.set_edgecolor(GRID_COLOR)
            
        self.axes.title.set_color(LIGHT_TEXT)
        
    def update_network_graph(self, networks: List[WiFiNetwork], band='2.4GHz'):
        """Update the network graph with new data."""
        self.axes.clear()
        
        # Create a new graph
        self.G = nx.Graph()
        
        # Add channel nodes
        if band == '2.4GHz':
            channels = CHANNELS_2_4GHZ
        else:
            channels = CHANNELS_5GHZ
            
        # Add channel nodes
        for ch in channels:
            self.G.add_node(f"CH{ch}", type='channel')
            
        # Dictionary to track networks already added
        added_networks = {}
        
        # Add network and BSSID nodes
        for network in networks:
            if network.band != band:
                continue
                
            # Skip if channel is not in our list
            if network.channel not in channels:
                continue
                
            # Add network node if not already added
            if network.ssid not in added_networks:
                self.G.add_node(network.ssid, type='network')
                added_networks[network.ssid] = True
                
            # Link network to channel
            self.G.add_edge(network.ssid, f"CH{network.channel}", 
                         weight=abs(network.signal_dbm)/100.0,
                         signal=network.signal_dbm)
            
            # Add BSSID nodes and link to networks
            for bssid in network.bssids:
                if bssid.band != band:
                    continue
                    
                self.G.add_node(bssid.bssid, type='bssid')
                self.G.add_edge(network.ssid, bssid.bssid, 
                             weight=0.5,
                             signal=bssid.signal_dbm)
        
        # Calculate network layout
        self._calculate_layout()
        
        # Draw the graph
        self._draw_graph()
        
        # Update canvas
        self.draw()
    
    def _calculate_layout(self):
        """Calculate node positions for the graph."""
        # Get nodes by type
        channel_nodes = [n for n, d in self.G.nodes(data=True) if d.get('type') == 'channel']
        network_nodes = [n for n, d in self.G.nodes(data=True) if d.get('type') == 'network']
        bssid_nodes = [n for n, d in self.G.nodes(data=True) if d.get('type') == 'bssid']
        
        # If no networks, just return
        if not network_nodes:
            self.pos = {}
            return
            
        # Positions for channel nodes - circular layout on the bottom
        ch_count = len(channel_nodes)
        channel_pos = {}
        radius = 0.8
        center_x, center_y = 0.5, 0.3  # Bottom-center

        for i, node in enumerate(sorted(channel_nodes, key=lambda x: int(x[2:]))):
            angle = 2 * math.pi * i / ch_count
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            channel_pos[node] = (x, y)
            
        # Positions for network nodes - force-directed layout starting from center
        network_pos = nx.spring_layout(
            nx.subgraph(self.G, network_nodes),
            k=0.5,
            iterations=50,
            center=(0.5, 0.7)  # Top-center
        )
        
        # Positions for BSSID nodes - near their parent networks
        bssid_pos = {}
        for bssid in bssid_nodes:
            # Find connected network
            for neighbor in self.G.neighbors(bssid):
                if neighbor in network_pos:
                    # Position slightly offset from the network
                    bssid_pos[bssid] = (
                        network_pos[neighbor][0] + np.random.uniform(-0.05, 0.05),
                        network_pos[neighbor][1] + np.random.uniform(-0.05, 0.05)
                    )
                    break
        
        # Combine all positions
        self.pos = {**channel_pos, **network_pos, **bssid_pos}
        
    def _draw_graph(self):
        """Draw the network graph."""
        if not self.pos:
            self.axes.text(0.5, 0.5, "No networks to display", 
                         ha='center', va='center', color=LIGHT_TEXT,
                         fontsize=12)
            return
            
        # Get nodes by type
        channel_nodes = [n for n, d in self.G.nodes(data=True) if d.get('type') == 'channel']
        network_nodes = [n for n, d in self.G.nodes(data=True) if d.get('type') == 'network']
        bssid_nodes = [n for n, d in self.G.nodes(data=True) if d.get('type') == 'bssid']
        
        # Get edges by type
        network_to_channel = [(u, v) for u, v in self.G.edges() 
                             if (u in network_nodes and v in channel_nodes) or
                               (v in network_nodes and u in channel_nodes)]
        
        network_to_bssid = [(u, v) for u, v in self.G.edges() 
                          if (u in network_nodes and v in bssid_nodes) or
                            (v in network_nodes and u in bssid_nodes)]
        
        # Draw channel nodes
        nx.draw_networkx_nodes(
            self.G, self.pos, nodelist=channel_nodes,
            node_color=ACCENT_COLOR, node_size=500, alpha=0.9,
            edgecolors='white', linewidths=1,
            ax=self.axes
        )
        
        # Draw network nodes
        nx.draw_networkx_nodes(
            self.G, self.pos, nodelist=network_nodes,
            node_color='#FF7043', node_size=700, alpha=0.9,
            edgecolors='white', linewidths=1,
            ax=self.axes
        )
        
        # Draw BSSID nodes
        nx.draw_networkx_nodes(
            self.G, self.pos, nodelist=bssid_nodes,
            node_color='#FFA726', node_size=300, alpha=0.8,
            edgecolors='white', linewidths=1,
            ax=self.axes
        )
        
        # Draw edges - network to channel (weighted by signal strength)
        edge_widths = [self.G[u][v]['weight'] * 2 for u, v in network_to_channel]
        
        nx.draw_networkx_edges(
            self.G, self.pos, edgelist=network_to_channel,
            width=edge_widths, alpha=0.7, edge_color='#FFFFFF',
            ax=self.axes
        )
        
        # Draw edges - network to BSSID
        nx.draw_networkx_edges(
            self.G, self.pos, edgelist=network_to_bssid,
            width=1, alpha=0.5, edge_color='#AAAAAA',
            style='dashed',
            ax=self.axes
        )
        
        # Draw labels - channels only fully, networks truncated
        ch_labels = {n: n for n in channel_nodes}
        
        # For networks, truncate to max 10 chars + ...
        net_labels = {}
        for n in network_nodes:
            if len(n) > 10:
                net_labels[n] = n[:10] + "..."
            else:
                net_labels[n] = n
        
        # BSSID - only last 4 chars
        bssid_labels = {n: n[-5:] for n in bssid_nodes}
        
        # Draw channel labels
        nx.draw_networkx_labels(
            self.G, self.pos, labels=ch_labels,
            font_size=10, font_weight='bold', font_color='white',
            ax=self.axes
        )
        
        # Draw network labels
        nx.draw_networkx_labels(
            self.G, self.pos, labels=net_labels,
            font_size=8, font_color='white',
            ax=self.axes
        )
        
        # Draw BSSID labels
        nx.draw_networkx_labels(
            self.G, self.pos, labels=bssid_labels,
            font_size=6, font_color='white',
            ax=self.axes
        )
        
        # Set title and adjust display
        self.axes.set_title("WiFi Network Relationship Graph", fontsize=12, fontweight='bold')
        self.axes.set_axis_off()
        
        # Configure style
        self._configure_style()


class ChannelGraphWidget(QWidget):
    """
    Enhanced widget for displaying WiFi channel graphs with NetworkX integration.
    """
    
    # Signal emitted when refresh is requested
    refresh_requested = pyqtSignal()
    
    def __init__(self, analyzer: ChannelAnalyzer, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the enhanced channel graph widget.
        
        Args:
            analyzer: Channel analyzer instance for processing network data
            parent: Optional parent widget
        """
        super().__init__(parent)
        
        # Store the channel analyzer
        self.channel_analyzer = analyzer
        
        # Initialize UI components
        self.current_band = '2.4GHz'
        self.auto_refresh = False
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._auto_refresh)
        
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create controls panel
        controls_panel = QWidget()
        controls_layout = QHBoxLayout(controls_panel)
        
        # Band selector
        self.band_selector = QComboBox()
        self.band_selector.addItems(['2.4GHz', '5GHz'])
        self.band_selector.currentTextChanged.connect(self._on_band_changed)
        controls_layout.addWidget(QLabel("Band:"))
        controls_layout.addWidget(self.band_selector)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._request_refresh)
        controls_layout.addWidget(refresh_btn)
        
        # Auto-refresh toggle and interval
        self.auto_refresh_toggle = QPushButton("Auto Refresh: Off")
        self.auto_refresh_toggle.setCheckable(True)
        self.auto_refresh_toggle.clicked.connect(self._toggle_auto_refresh)
        controls_layout.addWidget(self.auto_refresh_toggle)
        
        self.refresh_interval = QSlider(Qt.Orientation.Horizontal)
        self.refresh_interval.setMinimum(1)
        self.refresh_interval.setMaximum(30)
        self.refresh_interval.setValue(5)
        self.refresh_interval.setToolTip("Refresh interval (seconds)")
        controls_layout.addWidget(self.refresh_interval)
        
        controls_layout.addStretch()
        
        # Create tab widget for different visualizations
        self.tab_widget = QTabWidget()
        
        # Create channel usage graph
        self.channel_canvas = ChannelGraphCanvas(self)
        self.tab_widget.addTab(self.channel_canvas, "Channel Usage")
        
        # Create waterfall graph
        self.waterfall_canvas = WaterfallGraphCanvas(self)
        self.tab_widget.addTab(self.waterfall_canvas, "Signal History")
        
        # Create network relationship graph
        self.network_canvas = NetworkGraphCanvas(self)
        self.tab_widget.addTab(self.network_canvas, "Network Graph")
        
        # Add widgets to main layout
        main_layout.addWidget(controls_panel)
        main_layout.addWidget(self.tab_widget)
        
        # Initialize graphs
        self._update_graphs([])
        
    def _on_band_changed(self, band: str) -> None:
        """Handle band selection change."""
        self.current_band = band
        self._request_refresh()
        
    def _toggle_auto_refresh(self) -> None:
        """Toggle auto-refresh functionality."""
        self.auto_refresh = not self.auto_refresh
        self.auto_refresh_toggle.setText(f"Auto Refresh: {'On' if self.auto_refresh else 'Off'}")
        
        if self.auto_refresh:
            interval = self.refresh_interval.value() * 1000  # Convert to milliseconds
            self.refresh_timer.start(interval)
        else:
            self.refresh_timer.stop()
            
    def _auto_refresh(self) -> None:
        """Handler for auto-refresh timer."""
        self._request_refresh()
        
    def _request_refresh(self) -> None:
        """Request a data refresh."""
        self.refresh_requested.emit()
        
    def update_graphs(self, networks: List[WiFiNetwork]) -> None:
        """
        Update the graphs with new network data.
        
        Args:
            networks: List of detected WiFi networks
        """
        self._update_graphs(networks)
        
    def _update_graphs(self, networks: List[WiFiNetwork]) -> None:
        """
        Update all graph visualizations.
        
        Args:
            networks: List of detected WiFi networks
        """
        try:
            # Analyze networks first
            self.channel_analyzer.analyze_channel_usage(networks)
            
            # Get visualization data
            visualization_data = self.channel_analyzer.get_visualization_data()
            
            # Update channel usage graph
            if self.current_band in visualization_data:
                self.channel_canvas.update_graph(visualization_data, self.current_band)
            
            # Update waterfall graph with signal strength data
            if self.current_band in visualization_data:
                data = visualization_data[self.current_band]
                self.waterfall_canvas.update_waterfall(
                    data.get('signal_strengths', []),
                    data.get('channels', [])
                )
            
            # Update network relationship graph
            self.network_canvas.update_network_graph(networks, self.current_band)
            
        except Exception as e:
            logger.error(f"Error updating graphs: {e}")
            raise
