# LIMO Robot Dashboard

PyQt5 dashboard (Windows) for a LIMO robot running ROS2 Humble / Node-RED (Ubuntu 22.04). Talks to the robot over two WebSocket channels served by Node-RED (`/dashboard/control`, `/dashboard/status`) -- no ROS2 install needed on Windows.

## Layout

- `main.py` -- entry point
- `config/missions.json` -- shared checkpoint library + Mission 1 / Mission 2 definitions (checkpoints referenced by route, not duplicated per mission)
- `core/` -- `bridge_client.py` (WebSocket client), `settings.py` (remembers robot host/port), `mission_state.py` (live mission progress), `grid_numbering.py` (gamefield cell numbering, matches the robot's own mapping: 1 = bottom-left, 16 = top-right)
- `ui/` -- `main_window.py`, `mission_tab.py`, `checkpoint_button.py`, `gamefield_widget.py`
- `node-red-additions/` -- snapshot + docs of the bridge flow already deployed on the robot (adds `/dashboard/control` and `/dashboard/status`, wired directly into MISSION 1 / MISSION 2's real nodes)
- `scripts/deploy_bridge_flow.py` -- deploys the bridge flow onto a robot's Node-RED via its Admin API (additive-only, validated before sending)
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

The bridge flow is already deployed on the current robot (10.21.215.131). To (re)deploy it -- e.g. after a Node-RED reset, or on a different robot with the same flow structure -- see `node-red-additions/README.md` and run `scripts/deploy_bridge_flow.py`.

## Checkpoint numbering

`config/missions.json`'s `cell_number` values follow the robot's own gamefield mapping picture (1 bottom-left, increasing left-to-right then bottom-to-top, 16 top-right). Verify each checkpoint's `cell_number` against the physical field before competition.
