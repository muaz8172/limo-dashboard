from PyQt5.QtCore import QSettings

DEFAULT_HOST = "192.168.1.100"
DEFAULT_PORT = 1880


class Settings:
    """Thin wrapper around QSettings for the robot connection target.

    The robot's IP changes between environments (home WiFi vs. phone
    hotspot on competition day), so this only remembers the last value
    used -- it is always editable from the connection bar.
    """

    def __init__(self):
        self._settings = QSettings("LIMODashboard", "Dashboard")

    def get_host(self) -> str:
        return self._settings.value("robot/host", DEFAULT_HOST, type=str)

    def set_host(self, host: str) -> None:
        self._settings.setValue("robot/host", host)

    def get_port(self) -> int:
        return self._settings.value("robot/port", DEFAULT_PORT, type=int)

    def set_port(self, port: int) -> None:
        self._settings.setValue("robot/port", port)
