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
from gui.theme_manager import apply_theme

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


class ChannelGraphCanvas(FigureCanvas):
    """
    Canvas for rendering enhanced channel graphs using Matplotlib.
    """
    
    # Signal emitted when a channel is clicked
    channel_clicked = pyqtSignal(dict)
    draw_complete = pyqtSignal()
    
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
        self.fig.canvas.mpl_connect('button_press_event', self._on_click)
        
        # Store data
        self.hover_annotation = None
        self.bar_containers = {}
        self.recommended_channel_line = None
        self.current_band = '2.4GHz'
        self.network_data = None
        
        # Configure style for dark theme
        self._configure_style()
        
    def _configure_style(self):
        """Configure graph style."""
        # Increase figure size and adjust margins
        self.figure.set_size_inches(8, 5)
        self.figure.subplots_adjust(left=0.12, right=0.95, top=0.9, bottom=0.12)
        
        # Set background color
        self.figure.patch.set_facecolor(DARK_BG)
        self.axes.set_facecolor(DARK_BG)
        
        # Configure axis styling
        self.axes.spines['bottom'].set_color(GRID_COLOR)
        self.axes.spines['top'].set_visible(False)  # Hide top spine
        self.axes.spines['left'].set_color(GRID_COLOR)
        self.axes.spines['right'].set_visible(False) # Hide right spine
        
        # Configure tick styling
        self.axes.tick_params(axis='x', colors=LIGHT_TEXT)
        self.axes.tick_params(axis='y', colors=LIGHT_TEXT)
        
        # Configure labels
        self.axes.set_xlabel('Channel', color=LIGHT_TEXT)
        self.axes.set_ylabel('Networks', color=LIGHT_TEXT)
        self.axes.set_title('Channel Utilization', color=LIGHT_TEXT, fontweight='bold')
        
    def update_graph(self, visualization_data: VisualizationData, band: str = '2.4GHz') -> None:
        """Update the graph with new visualization data."""
        # --- UPDATED DEBUG PREFIX ---
        print(f"DEBUG [ChannelGraph]: Update called for band {band}. Received viz data slice: {visualization_data.get(band)}")
        try:
            self.current_band = band
            if band not in visualization_data or not visualization_data[band]:
                self.axes.clear()
                self.axes.text(0.5, 0.5, f"No data available for {band}", 
                            ha='center', va='center', color=LIGHT_TEXT)
                self._configure_style() # Keep style consistent
                self.draw()
                self.draw_complete.emit()
                return
                
            self.network_data = visualization_data[band]
            
            # Determine the full channel list for the band
            all_channels = CHANNELS_2_4GHZ if band == '2.4GHz' else CHANNELS_5GHZ
            
            # Get data from analyzer (potentially sparse)
            analyzer_channels = self.network_data.get('channels', [])
            analyzer_counts = self.network_data.get('network_counts', [])
            analyzer_congestion = self.network_data.get('congestion_scores', [])
            analyzer_signals = self.network_data.get('signal_strengths', [])
            recommended_channel = self.network_data.get('recommended_channel')
            
            # Create a map for easy lookup
            data_map = {ch: {
                'count': analyzer_counts[i] if i < len(analyzer_counts) else 0,
                'congestion': analyzer_congestion[i] if i < len(analyzer_congestion) else 0,
                'signal': analyzer_signals[i] if i < len(analyzer_signals) else None
            } for i, ch in enumerate(analyzer_channels)}
            
            # Create full data lists aligned with all_channels
            full_network_counts = [data_map.get(ch, {}).get('count', 0) for ch in all_channels]
            full_congestion_scores = [data_map.get(ch, {}).get('congestion', 0) for ch in all_channels]
            full_signal_strengths = [data_map.get(ch, {}).get('signal', None) for ch in all_channels]
            
            # --- UPDATED DEBUG PREFIX ---
            print(f"DEBUG [ChannelGraph]: Processed data for band {band}:")
            print(f"  Channels ({len(all_channels)}): {all_channels}")
            print(f"  Counts   ({len(full_network_counts)}): {full_network_counts}")
            print(f"  Congest. ({len(full_congestion_scores)}): {full_congestion_scores}")
            print(f"  Signals  ({len(full_signal_strengths)}): {full_signal_strengths}")
            print(f"  Recommend: {recommended_channel}")
            
            # Validate data arrays (should match all_channels length now)
            if not (len(full_network_counts) == len(all_channels) == 
                    len(full_congestion_scores) == len(full_signal_strengths)):
                raise ValueError("Full data arrays have inconsistent lengths after mapping")
            
            # Clear previous graph
            self.axes.clear()

            # --- Plotting Logic (adapted for full lists) ---
            if band == '2.4GHz':
                # Area chart based on full data
                x_range_full = np.linspace(min(all_channels)-2, max(all_channels)+2, 300)
                y_data_full = np.zeros(len(x_range_full))
                for i, ch in enumerate(all_channels):
                    if full_network_counts[i] > 0:
                        channel_influence = full_network_counts[i] * np.exp(-0.5 * ((x_range_full - ch) / 1.2) ** 2)
                        y_data_full += channel_influence
                self.axes.fill_between(x_range_full, y_data_full, alpha=0.6, color=ACCENT_COLOR, label='Channel Overlap')
                
                # Vertical lines and text for channels with networks
                for i, ch in enumerate(all_channels):
                    if full_network_counts[i] > 0:
                        congestion = full_congestion_scores[i]
                        color = '#66BB6A' if congestion < 30 else '#FFA726' if congestion < 60 else '#F44336'
                        self.axes.axvline(x=ch, alpha=0.7, linestyle='-', linewidth=1.5, color=color)
                        height = full_network_counts[i] + 0.2
                        self.axes.text(ch, height, f"{ch}\n({full_network_counts[i]})", 
                                 ha='center', va='bottom', fontsize=9, color=LIGHT_TEXT,
                                 bbox=dict(boxstyle='round,pad=0.2', fc=color, alpha=0.6))
                
                for ch in NON_OVERLAPPING_2_4GHZ:
                     if ch in all_channels:
                          self.axes.axvspan(ch-0.5, ch+0.5, color='#4CAF50', alpha=0.15)
                    
            else: # 5GHz
                # Bar chart using full channel list
                bar_colors = []
                for score in full_congestion_scores:
                    if score < 30: bar_colors.append('#66BB6A')
                    elif score < 60: bar_colors.append('#FFA726')
                    else: bar_colors.append('#F44336')
                
                bars = self.axes.bar(all_channels, full_network_counts, alpha=0.8, color=bar_colors, width=2) 
                self.bar_containers['networks'] = bars
                
                # Mark DFS channels
                for i, ch in enumerate(all_channels):
                    if ch in DFS_CHANNELS:
                         # Only hatch if channel has networks or just mark existence?
                         # Let's hatch lightly even if empty to indicate DFS status.
                         pattern = '///' if full_network_counts[i] > 0 else '..' 
                         bars[i].set_hatch(pattern)
                         bars[i].set_edgecolor('#AAAAAA') # Make hatch visible on empty bars
                         if full_network_counts[i] > 0: # Only add text if networks are present
                             self.axes.text(ch, full_network_counts[i] + 0.1, 'DFS', 
                                           ha='center', va='bottom', fontsize=7, 
                                           color='white', fontweight='bold',
                                           bbox=dict(boxstyle='round,pad=0.1', fc='#FFA726', alpha=0.9))
            
            # Network count numbers (using full lists)
            for i, ch in enumerate(all_channels):
                if full_network_counts[i] > 0:
                    self.axes.text(ch, full_network_counts[i] + 0.1, f"{full_network_counts[i]}", 
                                 ha='center', va='bottom', fontsize=9, fontweight='bold', color=LIGHT_TEXT)
            
            # Signal marker circles (using full lists)
            if full_signal_strengths:
                 for i, ch in enumerate(all_channels):
                     signal = full_signal_strengths[i]
                     count = full_network_counts[i]
                     if signal is not None and signal > -100 and count > 0:
                         signal_norm = min(1.0, max(0.0, (signal + 90) / 60))
                         marker_size = 50 + signal_norm * 150
                         self.axes.scatter(ch, count * 0.5, 
                                         s=marker_size, color='#29B6F6', alpha=0.7, zorder=10,
                                         edgecolors='white', linewidths=1)
            
            # Congestion score axis (using full lists)
            ax2 = self.axes.twinx()
            if len(all_channels) > 2:
                 x_smooth_full = np.linspace(min(all_channels), max(all_channels), 200) 
                 from scipy.interpolate import make_interp_spline
                 if len(all_channels) >= 4:
                     spl = make_interp_spline(all_channels, full_congestion_scores, k=3)
                     congestion_smooth = spl(x_smooth_full)
                     congestion_line = ax2.plot(x_smooth_full, congestion_smooth, color=SECONDARY_COLOR, linestyle='-', linewidth=2.5, alpha=0.8, label='Congestion Score')
                     ax2.fill_between(x_smooth_full, congestion_smooth, alpha=0.25, color=SECONDARY_COLOR)
                 else:
                     congestion_line = ax2.plot(all_channels, full_congestion_scores, color=SECONDARY_COLOR, marker='o', linewidth=2, markersize=6, label='Congestion Score')
                     ax2.fill_between(all_channels, full_congestion_scores, alpha=0.25, color=SECONDARY_COLOR)
            else:
                 congestion_line = ax2.plot(all_channels, full_congestion_scores, color=SECONDARY_COLOR, marker='o', linewidth=2, markersize=6, label='Congestion Score')
            
            # Recommended channel highlight
            if recommended_channel is not None and recommended_channel in all_channels:
                idx = all_channels.index(recommended_channel)
                rec_count = full_network_counts[idx] # Use count from full list
                max_count_overall = max(full_network_counts) if full_network_counts else 0
                self.axes.add_patch(
                    plt.Rectangle(
                        (recommended_channel - 0.8, 0), 1.6, max(rec_count + 1, max_count_overall * 0.3, 1), # Ensure min height 1
                        fill=True, color='#4CAF50', alpha=0.15, linewidth=2, zorder=0
                    )
                )
                self.axes.annotate(
                    'RECOMMENDED', 
                    xy=(recommended_channel, 0.1), xytext=(recommended_channel, -0.5),
                    arrowprops=dict(arrowstyle='->', color='#4CAF50', lw=1.5),
                    ha='center', va='center', fontsize=10, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', fc='#4CAF50', alpha=0.7, ec='white'),
                    color='white'
                )

            # Configure graph appearance using full channel list
            self._configure_graph_appearance(ax2, all_channels, full_network_counts)
            
            # Apply tight layout before drawing
            try:
                 self.fig.tight_layout()
            except ValueError as layout_error:
                 logger.warning(f"Tight layout failed in ChannelGraph: {layout_error}")
            
            # Update canvas
            self.draw()
            self.draw_complete.emit()
            
        except KeyError as e:
            # --- UPDATED DEBUG PREFIX ---
             logger.warning(f"[ChannelGraph] KeyError accessing visualization data for band {band}: {e}. Might be missing data.")
             self.axes.clear()
             self.axes.text(0.5, 0.5, f"Incomplete data for {band}", ha='center', va='center', color='orange')
             self._configure_style()
             self.draw()
             self.draw_complete.emit()
        except Exception as e:
            logger.error(f"Error updating graph: {e}", exc_info=True)
            self.axes.clear()
            self.axes.text(0.5, 0.5, f"Error updating graph: {str(e)}", 
                          ha='center', va='center', color='red')
            self._configure_style()
            self.draw()
            self.draw_complete.emit()
            
    def _configure_graph_appearance(self, ax2: Axes, all_channels: List[int], 
                                  full_network_counts: List[int]) -> None:
        """Configure graph labels, title, and styling using the full channel list."""
        # Set labels and title
        self.axes.set_xlabel('Channel', fontsize=10, fontweight='bold')
        self.axes.set_ylabel('Number of Networks', fontsize=10, fontweight='bold')
        ax2.set_ylabel('Congestion Score', fontsize=10, fontweight='bold')
        
        title = f'{self.current_band} WiFi Channel Usage'
        self.axes.set_title(title, fontsize=12, fontweight='bold')
        
        # Set x-axis to show all integer channel numbers for the band
        self.axes.set_xticks(all_channels)
        # Optionally rotate labels if too crowded, especially for 5GHz
        if self.current_band == '5GHz' and len(all_channels) > 15:
             self.axes.tick_params(axis='x', labelrotation=45, labelsize=8)
        else:
             self.axes.tick_params(axis='x', labelrotation=0, labelsize=9)

        # Set y-axis limits with some padding
        max_networks = max(full_network_counts) if full_network_counts else 0
        y_max = max(max_networks * 1.2, 1)  # Ensure min height 1
        self.axes.set_ylim(0, y_max)
        ax2.set_ylim(0, 100)  # Congestion score is 0-100
        
        # Add grid (horizontal only, slightly lighter)
        self.axes.grid(True, axis='y', linestyle='--', alpha=0.2, color=GRID_COLOR)
        ax2.grid(False) # Ensure secondary axis doesn't have grid
        
        # Add legend
        lines, labels = self.axes.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        if lines or lines2: # Only show legend if there's something to label
            legend = self.axes.legend(lines + lines2, labels + labels2, 
                                loc='upper right', framealpha=0.8, facecolor="#353535", 
                                edgecolor=GRID_COLOR)
            for text in legend.get_texts():
                text.set_color(LIGHT_TEXT)
        
    def _on_click(self, event: matplotlib.backend_bases.MouseEvent) -> None:
        """Handle mouse click event to emit channel details."""
        if not event.inaxes or event.button != 1: # Only handle left clicks inside axes
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
        avg_signal = self.network_data['signal_strengths'][closest_channel_idx]
        is_recommended = closest_channel == self.network_data['recommended_channel']
        
        # Get BSSIDs on this channel (requires ChannelAnalyzer access or storing more data)
        # For simplicity, we'll just emit basic details for now.
        # To get BSSIDs, we would need to pass the full analyzer result or 
        # modify get_visualization_data to include top SSIDs per channel.
        
        channel_details = {
            'channel': closest_channel,
            'band': self.current_band,
            'network_count': network_count,
            'congestion_score': congestion_score,
            'avg_signal': avg_signal,
            'is_recommended': is_recommended,
            'is_dfs': self.current_band == '5GHz' and closest_channel in DFS_CHANNELS,
            'is_non_overlapping': self.current_band == '2.4GHz' and closest_channel in NON_OVERLAPPING_2_4GHZ
        }
        
        # Emit the signal
        self.channel_clicked.emit(channel_details)

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
            # Remove the previous annotation explicitly
            try:
                self.hover_annotation.remove()
            except Exception as e:
                logger.debug(f"[ChannelGraph] Error removing old annotation: {e}")
            self.hover_annotation = None # Ensure it's cleared

        # Create new annotation
        self.hover_annotation = self.axes.annotate(
            text,
            xy=(closest_channel, network_count),
            xytext=(15, 15),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.5', fc='#444444', alpha=0.9, ec=ACCENT_COLOR),
            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color=ACCENT_COLOR),
            color=LIGHT_TEXT,
            visible=True # Ensure it's visible initially
        )
        
        self.draw_idle()


