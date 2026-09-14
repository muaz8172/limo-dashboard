from PyQt5.QtCore import QObject, pyqtSignal

MAX_LOG_ENTRIES = 300


class MissionState(QObject):
    """Tracks one mission's live progress from incoming status events.

    Checklist steps aren't given a 1:1 mapping to checkpoints by the
    robot side, so step completion is driven by overall route progress
    (checkpoints visited / total checkpoints in the route) rather than
    guessing which specific event maps to which step text.
    """

    updated = pyqtSignal()

    def __init__(self, mission_id: str, mission_def: dict, parent=None):
        super().__init__(parent)
        self.mission_id = mission_id
        self.route = mission_def["route"]
        self.steps = mission_def["steps"]
        self.reset()

    def reset(self) -> None:
        self.active_checkpoint = None
        self.visited = set()
        self.last_ocr_text = None
        self.last_apriltag_id = None
        self.waiting_for_staff = False
        self.mission_complete = False
        self.log_entries = []
        self.updated.emit()

    def _log(self, message: str) -> None:
        self.log_entries.append(message)
        if len(self.log_entries) > MAX_LOG_ENTRIES:
            del self.log_entries[: len(self.log_entries) - MAX_LOG_ENTRIES]

    def handle_event(self, event: dict) -> None:
        etype = event.get("event")
        if etype == "checkpoint_reached":
            cp = event.get("checkpoint")
            self.active_checkpoint = cp
            if cp:
                self.visited.add(cp)
            self._log(f"Checkpoint reached: {cp}")
        elif etype == "ocr_result":
            self.last_ocr_text = event.get("text")
            self.active_checkpoint = "OCR"
            self.visited.add("OCR")
            self._log(f"OCR result: {self.last_ocr_text}")
        elif etype == "apriltag_detected":
            self.last_apriltag_id = event.get("id")
            self.active_checkpoint = "APRILTAG"
            self.visited.add("APRILTAG")
            self._log(f"AprilTag detected: {self.last_apriltag_id}")
        elif etype == "waiting_for_staff":
            self.waiting_for_staff = True
            self._log("Waiting for staff to open toll barrier")
        elif etype == "mission_complete":
            self.mission_complete = True
            self._log("Mission complete")
        else:
            self._log(f"Unhandled event: {event}")
        self.updated.emit()

    def mark_checkpoint_triggered(self, checkpoint_id: str) -> None:
        """Optimistically highlight a manually-clicked checkpoint before its status event arrives."""
        self.active_checkpoint = checkpoint_id
        self._log(f"Manually triggered: {checkpoint_id}")
        self.updated.emit()

    @property
    def progress_fraction(self) -> float:
        total = len(self.route)
        if total == 0:
            return 1.0 if self.mission_complete else 0.0
        return len(self.visited) / total

    def completed_step_count(self) -> int:
        if self.mission_complete:
            return len(self.steps)
        return min(len(self.steps), int(self.progress_fraction * len(self.steps)))
