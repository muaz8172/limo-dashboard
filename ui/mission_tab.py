from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.mission_state import MissionState
from ui.checkpoint_button import CheckpointButton
from ui.gamefield_widget import GameFieldWidget

CHECKPOINT_COLUMNS = 6


class MissionTab(QWidget):
    """One mission's full UI: objective checklist, gamefield, a palette of
    individually-clickable checkpoint buttons (shared library, reused
    across missions), a Start Mission button, and an event log.
    """

    def __init__(self, mission_id: str, mission_def: dict, checkpoints_lib: dict, landmarks: dict, bridge_client, parent=None):
        super().__init__(parent)
        self.mission_id = mission_id
        self.mission_def = mission_def
        self.checkpoints_lib = checkpoints_lib
        self.bridge_client = bridge_client
        self.state = MissionState(mission_id, mission_def, parent=self)
        self._checkpoint_buttons = {}

        self._build_ui(landmarks)

        self.bridge_client.status_event.connect(self._on_status_event)
        self.state.updated.connect(self._refresh_ui)
        self._refresh_ui()

    def _build_ui(self, landmarks: dict) -> None:
        layout = QVBoxLayout(self)

        title = QLabel(self.mission_def["name"])
        title_font = title.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        top_row = QHBoxLayout()

        objective_group = QGroupBox("Mission Objective")
        objective_layout = QVBoxLayout(objective_group)
        self.objective_label = QLabel()
        self.objective_label.setWordWrap(True)
        objective_layout.addWidget(self.objective_label)
        top_row.addWidget(objective_group, 1)

        field_group = QGroupBox("Gamefield")
        field_layout = QVBoxLayout(field_group)
        self.gamefield = GameFieldWidget(landmarks=landmarks)
        field_layout.addWidget(self.gamefield)
        top_row.addWidget(field_group, 1)

        layout.addLayout(top_row)

        checkpoint_group = QGroupBox("Checkpoints (click to trigger manually)")
        checkpoint_layout = QGridLayout(checkpoint_group)
        for index, checkpoint_id in enumerate(self.mission_def["route"]):
            definition = self.checkpoints_lib.get(checkpoint_id, {"label": checkpoint_id, "group": ""})
            button = CheckpointButton(checkpoint_id, definition)
            button.clicked.connect(lambda _checked, cid=checkpoint_id: self._trigger_checkpoint(cid))
            checkpoint_layout.addWidget(button, index // CHECKPOINT_COLUMNS, index % CHECKPOINT_COLUMNS)
            self._checkpoint_buttons[checkpoint_id] = button
        layout.addWidget(checkpoint_group)

        controls_row = QHBoxLayout()
        self.start_button = QPushButton("Start Mission")
        self.start_button.clicked.connect(self._start_mission)
        controls_row.addWidget(self.start_button)
        controls_row.addStretch()
        layout.addLayout(controls_row)

        log_group = QGroupBox("Event Log")
        log_layout = QVBoxLayout(log_group)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(500)
        log_layout.addWidget(self.log_view)
        layout.addWidget(log_group, 1)

    def _trigger_checkpoint(self, checkpoint_id: str) -> None:
        if checkpoint_id == "OCR":
            command = {"cmd": "trigger_ocr"}
        elif checkpoint_id == "APRILTAG":
            command = {"cmd": "trigger_apriltag"}
        else:
            command = {"cmd": "trigger_checkpoint", "checkpoint": checkpoint_id}

        if self.bridge_client.send_command(command):
            self.state.mark_checkpoint_triggered(checkpoint_id)
        else:
            self.log_view.appendPlainText("Not connected -- command not sent.")

    def _start_mission(self) -> None:
        command = {"cmd": "start_mission", "mission": int(self.mission_id)}
        if not self.bridge_client.send_command(command):
            self.log_view.appendPlainText("Not connected -- command not sent.")

    def _on_status_event(self, event: dict) -> None:
        if str(event.get("mission")) != str(self.mission_id):
            return
        self.state.handle_event(event)

    def _refresh_ui(self) -> None:
        completed = self.state.completed_step_count()
        lines = []
        for i, step in enumerate(self.mission_def["steps"]):
            mark = "✅" if i < completed else "⬜"
            lines.append(f"{mark} {step}")
        self.objective_label.setText("\n".join(lines))

        active_def = self.checkpoints_lib.get(self.state.active_checkpoint) if self.state.active_checkpoint else None
        self.gamefield.set_active_cell(active_def["cell"] if active_def else None)

        visited_cells = [
            self.checkpoints_lib[cid]["cell"] for cid in self.state.visited if cid in self.checkpoints_lib
        ]
        self.gamefield.set_visited_cells(visited_cells)

        for checkpoint_id, button in self._checkpoint_buttons.items():
            button.set_active(checkpoint_id == self.state.active_checkpoint)
            button.set_visited(checkpoint_id in self.state.visited)

        self.log_view.setPlainText("\n".join(self.state.log_entries))
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
