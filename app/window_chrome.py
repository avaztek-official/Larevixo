"""Operation toast widgets."""
from PySide6.QtCore import Qt, QPoint, QRectF, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, Signal
from PySide6.QtGui import QPainterPath, QRegion
from PySide6.QtWidgets import QFrame

class OperationToast(QFrame):
    clicked = Signal()
    hovered = Signal(bool)

    def __init__(self, parent, frame):
        super().__init__(parent)
        self.frame = frame

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_clip()

    def moveEvent(self, event):
        super().moveEvent(event)
        self.update_clip()

    def update_clip(self):
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 10, 10)
        frame_origin = self.frame.mapTo(self.parentWidget(), QPoint(0, 0))
        clip = QRegion(frame_origin.x() - self.x(), frame_origin.y() - self.y(),
                       self.frame.width(), self.frame.height())
        mask = QRegion(path.toFillPolygon().toPolygon()).intersected(clip)
        self.setMask(mask if not mask.isEmpty() else QRegion(-2, -2, 1, 1))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self.hovered.emit(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered.emit(False)
        super().leaveEvent(event)
