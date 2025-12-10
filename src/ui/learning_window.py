from PyQt5.QtWidgets import (
    QPushButton, QMessageBox, QProgressDialog, QDialog, QVBoxLayout,
    QLabel, QTextEdit, QDialogButtonBox, QFrame, QHBoxLayout, QTextBrowser
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from ui.test_window import TestWindow
from ui.hint_worker import HintWorker
import webbrowser
import json
import os
import openai

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

class StudyTopicWorker(QThread):
    """Worker thread to fetch study resources from OpenAI."""
    finished = pyqtSignal(dict)  # emits {"url": "...", "title": "...", "keywords": "..."}
    error = pyqtSignal(str)

    def __init__(self, question_text, exam_type, api_key=None):
        super().__init__()
        self.question_text = question_text
        self.exam_type = exam_type
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")

    def run(self):
        try:
            if not self.api_key:
                raise ValueError("OpenAI API key not found.")

            openai.api_key = self.api_key

            # Step 1: Extract keywords from question
            keyword_prompt = f"""Extract 2-3 main topics/keywords from this question:
{self.question_text}

Return ONLY the keywords separated by commas, no explanation."""

            keyword_response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": keyword_prompt}],
                max_tokens=100,
                temperature=0.3
            )
            keywords = keyword_response.choices[0].message.content.strip()

            # Step 2: Find best study resource
            exam_context = ""
            if self.exam_type and self.exam_type != "Other":
                exam_context = f"This is for {self.exam_type} exam preparation. "

            resource_prompt = f"""{exam_context}Suggest ONE best FREE online study resource (website) for learning about: {keywords}

Prioritize: Khan Academy > Wikipedia > Britannica > Official textbooks > Educational blogs

Return ONLY valid JSON (no markdown):
{{"url": "https://...", "title": "Resource Title"}}

No explanation, just JSON."""

            resource_response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": resource_prompt}],
                max_tokens=300,
                temperature=0.3
            )
            
            result_text = resource_response.choices[0].message.content.strip()
            
            # Extract JSON
            start = result_text.find('{')
            end = result_text.rfind('}') + 1
            if start == -1 or end == 0:
                raise ValueError("No valid JSON in response.")
            
            json_str = result_text[start:end]
            data = json.loads(json_str)
            
            # Validate URL
            if "url" not in data or not data["url"].startswith("http"):
                raise ValueError("Invalid URL in response.")
            
            data["keywords"] = keywords
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))


class LearningWindow(TestWindow):
    """
    Learning mode window. Inherits behaviour from TestWindow and
    adds hint support and simple hint-usage tracking.
    """

    def __init__(self, pdf_path, time_limit, num_questions, exam_type="Other",
                 marks_per_correct=1.0, negative_mark=0.0):
        super().__init__(pdf_path, time_limit, num_questions, exam_type=exam_type,
                         marks_per_correct=marks_per_correct, negative_mark=negative_mark)
        self.learning_mode = True
        self.hints_used = {}
        self.hint_limit = 6
        self.user_question_texts = {}
        self.user_option_texts = {}
        self.study_resources_cache = {}  # Cache: question_idx -> resource data
        self._add_learning_controls()
        self._build_hint_panel()
        try:
            self.setWindowTitle(f"Learning Mode — {self.exam_type}")
        except Exception:
            pass

    def _add_learning_controls(self):
        self.hint_button = QPushButton("Hint")
        self.hint_button.setFont(QFont("Arial", 11, QFont.Bold))
        self.hint_button.setToolTip("Request a hint for the current question (limited)")
        self.hint_button.clicked.connect(self.request_hint)

        self.study_button = QPushButton("Study this topic")
        self.study_button.setFont(QFont("Arial", 11, QFont.Bold))
        self.study_button.setToolTip("Find a study resource for this question's topic")
        self.study_button.clicked.connect(self.request_study_resource)

        # Place buttons into exposed layout if available
        try:
            if hasattr(self, "actions_layout_bottom") and self.actions_layout_bottom is not None:
                self.actions_layout_bottom.addWidget(self.hint_button)
                self.actions_layout_bottom.addWidget(self.study_button)
            else:
                root = self.layout()
                if root is not None:
                    root.addWidget(self.hint_button)
                    root.addWidget(self.study_button)
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

    def request_study_resource(self):
        """Request a study resource for the current question's topic."""
        idx = getattr(self, "current_question", 0)

        # Check cache first
        if idx in self.study_resources_cache:
            resource = self.study_resources_cache[idx]
            self._open_study_resource(resource)
            return

        # Get question text
        qtext = getattr(self, "current_question_text", None)
        if not qtext and idx in self.user_question_texts:
            qtext = self.user_question_texts[idx]

        if not qtext:
            initial_q = qtext or ""
            dlg = QuestionContextDialog(self, initial_q, "")
            dlg.accepted.connect(lambda d=dlg: self._on_study_context_provided(d))
            dlg.rejected.connect(lambda: None)
            dlg.show()
            return

        self._start_study_worker(qtext)

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

    def _on_study_context_provided(self, dlg):
        """Called when user provides question text for study resource."""
        idx = getattr(self, "current_question", 0)
        qtext, _ = dlg.get_values()
        if qtext:
            self.user_question_texts[idx] = qtext
            self._start_study_worker(qtext)
        else:
            self._show_warning("Missing Input", "Please enter the question text to find study resources.")

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

    def _start_study_worker(self, qtext):
        """Start worker to fetch study resource from OpenAI."""
        self._progress = QProgressDialog("Finding study resource...", "Hide", 0, 0, self)
        self._progress.setModal(False)
        self._progress.setWindowModality(Qt.NonModal)
        self._progress.setAutoClose(True)
        self._progress.setAutoReset(True)
        self._progress.setMinimumDuration(0)
        self._progress.show()

        self._study_worker = StudyTopicWorker(
            question_text=qtext,
            exam_type=self.exam_type
        )
        self._study_worker.finished.connect(self._on_study_resource_ready)
        self._study_worker.error.connect(self._on_study_resource_error)
        self._study_worker.start()

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

    def _on_study_resource_ready(self, resource_data):
        """Called when study resource is fetched successfully."""
        try:
            if hasattr(self, "_progress"):
                self._progress.close()
            
            idx = getattr(self, "current_question", 0)
            self.study_resources_cache[idx] = resource_data
            
            self._open_study_resource(resource_data)
        finally:
            try:
                self._study_worker.quit()
                self._study_worker.wait(100)
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

    def _on_study_resource_error(self, msg):
        """Called when study resource fetch fails."""
        if hasattr(self, "_progress"):
            self._progress.close()
        self._show_warning("Study Resource Error", f"Failed to find study resource:\n{msg}")
        try:
            self._study_worker.quit()
            self._study_worker.wait(100)
        except Exception:
            pass

    def _open_study_resource(self, resource_data):
        """Open the study resource in browser."""
        url = resource_data.get("url", "")
        title = resource_data.get("title", "Resource")
        keywords = resource_data.get("keywords", "")
        
        if not url:
            self._show_warning("Invalid Resource", "Resource URL is empty.")
            return
        
        # Show confirmation with resource details
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Study Resource Found")
        msg.setText(f"<b>{title}</b><br/><br/>Keywords: {keywords}<br/><br/>Opening in browser...")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setModal(False)
        msg.setWindowModality(Qt.NonModal)
        msg.setAttribute(Qt.WA_DeleteOnClose, True)
        msg.show()
        
        # Open in default browser
        try:
            webbrowser.open(url)
        except Exception as e:
            self._show_warning("Browser Error", f"Failed to open URL:\n{e}")