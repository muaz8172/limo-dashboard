import math

from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QLabel, QWidget

from robot_monitor.map_utils import occupancy_grid_to_qimage

ROBOT_RADIUS_PX = 9
HEADING_LENGTH_PX = 22


class MapWidget(QWidget):
    """Renders the occupancy grid map with the robot's live position and
    heading overlaid, similar in spirit to the reference dashboard (a blue
    circle + heading line for the robot), but computed from real TF data
    rather than an example screenshot."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        self._map_image = None
        self._meta = None
        self._pose = None  # (x, y, yaw) in the map frame, or None

        self._empty_label = QLabel("Waiting for /map ...", self)
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: #777;")

    def set_map(self, msg) -> None:
        self._map_image, self._meta = occupancy_grid_to_qimage(msg)
        self._empty_label.hide()
        self.update()

    def set_pose(self, x: float, y: float, yaw: float) -> None:
        self._pose = (x, y, yaw)
        self.update()

    def clear_pose(self) -> None:
        self._pose = None
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._empty_label.setGeometry(self.rect())

    def _draw_rect(self):
        """Rect the map image is actually drawn into (aspect-ratio preserved, centered)."""
        if self._map_image is None:
            return None, 1.0
        img_w, img_h = self._map_image.width(), self._map_image.height()
        if img_w == 0 or img_h == 0:
            return None, 1.0
        scale = min(self.width() / img_w, self.height() / img_h)
        draw_w, draw_h = img_w * scale, img_h * scale
        x0 = (self.width() - draw_w) / 2
        y0 = (self.height() - draw_h) / 2
        return (x0, y0, draw_w, draw_h), scale

    def paintEvent(self, _event) -> None:
        if self._map_image is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect, scale = self._draw_rect()
        if rect is None:
            return
        x0, y0, draw_w, draw_h = rect
        scaled_image = self._map_image.scaled(
            int(draw_w), int(draw_h), Qt.IgnoreAspectRatio, Qt.SmoothTransformation
        )
        painter.drawImage(QPointF(x0, y0), scaled_image)

        if self._pose is not None and self._meta is not None:
            x, y, yaw = self._pose
            px, py = self._meta.world_to_pixel(x, y)
            screen_x = x0 + px * scale
            screen_y = y0 + py * scale

            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.setBrush(QColor(41, 128, 185))
            painter.drawEllipse(QPointF(screen_x, screen_y), ROBOT_RADIUS_PX, ROBOT_RADIUS_PX)

            # Heading line -- yaw is measured counter-clockwise from +x in the
            # map frame; screen y grows downward, so flip the y component.
            hx = screen_x + HEADING_LENGTH_PX * math.cos(yaw)
            hy = screen_y - HEADING_LENGTH_PX * math.sin(yaw)
            painter.setPen(QPen(QColor(231, 76, 60), 3))
            painter.drawLine(QPointF(screen_x, screen_y), QPointF(hx, hy))
