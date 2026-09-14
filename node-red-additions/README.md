# Dashboard Bridge (Node-RED flow)

**Status: already deployed** on the robot at `10.21.215.131:1880` (2026-09-14), via `scripts/deploy_bridge_flow.py` talking directly to Node-RED's Admin HTTP API -- not via manual import/wiring in the editor. `dashboard-bridge.json` in this folder is a snapshot of exactly what was added, for reference.

## What it does

Adds two WebSocket endpoints:

- `/dashboard/control` -- receives `{"cmd": "start_mission", "mission": 1|2}`, `{"cmd": "trigger_checkpoint", "mission": 1|2, "checkpoint": "CP..."}`, `{"cmd": "trigger_ocr", "mission": 2}`, `{"cmd": "trigger_apriltag", "mission": 2}`
- `/dashboard/status` -- pushes `{"mission": ..., "event": "checkpoint_reached"|"ocr_result"|"apriltag_detected"|"waiting_for_staff"|"mission_complete", ...}`

Every wire it adds is **additive**: new nodes on a new "Dashboard Bridge" tab, plus new outgoing wires appended to specific existing nodes' output ports in the MISSION 1 / MISSION 2 tabs. Nothing existing was deleted, reordered, or reconfigured -- verified by diffing the robot's flow before/after the deploy.

## What was actually found (read this before trusting the mapping below)

Fetching the robot's live flow (`GET /flows`) showed the real structure differs from the original mission slides:

- **Mission 1**'s auto-advancing chain has **9 segments, not 14** -- some checkpoints are combined into single nav goals (`Checkpoint 2-3`, `4-5`, `7-8`, `10-11`). There's also a second, disconnected set of same-named "Checkpoint N" nodes left over from earlier development, which this bridge ignores.
- **Mission 2** is fully chained from start through the toll-wait point (CP1→CP2→CP3→CP4→OCR→CP5→CP6→CP7→CP8→AprilTag→wait), but **checkpoints 9-14 (the return leg) are not chained together yet** -- they exist as individually-triggerable nodes only. The dashboard's per-checkpoint buttons still work for these (each is wired directly), you just won't get one continuous auto-run through them yet from "Start Mission 2" -- click them one at a time until that part of the flow is finished.
- Each checkpoint's `Switch` node has two outputs; in all 23 examined, one branch advances to the next checkpoint and the other is a debug-only dead end. The tap points below assume the **advancing branch** is output index `0` in every case -- this was inferred from wiring shape, not from reading each switch's actual rule condition, so spot-check it against real robot behavior.

## Tap / trigger map

| Checkpoint | Mission 1 real node | Mission 2 real node |
|---|---|---|
| CP1 | `60cbcc48...` (start) | `ef7ccf86...` (start) |
| CP2 | -- | `c922eb21...` |
| CP2_3 | `3e2d5285...` | -- |
| CP3 | -- | `a858b658...` |
| CP4 | -- | `480d89dd...` |
| CP4_5 | `4396585b...` | -- |
| OCR | -- | `9d282552...` (trigger) / tap on `241a99b9...` |
| CP5 | -- | `b3d059bb...` |
| CP6 | `fa22abbc...` | `8180f253...` |
| CP7 | -- | `104b650d...` |
| CP7_8 | `98606289...` | -- |
| CP8 | -- | `2fc35301...` |
| APRILTAG | -- | `07af6387...` (trigger) / tap on `2ab19683...` |
| CP9 | `8d3f957f...` | `0a38de82...` |
| CP10 | -- | `208fdda4...` |
| CP10_11 | `6bfbe88c...` | -- |
| CP11 | -- | `d9ec7f8e...` |
| CP12 | `0d247261...` | `227df3a3...` |
| CP13 | `b6b960f1...` (+ mission_complete) | `a685f691...` |
| CP14 | -- | `b86f2f26...` (+ mission_complete) |

(Full ids are in `scripts/deploy_bridge_flow.py`'s `MISSION1_TRIGGERS` / `MISSION2_TRIGGERS` dicts, matched by the prefixes shown here.)

## Redeploying

If the robot's Node-RED gets reset/rebuilt, or you want to push this to a different robot with the same flow structure:

```
python scripts/deploy_bridge_flow.py <robot-ip> --dry-run   # validate first
python scripts/deploy_bridge_flow.py <robot-ip>             # actually deploy
```

It refuses to run if a "Dashboard Bridge" tab already exists (delete it in the editor first to force a clean redeploy). If the robot's flow has since been restructured, node id prefixes will fail to resolve and it aborts loudly rather than guessing -- update the prefix constants at the top of the script to match.

## Still to do (not part of this bridge)

- Chain Mission 2's checkpoints 9-14 together and connect them after the toll-wait point, the same way 1-8 already are.
- Mission 3's flow isn't built yet -- extend `MISSION1_TAPS`-style tables once it exists.
