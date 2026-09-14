from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from robot_monitor.map_widget import MapWidget
from robot_monitor.pose_panel import PosePanel
from robot_monitor.ros_bridge import RosBridge

CONNECTED_STYLE = "color: #2e7d32; font-weight: bold;"
DISCONNECTED_STYLE = "color: #c62828; font-weight: bold;"


class CameraFeedWidget(QLabel):
    """Displays the latest frame, scaled to fit, preserving aspect ratio."""

    def __init__(self, placeholder_text: str, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: #1a1a1a; color: #777;")
        self.setText(placeholder_text)
        self._latest_pixmap = None

    def set_frame(self, image: QImage) -> None:
        self._latest_pixmap = QPixmap.fromImage(image)
        self._rescale()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self) -> None:
        if self._latest_pixmap is None:
            return
        scaled = self._latest_pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.setPixmap(scaled)


class MainWindow(QMainWindow):
    """Runs on the robot itself -- subscribes to ROS2 topics directly via
    rclpy (no Windows-side WebSocket bridge needed for this app)."""

    def __init__(self, bridge: RosBridge):
        super().__init__()
        self.bridge = bridge
        self.setWindowTitle("LIMO Robot Monitor")
        self.resize(1200, 800)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self._build_header())

        tabs = QTabWidget()
        tabs.addTab(self._build_monitor_tab(), "Monitor")
        self.pose_panel = PosePanel()
        tabs.addTab(self.pose_panel, "Robot Pose")
        layout.addWidget(tabs, 1)

        self.setCentralWidget(central)

        self.bridge.rgb_frame_received.connect(self.rgb_feed.set_frame)
        self.bridge.robot_description_received.connect(self._on_robot_description)
        self.bridge.map_received.connect(self.map_widget.set_map)
        self.bridge.pose_updated.connect(self._on_pose_updated)
        self.bridge.pose_lost.connect(self.map_widget.clear_pose)
        self.bridge.voice_connected.connect(self._on_voice_connected)
        self.bridge.voice_disconnected.connect(self._on_voice_disconnected)
        self.bridge.voice_message_received.connect(self._on_voice_message)

    def _on_pose_updated(self, pose: dict) -> None:
        self.map_widget.set_pose(pose["x"], pose["y"], pose["yaw_rad"])
        self.pose_panel.set_pose(pose)

    def _build_monitor_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        body = QHBoxLayout()
        body.addWidget(self._build_camera_column(), 1)
        body.addWidget(self._build_map_panel(), 2)
        layout.addLayout(body, 1)

        layout.addWidget(self._build_voice_panel())
        return tab

    def _build_header(self) -> QWidget:
        header = QWidget()
        row = QHBoxLayout(header)
        title = QLabel("LIMO Robot Monitor")
        title_font = title.font()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        row.addWidget(title)
        row.addStretch()

        self.model_status_label = QLabel("● Model not loaded")
        self.model_status_label.setStyleSheet(DISCONNECTED_STYLE)
        row.addWidget(self.model_status_label)

        self.voice_status_label = QLabel("● Voice disconnected")
        self.voice_status_label.setStyleSheet(DISCONNECTED_STYLE)
        row.addWidget(self.voice_status_label)
        return header

    def _build_camera_column(self) -> QWidget:
        column = QWidget()
        layout = QVBoxLayout(column)

        rgb_group = QGroupBox("RGB Camera Feed")
        rgb_layout = QVBoxLayout(rgb_group)
        self.rgb_feed = CameraFeedWidget("Waiting for camera frames...")
        rgb_layout.addWidget(self.rgb_feed)
        layout.addWidget(rgb_group)

        return column

    def _build_map_panel(self) -> QWidget:
        group = QGroupBox("Live Map / Position")
        layout = QVBoxLayout(group)
        self.map_widget = MapWidget()
        layout.addWidget(self.map_widget)
        return group

    def _build_voice_panel(self) -> QWidget:
        group = QGroupBox("Voice Commands")
        layout = QVBoxLayout(group)
        self.voice_log = QPlainTextEdit()
        self.voice_log.setReadOnly(True)
        self.voice_log.setMaximumBlockCount(200)
        self.voice_log.setMaximumHeight(120)
        layout.addWidget(self.voice_log)
        return group

    def _on_robot_description(self, _urdf_xml: str) -> None:
        self.model_status_label.setText("● Model loaded")
        self.model_status_label.setStyleSheet(CONNECTED_STYLE)

    def _on_voice_connected(self) -> None:
        self.voice_status_label.setText("● Voice connected")
        self.voice_status_label.setStyleSheet(CONNECTED_STYLE)

    def _on_voice_disconnected(self) -> None:
        self.voice_status_label.setText("● Voice disconnected")
        self.voice_status_label.setStyleSheet(DISCONNECTED_STYLE)

    def _on_voice_message(self, data: dict) -> None:
        self.voice_log.appendPlainText(str(data))
