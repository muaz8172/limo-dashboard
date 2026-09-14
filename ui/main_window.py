import json
from pathlib import Path

from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.bridge_client import BridgeClient
from core.grid_numbering import resolve_config_cells
from core.settings import Settings
from ui.mission_tab import MissionTab

CONNECTED_STYLE = "color: #2e7d32; font-weight: bold;"
DISCONNECTED_STYLE = "color: #c62828; font-weight: bold;"
CONNECTING_STYLE = "color: #f9a825; font-weight: bold;"

MISSIONS_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "missions.json"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LIMO Robot Dashboard")
        self.resize(1100, 750)

        self.settings = Settings()
        self.bridge_client = BridgeClient(self)
        self.bridge_client.connected.connect(self._on_connected)
        self.bridge_client.disconnected.connect(self._on_disconnected)
        self.bridge_client.connection_error.connect(self._on_connection_error)

        self.missions_config = self._load_missions_config()

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(self._build_connection_bar())

        self.tabs = QTabWidget()
        self._build_mission_tabs()
        layout.addWidget(self.tabs)

        self.setCentralWidget(central)

    @staticmethod
    def _load_missions_config() -> dict:
        with open(MISSIONS_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        return resolve_config_cells(config)

    def _build_connection_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel("Robot host:"))

        self.host_edit = QLineEdit(self.settings.get_host())
        self.host_edit.setMinimumWidth(140)
        row.addWidget(self.host_edit)

        row.addWidget(QLabel("Port:"))
        self.port_edit = QLineEdit(str(self.settings.get_port()))
        self.port_edit.setValidator(QIntValidator(1, 65535))
        self.port_edit.setFixedWidth(60)
        row.addWidget(self.port_edit)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self._toggle_connection)
        row.addWidget(self.connect_button)

        self.status_label = QLabel("● Disconnected")
        self.status_label.setStyleSheet(DISCONNECTED_STYLE)
        row.addWidget(self.status_label)

        row.addStretch()
        return row

    def _build_mission_tabs(self) -> None:
        checkpoints_lib = self.missions_config["checkpoints"]
        landmarks = self.missions_config.get("landmarks", {})

        self.mission_tabs = {}
        for mission_id, mission_def in self.missions_config["missions"].items():
            tab = MissionTab(mission_id, mission_def, checkpoints_lib, landmarks, self.bridge_client)
            self.mission_tabs[mission_id] = tab
            self.tabs.addTab(tab, mission_def["name"])

        placeholder = QWidget()
        placeholder_layout = QVBoxLayout(placeholder)
        placeholder_layout.addWidget(
            QLabel(
                "Mission 3's Node-RED flow isn't finished yet.\n"
                "This tab will be enabled once it's ready -- no dashboard changes needed."
            )
        )
        index = self.tabs.addTab(placeholder, "Mission 3 (coming soon)")
        self.tabs.setTabEnabled(index, False)

    def _toggle_connection(self) -> None:
        if self.bridge_client.is_connected:
            self.bridge_client.disconnect_from_robot()
            return

        host = self.host_edit.text().strip()
        if not host:
            self.status_label.setText("● Host required")
            self.status_label.setStyleSheet(DISCONNECTED_STYLE)
            return
        try:
            port = int(self.port_edit.text())
        except ValueError:
            self.status_label.setText("● Invalid port")
            self.status_label.setStyleSheet(DISCONNECTED_STYLE)
            return

        self.settings.set_host(host)
        self.settings.set_port(port)

        self.status_label.setText("● Connecting...")
        self.status_label.setStyleSheet(CONNECTING_STYLE)
        self.bridge_client.connect_to(host, port)

    def _on_connected(self) -> None:
        self.status_label.setText("● Connected")
        self.status_label.setStyleSheet(CONNECTED_STYLE)
        self.connect_button.setText("Disconnect")

    def _on_disconnected(self) -> None:
        self.status_label.setText("● Disconnected")
        self.status_label.setStyleSheet(DISCONNECTED_STYLE)
        self.connect_button.setText("Connect")

    def _on_connection_error(self, message: str) -> None:
        self.status_label.setText("● Error (see tooltip)")
        self.status_label.setStyleSheet(DISCONNECTED_STYLE)
        self.status_label.setToolTip(message)
