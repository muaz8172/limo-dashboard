"""Owns the ROS2 node this app uses to subscribe to robot topics, plus the
WebSocket client for the voice-command channel already running in Node-RED
on this same machine. Runs directly on the robot -- no Windows-side bridge
involved, unlike core/bridge_client.py in the main dashboard.
"""

import json

import rclpy
from PyQt5.QtCore import QObject, QUrl, pyqtSignal
from PyQt5.QtGui import QImage
from PyQt5.QtWebSockets import QWebSocket
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String

from robot_monitor.image_utils import imgmsg_to_qimage

RGB_TOPIC = "/limo/camera/color/image_raw"
ROBOT_DESCRIPTION_TOPIC = "/limo/robot_description"
VOICE_WS_URL = "ws://localhost:1880/voice/muaz"


class RosBridge(QObject):
    rgb_frame_received = pyqtSignal(QImage)
    robot_description_received = pyqtSignal(str)
    voice_message_received = pyqtSignal(dict)
    voice_connected = pyqtSignal()
    voice_disconnected = pyqtSignal()

    def __init__(self, node_name: str = "limo_dashboard_monitor", parent=None):
        super().__init__(parent)
        self.node = rclpy.create_node(node_name)

        self._rgb_sub = self.node.create_subscription(
            Image, RGB_TOPIC, self._on_rgb, qos_profile_sensor_data
        )

        # robot_description is normally published once, latched (transient
        # local), so a fresh subscriber still receives it.
        description_qos = QoSProfile(depth=1)
        description_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self._description_sub = self.node.create_subscription(
            String, ROBOT_DESCRIPTION_TOPIC, self._on_description, description_qos
        )

        self._voice_socket = QWebSocket()
        self._voice_socket.connected.connect(self.voice_connected)
        self._voice_socket.disconnected.connect(self.voice_disconnected)
        self._voice_socket.textMessageReceived.connect(self._on_voice_message)

    def start(self) -> None:
        self._voice_socket.open(QUrl(VOICE_WS_URL))

    def spin_once(self) -> None:
        rclpy.spin_once(self.node, timeout_sec=0)

    def shutdown(self) -> None:
        self._voice_socket.close()
        self.node.destroy_node()

    def _on_rgb(self, msg: Image) -> None:
        try:
            qimg = imgmsg_to_qimage(msg)
        except ValueError as exc:
            self.node.get_logger().warn(str(exc))
            return
        self.rgb_frame_received.emit(qimg)

    def _on_description(self, msg: String) -> None:
        self.robot_description_received.emit(msg.data)

    def _on_voice_message(self, message: str) -> None:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return
        if isinstance(data, dict):
            self.voice_message_received.emit(data)
