"""
Qt Compatibility Module

This module provides compatibility functions and constants for PyQt6 to handle
differences between PyQt5 and PyQt6 API.
"""

import sys
import importlib
from PyQt6.QtCore import Qt, QModelIndex
from PyQt6.QtWidgets import QStyleOptionViewItem, QStyle

# Determine which PyQt version is being used
qt_version = 6  # Default to PyQt6
try:
    from PyQt6 import QtCore
except ImportError:
    try:
        from PyQt5 import QtCore
        qt_version = 5
    except ImportError:
        raise ImportError("Neither PyQt5 nor PyQt6 found. Please install one of them.")

def get_qt_module(name):
    """
    Dynamically import and return a Qt module based on the detected version.
    
    Args:
        name: The module name (without PyQt prefix)
        
    Returns:
        The imported module
    """
    module_name = f"PyQt{qt_version}.{name}"
    return importlib.import_module(module_name)

# Qt 6 renamed many enum values
# Mapping function for State flags
def get_state_flag(flag_name):
    """
    Get the correct enum flag for QStyleOptionViewItem.State based on flag name.
    
    Args:
        flag_name: Name of the flag (e.g., 'Selected', 'Enabled', etc.)
        
    Returns:
        The correct QStyleOptionViewItem.StateFlag enum value
    """
    try:
        return getattr(QStyleOptionViewItem.StyleOptionType, flag_name)
    except AttributeError:
        try:
            return getattr(QStyleOptionViewItem.StateFlag, flag_name)
        except AttributeError:
            # Fallback for different Qt6 versions
            return getattr(QStyle.StateFlag, flag_name)

# Selected state flags for convenience
STATE_SELECTED = get_state_flag('Selected')
STATE_ENABLED = get_state_flag('Enabled')
STATE_FOCUS = get_state_flag('HasFocus')

# Item roles
def get_item_role(role_name):
    """Get the correct enum value for Qt.ItemDataRole based on role name."""
    try:
        return getattr(Qt.ItemDataRole, role_name)
    except AttributeError:
        # Fallback for different Qt6 versions
        return getattr(Qt, role_name)

# Common item roles for convenience
DISPLAY_ROLE = get_item_role('DisplayRole')
EDIT_ROLE = get_item_role('EditRole')
DECORATION_ROLE = get_item_role('DecorationRole')
BACKGROUND_ROLE = get_item_role('BackgroundRole')
FOREGROUND_ROLE = get_item_role('ForegroundRole')
TOOLTIP_ROLE = get_item_role('ToolTipRole')
TEXT_ALIGNMENT_ROLE = get_item_role('TextAlignmentRole')

# Sort orders
ASCENDING_ORDER = Qt.SortOrder.AscendingOrder
DESCENDING_ORDER = Qt.SortOrder.DescendingOrder

# Orientations
HORIZONTAL = Qt.Orientation.Horizontal
VERTICAL = Qt.Orientation.Vertical

# Text alignment
ALIGN_LEFT = Qt.AlignmentFlag.AlignLeft
ALIGN_RIGHT = Qt.AlignmentFlag.AlignRight
ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
ALIGN_VCENTER = Qt.AlignmentFlag.AlignVCenter
ALIGN_HCENTER = Qt.AlignmentFlag.AlignHCenter

# Other constants
def get_primitive_element(element_name):
    """Get the correct enum value for QStyle.PrimitiveElement based on name."""
    try:
        return getattr(QStyle.PrimitiveElement, element_name)
    except AttributeError:
        # Fallback for different Qt6 versions
        return getattr(QStyle, element_name)

PE_PANEL_ITEM_VIEW_ITEM = get_primitive_element('PE_PanelItemViewItem')

# Common helper functions for version differences
def get_selected_state_flag():
    """Get the appropriate selected state flag for the current PyQt version."""
    if qt_version == 6:
        return STATE_SELECTED
    else:
        return QStyle.State_Selected

def is_selected(option):
    """
    Check if an item is selected, compatible with both PyQt5 and PyQt6.
    
    Args:
        option: The QStyleOptionViewItem
        
    Returns:
        bool: True if the item is selected, False otherwise
    """
    selected_flag = get_selected_state_flag()
    return bool(option.state & selected_flag)

def get_matplotlib_backend():
    """Get the appropriate matplotlib backend name for the current PyQt version."""
    return f"Qt{qt_version}Agg"

def setup_matplotlib():
    """Configure matplotlib to use the appropriate Qt backend."""
    import matplotlib
    backend = get_matplotlib_backend()
    matplotlib.use(backend)