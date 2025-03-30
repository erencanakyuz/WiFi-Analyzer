"""
Tests for the theme manager module.

Tests cover:
- Basic theme operations
- Theme observer pattern
- Color retrieval
- Error handling
"""

import unittest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

import sys
from gui.theme_manager import (
    ThemeManager, ThemeObserver, ThemeUpdateEvent, THEMES,
    apply_theme, get_color, get_current_theme, ThemeObservable
)

class TestThemeManager(unittest.TestCase):
    """Test theme system integration."""
    
    @classmethod
    def setUpClass(cls):
        """Create QApplication instance for tests."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
    
    def setUp(self):
        """Set up test environment."""
        self.manager = ThemeManager()
        self.test_widget = QWidget()
    
    def test_theme_change(self):
        """Test basic theme switching."""
        initial_theme = self.manager.get_current_theme()
        new_theme = 'dark' if initial_theme == 'light' else 'light'
        
        self.manager.apply_theme(new_theme)
        self.assertEqual(self.manager.get_current_theme(), new_theme)
    
    def test_invalid_theme(self):
        """Test handling of invalid theme names."""
        with self.assertRaises(ValueError):
            self.manager.apply_theme('nonexistent_theme')
    
    def test_theme_observer(self):
        """Test observer notification."""
        mock_observer = Mock(spec=ThemeObserver)
        ThemeObservable.register_observer(mock_observer)
        
        self.manager.apply_theme('dark')
        mock_observer.on_theme_changed.assert_called_once()
        
        # Test observer removal
        ThemeObservable.unregister_observer(mock_observer)
        mock_observer.on_theme_changed.reset_mock()
        self.manager.apply_theme('light')
        mock_observer.on_theme_changed.assert_not_called()
    
    def test_color_retrieval(self):
        """Test color retrieval from current theme."""
        self.manager.apply_theme('light')
        color = self.manager.get_color('window')
        self.assertEqual(color, THEMES['light']['window'])
        
        with self.assertRaises(KeyError):
            self.manager.get_color('nonexistent_color')
    
    def test_convenience_functions(self):
        """Test theme convenience functions."""
        apply_theme('dark')
        self.assertEqual(get_current_theme(), 'dark')
        self.assertEqual(get_color('window'), THEMES['dark']['window'])

if __name__ == '__main__':
    unittest.main()
