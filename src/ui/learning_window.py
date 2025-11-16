from PyQt5.QtWidgets import QPushButton, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from ui.test_window import TestWindow

class LearningWindow(TestWindow):
    """
    Learning mode window. Inherits all behaviour from TestWindow and
    adds hint support, per-question logging and learning-specific UI.
    """

    def __init__(self, pdf_path, time_limit, num_questions):
        # initialize base TestWindow (keeps PDF viewer, question navigation, timer etc.)
        super().__init__(pdf_path, time_limit, num_questions)

        # mark mode
        self.learning_mode = True
        self.hints_used = {}         # question_index -> count
        self.hint_limit = 2          # default limit, changeable
        self._add_learning_controls()

        # change window title to indicate learning mode
        try:
            self.setWindowTitle("Learning Mode - TestMocker")
        except Exception:
            pass

    def _add_learning_controls(self):
        """
        Add learning-mode controls. This attempts to add a Hint button
        next to existing action buttons. If the exact test_window layout
        differs, adjust this method to place the button where desired.
        """
        # create hint button
        self.hint_button = QPushButton("Hint")
        self.hint_button.setFont(QFont("Arial", 11, QFont.Bold))
        self.hint_button.setToolTip("Request a hint for the current question (limited)")
        self.hint_button.clicked.connect(self.request_hint)

        # Try to place the button next to existing action area
        # If TestWindow created a layout or known container (e.g. self.actions_layout_bottom),
        # add it there; otherwise add it to the main layout if available.
        try:
            if hasattr(self, "actions_layout_bottom"):
                self.actions_layout_bottom.addWidget(self.hint_button)
            elif hasattr(self, "right_layout"):
                self.right_layout.addWidget(self.hint_button)
            else:
                # best-effort: add to layout() root if present
                root = self.layout()
                if root is not None:
                    root.addWidget(self.hint_button)
        except Exception:
            # non-fatal: leave the button floating; user can refine placement later
            pass

    def request_hint(self):
        """Called when the user clicks 'Hint'."""
        idx = getattr(self, "current_question", 0)
        used = self.hints_used.get(idx, 0)
        if used >= self.hint_limit:
            QMessageBox.information(self, "Hint limit", "No more hints allowed for this question.")
            return

        # TODO: check for static hint first (self.get_static_hint)
        # If not available, spawn HintWorker (QThread) to fetch dynamic hint.
        # For now show a placeholder hint and increment counter.
        QMessageBox.information(self, "Hint", "Placeholder hint — implement HintWorker to fetch actual hints.")
        self.hints_used[idx] = used + 1

    # Add other learning-mode helpers (logging attempts, storing hint counts, etc.)
    # def log_attempt(self, question_index, selected_answer, time_spent, hint_count): ...
    # def get_static_hint(self, question_index): ...
    # def show_hint_dialog(self, hint_text): ...