class WaterfallGraphCanvas(FigureCanvas):
    """
    Canvas for rendering enhanced waterfall charts to show signal strength over time.
    """
    
    # Signal emitted when drawing is complete
    draw_complete = pyqtSignal()
    
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
        # Hide top/right spines
        self.axes.spines['top'].set_visible(False)
        self.axes.spines['right'].set_visible(False)
        # Set color for bottom/left spines
        self.axes.spines['bottom'].set_color(GRID_COLOR)
        self.axes.spines['left'].set_color(GRID_COLOR)
            
        self.axes.title.set_color(LIGHT_TEXT)
        self.axes.xaxis.label.set_color(LIGHT_TEXT)
        self.axes.yaxis.label.set_color(LIGHT_TEXT)
        
        # Add subtle horizontal grid
        self.axes.grid(True, axis='y', linestyle=':', alpha=0.2, color=GRID_COLOR)
        
    def initialize_data(self, band: str) -> None:
        """
        Initialize the waterfall data structure for a set of channels.
        
        Args:
            band: The frequency band ('2.4GHz' or '5GHz')
        """
        # Use the full channel list for the band
        self.current_channels = CHANNELS_2_4GHZ if band == '2.4GHz' else CHANNELS_5GHZ
        if not self.current_channels:
             logger.warning(f"No standard channels defined for band: {band}")
             self.history_data = np.array([[]] * self.history_depth) # Empty history
             return
             
        self.history_data = np.zeros((self.history_depth, len(self.current_channels)))
        self.history_data.fill(np.nan)  # Fill with NaN to indicate no data
    
    def update_waterfall(self, signal_data: List[float], channels: List[int], band: str) -> None:
        """
        Update the waterfall chart with new signal data for a specific band.
        
        Args:
            signal_data: List of signal strengths by channel (in dBm), aligned with `channels`
            channels: List of channel numbers corresponding to `signal_data`
            band: The frequency band ('2.4GHz' or '5GHz') to display
            
        Note:
            Updates the waterfall display showing signal strength history over time.
            Newest data is shown at the top of the chart, covering the full channel range.
        """
        # --- UPDATED DEBUG PREFIX ---
        print(f"DEBUG [Waterfall]: Update called for band {band}.")
        print(f"  Received signal_data ({len(signal_data)}): {signal_data}")
        print(f"  Received channels ({len(channels)}): {channels}")
        
        # Determine the full channel list for the band
        all_channels = CHANNELS_2_4GHZ if band == '2.4GHz' else CHANNELS_5GHZ
        
        # Initialize data if needed or if channels/band changed
        # Check if history_data matches the expected shape for all_channels
        expected_shape = (self.history_depth, len(all_channels))
        if self.history_data is None or self.history_data.shape != expected_shape:
            self.initialize_data(band)
        
        # Check if initialization resulted in empty data
        if self.history_data.size == 0:
             logger.warning(f"Waterfall history data is empty for band {band}, cannot update.")
             # Optionally display a message on the graph
             self.axes.clear()
             self.axes.text(0.5, 0.5, f"Cannot display waterfall for {band}", ha='center', va='center', color=LIGHT_TEXT)
             self._configure_style()
             self.draw()
             self.draw_complete.emit()
             return
             
        # Roll the history data (shift older data down)
        self.history_data = np.roll(self.history_data, 1, axis=0)
        
        # Create a map for the incoming sparse signal data
        signal_map = {ch: signal_data[i] 
                      for i, ch in enumerate(channels) 
                      if i < len(signal_data) and signal_data[i] is not None}
        
        # Fill in the newest row with current data, aligned to all_channels
        for i, ch in enumerate(all_channels):
            self.history_data[0, i] = signal_map.get(ch, np.nan) # Use NaN if no signal data
        
        # --- UPDATED DEBUG PREFIX ---
        print(f"DEBUG [Waterfall]: Updated history_data shape: {self.history_data.shape}")
        print(f"  Newest row (history_data[0]): {self.history_data[0]}")
        
        # Clear previous graph
        self.axes.clear()
        
        # Ensure there are channels to plot
        if not all_channels:
            self.axes.text(0.5, 0.5, f"No channels defined for {band}", 
                        ha='center', va='center', color=LIGHT_TEXT)
            self._configure_style()
            self.draw()
            self.draw_complete.emit()
            return
            
        # Create waterfall plot using the full channel range
        min_ch = min(all_channels)
        max_ch = max(all_channels)
        # Adjust extent calculation slightly if only one channel
        extent_min_x = min_ch - 0.5
        extent_max_x = max_ch + 0.5 if len(all_channels) > 1 else min_ch + 0.5
        extent_val = [extent_min_x, extent_max_x, self.history_depth - 0.5, -0.5]
        
        # Handle case where history_data might be empty after roll if initialized empty
        if self.history_data.size == 0:
            logger.warning(f"Waterfall history data became empty during update for {band}.")
            self.axes.text(0.5, 0.5, f"No history data for {band}", ha='center', va='center', color=LIGHT_TEXT)
            self._configure_style()
            self.draw()
            self.draw_complete.emit()
            return
            
        self.im = self.axes.imshow(
            self.history_data, 
            aspect='auto',
            cmap='viridis',
            interpolation='nearest', # Use 'nearest' for clearer blocks
            extent=extent_val,
            vmin=-90,
            vmax=-30
        )
        
        # Add/Update colorbar
        try:
            if self.colorbar is None:
                 # Check if self.im was successfully created
                 if self.im:
                      self.colorbar = self.fig.colorbar(self.im, ax=self.axes)
                 else:
                      logger.warning("imshow object (self.im) not created, cannot add colorbar.")
            elif self.im: # Check if self.im exists before updating
                 self.colorbar.update_normal(self.im)
            
            if self.colorbar: # Check if colorbar exists before configuring
                 self.colorbar.set_label('Signal Strength (dBm)', color=LIGHT_TEXT)
                 self.colorbar.ax.yaxis.set_tick_params(color=LIGHT_TEXT)
                 plt.setp(self.colorbar.ax.get_yticklabels(), color=LIGHT_TEXT)
        except Exception as cbar_err:
             logger.error(f"Error handling colorbar: {cbar_err}", exc_info=True)
            
        # Set labels and title
        self.axes.set_xlabel('Channel', fontsize=10, fontweight='bold')
        self.axes.set_ylabel('Time (newest at top)', fontsize=10, fontweight='bold')
        self.axes.set_title(f'Signal Strength History ({band})', fontsize=12, fontweight='bold')
        
        # Set x-axis to show all integer channel numbers for the band
        self.axes.set_xticks(all_channels)
        # Optionally rotate labels if too crowded
        if band == '5GHz' and len(all_channels) > 15:
             self.axes.tick_params(axis='x', labelrotation=45, labelsize=8)
        else:
             self.axes.tick_params(axis='x', labelrotation=0, labelsize=9)

        # Configure y-axis ticks
        # Ensure history_depth is used correctly
        if self.history_depth > 0:
            self.axes.set_yticks(np.arange(self.history_depth))
            self.axes.set_yticklabels([f"{i} scans ago" if i > 0 else "Current" 
                                     for i in range(self.history_depth)])
        else:
             self.axes.set_yticks([]) # No ticks if depth is 0
             
        # Configure style for dark theme
        self._configure_style()
        
        # Apply tight layout before drawing
        try:
            self.fig.tight_layout()
        except ValueError as layout_error:
            logger.warning(f"Tight layout failed in Waterfall: {layout_error}")
            
        # Update canvas
        self.draw()
        self.draw_complete.emit()


