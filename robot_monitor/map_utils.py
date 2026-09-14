"""Converts nav_msgs/OccupancyGrid into a QImage, plus the world<->pixel
coordinate transform needed to place the robot marker on it.

OccupancyGrid.data is row-major starting at the map's bottom-left corner
(row index increases with +y), but QImage row 0 is the top of the image --
so rows are flipped when building the image.
"""

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


def occupancy_grid_to_qimage(msg) -> tuple:
    """msg: nav_msgs/msg/OccupancyGrid. Returns (QImage, MapMeta)."""
    width = msg.info.width
    height = msg.info.height
    meta = MapMeta(
        width=width,
        height=height,
        resolution=msg.info.resolution,
        origin_x=msg.info.origin.position.x,
        origin_y=msg.info.origin.position.y,
    )

    data = msg.data
    buf = bytearray(width * height)

    for row in range(height):
        image_row = height - 1 - row  # flip: OccupancyGrid row 0 is the bottom
        src_start = row * width
        dst_start = image_row * width
        for col in range(width):
            value = data[src_start + col]
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
    return image.copy(), meta
