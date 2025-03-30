"""
Network Table Module

This module provides a table view for displaying WiFi networks with sorting,
filtering, theme support, and modernized signal strength visualization.
"""

import logging
from typing import List, Optional, Dict, Any
from PyQt6.QtWidgets import (
    QTableView, QHeaderView, QMenu, QWidget, QAbstractItemView,
    QStyledItemDelegate, QStyleOptionViewItem, QStyle
)
from PyQt6.QtCore import Qt
from PyQt6.QtCore import (
    Qt, QSortFilterProxyModel, QModelIndex, pyqtSignal,
    QAbstractTableModel, QRect, QPoint
)
from PyQt6.QtGui import (
    QColor, QPalette, QAction, QContextMenuEvent, QPainter, QBrush, QPen
)

# ----- Dummy WiFiNetwork class for demonstration -----
# Replace this with your actual import: from scanner.models import WiFiNetwork
class WiFiNetwork:
    def __init__(self, ssid, bssid, signal, channel, band, security):
        self.ssid = ssid
        self.bssid = bssid
        self.signal_dbm = signal
        self.channel = channel
        self.band = band
        self.security_type = security
# ---------------------------------------------------

# ----- Dummy Theme Manager for demonstration -----
# Replace this with your actual import:
# from gui.theme_manager import (
#     ThemeObserver, ThemeUpdateEvent, register_theme_observer,
#     get_color, get_current_theme
# )
# Example theme data (replace with your actual theme structure)
THEMES_DATA = {
    'light': {
        'signalStrong': '#00A000', 'signalMedium': '#E0E000', 'signalWeak': '#FFA500',
        'signalVeryWeak': '#D00000', 'iconInactive': '#D3D3D3',
        'window': '#FFFFFF', 'base': '#FFFFFF', 'text': '#000000',
        'highlight': '#3399FF', 'highlightedText': '#FFFFFF',
        # Add other theme colors here
    },
    'dark': {
        'signalStrong': '#00FF00', 'signalMedium': '#FFFF00', 'signalWeak': '#FFA500',
        'signalVeryWeak': '#FF4040', 'iconInactive': '#505050',
        'window': '#2E2E2E', 'base': '#1E1E1E', 'text': '#E0E0E0',
        'highlight': '#4A4A7A', 'highlightedText': '#FFFFFF',
         # Add other theme colors here
    }
}
_current_theme = 'light'
_observers = []

class ThemeUpdateEvent:
    def __init__(self, theme_name):
        self.theme_name = theme_name

class ThemeObserver:
    def on_theme_changed(self, event: ThemeUpdateEvent) -> None:
        raise NotImplementedError

def get_color(key: str, default: str = '#FF00FF') -> str: # Added default magenta for missing keys
    return THEMES_DATA.get(_current_theme, {}).get(key, default)

def get_current_theme() -> str:
    return _current_theme

def register_theme_observer(observer: ThemeObserver):
    if observer not in _observers:
        _observers.append(observer)

def set_theme(theme_name: str): # Added function to change theme for demo
    global _current_theme
    if theme_name in THEMES_DATA:
        _current_theme = theme_name
        event = ThemeUpdateEvent(theme_name)
        for observer in _observers:
            try:
                observer.on_theme_changed(event)
            except Exception as e:
                logger.error(f"Error notifying observer {observer}: {e}")
# ---------------------------------------------------


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Basic logging for demo


