# LIMO Robot Dashboard

PyQt5 dashboard (Windows) for a LIMO robot running ROS2 Humble / Node-RED (Ubuntu 22.04). Talks to the robot over two WebSocket channels served by Node-RED (`/dashboard/control`, `/dashboard/status`) -- no ROS2 install needed on Windows.

## Layout

- `main.py` -- entry point
- `config/missions.json` -- shared checkpoint library + Mission 1 / Mission 2 definitions (checkpoints referenced by route, not duplicated per mission)
- `core/` -- `bridge_client.py` (WebSocket client), `settings.py` (remembers robot host/port), `mission_state.py` (live mission progress), `grid_numbering.py` (gamefield cell numbering, matches the robot's own mapping: 1 = bottom-left, 16 = top-right)
- `ui/` -- `main_window.py`, `mission_tab.py`, `checkpoint_button.py`, `gamefield_widget.py`
- `node-red-additions/` -- importable Node-RED flow (`dashboard-bridge.json`) adding the `/dashboard/control` and `/dashboard/status` websocket nodes, plus a `README.md` with import/wiring/deploy steps
- `scripts/deploy_to_robot.ps1` -- SCP helper for pushing a single file to the robot

## Windows setup

```
pip install -r requirements.txt
python main.py
```

Enter the robot's current IP and port `1880` in the connection bar (this changes between environments -- home WiFi vs. competition-day hotspot -- and is not hardcoded).

## Robot (Ubuntu) setup

```
git clone https://github.com/muaz8172/limo-dashboard.git
```

Then follow `node-red-additions/README.md` to import `dashboard-bridge.json` into the robot's Node-RED editor and wire it into the existing checkpoint/OCR/AprilTag flow.

## Checkpoint numbering

`config/missions.json`'s `cell_number` values follow the robot's own gamefield mapping picture (1 bottom-left, increasing left-to-right then bottom-to-top, 16 top-right). Verify each checkpoint's `cell_number` against the physical field before competition.
