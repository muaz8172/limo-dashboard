import sys

import rclpy
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

from robot_monitor.main_window import MainWindow
from robot_monitor.ros_bridge import RosBridge

SPIN_INTERVAL_MS = 20  # 50 Hz


def main():
    rclpy.init(args=sys.argv)
    app = QApplication(sys.argv)

    bridge = RosBridge()
    bridge.start()

    window = MainWindow(bridge)
    window.show()

    spin_timer = QTimer()
    spin_timer.timeout.connect(bridge.spin_once)
    spin_timer.start(SPIN_INTERVAL_MS)

    exit_code = app.exec_()

    bridge.shutdown()
    rclpy.shutdown()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