# ==================================================
# == MODIFIED SignalStrengthDelegate (Modernized) ==
# ==================================================
class SignalStrengthDelegate(QStyledItemDelegate):
    """
    Custom delegate for rendering signal strength as modern WiFi bars.
    """
    NUM_BARS = 4 # Number of bars to draw for the icon

    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex) -> None:
        """Paint the signal strength cell with WiFi bar icons."""
        try:
            # --- Basic Setup ---
            painter.save()

            # Background and Base Colors
            is_selected = option.state & QStyle.StateFlag.State_Selected
            if is_selected:
                bg_brush = option.palette.highlight()
                text_pen_color = option.palette.highlightedText().color()
                 # Use text color for inactive bars when selected for contrast
                base_icon_color = text_pen_color
            else:
                bg_brush = option.palette.base()
                text_pen_color = option.palette.text().color()
                # Use a subtle color for inactive bars from theme or fallback
                try:
                    base_icon_color = QColor(get_color('iconInactive', '#cccccc'))
                except KeyError:
                    base_icon_color = QColor('#cccccc') # Fallback gray

            painter.fillRect(option.rect, bg_brush)


            # --- Get Data ---
            signal_dbm_data = index.data(Qt.ItemDataRole.DisplayRole)
            is_int = isinstance(signal_dbm_data, int)
            signal_dbm = signal_dbm_data if is_int else None


            # --- Determine Active Bars and Color ---
            active_bars = 0
            # Default to inactive color, override if signal is valid
            active_color = base_icon_color

            if signal_dbm is not None:
                # Strong signal: All bars, strong color
                if signal_dbm >= -55:
                    active_bars = 4
                    active_color = QColor(get_color('signalStrong', '#00A000'))
                # Medium signal: 3 bars, medium color
                elif signal_dbm >= -65:
                    active_bars = 3
                    active_color = QColor(get_color('signalMedium', '#E0E000'))
                # Weak signal: 2 bars, weak color
                elif signal_dbm >= -75:
                    active_bars = 2
                    active_color = QColor(get_color('signalWeak', '#FFA500'))
                # Very weak signal: 1 bar, very weak color
                else: # <= -75
                    active_bars = 1
                    active_color = QColor(get_color('signalVeryWeak', '#D00000'))
            else:
                 # Handle non-integer/missing data gracefully
                 display_text = str(signal_dbm_data) # Show original data if not int


            # --- Draw WiFi Bars ---
            total_icon_width = 18 # Total width allocated for bars icon area
            bar_spacing = 1
            max_bar_height = option.rect.height() * 0.6 # Max height relative to cell
            min_bar_height = max_bar_height * 0.4 # Min height relative to cell
            height_step = (max_bar_height - min_bar_height) / (self.NUM_BARS - 1) if self.NUM_BARS > 1 else 0
            # Calculate bar width based on total width and spacing
            bar_width = (total_icon_width - (self.NUM_BARS - 1) * bar_spacing) / self.NUM_BARS

            start_x = option.rect.x() + 4 # Small padding from left edge
            center_y = option.rect.center().y()

            painter.setPen(Qt.PenStyle.NoPen) # No outline for bars

            for i in range(self.NUM_BARS):
                bar_height = min_bar_height + i * height_step
                bar_y = center_y - bar_height / 2.0 # Use float division for centering
                bar_rect = QRect(int(start_x + i * (bar_width + bar_spacing)),
                                 int(bar_y),
                                 int(bar_width),
                                 int(bar_height))

                # Set color based on whether the bar is active
                if i < active_bars:
                    painter.setBrush(QBrush(active_color))
                else:
                    painter.setBrush(QBrush(base_icon_color)) # Inactive bars color

                painter.drawRect(bar_rect)


            # --- Draw Text (dBm value or original data) ---
            # Adjust text position to be after the icon area
            text_start_x = start_x + total_icon_width + 6
            text_rect = option.rect.adjusted(int(text_start_x), 0, -2, 0)

            if signal_dbm is not None:
                 display_text = f"{signal_dbm} dBm"
            # else: display_text is already set above

            painter.setPen(text_pen_color) # Use determined text color
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                display_text
            )

            painter.restore()

        except Exception as e:
            logger.error(f"Error painting signal strength: {e}", exc_info=True)
            # Fallback to default painting if error occurs
            painter.restore() # Ensure painter state is restored on error too
            super().paint(painter, option, index) # Call base class paint

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QRect:
        # Provide a hint that accommodates the icon and text comfortably
        hint = super().sizeHint(option, index)
        # Ensure minimum width for icon + text + padding
        hint.setWidth(max(hint.width(), 70)) # Adjust 70 as needed
        return hint

