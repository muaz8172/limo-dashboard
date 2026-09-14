"""Converts occupancy-grid map data into QImages, plus the world<->pixel
coordinate transform needed to place the robot marker on it.

Handles both a full nav_msgs/OccupancyGrid and incremental
map_msgs/OccupancyGridUpdate patches (the map server publishes a full grid
once, then only the changed sub-rectangle on each update -- re-requesting
the whole grid every time would be wasteful and isn't what's actually
published).

Grid data is row-major starting at the map's bottom-left corner (row index
increases with +y), but QImage row 0 is the top of the image -- so rows are
flipped when building the image.
"""

from array import array
from dataclasses import dataclass

from PyQt5.QtGui import QImage

UNKNOWN_GRAY = 128


@dataclass
class MapMeta:
    width: int
    height: int
    resolution: float  # metres/cell
    origin_x: float  # world x of cell (0, 0)'s corner
    origin_y: float

    def world_to_pixel(self, x: float, y: float) -> tuple:
        """Returns (px, py) in the *unflipped* QImage's pixel space (py=0 at top)."""
        col = (x - self.origin_x) / self.resolution
        row_from_bottom = (y - self.origin_y) / self.resolution
        row = self.height - 1 - row_from_bottom
        return col, row


def _cells_to_qimage(cells, width: int, height: int) -> QImage:
    buf = bytearray(width * height)
    for row in range(height):
        image_row = height - 1 - row  # flip: grid row 0 is the bottom
        src_start = row * width
        dst_start = image_row * width
        for col in range(width):
            value = cells[src_start + col]
            if value < 0:
                pixel = UNKNOWN_GRAY
            else:
                v = 100 if value > 100 else value
                pixel = 255 - round(v / 100 * 255)
            buf[dst_start + col] = pixel

    # bytesPerLine passed explicitly (= width, no padding) so it matches
    # exactly how `buf` was laid out above, regardless of Qt's own
    # alignment conventions.
    image = QImage(bytes(buf), width, height, width, QImage.Format_Grayscale8)
    return image.copy()


def occupancy_grid_to_qimage(msg) -> tuple:
    """One-shot conversion of a full nav_msgs/msg/OccupancyGrid. Returns (QImage, MapMeta)."""
    meta = MapMeta(
        width=msg.info.width,
        height=msg.info.height,
        resolution=msg.info.resolution,
        origin_x=msg.info.origin.position.x,
        origin_y=msg.info.origin.position.y,
    )
    image = _cells_to_qimage(msg.data, meta.width, meta.height)
    return image, meta


class OccupancyGridState:
    """Accumulates a full grid plus incremental OccupancyGridUpdate patches,
    so the map doesn't need to be re-sent in full on every change."""

    def __init__(self):
        self.width = 0
        self.height = 0
        self.resolution = 0.0
        self.origin_x = 0.0
        self.origin_y = 0.0
        self.cells = array("b")

    @property
    def has_data(self) -> bool:
        return self.width > 0 and self.height > 0

    def reset_from_grid(self, msg) -> None:
        self.width = msg.info.width
        self.height = msg.info.height
        self.resolution = msg.info.resolution
        self.origin_x = msg.info.origin.position.x
        self.origin_y = msg.info.origin.position.y
        self.cells = array("b", msg.data)

    def apply_update(self, update_msg) -> bool:
        """update_msg: map_msgs/msg/OccupancyGridUpdate. Returns False (ignored)
        if no base grid has been received yet -- the update can't be placed."""
        if not self.has_data:
            return False

        ux, uy = update_msg.x, update_msg.y
        uw, uh = update_msg.width, update_msg.height
        row_count = min(uw, max(0, self.width - ux))
        if row_count <= 0:
            return True

        for row in range(uh):
            dst_row = uy + row
            if dst_row < 0 or dst_row >= self.height:
                continue
            src_start = row * uw
            dst_start = dst_row * self.width + ux
            self.cells[dst_start:dst_start + row_count] = array(
                "b", update_msg.data[src_start:src_start + row_count]
            )
        return True

    def to_qimage(self) -> QImage:
        return _cells_to_qimage(self.cells, self.width, self.height)

    def meta(self) -> MapMeta:
        return MapMeta(
            width=self.width, height=self.height, resolution=self.resolution,
            origin_x=self.origin_x, origin_y=self.origin_y,
        )
