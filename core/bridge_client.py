import json

from PyQt5.QtCore import QObject, QTimer, QUrl, pyqtSignal
from PyQt5.QtWebSockets import QWebSocket

CONTROL_PATH = "/dashboard/control"
STATUS_PATH = "/dashboard/status"

INITIAL_RECONNECT_MS = 1000
MAX_RECONNECT_MS = 15000


class BridgeClient(QObject):
    """Owns the two WebSocket channels to the robot's Node-RED bridge.

    One socket for /dashboard/control (dashboard -> robot commands) and
    one for /dashboard/status (robot -> dashboard events). Both are
    required before `connected` fires. Auto-reconnects with backoff since
    the robot's IP/network changes between environments and hotspot
    links can be flaky.
    """

    connected = pyqtSignal()
    disconnected = pyqtSignal()
    status_event = pyqtSignal(dict)
    connection_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._host = ""
        self._port = 0
        self._want_connected = False
        self._control_up = False
        self._status_up = False
        self._reconnect_delay_ms = INITIAL_RECONNECT_MS

        self._control_socket = QWebSocket()
        self._status_socket = QWebSocket()

        self._control_socket.connected.connect(self._on_control_connected)
        self._control_socket.disconnected.connect(self._on_control_disconnected)
        self._control_socket.error.connect(self._on_control_error)

        self._status_socket.connected.connect(self._on_status_connected)
        self._status_socket.disconnected.connect(self._on_status_disconnected)
        self._status_socket.error.connect(self._on_status_error)
        self._status_socket.textMessageReceived.connect(self._on_status_message)

        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self._attempt_reconnect)

    @property
    def is_connected(self) -> bool:
        return self._control_up and self._status_up

    def connect_to(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._want_connected = True
        self._reconnect_delay_ms = INITIAL_RECONNECT_MS
        self._reconnect_timer.stop()
        self._open_sockets()

    def disconnect_from_robot(self) -> None:
        self._want_connected = False
        self._reconnect_timer.stop()
        self._control_socket.close()
        self._status_socket.close()

    def send_command(self, command: dict) -> bool:
        if not self._control_up:
            return False
        self._control_socket.sendTextMessage(json.dumps(command))
        return True

    def _open_sockets(self) -> None:
        self._control_socket.open(QUrl(f"ws://{self._host}:{self._port}{CONTROL_PATH}"))
        self._status_socket.open(QUrl(f"ws://{self._host}:{self._port}{STATUS_PATH}"))

    def _on_control_connected(self) -> None:
        self._control_up = True
        self._maybe_emit_connected()

    def _on_status_connected(self) -> None:
        self._status_up = True
        self._maybe_emit_connected()

    def _maybe_emit_connected(self) -> None:
        if self._control_up and self._status_up:
            self._reconnect_delay_ms = INITIAL_RECONNECT_MS
            self.connected.emit()

    def _on_control_disconnected(self) -> None:
        was_up = self._control_up
        self._control_up = False
        if was_up:
            self.disconnected.emit()
        self._schedule_reconnect()

    def _on_status_disconnected(self) -> None:
        was_up = self._status_up
        self._status_up = False
        if was_up:
            self.disconnected.emit()
        self._schedule_reconnect()

    def _on_control_error(self, _error) -> None:
        self.connection_error.emit(f"control: {self._control_socket.errorString()}")
        self._schedule_reconnect()

    def _on_status_error(self, _error) -> None:
        self.connection_error.emit(f"status: {self._status_socket.errorString()}")
        self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        if not self._want_connected or self._reconnect_timer.isActive():
            return
        self._reconnect_timer.start(self._reconnect_delay_ms)
        self._reconnect_delay_ms = min(self._reconnect_delay_ms * 2, MAX_RECONNECT_MS)

    def _attempt_reconnect(self) -> None:
        if self._want_connected:
            self._open_sockets()

    def _on_status_message(self, message: str) -> None:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            self.connection_error.emit(f"Malformed status message: {message}")
            return
        if isinstance(data, dict):
            self.status_event.emit(data)
