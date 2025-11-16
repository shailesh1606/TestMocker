from PyQt5.QtWidgets import (
    QPushButton, QMessageBox, QProgressDialog, QDialog, QVBoxLayout,
    QLabel, QTextEdit, QDialogButtonBox, QFrame, QHBoxLayout, QTextBrowser
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from ui.test_window import TestWindow
from ui.hint_worker import HintWorker
import uuid
from db import storage

class QuestionContextDialog(QDialog):
    def __init__(self, parent=None, initial_question="", initial_options=""):
        super().__init__(parent)
        self.setWindowTitle("Add Question Context")
        # Modeless, focusable dialog (no tool flag)
        self.setModal(False)
        self.setWindowModality(Qt.NonModal)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Enter the question text (optional but recommended):"))
        self.question_edit = QTextEdit(self)
        self.question_edit.setPlainText(initial_question or "")
        self.question_edit.setMinimumHeight(120)
        layout.addWidget(self.question_edit)

        layout.addWidget(QLabel("Enter options (one per line, optional):"))
        self.options_edit = QTextEdit(self)
        self.options_edit.setPlainText(initial_options or "")
        self.options_edit.setMinimumHeight(100)
        layout.addWidget(self.options_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self):
        qtext = self.question_edit.toPlainText().strip()
        options_text = self.options_edit.toPlainText().strip()
        options = [line.strip() for line in options_text.splitlines() if line.strip()]
        return qtext, options

class LearningWindow(TestWindow):
    """
    Learning mode window. Inherits behaviour from TestWindow and
    adds hint support and simple hint-usage tracking.
    """

    def __init__(self, pdf_path, time_limit, num_questions):
        super().__init__(pdf_path, time_limit, num_questions)
        self.learning_mode = True
        self.hints_used = {}              # question_index -> count
        self.hint_limit = 6               # default limit
        self.attempt_uuid = str(uuid.uuid4())
        self.user_question_texts = {}     # user-provided context per question
        self.user_option_texts = {}       # user-provided options per question (list[str])
        self._add_learning_controls()
        self._build_hint_panel()
        try:
            self.setWindowTitle("Learning Mode - TestMocker")
        except Exception:
            pass

    def _add_learning_controls(self):
        self.hint_button = QPushButton("Hint")
        self.hint_button.setFont(QFont("Arial", 11, QFont.Bold))
        self.hint_button.setToolTip("Request a hint for the current question (limited)")
        self.hint_button.clicked.connect(self.request_hint)

        # Place hint button into exposed layout if available
        try:
            if hasattr(self, "actions_layout_bottom") and self.actions_layout_bottom is not None:
                self.actions_layout_bottom.addWidget(self.hint_button)
            else:
                root = self.layout()
                if root is not None:
                    root.addWidget(self.hint_button)
        except Exception:
            pass

    def _build_hint_panel(self):
        # Inline, non-modal hint panel (hidden by default)
        self.hint_panel = QFrame(self)
        self.hint_panel.setFrameShape(QFrame.StyledPanel)
        self.hint_panel.setObjectName("hintPanel")
        self.hint_panel.setStyleSheet("""
            QFrame#hintPanel {
                background: #fffbea;
                border: 1px solid #ffe082;
                border-radius: 8px;
            }
        """)
        v = QVBoxLayout(self.hint_panel)
        v.setContentsMargins(10, 10, 10, 10)
        title_row = QHBoxLayout()
        title = QLabel("Hint")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title_row.addWidget(title)
        title_row.addStretch()
        self.hint_close_btn = QPushButton("×")
        self.hint_close_btn.setFixedWidth(28)
        self.hint_close_btn.clicked.connect(self._hide_hint_panel)
        title_row.addWidget(self.hint_close_btn)
        v.addLayout(title_row)

        self.hint_body = QTextBrowser(self.hint_panel)
        self.hint_body.setOpenExternalLinks(True)
        self.hint_body.setStyleSheet("QTextBrowser { background: transparent; border: none; }")
        v.addWidget(self.hint_body)

        # Place the panel in a sensible area (e.g., right side or at bottom)
        try:
            # If TestWindow has a right_layout, add there; else add to root
            if hasattr(self, "right_layout") and self.right_layout is not None:
                self.right_layout.addWidget(self.hint_panel)
            else:
                root = self.layout()
                if root is not None:
                    root.addWidget(self.hint_panel)
        except Exception:
            pass
        self.hint_panel.hide()

    def _show_hint_panel(self, html_text):
        self.hint_body.setHtml(html_text)
        self.hint_panel.show()
        self.hint_panel.raise_()

    def _hide_hint_panel(self):
        self.hint_panel.hide()

    def _show_warning(self, title, text):
        # Keep warnings non-blocking and modeless
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setModal(False)
        msg.setWindowModality(Qt.NonModal)
        msg.setAttribute(Qt.WA_DeleteOnClose, True)
        msg.show()

    def request_hint(self):
        idx = getattr(self, "current_question", 0)
        used = self.hints_used.get(idx, 0)
        if used >= self.hint_limit:
            # Use inline panel to notify limit
            self._show_hint_panel("<b>No more hints</b><br/>You have used all hints for this question.")
            return

        # Try to use any context exposed by TestWindow
        qtext = getattr(self, "current_question_text", None)
        options = getattr(self, "current_options", None)

        # If not available, use user-provided context (cached) or prompt for it
        if not qtext and idx in self.user_question_texts:
            qtext = self.user_question_texts[idx]
        if (not options or len(options) == 0) and idx in self.user_option_texts:
            options = self.user_option_texts[idx]

        if not qtext or not options:
            initial_q = qtext or ""
            initial_opts = "\n".join(options) if options else ""
            dlg = QuestionContextDialog(self, initial_q, initial_opts)
            # Modeless: continue in callback on accept
            dlg.accepted.connect(lambda d=dlg: self._on_context_provided(d))
            dlg.rejected.connect(lambda: None)
            dlg.show()
            return

        # Still missing both? Fall back to minimal placeholders
        if not qtext:
            qtext = f"Question {idx+1} (text not available). Provide a conceptual hint."
        if not options:
            options = ["A", "B", "C", "D"]

        self._start_hint_worker(qtext, options)

    def _on_context_provided(self, dlg):
        idx = getattr(self, "current_question", 0)
        qtext, options = dlg.get_values()
        if qtext:
            self.user_question_texts[idx] = qtext
        if options:
            self.user_option_texts[idx] = options
        if not qtext:
            qtext = f"Question {idx+1} (text not available). Provide a conceptual hint."
        if not options:
            options = ["A", "B", "C", "D"]
        self._start_hint_worker(qtext, options)

    def _start_hint_worker(self, qtext, options):
        # Modeless progress indicator
        self._progress = QProgressDialog("Fetching hint...", "Hide", 0, 0, self)
        self._progress.setModal(False)
        self._progress.setWindowModality(Qt.NonModal)
        self._progress.setAutoClose(True)
        self._progress.setAutoReset(True)
        self._progress.setMinimumDuration(0)
        self._progress.show()

        self._hint_worker = HintWorker(question_text=qtext, options=options)
        self._hint_worker.finished.connect(self._on_hint_ready)
        self._hint_worker.error.connect(self._on_hint_error)
        self._hint_worker.start()

    def _on_hint_ready(self, hint_text):
        try:
            if hasattr(self, "_progress"):
                self._progress.close()
            idx = getattr(self, "current_question", 0)
            self.hints_used[idx] = self.hints_used.get(idx, 0) + 1
            # Render hint inline (HTML escaped by QTextBrowser automatically if plain)
            self._show_hint_panel(hint_text)
        finally:
            try:
                self._hint_worker.quit()
                self._hint_worker.wait(100)
            except Exception:
                pass

    def _on_hint_error(self, msg):
        if hasattr(self, "_progress"):
            self._progress.close()
        self._show_warning("Hint Error", f"Failed to fetch hint:\n{msg}")
        try:
            self._hint_worker.quit()
            self._hint_worker.wait(100)
        except Exception:
            pass

    def _log_all_attempts(self):
        """
        Persist all answered questions from this session to DB.
        correct_answer/time_spent not tracked in learning mode yet.
        """
        try:
            num_q = getattr(self, "num_questions", 0)
            answers = getattr(self, "answers", [])
            for i in range(num_q):
                selected = answers[i] if i < len(answers) else None
                hint_count = self.hints_used.get(i, 0)
                storage.log_attempt(
                    attempt_uuid=self.attempt_uuid,
                    question_index=i,
                    selected_answer=selected,
                    correct_answer=None,
                    time_spent_sec=0,
                    hint_count=hint_count
                )
        except Exception:
            pass

    def submit_test(self, auto=False):
        """
        On submit in learning mode, log attempts to DB, then reuse base flow.
        """
        try:
            if hasattr(self, "save_current_answer"):
                self.save_current_answer()
        except Exception:
            pass
        self._log_all_attempts()
        return super().submit_test(auto)