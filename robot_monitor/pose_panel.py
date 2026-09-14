"""Numeric pose readout -- ports robot_pose_gui/limo_pose_gui.py's info
panel (position, quaternion, roll/pitch/yaw, copy-to-clipboard) into this
dashboard so a separate Tk window isn't needed. Values and the LIVE/STALE/
WAITING logic match the original; clipboard copy uses QClipboard directly,
which doesn't need the xclip/WSL workarounds the Tk version required.
"""

import time

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

STALE_AFTER_SEC = 0.5
STATUS_REFRESH_MS = 200

GREEN = "#22C55E"
YELLOW = "#FACC15"
RED = "#F87171"

_POSITION_FIELDS = [("x", "X", "{:.3f}"), ("y", "Y", "{:.3f}"), ("z", "Z", "{:.3f}")]
_QUATERNION_FIELDS = [
    ("qx", "X", "{:.6f}"), ("qy", "Y", "{:.6f}"),
    ("qz", "Z", "{:.6f}"), ("qw", "W", "{:.6f}"),
]
_ORIENTATION_FIELDS = [("roll", "Roll", "{:.2f}°"), ("pitch", "Pitch", "{:.2f}°"), ("yaw", "Yaw", "{:.2f}°")]


class PosePanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Robot Pose", parent)
        self._pose = None
        self._value_labels = {}
        self._build_ui()

        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_status)
        self._status_timer.start(STATUS_REFRESH_MS)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.status_label = QLabel("● WAITING FOR TF")
        self.status_label.setStyleSheet(f"color: {YELLOW}; font-weight: bold;")
        layout.addWidget(self.status_label)

        layout.addWidget(QLabel("POSITION (m)"))
        layout.addLayout(self._build_field_grid(_POSITION_FIELDS))

        layout.addWidget(QLabel("QUATERNION"))
        layout.addLayout(self._build_field_grid(_QUATERNION_FIELDS))

        layout.addWidget(QLabel("ORIENTATION"))
        layout.addLayout(self._build_field_grid(_ORIENTATION_FIELDS))

        copy_all_btn = QPushButton("Copy All")
        copy_all_btn.clicked.connect(self._copy_all)
        layout.addWidget(copy_all_btn)

        self.copy_status_label = QLabel("")
        self.copy_status_label.setStyleSheet("color: #38BDF8;")
        layout.addWidget(self.copy_status_label)

        layout.addStretch()

    def _build_field_grid(self, fields) -> QGridLayout:
        grid = QGridLayout()
        for row, (key, label, fmt) in enumerate(fields):
            grid.addWidget(QLabel(label), row, 0)
            value_label = QLabel("--")
            value_label.setStyleSheet("font-family: Consolas, monospace;")
            grid.addWidget(value_label, row, 1)
            copy_btn = QPushButton("Copy")
            copy_btn.setFixedWidth(50)
            copy_btn.clicked.connect(lambda _checked, k=key, f=fmt: self._copy(k, f))
            grid.addWidget(copy_btn, row, 2)
            self._value_labels[key] = (value_label, fmt)
        return grid

    def set_pose(self, pose: dict) -> None:
        self._pose = pose
        for key, (label, fmt) in self._value_labels.items():
            label.setText(fmt.format(pose[key]))

    def _refresh_status(self) -> None:
        if self._pose is None:
            self.status_label.setText("● WAITING FOR TF")
            self.status_label.setStyleSheet(f"color: {YELLOW}; font-weight: bold;")
            return

        age = time.time() - self._pose.get("timestamp", 0)
        if age < STALE_AFTER_SEC:
            self.status_label.setText("● LIVE TF DATA")
            self.status_label.setStyleSheet(f"color: {GREEN}; font-weight: bold;")
        else:
            self.status_label.setText(f"● NO UPDATE FOR {age:.1f}s")
            self.status_label.setStyleSheet(f"color: {RED}; font-weight: bold;")

    def _copy(self, key: str, fmt: str) -> None:
        if self._pose is None:
            self.copy_status_label.setText("No pose data available")
            return
        value = fmt.format(self._pose[key])
        QApplication.clipboard().setText(value)
        self.copy_status_label.setText(f"Copied {key}: {value}")

    def _copy_all(self) -> None:
        if self._pose is None:
            self.copy_status_label.setText("No pose data available")
            return
        p = self._pose
        text = (
            "LIMO ROBOT POSE\n"
            "==============================\n"
            "POSITION\n"
            f"X = {p['x']:.3f} m\nY = {p['y']:.3f} m\nZ = {p['z']:.3f} m\n\n"
            "QUATERNION\n"
            f"X = {p['qx']:.6f}\nY = {p['qy']:.6f}\nZ = {p['qz']:.6f}\nW = {p['qw']:.6f}\n\n"
            "ORIENTATION\n"
            f"Roll = {p['roll']:.2f}°\nPitch = {p['pitch']:.2f}°\nYaw = {p['yaw']:.2f}°\n"
        )
        QApplication.clipboard().setText(text)
        self.copy_status_label.setText("Copied complete robot pose")
