# Dashboard Bridge (Node-RED flow)

`dashboard-bridge.json` adds the two WebSocket endpoints the Windows dashboard talks to:

- `/dashboard/control` -- receives commands from the dashboard (`start_mission`, `trigger_checkpoint`, `trigger_ocr`, `trigger_apriltag`)
- `/dashboard/status` -- pushes live events back to the dashboard (`checkpoint_reached`, `ocr_result`, `apriltag_detected`, `waiting_for_staff`, `mission_complete`)

There's nothing to separately "start" -- a WebSocket node in Node-RED becomes live the moment you **Deploy** the flow it's in, as long as Node-RED itself is already running (which it is, since you can open its editor in Edge at `http://<robot-ip>:1880`). So "running the websocket" = import this flow, wire it up, hit Deploy.

## 1. Import

1. On the robot, open the Node-RED editor (the same `http://<robot-ip>:1880` you already use).
2. Menu (☰, top right) -> **Import**.
3. Choose **select a file to import** and pick `dashboard-bridge.json` from this repo (or paste its contents).
4. Import to **a new flow** -- this creates a new tab called "Dashboard Bridge" so your existing flow is untouched.
5. Don't click Deploy yet -- wire the stubs first (next section), otherwise the new endpoints exist but don't actually trigger anything.

## 2. Wire the control side

The imported flow ends in a set of placeholder **function nodes named `TODO: wire to ...`** -- one per checkpoint (CP1-CP14), one per mission start, and one each for OCR/AprilTag. Each is a harmless pass-through. For each one:

- Drag a wire from the stub's output straight into the input of the real node it names (e.g. the `TODO: wire to your existing CP3 node` stub's output -> your existing `Checkpoint 3` function node's input, the same one your `ROS2 Inject` node already feeds).
- You don't need to delete the stub or remove your existing manual Inject nodes -- Node-RED nodes accept multiple incoming wires, so manual editor-testing keeps working alongside dashboard-triggered commands.
- The two mission-start stubs (`TODO: wire to first checkpoint of Mission 1/2`) should point at whatever kicks off that mission's full sequence in your existing flow (its first checkpoint) -- this only works end-to-end once your checkpoint chain auto-advances checkpoint N -> N+1 on its own.

## 3. Wire the status side

At each point in your **existing** flow you want the dashboard to hear about (a checkpoint's `Switch` output, the OCR `Switch` output, the AprilTag `Switch` output, end of mission):

1. Add a small **Change** or **Function** node that shapes `msg.payload` into one of these (`mission` must match `"1"` or `"2"` as used in `config/missions.json`):
   ```json
   {"mission": 1, "event": "checkpoint_reached", "checkpoint": "CP3"}
   {"mission": 2, "event": "ocr_result", "text": "detected text"}
   {"mission": 2, "event": "apriltag_detected", "id": 7}
   {"mission": 2, "event": "waiting_for_staff"}
   {"mission": 1, "event": "mission_complete"}
   ```
2. Add a **link out** node after it, and in its target picker choose the existing link-in node named **"Dashboard Status In"** (it's already in the imported "Dashboard Bridge" tab -- you're just pointing at it by name, no need to know its id).

## 4. Deploy and verify

1. Click **Deploy** (top right).
2. In the "Dashboard Bridge" tab, the `websocket in`/`websocket out` nodes should show a small green "connected"/blue "listening" status dot underneath once deployed.
3. Easiest end-to-end check: open the Windows dashboard (`python main.py`), type the robot's current IP into the connection bar, click **Connect** -- the status indicator turns green once both `/dashboard/control` and `/dashboard/status` are reachable.
4. Click a checkpoint button in the dashboard and confirm the robot actually moves -- that proves the control-side wiring from step 2 is correct for that checkpoint.
5. Manually trigger a checkpoint/OCR/AprilTag node in the *main* flow's editor and confirm a line appears in the dashboard's event log -- that proves the status-side wiring from step 3 is correct.

## Troubleshooting

- **Dashboard won't connect at all**: confirm Node-RED's port (1880) is reachable from Windows -- `Test-NetConnection <robot-ip> -Port 1880` in PowerShell, or just re-open `http://<robot-ip>:1880` in Edge from the Windows machine.
- **Connects but clicking a checkpoint does nothing on the robot**: that checkpoint's stub function isn't wired to the real node yet (step 2).
- **Robot moves but the dashboard never updates**: the status-side tap point for that event is missing (step 3).
