"""
Signal strength indicator widget.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, QRect, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPainterPath

class SignalIndicator(QWidget):
    """
    Visual indicator for WiFi signal strength.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(60, 60)
        
        # Signal strength in dBm (-30 to -100)
        self._signal = -100
        self._animation = None
    
    def setSignal(self, signal_dbm):
        """Set the signal strength value."""
        self._signal = max(-100, min(signal_dbm, -30))
        self.update()
    
    def setSignalWithAnimation(self, signal_dbm):
        """Set the signal with smooth animation."""
        if self._animation and self._animation.state() == QPropertyAnimation.State.Running:
            self._animation.stop()
        
        new_signal = max(-100, min(signal_dbm, -30))
        self._animation = QPropertyAnimation(self, b"signal")
        self._animation.setDuration(500)
        self._animation.setStartValue(self._signal)
        self._animation.setEndValue(new_signal)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()
    
    def getSignal(self):
        return self._signal
    
    def setSignalProp(self, value):
        self._signal = value
        self.update()
    
    signal = pyqtProperty(float, getSignal, setSignalProp)
    
    def paintEvent(self, event):
        """Custom paint event to draw the signal indicator."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate percentage (0-100)
        percentage = (self._signal + 100) / 70 * 100
        percentage = max(0, min(percentage, 100))
        
        # Choose color based on signal strength
        if percentage > 70:
            color = QColor(76, 175, 80)  # Green
        elif percentage > 40:
            color = QColor(255, 193, 7)  # Amber
        else:
            color = QColor(244, 67, 54)  # Red
        
        # Draw background circle
        rect = self.rect().adjusted(5, 5, -5, -5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(220, 220, 220))
        painter.drawEllipse(rect)
        
        # Draw filled arc for signal strength
        angle = percentage * 3.6  # 3.6 degrees per percentage point (360 / 100)
        
        # Create a path for the arc
        path = QPainterPath()
        center = rect.center()
        path.moveTo(center.x(), center.y())
        
        # Fix: Convert QRect to QRectF for arcTo
        rect_f = QRectF(rect)
        path.arcTo(rect_f, 90, -angle)
        
        path.lineTo(center.x(), center.y())
        
        # Fill the path
        painter.setBrush(color)
        painter.drawPath(path)
        
        # Draw a white inner circle
        inner_rect = rect.adjusted(
            int(rect.width() * 0.25), 
            int(rect.height() * 0.25),
            -int(rect.width() * 0.25), 
            -int(rect.height() * 0.25)
        )
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(inner_rect)
        
        # Draw the signal value
        painter.setPen(QColor(50, 50, 50))
        painter.setFont(self.font())
        painter.drawText(inner_rect, Qt.AlignmentFlag.AlignCenter, f"{self._signal}")