class NetworkGraphCanvas(FigureCanvas):
    """
    Canvas for rendering network relationship graphs using NetworkX.
    Shows relationships between networks, access points, and channels.
    """
    
    # Signal emitted when drawing is complete
    draw_complete = pyqtSignal()
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        """Initialize the network graph canvas."""
        self.fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        self.fig.patch.set_facecolor(DARK_BG)
        self.axes = self.fig.add_subplot(111)
        self.axes.set_facecolor("#404040")
        
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
        
    def update_network_graph(self, networks: List[WiFiNetwork], band='2.4GHz', layout_type='concentric'):
        """Update the network graph with new data."""
        # --- REVISED LOGIC FOR BAND FILTERING AND NODE CREATION ---
        logger.debug(f"[NetworkGraph] Updating for band '{band}' with {len(networks)} total networks.")
        try:
            self.G = nx.Graph()
            self.current_band = band # Store current band
            
            channels_in_band = set()
            networks_added_to_graph = set() # Keep track of SSIDs added
            bssid_nodes_added = set() # Keep track of BSSIDs added

            # --- First pass: Add nodes and network-to-channel edges ---
            for network in networks:
                ssid = network.ssid if network.ssid else "<Hidden Network>"
                network_node_added = False
                if not network.bssids:
                    continue

                primary_signal = -100 # Use strongest signal for network node color
                primary_channel = None
                bssids_in_band = []

                # Check BSSIDs for the target band
                for bssid in network.bssids:
                    if bssid.band and bssid.band.startswith(band[:3]): # Match '2.4' or '5'
                        bssids_in_band.append(bssid)
                        if bssid.signal_dbm > primary_signal:
                            primary_signal = bssid.signal_dbm
                        if bssid.channel:
                             channels_in_band.add(bssid.channel)
                             primary_channel = bssid.channel # Use one channel for positioning

                # If any BSSIDs were in the band, add the network node
                if bssids_in_band:
                    if ssid not in networks_added_to_graph:
                         self.G.add_node(ssid, type='network', signal=primary_signal)
                         networks_added_to_graph.add(ssid)
                         network_node_added = True

                    # Connect network to its primary channel (if found)
                    if primary_channel and network_node_added:
                        ch_node_id = f"CH {primary_channel}"
                        if not self.G.has_node(ch_node_id):
                            self.G.add_node(ch_node_id, type='channel', weight=1) # Initial weight
                        else:
                            # Increment weight if channel node exists
                            self.G.nodes[ch_node_id]['weight'] = self.G.nodes[ch_node_id].get('weight', 0) + 1
                        
                        # Add edge network <-> channel
                        weight = max(0.1, min(1.0, (primary_signal + 90) / 60))
                        self.G.add_edge(ssid, ch_node_id, weight=weight*3)

                    # Add BSSID nodes and connect them to the network node
                    for bssid in bssids_in_band:
                        if bssid.bssid not in bssid_nodes_added:
                             self.G.add_node(bssid.bssid, type='bssid', signal=bssid.signal_dbm)
                             bssid_nodes_added.add(bssid.bssid)
                        # Always add edge from network to its BSSIDs in band
                        self.G.add_edge(ssid, bssid.bssid, weight=1) 
            
            logger.debug(f"[NetworkGraph] Added {len(networks_added_to_graph)} networks, {len(channels_in_band)} channels, {len(bssid_nodes_added)} BSSIDs for band {band}")

            if len(networks_added_to_graph) == 0:
                self.axes.clear()
                self.axes.text(0.5, 0.5, f"No networks found in {band} band", 
                             ha='center', va='center', color=LIGHT_TEXT, fontsize=14)
                self._configure_style() # Apply style even when empty
                self.axes.set_axis_off()
                self.draw()
                self.draw_complete.emit()
                return
                
            # Calculate layout based on type
            if layout_type == 'radial':
                self.pos = self._calculate_radial_layout()
            else:
                self._calculate_layout(layout_type)
            
            # Draw the graph
            self.axes.clear()
            # --- SET BG and hide spines before drawing ---
            self.axes.set_facecolor("#404040")
            self.axes.spines['top'].set_visible(False)
            self.axes.spines['right'].set_visible(False)
            self.axes.spines['bottom'].set_visible(False)
            self.axes.spines['left'].set_visible(False)
            self.axes.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False) # Hide ticks too

            self._draw_graph()
            self.draw()
            self.draw_complete.emit()
            
            # Store networks for layout changes
            self.last_networks = networks
            
        except Exception as e:
            logger.error(f"Error updating network graph: {e}")
            # Clear the graph on error
            self.G = nx.Graph()
            self.pos = {}
            self.axes.clear()
            self.axes.text(0.5, 0.5, "Error loading graph data", 
                          ha='center', va='center', color=LIGHT_TEXT)
            self.draw()
            self.draw_complete.emit()
        
    def _calculate_layout(self, layout_type='radial'):
        """Calculate node positions for the graph."""
        if len(self.G.nodes) == 0:
            self.pos = {}
            return
        
        # Get nodes by type 
        channel_nodes = [n for n, d in self.G.nodes(data=True) if d.get('type') == 'channel']
        network_nodes = [n for n, d in self.G.nodes(data=True) if d.get('type') == 'network']
        bssid_nodes = [n for n, d in self.G.nodes(data=True) if d.get('type') == 'bssid']
        
        if layout_type == 'circular':
            # Circular layout - channels on outside, networks in middle, BSSIDs in center
            self.pos = nx.circular_layout(self.G)
        elif layout_type == 'radial':
            # New radial layout that better shows channel weights
            self.pos = self._calculate_radial_layout()
        elif layout_type == 'concentric':
            # Concentric layout - channels in outer ring, networks in middle, BSSIDs in center
            node_groups = [channel_nodes, network_nodes, bssid_nodes]
            self.pos = nx.shell_layout(self.G, nlist=node_groups)
        elif layout_type == 'spectral':
            # Spectral layout - shows natural clustering
            self.pos = nx.spectral_layout(self.G)
        else:  # 'force_directed' or default
            # Spring layout with weighted edges
            self.pos = nx.spring_layout(self.G, k=0.15, iterations=50)
    
    def _calculate_radial_layout(self):
        """Calculate a radial layout that shows channel weights more clearly."""
        channel_nodes = [n for n, d in self.G.nodes(data=True) if d.get('type') == 'channel']
        network_nodes = [n for n, d in self.G.nodes(data=True) if d.get('type') == 'network']
        bssid_nodes = [n for n, d in self.G.nodes(data=True) if d.get('type') == 'bssid']
        
        pos = {}
        
        # Calculate positions for channel nodes in outer circle
        num_channels = len(channel_nodes)
        if num_channels > 0:
            for i, node in enumerate(sorted(channel_nodes)):
                angle = 2 * np.pi * i / num_channels
                # Larger radius for the outer circle
                pos[node] = np.array([1.5 * np.cos(angle), 1.5 * np.sin(angle)])
        
        # Calculate positions for network nodes - arrange based on their channel
        network_channel = {}
        for network in network_nodes:
            # Find connected channel
            connected_channels = []
            for channel in channel_nodes:
                if self.G.has_edge(network, channel):
                    connected_channels.append(channel)
            
            if connected_channels:
                # Use first connected channel as primary
                network_channel[network] = connected_channels[0]
            else:
                # Place in center if no channel connection
                network_channel[network] = None
        
        # Group networks by channel
        channel_networks = {}
        for network, channel in network_channel.items():
            if channel not in channel_networks:
                channel_networks[channel] = []
            channel_networks[channel].append(network)
        
        # Position networks around their channels
        for channel, networks in channel_networks.items():
            if channel is None:
                # Place unassigned networks in center
                num_unassigned = len(networks)
                for i, network in enumerate(networks):
                    angle = 2 * np.pi * i / max(1, num_unassigned)
                    pos[network] = np.array([0.3 * np.cos(angle), 0.3 * np.sin(angle)])
            else:
                # Get channel position
                channel_pos = pos[channel]
                channel_angle = np.arctan2(channel_pos[1], channel_pos[0])
                
                # Place networks around their channel
                num_networks = len(networks)
                radius = 0.8  # Smaller radius for the middle circle
                
                for i, network in enumerate(networks):
                    # Distribute networks around their channel
                    offset = -0.2 + 0.4 * (i / max(1, num_networks - 1))
                    network_angle = channel_angle + offset
                    pos[network] = np.array([
                        radius * np.cos(network_angle),
                        radius * np.sin(network_angle)
                    ])
        
        # Position BSSIDs near their networks
        for bssid in bssid_nodes:
            # Find connected network
            connected_networks = []
            for network in network_nodes:
                if self.G.has_edge(bssid, network):
                    connected_networks.append(network)
            
            if connected_networks:
                # Place close to the connected network
                network_pos = pos[connected_networks[0]]
                # Add a small random offset
                offset = np.random.uniform(-0.1, 0.1, 2)
                pos[bssid] = network_pos + offset
            else:
                # Place in center if no connections
                pos[bssid] = np.array([0, 0])
        
        return pos

    def _draw_graph(self):
        """Draw the network graph with improved visuals."""
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
        
        # Calculate sizes for channel nodes based on the number of networks
        channel_sizes = []
        for node in channel_nodes:
            weight = self.G.nodes[node].get('weight', 1)
            # Size increases with number of networks
            channel_sizes.append(250 + weight * 200)
        
        # Calculate colors for network nodes based on signal strength
        network_colors = []
        for node in network_nodes:
            signal = self.G.nodes[node].get('signal', -75)
            # Red for weak signals, green for strong
            if signal >= -65:
                network_colors.append('#4CAF50')  # Strong - green
            elif signal >= -75:
                network_colors.append('#FFC107')  # Medium - yellow/amber
            else:
                network_colors.append('#F44336')  # Weak - red
        
        # Draw channel nodes - size varies by network count
        nx.draw_networkx_nodes(
            self.G, self.pos, nodelist=channel_nodes,
            node_color='#5294E2', node_size=channel_sizes, alpha=0.85,
            edgecolors='white', linewidths=1.5,
            ax=self.axes
        )
        
        # Draw network nodes - color varies by signal strength
        nx.draw_networkx_nodes(
            self.G, self.pos, nodelist=network_nodes,
            node_color=network_colors, node_size=200, alpha=0.8,
            edgecolors='white', linewidths=1,
            ax=self.axes
        )
        
        # Draw BSSID nodes
        nx.draw_networkx_nodes(
            self.G, self.pos, nodelist=bssid_nodes,
            node_color='#AB47BC', node_size=100, alpha=0.65,
            edgecolors='white', linewidths=0.5,
            ax=self.axes
        )
        
        # Draw edges - network to channel (weighted by signal strength)
        edge_widths = [self.G[u][v].get('weight', 1) * 1.5 for u, v in network_to_channel]
        
        nx.draw_networkx_edges(
            self.G, self.pos, edgelist=network_to_channel,
            width=edge_widths, alpha=0.8, edge_color='#FFFFFF',
            ax=self.axes
        )
        
        # Draw edges - network to BSSID
        nx.draw_networkx_edges(
            self.G, self.pos, edgelist=network_to_bssid,
            width=0.8, alpha=0.5, edge_color='#AAAAAA',
            style='dashed',
            ax=self.axes
        )
        
        # Draw labels with customized appearance
        ch_labels = {n: n for n in channel_nodes}
        
        # For networks, truncate to max 10 chars + ...
        net_labels = {}
        for n in network_nodes:
            if len(n) > 10:
                net_labels[n] = n[:10] + "..."
            else:
                net_labels[n] = n
        
        # BSSID - only last 5 chars
        bssid_labels = {n: n[-5:] for n in bssid_nodes}
        
        # Draw channel labels with larger font
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
        
        # Don't draw BSSID labels (too cluttered)
        # Only uncomment if you really want them:
        # nx.draw_networkx_labels(
        #     self.G, self.pos, labels=bssid_labels,
        #     font_size=6, font_color='white',
        #     ax=self.axes
        # )
        
        # Add a legend
        from matplotlib.lines import Line2D
        from matplotlib.patches import Patch
        
        legend_elements = [
            Patch(facecolor='#5294E2', edgecolor='w', label='Channels'),
            Patch(facecolor='#4CAF50', edgecolor='w', label='Strong Signal'),
            Patch(facecolor='#FFC107', edgecolor='w', label='Medium Signal'),
            Patch(facecolor='#F44336', edgecolor='w', label='Weak Signal'),
            Patch(facecolor='#AB47BC', edgecolor='w', label='Access Points')
        ]
        
        self.axes.legend(handles=legend_elements, loc='upper right', 
                        fontsize=8, framealpha=0.7, facecolor='#333333')
        
        # Set title and adjust display
        band_text = "2.4GHz" if hasattr(self, 'current_band') and self.current_band == '2.4GHz' else "5GHz"
        self.axes.set_title(f"WiFi Network Topology ({band_text} Band)", 
                           fontsize=12, fontweight='bold', color=LIGHT_TEXT)
        self.axes.set_axis_off()


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
        
        # Graph layout selector
        layout_label = QLabel("Layout:")
        controls_layout.addWidget(layout_label)

        self.layout_selector = QComboBox()
        self.layout_selector.addItems(['Radial', 'Concentric', 'Circular', 'Spectral', 'Force-Directed'])
        self.layout_selector.setCurrentText('Radial')  # Default to radial layout
        self.layout_selector.currentTextChanged.connect(self._on_layout_changed)
        controls_layout.addWidget(self.layout_selector)
        
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
        
        # --- ADDED: Connect tab change signal ---
        self.tab_widget.currentChanged.connect(self._handle_tab_change)
        
        # Initialize graphs
        self._update_graphs([])
        
    def _on_band_changed(self, band: str) -> None:
        """Handle band selection change."""
        self.current_band = band
        self._request_refresh()
        
    def _on_layout_changed(self, layout: str) -> None:
        """Handle layout style change."""
        # Convert friendly name to layout type
        layout_map = {
            'Radial': 'radial',
            'Concentric': 'concentric',
            'Circular': 'circular',
            'Spectral': 'spectral',
            'Force-Directed': 'force_directed'
        }
        layout_type = layout_map.get(layout, 'radial')
        
        # Store the layout preference
        self.current_layout = layout_type
        
        # Update the network graph with the current networks and new layout
        if hasattr(self, 'last_networks'):
            self.network_canvas.update_network_graph(self.last_networks, self.current_band, layout_type)
            # --- EMIT SIGNAL after redraw ---
            self.network_canvas.draw_complete.emit()
        
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
        # --- UPDATED DEBUG PREFIX ---
        print(f"DEBUG [GraphWidget]: _update_graphs called with {len(networks)} networks for band {self.current_band}")
        try:
            # Analyze networks first
            self.channel_analyzer.analyze_channel_usage(networks)
            
            # Get visualization data
            visualization_data = self.channel_analyzer.get_visualization_data()
            # --- UPDATED DEBUG PREFIX ---
            print(f"DEBUG [GraphWidget]: Viz data for {self.current_band}: {visualization_data.get(self.current_band)}")
            logger.debug(f"Visualization data for {self.current_band}: {visualization_data.get(self.current_band)}")
            
            # Update channel usage graph
            if self.current_band in visualization_data:
                self.channel_canvas.update_graph(visualization_data, self.current_band)
            
            # Update waterfall graph with signal strength data
            if self.current_band in visualization_data:
                data = visualization_data[self.current_band]
                # Make sure data dictionary is not empty
                if data:
                     self.waterfall_canvas.update_waterfall(
                         data.get('signal_strengths', []),
                         data.get('channels', []),
                         self.current_band # Pass the band
                     )
                else:
                     # Handle case where band exists but data is empty
                     self.waterfall_canvas.update_waterfall([], [], self.current_band)
            else:
                 # Handle case where band key doesn't exist
                 self.waterfall_canvas.update_waterfall([], [], self.current_band)

            # Update network relationship graph
            # Ensure layout type is passed correctly
            current_layout = getattr(self, 'current_layout', 'radial') # Default to radial if not set
            self.network_canvas.update_network_graph(networks, self.current_band, current_layout)
            
            # Store networks for layout changes
            self.last_networks = networks
            
        except Exception as e:
            logger.error(f"Error updating graphs: {e}")
            raise

    # --- ADDED: Slot for tab changes ---
    def _handle_tab_change(self, index: int) -> None:
        """Handles tab switching to force graph updates if necessary."""
        widget = self.tab_widget.widget(index)
        logger.debug(f"[GraphWidget] Tab changed to index {index} ({type(widget).__name__})")
        
        # Force redraw Network Graph when selected to fix potential overlap/styling issues
        if isinstance(widget, NetworkGraphCanvas):
            logger.debug("[GraphWidget] Network Graph tab selected, forcing redraw.")
            # Use last known data and layout
            networks = getattr(self, 'last_networks', [])
            layout = getattr(self, 'current_layout', 'radial')
            self.network_canvas.update_network_graph(networks, self.current_band, layout)
            # --- EMIT SIGNAL after redraw ---
            self.network_canvas.draw_complete.emit()
        
        # Attempt to fix hover annotation issue by redrawing Channel Graph
        elif isinstance(widget, ChannelGraphCanvas):
            logger.debug("[GraphWidget] Channel Usage tab selected, forcing redraw to potentially fix hover.")
            self.channel_canvas.draw_idle() 
            # --- EMIT SIGNAL after redraw ---
            self.channel_canvas.draw_complete.emit()
            # Re-enable hover annotation just in case it got stuck invisible
            if self.channel_canvas.hover_annotation:
                 self.channel_canvas.hover_annotation.set_visible(False) # Hide first
