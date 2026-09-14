from PyQt5.QtWidgets import QPushButton

DEFAULT_STYLE = "background-color: #e0e0e0; color: #212121; border: 1px solid #9e9e9e; padding: 4px;"
VISITED_STYLE = "background-color: #c8e6c9; color: #1b5e20; border: 1px solid #66bb6a; padding: 4px;"
ACTIVE_STYLE = "background-color: #1e88e5; color: white; font-weight: bold; border: 2px solid #0d47a1; padding: 4px;"


class CheckpointButton(QPushButton):
    """One checkpoint from the shared library, rendered as a clickable button.

    Built from a single checkpoint definition (id, label, group) so the
    same checkpoint can be instantiated by multiple mission tabs without
    duplicating its config -- editing the definition once updates every
    tab that uses it.
    """

    def __init__(self, checkpoint_id: str, definition: dict, parent=None):
        super().__init__(definition.get("label", checkpoint_id), parent)
        self.checkpoint_id = checkpoint_id
        self.group = definition.get("group", "")
        self.setToolTip(self.group)
        self._active = False
        self._visited = False
        self._apply_style()

    def set_active(self, active: bool) -> None:
        if active == self._active:
            return
        self._active = active
        self._apply_style()

    def set_visited(self, visited: bool) -> None:
        if visited == self._visited:
            return
        self._visited = visited
        self._apply_style()

    def _apply_style(self) -> None:
        if self._active:
            self.setStyleSheet(ACTIVE_STYLE)
        elif self._visited:
            self.setStyleSheet(VISITED_STYLE)
        else:
            self.setStyleSheet(DEFAULT_STYLE)
