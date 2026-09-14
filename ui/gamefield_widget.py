from PyQt5.QtCore import QLineF, QRectF, QSize, Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QWidget

from core.grid_numbering import GRID_COLS, GRID_ROWS, rc_to_number


class GameFieldWidget(QWidget):
    """Schematic gamefield grid: draws grid lines, small reference numbers
    matching the robot's own cell numbering (1 = bottom-left, matching the
    robot mapping picture), landmark labels (P1/P2/P3), a marker for the
    currently active checkpoint, and dots for already-visited checkpoints.
    Cell positions come from config, not from this widget -- it just
    renders whatever it's told.
    """

    def __init__(self, landmarks=None, rows: int = GRID_ROWS, cols: int = GRID_COLS, parent=None):
        super().__init__(parent)
        self._landmarks = landmarks or {}
        self._rows = rows
        self._cols = cols
        self._visited_cells = set()
        self._active_cell = None
        self.setMinimumSize(220, 220)

    def sizeHint(self) -> QSize:
        return QSize(300, 300)

    def set_visited_cells(self, cells) -> None:
        self._visited_cells = {tuple(c) for c in cells}
        self.update()

    def set_active_cell(self, cell) -> None:
        self._active_cell = tuple(cell) if cell else None
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        margin = 10
        drawable_w = self.width() - 2 * margin
        drawable_h = self.height() - 2 * margin
        origin_x = margin
        origin_y = margin
        cell_w = drawable_w / self._cols
        cell_h = drawable_h / self._rows

        painter.fillRect(QRectF(origin_x, origin_y, drawable_w, drawable_h), QColor("#f0f0f0"))

        pen = QPen(QColor("#9e9e9e"))
        pen.setWidth(1)
        painter.setPen(pen)
        for c in range(self._cols + 1):
            x = origin_x + c * cell_w
            painter.drawLine(QLineF(x, origin_y, x, origin_y + drawable_h))
        for r in range(self._rows + 1):
            y = origin_y + r * cell_h
            painter.drawLine(QLineF(origin_x, y, origin_x + drawable_w, y))

        number_font = painter.font()
        number_font.setPointSize(max(7, int(cell_h * 0.16)))
        number_font.setBold(False)
        painter.setFont(number_font)
        painter.setPen(QColor("#b0b0b0"))
        for r in range(self._rows):
            for c in range(self._cols):
                number = rc_to_number(r, c, self._rows, self._cols)
                rect = QRectF(origin_x + c * cell_w + 2, origin_y + r * cell_h + 2, cell_w - 4, cell_h - 4)
                painter.drawText(rect, Qt.AlignTop | Qt.AlignLeft, str(number))

        label_font = painter.font()
        label_font.setBold(True)
        label_font.setPointSize(max(9, int(cell_h * 0.22)))
        painter.setFont(label_font)
        painter.setPen(QColor("#424242"))
        for label, rc in self._landmarks.items():
            r, c = rc
            rect = QRectF(origin_x + c * cell_w, origin_y + r * cell_h, cell_w, cell_h)
            painter.drawText(rect, Qt.AlignCenter, label)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#66bb6a"))
        for r, c in self._visited_cells:
            cx = origin_x + c * cell_w + cell_w / 2
            cy = origin_y + r * cell_h + cell_h / 2
            radius = min(cell_w, cell_h) * 0.08
            painter.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))

        if self._active_cell is not None:
            r, c = self._active_cell
            cx = origin_x + c * cell_w + cell_w / 2
            cy = origin_y + r * cell_h + cell_h / 2
            radius = min(cell_w, cell_h) * 0.22
            painter.setBrush(QColor("#e53935"))
            painter.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))
