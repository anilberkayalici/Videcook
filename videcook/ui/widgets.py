"""Custom UI components for VideCook's modern interface."""

from PySide6.QtCore import Qt, QPropertyAnimation, Property, QPoint, QEasingCurve, Signal
from PySide6.QtGui import QPainter, QColor, QBrush, QPainterPath
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGraphicsDropShadowEffect, QLabel

class ModernCard(QWidget):
    """A premium web-like card with drop shadow."""
    def __init__(self, parent=None, layout=None, title: str = ""):
        super().__init__(parent)
        self.setObjectName("modernCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)
        
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(24, 24, 24, 24)
        self._main_layout.setSpacing(16)
        
        if title:
            title_label = QLabel(title)
            title_label.setObjectName("cardTitle")
            self._main_layout.addWidget(title_label)
            
        if layout:
            self._main_layout.addLayout(layout)

    def addLayout(self, layout):
        self._main_layout.addLayout(layout)
        
    def addWidget(self, widget, stretch=0):
        self._main_layout.addWidget(widget, stretch)

class ToggleSwitch(QWidget):
    """iOS/Web style modern toggle switch."""
    toggled = Signal(bool)
    
    def __init__(self, parent=None, checked=False):
        super().__init__(parent)
        self.setFixedSize(50, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = checked
        self._position = 22 if checked else 4
        
    @Property(float)
    def position(self):
        return self._position
        
    @position.setter
    def position(self, pos):
        self._position = pos
        self.update()
        
    def isChecked(self):
        return self._checked
        
    def setChecked(self, checked):
        if self._checked == checked:
            return
        self._checked = checked
        self.start_animation()
        self.toggled.emit(checked)
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
            
    def start_animation(self):
        self.anim = QPropertyAnimation(self, b"position")
        self.anim.setEasingCurve(QEasingCurve.Type.InOutCirc)
        self.anim.setEndValue(22 if self._checked else 4)
        self.anim.setDuration(250)
        self.anim.start()
        
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # We use transparent-compatible theme colors
        bg_color = QColor("#8D96A1") if self._checked else QColor("#252A30")
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 13, 13)
        p.fillPath(path, QBrush(bg_color))
        
        handle_radius = 11
        p.setBrush(QBrush(Qt.GlobalColor.white))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPoint(int(self._position) + handle_radius, 13), handle_radius, handle_radius)
        p.end()
