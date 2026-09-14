"""Owns the ROS2 node this app uses to subscribe to robot topics, plus the
WebSocket client for the voice-command channel already running in Node-RED
on this same machine. Runs directly on the robot -- no Windows-side bridge
involved, unlike core/bridge_client.py in the main dashboard.
"""

import json
import math

import rclpy
import rclpy.time
from PyQt5.QtCore import QObject, QUrl, pyqtSignal
from PyQt5.QtGui import QImage
from PyQt5.QtWebSockets import QWebSocket
from nav_msgs.msg import OccupancyGrid
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String
from tf2_ros import Buffer, TransformException, TransformListener

from robot_monitor.image_utils import imgmsg_to_qimage

RGB_TOPIC = "/limo/camera/color/image_raw"
ROBOT_DESCRIPTION_TOPIC = "/limo/robot_description"
MAP_TOPIC = "/map"
VOICE_WS_URL = "ws://localhost:1880/voice/muaz"

# Same frames used by robot_pose_gui/limo_pose_gui.py on the robot.
PARENT_FRAME = "map"
ROBOT_FRAME = "limo/base_footprint"


class RosBridge(QObject):
    rgb_frame_received = pyqtSignal(QImage)
    robot_description_received = pyqtSignal(str)
    map_received = pyqtSignal(object)  # raw nav_msgs/OccupancyGrid
    pose_updated = pyqtSignal(float, float, float)  # x, y, yaw (radians)
    pose_lost = pyqtSignal()
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

        map_qos = QoSProfile(depth=1)
        map_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self._map_sub = self.node.create_subscription(
            OccupancyGrid, MAP_TOPIC, self._on_map, map_qos
        )

        # Robot position comes from TF (map -> limo/base_footprint), same
        # as robot_pose_gui/limo_pose_gui.py on the robot -- polled once per
        # spin_once() tick rather than a separate thread, since everything
        # here already runs off one QTimer on the Qt main thread.
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self.node)
        self._had_pose = False

        self._voice_socket = QWebSocket()
        self._voice_socket.connected.connect(self.voice_connected)
        self._voice_socket.disconnected.connect(self.voice_disconnected)
        self._voice_socket.textMessageReceived.connect(self._on_voice_message)

    def start(self) -> None:
        self._voice_socket.open(QUrl(VOICE_WS_URL))

    def spin_once(self) -> None:
        rclpy.spin_once(self.node, timeout_sec=0)
        self._poll_pose()

    def _poll_pose(self) -> None:
        try:
            transform = self.tf_buffer.lookup_transform(
                PARENT_FRAME, ROBOT_FRAME, rclpy.time.Time()
            )
        except TransformException:
            if self._had_pose:
                self._had_pose = False
                self.pose_lost.emit()
            return

        t = transform.transform.translation
        q = transform.transform.rotation
        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z),
        )
        self._had_pose = True
        self.pose_updated.emit(t.x, t.y, yaw)

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

    def _on_map(self, msg: OccupancyGrid) -> None:
        self.map_received.emit(msg)

    def _on_voice_message(self, message: str) -> None:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return
        if isinstance(data, dict):
            self.voice_message_received.emit(data)
