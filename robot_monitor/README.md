# LIMO Robot Monitor (runs ON the robot)

A separate, from-scratch monitoring-only dashboard, distinct from the Mission 1/2 control dashboard in the repo root (that one runs on Windows and talks to the robot over WebSocket; this one runs directly on the robot's Ubuntu machine and subscribes to ROS2 topics via `rclpy` -- no bridge needed).

**Status: built, not yet run on real hardware.** The camera/map/pose/voice pieces are all implemented and the map-rendering math is unit-tested against a synthetic grid, but nothing here has been run against your actual robot -- I have no ROS2/rclpy/display access from where this was written. Run it on the robot and expect to debug.

## What's wired up

- **RGB camera feed** (`/limo/camera/color/image_raw`) -- subscribed, decoded (no `cv_bridge` dependency), displayed live, scaled to fit.
- **`/limo/robot_description`** -- subscribed (transient-local QoS, as `robot_state_publisher` normally latches it); currently just flips a "Model loaded" status indicator. Confirm this is the behavior you want.
- **Live map + robot position** (`/map`, transient-local QoS) -- occupancy grid rendered as a grayscale image (free=white, occupied=black, unknown=gray), with the robot's live position + heading drawn as a blue circle + red heading line. Position comes from **TF** (`map` -> `limo/base_footprint`), the exact frames used by your existing `robot_pose_gui/limo_pose_gui.py` on the robot -- reused directly rather than guessed, including its quaternion-to-yaw math. Polled once per spin tick (50 Hz) rather than a separate thread, since everything already runs off one `QTimer`.
- **Robot Pose panel** -- `limo_pose_gui.py`'s numeric readout (position, quaternion, roll/pitch/yaw, per-field Copy buttons + Copy All, LIVE/STALE/WAITING status) ported in directly so it's one app instead of two. Same values, same staleness threshold (0.5s), same math -- clipboard copy uses Qt's own clipboard instead of the Tk version's xclip/WSL workarounds, which aren't needed here.
- **Voice commands** -- connects to `ws://localhost:1880/voice/muaz` (the same Node-RED voice channel used elsewhere in this repo, but connected locally since this app runs on the robot itself) and logs incoming messages.

## What's still missing

- **Depth camera feed** -- no topic given yet, so it's not in the layout at all.
- Any styling polish to match the reference screenshot more closely (colors, header branding) -- functional layout only so far.

## Layout

```
robot_monitor/
├── main.py          -- entry point: rclpy.init + QApplication, QTimer drives rclpy.spin_once()
├── ros_bridge.py     -- QObject wrapping the rclpy Node (camera/map/description/TF subs) + voice websocket client
├── map_utils.py      -- nav_msgs/OccupancyGrid -> QImage + world<->pixel transform
├── map_widget.py     -- paints the map image + robot position/heading marker
├── pose_panel.py      -- numeric pose readout, ported from robot_pose_gui/limo_pose_gui.py
├── image_utils.py    -- sensor_msgs/Image -> QImage conversion (no cv_bridge)
└── main_window.py    -- window layout: header, RGB feed panel, live map panel, voice log
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

## Known unknowns to check once running

- Whether `/map` is actually published transient-local on your setup (if the map panel stays blank, try re-publishing/relaunching your map source, or drop the `DurabilityPolicy.TRANSIENT_LOCAL` in `ros_bridge.py` to match whatever QoS it's actually using).
- Whether the occupancy-grid-to-image conversion (a plain Python loop, no numpy) is fast enough for your map's resolution -- fine for occasional map updates, but if it visibly stutters on very large maps, that loop is the first place to optimize.