# ==================================================
# ==         NetworkTableModel (Unchanged)        ==
# ==================================================
class NetworkTableModel(QAbstractTableModel):
    """Model for storing and managing network data."""

    COLUMNS = ['SSID', 'BSSID', 'Signal', 'Channel', 'Band', 'Security']

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize network table model."""
        super().__init__(parent)
        self.networks: List[WiFiNetwork] = []

    def tooltip(self, row: int, column: int) -> str:
        """Generate tooltip text for a cell."""
        if row < 0 or row >= len(self.networks):
            return ""

        try:
            network = self.networks[row]
            column_name = self.COLUMNS[column]

            if column_name == 'Signal' and isinstance(network.signal_dbm, int):
                signal = network.signal_dbm
                quality = "Excellent" if signal >= -55 else \
                          "Good" if signal >= -65 else \
                          "Fair" if signal >= -75 else \
                          "Poor"
                return f"Signal Strength: {signal} dBm\nQuality: {quality}"
            elif column_name == 'Security':
                 return f"Security: {network.security_type}" # Example tooltip for Security
            elif column_name == 'SSID':
                 return f"Network Name: {network.ssid if network.ssid else '<Hidden>'}"
            elif column_name == 'BSSID':
                 return f"MAC Address: {network.bssid}"
        except IndexError:
             return ""
        except Exception as e:
            logger.warning(f"Error generating tooltip for [{row},{column}]: {e}")
            return ""

        return "" # Default empty tooltip

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of rows in the model."""
        return len(self.networks)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return number of columns in the model."""
        return len(self.COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation,
                     role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return header data for the model."""
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
             if 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section]
        # Add Tooltip Role for header
        if role == Qt.ItemDataRole.ToolTipRole and orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self.COLUMNS):
                col_name = self.COLUMNS[section]
                # Add helpful tooltips for headers
                if col_name == 'SSID': return "Service Set Identifier (Network Name)"
                if col_name == 'BSSID': return "Basic Service Set Identifier (Access Point MAC Address)"
                if col_name == 'Signal': return "Signal strength in dBm (higher is better)"
                if col_name == 'Channel': return "WiFi Channel Number"
                if col_name == 'Band': return "Frequency Band (e.g., 2.4GHz, 5GHz)"
                if col_name == 'Security': return "Wireless Security Protocol"
                return col_name # Default tooltip is the column name
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return data for the given index and role."""
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row < 0 or row >= len(self.networks):
            return None

        network = self.networks[row]

        # --- Display and Edit Roles ---
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if 0 <= col < len(self.COLUMNS):
                column_name = self.COLUMNS[col]
                if column_name == 'SSID':
                    return network.ssid if network.ssid else '<Hidden Network>'
                elif column_name == 'BSSID':
                    return network.bssid
                elif column_name == 'Signal':
                    # Return the raw value, delegate handles display
                    return network.signal_dbm
                elif column_name == 'Channel':
                    return network.channel
                elif column_name == 'Band':
                    return network.band
                elif column_name == 'Security':
                    return network.security_type
            return None # Should not happen if col is valid

        # --- Tooltip Role ---
        elif role == Qt.ItemDataRole.ToolTipRole:
            # Reuse the tooltip logic defined earlier
            return self.tooltip(row, col)

        # --- Text Alignment Role ---
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            # Center signal, channel maybe? Left align others.
            column_name = self.COLUMNS[col]
            if column_name in ['Signal', 'Channel']:
                 return Qt.AlignmentFlag.AlignCenter
            else:
                 return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft


        # --- Sorting Role (Important!) ---
        # Ensure numerical columns sort numerically, not alphabetically
        elif role == Qt.ItemDataRole.UserRole: # Often used for sorting data types
            column_name = self.COLUMNS[col]
            if column_name == 'Signal':
                # Return integer or a very small number if not an int to sort correctly
                return network.signal_dbm if isinstance(network.signal_dbm, int) else -999
            elif column_name == 'Channel':
                return network.channel if isinstance(network.channel, int) else 0
            # For other columns, returning the display data is usually fine for sorting
            # You might need specific handling for Band or Security if complex sorting is needed
            return self.data(index, Qt.ItemDataRole.DisplayRole)


        return None # Default case

    def update_networks(self, networks: List[WiFiNetwork]) -> None:
        """Update the model with new network data."""
        logger.debug(f"Updating model with {len(networks)} networks.")
        self.beginResetModel()
        self.networks = sorted(networks, key=lambda x: x.signal_dbm if isinstance(x.signal_dbm, int) else -999, reverse=True) # Pre-sort by signal
        self.endResetModel()

# ==================================================
# ==  NetworkFilterProxyModel (Minor Improvement) ==
# ==================================================
class NetworkFilterProxyModel(QSortFilterProxyModel):
    """Proxy model for filtering and sorting networks."""

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize network filter proxy model."""
        super().__init__(parent)
        self.band_filter: Optional[str] = None
        self._source_model: Optional[NetworkTableModel] = None # Cache source model
         # Set dynamicSortFilter to True to re-apply filter when data changes
        self.setDynamicSortFilter(True)
         # Use UserRole for numerical sorting if defined in source model
        self.setSortRole(Qt.ItemDataRole.UserRole)

    def setSourceModel(self, sourceModel: Optional[QAbstractTableModel]) -> None:
        """Override setSourceModel to cache the specific type."""
        super().setSourceModel(sourceModel)
        if isinstance(sourceModel, NetworkTableModel):
            self._source_model = sourceModel
        else:
            self._source_model = None
            logger.warning("Source model is not a NetworkTableModel!")

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Determine if row should be included in filtered results."""
        if self._source_model is None:
            return False # Should not happen if set up correctly

        # Band Filter Logic
        band_filter_accepts = True
        if self.band_filter:
            band_index = self._source_model.index(source_row,
                                                  self._source_model.COLUMNS.index('Band'),
                                                  source_parent)
            band_data = self._source_model.data(band_index, Qt.ItemDataRole.DisplayRole)
            band_filter_accepts = (band_data == self.band_filter)

        # Add other filters here if needed (e.g., text search)
        # text_filter = self.filterRegularExpression() # Example for text filter
        # text_filter_accepts = True
        # if text_filter.isValid():
        #     ssid_index = self._source_model.index(source_row, self._source_model.COLUMNS.index('SSID'), source_parent)
        #     ssid_data = self._source_model.data(ssid_index, Qt.ItemDataRole.DisplayRole)
        #     text_filter_accepts = text_filter.match(ssid_data).hasMatch()

        # Combine filter results
        return band_filter_accepts # and text_filter_accepts

    def set_band_filter(self, band: Optional[str]) -> None:
        """Set band filter for the model (e.g., '2.4GHz', '5GHz', None for all)."""
        logger.debug(f"Setting band filter to: {band}")
        if band == self.band_filter: # Avoid unnecessary invalidation
            return
        self.band_filter = band
        self.invalidateFilter() # Re-apply the filter


# ==================================================
# ==   NetworkTableView (Minor Improvements)      ==
# ==================================================
class NetworkTableView(QTableView, ThemeObserver):
    """
    Table view for displaying WiFi networks.

    Supports:
    - Sorting by columns (numerical for Signal/Channel)
    - Filtering by band
    - Theme-aware rendering with modern signal bars
    - Context menu actions
    - Tooltips for data cells and headers
    """

    network_selected = pyqtSignal(WiFiNetwork) # Emits WiFiNetwork object

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize network table view."""
        super().__init__(parent)

        # Set up model
        self.model = NetworkTableModel(self)
        self.proxy_model = NetworkFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        self.setModel(self.proxy_model)

        # Configure view
        self.setup_ui()

        # Register for theme updates AFTER setup_ui might have applied initial theme styles
        register_theme_observer(self)

        # Apply current theme explicitly after registration
        self.apply_theme(get_current_theme())


    def setup_ui(self) -> None:
        """Set up the user interface."""
        logger.debug("Setting up NetworkTableView UI")
        # Basic Appearance
        self.setAlternatingRowColors(True) # Makes rows easier to distinguish
        self.setShowGrid(False) # Cleaner look without grid lines

        # Configure selection
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setWordWrap(False) # Prevent text wrapping in cells
        self.verticalHeader().hide() # Usually not needed for this type of table

        # Configure header
        header = self.horizontalHeader()
        header.setSectionsMovable(True)
        header.setStretchLastSection(True) # Let last column fill remaining space
        # Set interactive resize initially, then maybe fixed after first data load
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # Enable clicking header to sort
        self.setSortingEnabled(True)
        # Initial sort by Signal Strength (column index from source model) descending
        signal_col_index = self.model.COLUMNS.index('Signal')
        self.sortByColumn(signal_col_index, Qt.SortOrder.DescendingOrder)

        # Set custom delegate for signal strength column (using the NEW delegate)
        # Ensure column index is correct
        try:
             signal_column_idx = self.model.COLUMNS.index('Signal')
             self.setItemDelegateForColumn(signal_column_idx, SignalStrengthDelegate(self))
             logger.info("SignalStrengthDelegate set for 'Signal' column.")
        except ValueError:
             logger.error("'Signal' column not found in model.COLUMNS. Delegate not set.")


        # Enable tooltips for the entire table view
        self.setMouseTracking(True) # Needed for some tooltip scenarios if data changes often
        self.setToolTipDuration(2000) # Show tooltips for 2 seconds


    def set_networks(self, networks: List[WiFiNetwork]) -> None:
        """Update table with new network data and adjust columns."""
        self.model.update_networks(networks)
        # Optionally resize columns to content after data is loaded
        # QTimer.singleShot(0, self.resizeColumnsToContents) # Resize after model update finishes
        # Or set fixed widths based on expected content
        self.set_column_widths()


    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Handle context menu events."""
        index_at_pos = self.indexAt(event.pos())
        if not index_at_pos.isValid():
            return

        # Get selected network via the proxy model
        source_index = self.proxy_model.mapToSource(index_at_pos)
        if not source_index.isValid() or source_index.row() >= len(self.model.networks):
            logger.warning("Context menu triggered on invalid source index.")
            return

        network = self.model.networks[source_index.row()]

        # Create context menu
        menu = QMenu(self)

        # Add actions
        details_action = QAction(f"Details for {network.ssid or network.bssid}...", self)
        details_action.triggered.connect(lambda checked=False, net=network: self.network_selected.emit(net)) # Use lambda capture
        menu.addAction(details_action)

        # Example: Add a 'Copy BSSID' action
        copy_bssid_action = QAction(f"Copy BSSID ({network.bssid})", self)
        copy_bssid_action.triggered.connect(lambda checked=False, bssid=network.bssid: self.copy_to_clipboard(bssid))
        menu.addAction(copy_bssid_action)


        menu.exec(event.globalPos())

    def copy_to_clipboard(self, text: str):
        """Helper to copy text to clipboard."""
        try:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(text)
                logger.info(f"Copied to clipboard: {text}")
            else:
                logger.warning("Could not get clipboard instance.")
        except Exception as e:
            logger.error(f"Error copying to clipboard: {e}")


    def on_theme_changed(self, event: ThemeUpdateEvent) -> None:
        """Handle theme change events."""
        logger.info(f"Theme changed to {event.theme_name}, applying to NetworkTableView.")
        try:
            self.apply_theme(event.theme_name)
        except Exception as e:
            logger.error(f"Error applying theme to network table: {e}", exc_info=True)

    def apply_theme(self, theme_name: str) -> None:
        """Apply theme colors and force redraw."""
        # Note: Standard Qt styling (QPalette) should handle most widget colors automatically
        # if the application's overall palette is set correctly by your theme manager.
        # Explicit styling here might override or duplicate that.

        # Force a style re-polish and update - this should make Qt re-evaluate palette etc.
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

        # The custom delegate needs a redraw to pick up new theme colors via get_color()
        # self.viewport().update() should be sufficient usually
        logger.debug("Updating viewport for theme change")
        self.viewport().update()

        # Update header appearance if necessary (usually handled by palette)
        header = self.horizontalHeader()
        header.style().unpolish(header)
        header.style().polish(header)
        header.update()


    def get_selected_network(self) -> Optional[WiFiNetwork]:
        """Get the currently selected network object."""
        current_index = self.currentIndex() # Get the single current index for single selection mode
        if not current_index.isValid():
            return None

        source_index = self.proxy_model.mapToSource(current_index)
        if source_index.isValid() and 0 <= source_index.row() < len(self.model.networks):
            return self.model.networks[source_index.row()]

        return None

    def set_column_widths(self) -> None:
        """Set appropriate column widths based on content or fixed values."""
        header = self.horizontalHeader()
        model = self.model # Use source model for column names

        try:
            ssid_col = model.COLUMNS.index('SSID')
            bssid_col = model.COLUMNS.index('BSSID')
            signal_col = model.COLUMNS.index('Signal')
            channel_col = model.COLUMNS.index('Channel')
            band_col = model.COLUMNS.index('Band')
            security_col = model.COLUMNS.index('Security')

            # Example widths - adjust based on typical content length!
            header.setSectionResizeMode(ssid_col, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(ssid_col, 150)

            header.setSectionResizeMode(bssid_col, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(bssid_col, 130)

            header.setSectionResizeMode(signal_col, QHeaderView.ResizeMode.Interactive) # Delegate handles size well
            header.resizeSection(signal_col, 85) # Fixed width might be better here

            header.setSectionResizeMode(channel_col, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(channel_col, 60) # Channels are usually short

            header.setSectionResizeMode(band_col, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(band_col, 60) # Bands are short

            # Let Security stretch or set interactively
            header.setSectionResizeMode(security_col, QHeaderView.ResizeMode.Stretch) # Stretch last section is on
            # header.resizeSection(security_col, 180) # Or set interactive width

        except ValueError as e:
            logger.error(f"Error finding column index for width setting: {e}")
        except Exception as e:
             logger.error(f"Error setting column widths: {e}", exc_info=True)

# ==================================================
# ==          Example Usage (for testing)         ==
# ==================================================
if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication, QVBoxLayout, QPushButton, QComboBox

    app = QApplication(sys.argv)

    # --- Create Main Widget ---
    main_widget = QWidget()
    layout = QVBoxLayout(main_widget)

    # --- Theme Selector ---
    theme_combo = QComboBox()
    theme_combo.addItems(THEMES_DATA.keys())
    theme_combo.setCurrentText(get_current_theme())
    theme_combo.currentTextChanged.connect(set_theme) # Connect to dummy theme changer
    layout.addWidget(theme_combo)

    # --- Band Filter ---
    band_filter_combo = QComboBox()
    band_filter_combo.addItems(["All Bands", "2.4GHz", "5GHz"]) # Example bands

    # --- Network Table ---
    table_view = NetworkTableView()
    layout.addWidget(table_view)

    # Connect band filter
    def on_band_filter_changed(text):
        if text == "All Bands":
            table_view.proxy_model.set_band_filter(None)
        else:
            table_view.proxy_model.set_band_filter(text)
    band_filter_combo.currentTextChanged.connect(on_band_filter_changed)
    layout.addWidget(band_filter_combo)


    # --- Dummy Data ---
    dummy_networks = [
        WiFiNetwork(ssid="HomeNetwork", bssid="AA:BB:CC:11:22:33", signal=-45, channel=6, band="2.4GHz", security="WPA2-PSK"),
        WiFiNetwork(ssid="OfficeWifi", bssid="DD:EE:FF:44:55:66", signal=-60, channel=44, band="5GHz", security="WPA3-SAE"),
        WiFiNetwork(ssid="CafeGuest", bssid="11:22:33:AA:BB:CC", signal=-72, channel=11, band="2.4GHz", security="Open"),
        WiFiNetwork(ssid="MyPhoneHotspot", bssid="44:55:66:DD:EE:FF", signal=-53, channel=149, band="5GHz", security="WPA2-PSK"),
        WiFiNetwork(ssid="NeighborsWifi", bssid="77:88:99:00:AA:BB", signal=-80, channel=1, band="2.4GHz", security="WPA/WPA2"),
        WiFiNetwork(ssid=None, bssid="CC:DD:EE:77:88:99", signal=-68, channel=36, band="5GHz", security="WPA2-PSK"), # Hidden Network
        WiFiNetwork(ssid="AnotherNetwork", bssid="EE:FF:00:11:22:AA", signal=-58, channel=1, band="2.4GHz", security="WEP"), # WEP is insecure!
        WiFiNetwork(ssid="WeakSignal", bssid="FF:00:11:22:AA:BB", signal=-88, channel=11, band="2.4GHz", security="WPA2-PSK"),
        WiFiNetwork(ssid="VeryStrong", bssid="00:11:22:AA:BB:CC", signal=-30, channel=52, band="5GHz", security="WPA3-SAE"),
    ]
    table_view.set_networks(dummy_networks)

    # --- Show Window ---
    main_widget.setWindowTitle("Network Table Test")
    main_widget.resize(700, 400)
    main_widget.show()

    # --- Signal Connection for Selection ---
    def display_selected(network):
        print("-" * 20)
        print(f"Network Selected via Signal:")
        print(f"  SSID: {network.ssid}")
        print(f"  BSSID: {network.bssid}")
        print(f"  Signal: {network.signal_dbm} dBm")
        print(f"  Band: {network.band}")
        print(f"  Security: {network.security_type}")
        print("-" * 20)

    table_view.network_selected.connect(display_selected)


    sys.exit(app.exec())
