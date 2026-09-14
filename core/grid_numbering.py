"""Converts between the robot's cell numbering (1 = bottom-left, increasing
left-to-right then bottom-to-top -- matching the robot mapping reference
image) and (row, col) grid coordinates used internally for drawing, where
row 0 is the TOP row.
"""

GRID_ROWS = 4
GRID_COLS = 4


def number_to_rc(number: int, rows: int = GRID_ROWS, cols: int = GRID_COLS) -> tuple:
    idx = number - 1
    row_from_bottom = idx // cols
    row = rows - 1 - row_from_bottom
    col = idx % cols
    return (row, col)


def rc_to_number(row: int, col: int, rows: int = GRID_ROWS, cols: int = GRID_COLS) -> int:
    row_from_bottom = rows - 1 - row
    return row_from_bottom * cols + col + 1


def resolve_config_cells(config: dict, rows: int = GRID_ROWS, cols: int = GRID_COLS) -> dict:
    """Expands 'cell_number' (as edited in missions.json, matching the robot
    mapping picture) into internal (row, col) tuples the UI widgets use."""
    for definition in config.get("checkpoints", {}).values():
        definition["cell"] = number_to_rc(definition["cell_number"], rows, cols)

    landmarks = config.get("landmarks", {})
    config["landmarks"] = {label: number_to_rc(number, rows, cols) for label, number in landmarks.items()}

    return config
