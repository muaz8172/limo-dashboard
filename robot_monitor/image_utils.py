"""Converts sensor_msgs/Image messages to QImage without depending on
cv_bridge/OpenCV -- one less package to have installed on the robot.
"""

from PyQt5.QtGui import QImage

# encoding -> (QImage.Format, bytes per pixel)
_FORMAT_MAP = {
    "rgb8": (QImage.Format_RGB888, 3),
    "bgr8": (QImage.Format_BGR888, 3),
    "mono8": (QImage.Format_Grayscale8, 1),
}


def imgmsg_to_qimage(msg) -> QImage:
    """msg: a sensor_msgs/msg/Image (as delivered by rclpy)."""
    fmt = _FORMAT_MAP.get(msg.encoding)
    if fmt is None:
        raise ValueError(f"unsupported image encoding: {msg.encoding!r}")
    qformat, _bpp = fmt

    # Copy the buffer -- msg.data may be a memoryview/bytes tied to the
    # subscriber's lifetime, and QImage doesn't copy by default.
    buf = bytes(msg.data)
    image = QImage(buf, msg.width, msg.height, msg.step, qformat)
    return image.copy()
