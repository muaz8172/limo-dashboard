"""Deploys the dashboard bridge (control/status websockets + real wiring
into MISSION 1 / MISSION 2) onto a robot's live Node-RED instance via its
Admin HTTP API.

This is the exact tool used to build the flow currently running at
10.21.215.131:1880 (traced 2026-09-14). It is ADDITIVE ONLY: it fetches the
robot's current flows, adds a new "Dashboard Bridge" tab, and appends new
outgoing wires to specific existing nodes' output ports -- it never removes,
reorders, or modifies any existing node or wire. Every write is validated
against the original before anything is sent.

Usage:
    python deploy_bridge_flow.py <robot-host> [--port 1880] [--dry-run]

If the robot's flow has been rebuilt/renamed since 2026-09-14, the target
node id prefixes below will fail to resolve (the script aborts loudly
rather than guessing) -- update MISSION1_TAPS / MISSION1_TRIGGERS / etc.
to match the current node ids in that case (use node-red-additions/README.md
for how each id was found).
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

TAB_ID = "dashboard_bridge_tab"
TAB_LABEL = "Dashboard Bridge"
CONTROL_LISTENER = "control_ws_listener"
STATUS_LISTENER = "status_ws_listener"

# (checkpoint_label, source_node_id_prefix, output_index, also_emits_mission_complete)
MISSION1_TAPS = [
    ("CP1", "b139eb", 0, False),
    ("CP2_3", "41dd54", 0, False),
    ("CP4_5", "2947e6", 0, False),
    ("CP6", "2789f3", 0, False),
    ("CP7_8", "a5fa88", 0, False),
    ("CP9", "789589", 0, False),
    ("CP10_11", "889d3a", 0, False),
    ("CP12", "8af1f9", 0, False),
    ("CP13", "5d700d", 0, True),
]
MISSION2_TAPS = [
    ("CP1", "0f7451", 0, False),
    ("CP2", "e76e64", 0, False),
    ("CP3", "bcd0ba", 0, False),
    ("CP4", "50173c", 0, False),
    ("CP5", "704bba", 0, False),
    ("CP6", "fba4d7", 0, False),
    ("CP7", "7d0609", 0, False),
    ("CP8", "090219", 0, False),
    ("CP9", "e1f203", 0, False),
    ("CP10", "930749", 0, False),
    ("CP11", "1405d1", 0, False),
    ("CP12", "037b70", 0, False),
    ("CP13", "868293", 0, False),
    ("CP14", "4ad0a2", 0, True),
]
MISSION1_TRIGGERS = {
    "CP1": "60cbcc", "CP2_3": "3e2d52", "CP4_5": "439658", "CP6": "fa22ab",
    "CP7_8": "986062", "CP9": "8d3f95", "CP10_11": "6bfbe8", "CP12": "0d2472", "CP13": "b6b960",
}
MISSION2_TRIGGERS = {
    "CP1": "ef7ccf", "CP2": "c922eb", "CP3": "a858b6", "CP4": "480d89",
    "CP5": "b3d059", "CP6": "8180f2", "CP7": "104b65", "CP8": "2fc353",
    "CP9": "0a38de", "CP10": "208fdd", "CP11": "d9ec7f", "CP12": "227df3",
    "CP13": "a685f6", "CP14": "b86f2f",
}
MISSION1_START_PREFIX = "60cbcc"
MISSION2_START_PREFIX = "ef7ccf"
OCR_TRIGGER_PREFIX = "9d2825"
APRILTAG_TRIGGER_PREFIX = "07af63"
OCR_TAP_PREFIX = "241a99"
APRILTAG_TAP_PREFIX = "2ab196"
WAITING_TAP_PREFIX = "2efc22"


def fetch_flows(base_url: str) -> list:
    with urllib.request.urlopen(f"{base_url}/flows", timeout=10) as resp:
        return json.load(resp)


def post_flows(base_url: str, flows: list) -> None:
    body = json.dumps(flows).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/flows", data=body, method="POST",
        headers={"Content-Type": "application/json", "Node-RED-Deployment-Type": "full"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status not in (200, 204):
            raise RuntimeError(f"unexpected status {resp.status}")


def build_patch(existing: list) -> list:
    if any(n.get("type") == "tab" and n.get("label") == TAB_LABEL for n in existing):
        raise RuntimeError(
            f"A '{TAB_LABEL}' tab already exists on this robot -- remove it in the "
            "Node-RED editor first if you want to redeploy fresh (re-running without "
            "removing it would try to create duplicate node ids)."
        )

    by_id = {n["id"]: n for n in existing}
    existing_ids = set(by_id.keys())
    new_nodes = []

    def full_id(prefix):
        matches = [i for i in existing_ids if i.startswith(prefix)]
        if len(matches) != 1:
            raise RuntimeError(f"node prefix {prefix!r} resolved to {matches} -- robot flow may have changed")
        return matches[0]

    def add(node):
        if node["id"] in existing_ids:
            raise RuntimeError(f"id collision: {node['id']}")
        new_nodes.append(node)
        return node["id"]

    def append_wire(source_prefix, output_index, target_id):
        node = by_id[full_id(source_prefix)]
        wires = node.setdefault("wires", [])
        while len(wires) <= output_index:
            wires.append([])
        wires[output_index].append(target_id)

    add({"id": TAB_ID, "type": "tab", "label": TAB_LABEL, "disabled": False, "info": (
        "Bridges the PyQt5 Windows dashboard to MISSION 1 / MISSION 2 over two "
        "WebSocket channels: /dashboard/control and /dashboard/status. All wires "
        "into/out of MISSION 1 / MISSION 2 were added without touching any "
        "existing node or wire -- see node-red-additions/README.md."
    )})
    new_nodes.append({"id": CONTROL_LISTENER, "type": "websocket-listener", "path": "/dashboard/control", "wholemsg": "false"})
    new_nodes.append({"id": STATUS_LISTENER, "type": "websocket-listener", "path": "/dashboard/status", "wholemsg": "false"})

    add({"id": "link_in_status", "type": "link in", "z": TAB_ID, "name": "Dashboard Status In", "links": [],
         "x": 140, "y": 40, "wires": [["format_status_json"]]})
    add({"id": "format_status_json", "type": "function", "z": TAB_ID, "name": "Format status JSON",
         "func": "msg.payload = JSON.stringify(msg.payload);\nreturn msg;",
         "outputs": 1, "timeout": 0, "noerr": 0, "initialize": "", "finalize": "", "libs": [],
         "x": 340, "y": 40, "wires": [["ws_out_status"]]})
    add({"id": "ws_out_status", "type": "websocket out", "z": TAB_ID, "name": "Dashboard Status Out",
         "server": STATUS_LISTENER, "client": "", "x": 560, "y": 40})

    tag_y = [100]

    def add_status_tag(tag_id, name, func_body):
        add({"id": tag_id, "type": "function", "z": TAB_ID, "name": name, "func": func_body,
             "outputs": 1, "timeout": 0, "noerr": 0, "initialize": "", "finalize": "", "libs": [],
             "x": 140, "y": tag_y[0], "wires": [["link_in_status"]]})
        tag_y[0] += 30

    def tap_func(mission, cp, also_complete):
        if also_complete:
            return (
                "var base = {mission: %d, checkpoint: %r};\n"
                "node.send([\n"
                "  {payload: Object.assign({event: 'checkpoint_reached'}, base)},\n"
                "  {payload: Object.assign({event: 'mission_complete'}, base)}\n"
                "]);\nreturn null;" % (mission, cp)
            )
        return f"msg.payload = {{mission: {mission}, event: 'checkpoint_reached', checkpoint: {cp!r}}};\nreturn msg;"

    for cp, source, out_idx, also_complete in MISSION1_TAPS:
        tag_id = f"tag_m1_{cp.lower()}"
        add_status_tag(tag_id, f"Tag M1 {cp}", tap_func(1, cp, also_complete))
        append_wire(source, out_idx, tag_id)

    for cp, source, out_idx, also_complete in MISSION2_TAPS:
        tag_id = f"tag_m2_{cp.lower()}"
        add_status_tag(tag_id, f"Tag M2 {cp}", tap_func(2, cp, also_complete))
        append_wire(source, out_idx, tag_id)

    add_status_tag("tag_m2_ocr", "Tag M2 OCR result", (
        "var text = msg.payload;\n"
        "if (text && typeof text === 'object') {\n"
        "  text = text.text || (text.result && text.result.text) || JSON.stringify(text);\n"
        "}\nmsg.payload = {mission: 2, event: 'ocr_result', text: text};\nreturn msg;"
    ))
    append_wire(OCR_TAP_PREFIX, 0, "tag_m2_ocr")

    add_status_tag("tag_m2_apriltag", "Tag M2 AprilTag detected", (
        "var id = msg.payload;\n"
        "if (id && typeof id === 'object') {\n"
        "  id = (id.id !== undefined) ? id.id : ((id.result && id.result.id !== undefined) ? id.result.id : JSON.stringify(id));\n"
        "}\nmsg.payload = {mission: 2, event: 'apriltag_detected', id: id};\nreturn msg;"
    ))
    append_wire(APRILTAG_TAP_PREFIX, 0, "tag_m2_apriltag")

    add_status_tag("tag_m2_waiting", "Tag M2 waiting for staff",
                   "msg.payload = {mission: 2, event: 'waiting_for_staff'};\nreturn msg;")
    append_wire(WAITING_TAP_PREFIX, 0, "tag_m2_waiting")

    add({"id": "comment_control", "type": "comment", "z": TAB_ID,
         "name": "Control side -- wired directly to real MISSION 1 / MISSION 2 nodes (see README)",
         "info": "", "x": 220, "y": 480, "wires": []})
    add({"id": "ws_in_control", "type": "websocket in", "z": TAB_ID, "name": "Dashboard Control In",
         "server": CONTROL_LISTENER, "client": "", "x": 140, "y": 520, "wires": [["json_parse_control"]]})
    add({"id": "json_parse_control", "type": "json", "z": TAB_ID, "name": "Parse JSON", "property": "payload",
         "action": "", "pretty": False, "x": 330, "y": 520, "wires": [["switch_cmd"]]})

    cmd_outputs = ["start_mission", "trigger_checkpoint", "trigger_ocr", "trigger_apriltag"]
    add({"id": "switch_cmd", "type": "switch", "z": TAB_ID, "name": "route on payload.cmd",
         "property": "payload.cmd", "propertyType": "msg",
         "rules": [{"t": "eq", "v": v, "vt": "str"} for v in cmd_outputs],
         "checkall": "true", "repair": False, "outputs": len(cmd_outputs), "x": 520, "y": 520,
         "wires": [["switch_start_mission"], ["switch_checkpoint_mission"], ["stub_ocr_direct"], ["stub_apriltag_direct"]]})

    add({"id": "switch_start_mission", "type": "switch", "z": TAB_ID, "name": "route on payload.mission (start)",
         "property": "payload.mission", "propertyType": "msg",
         "rules": [{"t": "eq", "v": "1", "vt": "num"}, {"t": "eq", "v": "2", "vt": "num"}],
         "checkall": "true", "repair": False, "outputs": 2, "x": 760, "y": 460,
         "wires": [[full_id(MISSION1_START_PREFIX)], [full_id(MISSION2_START_PREFIX)]]})

    add({"id": "switch_checkpoint_mission", "type": "switch", "z": TAB_ID,
         "name": "route on payload.mission (checkpoint)", "property": "payload.mission", "propertyType": "msg",
         "rules": [{"t": "eq", "v": "1", "vt": "num"}, {"t": "eq", "v": "2", "vt": "num"}],
         "checkall": "true", "repair": False, "outputs": 2, "x": 760, "y": 520,
         "wires": [["switch_checkpoint_m1"], ["switch_checkpoint_m2"]]})

    m1_targets = {k: full_id(v) for k, v in MISSION1_TRIGGERS.items()}
    add({"id": "switch_checkpoint_m1", "type": "switch", "z": TAB_ID, "name": "M1: route on payload.checkpoint",
         "property": "payload.checkpoint", "propertyType": "msg",
         "rules": [{"t": "eq", "v": k, "vt": "str"} for k in m1_targets],
         "checkall": "true", "repair": False, "outputs": len(m1_targets), "x": 980, "y": 460,
         "wires": [[v] for v in m1_targets.values()]})

    m2_targets = {k: full_id(v) for k, v in MISSION2_TRIGGERS.items()}
    add({"id": "switch_checkpoint_m2", "type": "switch", "z": TAB_ID, "name": "M2: route on payload.checkpoint",
         "property": "payload.checkpoint", "propertyType": "msg",
         "rules": [{"t": "eq", "v": k, "vt": "str"} for k in m2_targets],
         "checkall": "true", "repair": False, "outputs": len(m2_targets), "x": 980, "y": 560,
         "wires": [[v] for v in m2_targets.values()]})

    add({"id": "stub_ocr_direct", "type": "function", "z": TAB_ID, "name": "-> real OCR trigger (M2)",
         "func": "return msg;", "outputs": 1, "timeout": 0, "noerr": 0, "initialize": "", "finalize": "", "libs": [],
         "x": 760, "y": 620, "wires": [[full_id(OCR_TRIGGER_PREFIX)]]})
    add({"id": "stub_apriltag_direct", "type": "function", "z": TAB_ID, "name": "-> real AprilTag trigger (M2)",
         "func": "return msg;", "outputs": 1, "timeout": 0, "noerr": 0, "initialize": "", "finalize": "", "libs": [],
         "x": 760, "y": 660, "wires": [[full_id(APRILTAG_TRIGGER_PREFIX)]]})

    new_ids = {n["id"] for n in new_nodes}
    for n in new_nodes:
        for out in n.get("wires", []):
            for target in out:
                if target not in new_ids and target not in existing_ids:
                    raise RuntimeError(f"dangling target {target} from {n['id']}")

    return existing + new_nodes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host")
    parser.add_argument("--port", type=int, default=1880)
    parser.add_argument("--dry-run", action="store_true", help="build and validate but don't POST")
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"
    print(f"Fetching current flows from {base_url}/flows ...")
    existing = fetch_flows(base_url)
    print(f"  {len(existing)} existing nodes")

    merged = build_patch(existing)
    print(f"  {len(merged) - len(existing)} new nodes to add")

    if args.dry_run:
        print("--dry-run: not posting. Patch validated OK.")
        return

    print(f"Deploying to {base_url}/flows ...")
    post_flows(base_url, merged)
    print("Deployed.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, urllib.error.URLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
