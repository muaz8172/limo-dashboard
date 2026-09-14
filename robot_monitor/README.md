# LIMO Robot Monitor (runs ON the robot)

A separate, from-scratch monitoring-only dashboard, distinct from the Mission 1/2 control dashboard in the repo root (that one runs on Windows and talks to the robot over WebSocket; this one runs directly on the robot's Ubuntu machine and subscribes to ROS2 topics via `rclpy` -- no bridge needed).

**Status: skeleton only, not yet complete.** Built on branch `robot-monitor-dashboard`. I have not been able to run or test this against real ROS2 topics or a display (no ROS2/rclpy/robot access from where this was written) -- treat it as a first draft to run and debug on the robot itself.

## What's wired up

- **RGB camera feed** (`/limo/camera/color/image_raw`) -- subscribed, decoded (no `cv_bridge` dependency), displayed live, scaled to fit.
- **`/limo/robot_description`** -- subscribed (assumed latched/transient-local, as `robot_state_publisher` normally publishes it); currently just flips a "Model loaded" status indicator. Confirm this is the behavior you want.
- **Voice commands** -- connects to `ws://localhost:1880/voice/muaz` (the same Node-RED voice channel used elsewhere in this repo, but connected locally since this app runs on the robot itself) and logs incoming messages.

## What's still missing

- **Depth camera feed** -- no topic given yet.
- **Live Map / Position panel** -- currently a placeholder. Needs `limo_pose_gui.py`'s logic (map rendering + robot position/heading marker) ported in, or that script run as a source of truth this app subscribes to. Waiting on that file's content.

## Layout

```
robot_monitor/
├── main.py          -- entry point: rclpy.init + QApplication, QTimer drives rclpy.spin_once()
├── ros_bridge.py     -- QObject wrapping the rclpy Node + the voice websocket client
├── image_utils.py    -- sensor_msgs/Image -> QImage conversion (no cv_bridge)
└── main_window.py    -- window layout: header, RGB feed panel, map placeholder, voice log
```

## Running on the robot

```bash
source /opt/ros/humble/setup.bash      # or wherever your ROS2 workspace is sourced from
pip install PyQt5                       # into that same Python environment
cd ~/your-folder/limo-dashboard
git checkout robot-monitor-dashboard
python -m robot_monitor.main
```

(Run as a module -- `python -m robot_monitor.main`, not `python robot_monitor/main.py` -- so the package-relative imports resolve.)
