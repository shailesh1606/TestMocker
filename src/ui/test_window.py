from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QHBoxLayout, QRadioButton,
    QPushButton, QButtonGroup, QSizePolicy, QGroupBox, QGridLayout, QMessageBox,
    QSplitter, QWidget, QSlider, QDialog, QLineEdit, QComboBox
)
from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5.QtGui import QPixmap, QImage, QFont, QIntValidator
import fitz  # PyMuPDF
from ui.results_window import ResultsWindow
from ui.answer_key_dialog import AnswerKeyDialog
from ui.pymupdf_selectable_view import SelectablePdfViewer
import uuid
from db import storage

STATE_COLORS = {
    "not_visited": "#bdbdbd",      # grey
    "current" : "#f9f9f9",         #white
    "not_answered": "#e57373",     # red
    "answered": "#66bb6a",         # green
    "review": "#7e57c2",           # purple
}

class TestWindow(QWidget):
    def __init__(self, pdf_path, time_limit=60, num_questions=10, exam_type="Other",
                 marks_per_correct=1.0, negative_mark=0.0):
        super().__init__()
        self.exam_type = exam_type
        self.marks_per_correct = float(marks_per_correct)
        self.negative_mark = float(negative_mark)
        self.time_limit = time_limit
        self.num_questions = num_questions
        self.current_question = 0
        # Store answers as dicts:
        # {"type": "mcq", "value": 0..3} or {"type": "numeric", "value": "123"} or {"type": "text", "value": "NaCl"}
        self.answers = [None] * num_questions
        # Default question types (all mcq); can be changed per question from UI
        self.question_types = ["mcq"] * num_questions

        self.question_states = ["not_visited"] * self.num_questions
        self.review_flags = [False] * self.num_questions
        self.attempt_uuid = str(uuid.uuid4())

        self.setWindowTitle('Take Test')
        self.setGeometry(150, 150, 1200, 800)
        self.timer = QTimer(self)
        hours = self.time_limit // 60
        minutes = self.time_limit % 60
        self.time_left = QTime(hours, minutes, 0)
        self.timer.timeout.connect(self.update_timer)
        self.init_ui(pdf_path)
        self.start_timer()

    def init_ui(self, pdf_path):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(30)

        # Left: PDF Viewer
        pdf_layout = QVBoxLayout()
        pdf_layout.setSpacing(10)
        if not pdf_path:
            no_pdf_label = QLabel("No PDF uploaded.")
            no_pdf_label.setFont(QFont("Arial", 14, QFont.Bold))
            pdf_layout.addWidget(no_pdf_label)
        else:
            self.pdf_viewer = SelectablePdfViewer(pdf_path, zoom=1.5)
            pdf_layout.addWidget(self.pdf_viewer)
            self.zoom_slider = QSlider(Qt.Horizontal)
            self.zoom_slider.setMinimum(10)
            self.zoom_slider.setMaximum(300)
            self.zoom_slider.setValue(150)
            self.zoom_slider.setTickInterval(10)
            self.zoom_slider.setTickPosition(QSlider.TicksBelow)
            self.zoom_slider.setToolTip("Zoom")
            zoom_label = QLabel("Zoom:")
            zoom_label.setFont(QFont("Arial", 10, QFont.Bold))
            pdf_layout.addWidget(zoom_label)
            pdf_layout.addWidget(self.zoom_slider)
            self.pdf_path = pdf_path

        # Right: Q&A UI
        right_layout = QVBoxLayout()
        right_layout.setSpacing(20)

        # Palette
        self.palette_box = QGroupBox("Question Palette")
        self.palette_box.setFont(QFont("Arial", 11, QFont.Bold))
        palette_vbox = QVBoxLayout()
        self.palette_grid = QGridLayout()
        self.question_palette = []
        questions_per_row = 5
        for i in range(self.num_questions):
            btn = QPushButton(str(i + 1))
            btn.setCheckable(True)
            btn.setFixedSize(40, 36)
            btn.setFont(QFont("Arial", 12, QFont.Bold))
            btn.clicked.connect(lambda checked, idx=i: self.go_to_question(idx))
            self.palette_grid.addWidget(btn, i // questions_per_row, i % questions_per_row)
            self.question_palette.append(btn)
        palette_vbox.addLayout(self.palette_grid)
        legend = QLabel(
            "● <span style='color:#bdbdbd'>Not Visited</span>   "
            "● <span style='color:#e57373'>Not Answered</span>   "
            "● <span style='color:#66bb6a'>Answered</span>   "
            "● <span style='color:#7e57c2'>Review</span>"
        )
        legend.setFont(QFont("Arial", 10))
        legend.setTextFormat(Qt.RichText)
        palette_vbox.addWidget(legend)
        palette_vbox.addStretch()
        self.palette_box.setLayout(palette_vbox)
        right_layout.insertWidget(0, self.palette_box)

        # Timer, number, prompt
        self.timer_label = QLabel()
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.timer_label.setStyleSheet("color: #d32f2f; background: #fffde7; border-radius: 8px; padding: 8px;")
        right_layout.addWidget(self.timer_label)

        self.question_number_label = QLabel()
        self.question_number_label.setAlignment(Qt.AlignCenter)
        self.question_number_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.question_number_label.setStyleSheet("color: #1976d2;")
        right_layout.addWidget(self.question_number_label)

        self.question_label = QLabel("Select or enter the answer for this question:")
        self.question_label.setWordWrap(True)
        self.question_label.setFont(QFont("Arial", 14))
        right_layout.addWidget(self.question_label)

        # Answer type selector
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Answer Type:"))
        self.answer_type_selector = QComboBox()
        self.answer_type_selector.addItems(["Multiple Choice", "Numeric", "Text"])
        self.answer_type_selector.setCurrentIndex(0)  # default MCQ
        self.answer_type_selector.currentIndexChanged.connect(self._on_answer_type_changed)
        type_row.addWidget(self.answer_type_selector)
        right_layout.addLayout(type_row)

        # MCQ options
        self.button_group = QButtonGroup(self)
        self.options = []
        options_box = QGroupBox("Options")
        options_box.setFont(QFont("Arial", 13, QFont.Bold))
        options_layout = QVBoxLayout()
        for i, opt in enumerate(["A", "B", "C", "D"]):
            btn = QRadioButton(opt)
            btn.setFont(QFont("Arial", 14))
            btn.setStyleSheet("padding: 6px;")
            self.button_group.addButton(btn, i)
            options_layout.addWidget(btn)
            self.options.append(btn)
        options_box.setLayout(options_layout)
        right_layout.addWidget(options_box)

        # Numeric input
        self.numeric_input = QLineEdit()
        self.numeric_input.setPlaceholderText("Enter numeric answer (e.g., 123, -4, 3.14)")
        # Accept integers and decimals; use a basic validator for integers, and allow decimals via manual check
        self.numeric_input.textEdited.connect(lambda _t: self._on_text_numeric_changed())
        right_layout.addWidget(self.numeric_input)

        # Text input
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter text answer")
        self.text_input.textEdited.connect(lambda _t: self._on_text_numeric_changed())
        right_layout.addWidget(self.text_input)

        # Navigation/Actions
        actions_layout_top = QHBoxLayout()
        actions_layout_top.setSpacing(8)

        self.save_next_btn = QPushButton("SAVE && NEXT")
        self.save_next_btn.setStyleSheet("background-color: #43a047; color: white; font-weight: bold; padding: 8px 18px;")
        self.save_next_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.save_next_btn.clicked.connect(self.save_and_next)
        actions_layout_top.addWidget(self.save_next_btn)

        self.save_mark_review_btn = QPushButton("SAVE && MARK FOR REVIEW")
        self.save_mark_review_btn.setStyleSheet("background-color: #ffd600; color: #333; font-weight: bold; padding: 8px 18px;")
        self.save_mark_review_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.save_mark_review_btn.clicked.connect(self.save_and_mark_for_review)
        actions_layout_top.addWidget(self.save_mark_review_btn)
        right_layout.addLayout(actions_layout_top)

        actions_layout_bottom = QHBoxLayout()
        actions_layout_bottom.setSpacing(8)
        self.actions_layout_bottom = actions_layout_bottom  # exposed for LearningWindow

        self.mark_review_next_btn = QPushButton("MARK FOR REVIEW && NEXT")
        self.mark_review_next_btn.setStyleSheet("background-color: #512da8; color: white; font-weight: bold; padding: 8px 18px;")
        self.mark_review_next_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.mark_review_next_btn.clicked.connect(self.mark_for_review_and_next)
        actions_layout_bottom.addWidget(self.mark_review_next_btn)

        self.clear_response_btn = QPushButton("CLEAR RESPONSE")
        self.clear_response_btn.setStyleSheet("background-color: #e53935; color: white; font-weight: bold; padding: 8px 18px;")
        self.clear_response_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.clear_response_btn.clicked.connect(self.clear_response)
        actions_layout_bottom.addWidget(self.clear_response_btn)

        self.submit_btn = QPushButton("SUBMIT")
        self.submit_btn.setStyleSheet("background-color: #1976d2; color: white; font-weight: bold; padding: 8px 18px;")
        self.submit_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.submit_btn.clicked.connect(self.submit_test)
        actions_layout_bottom.addWidget(self.submit_btn)
        right_layout.addLayout(actions_layout_bottom)

        right_layout.addStretch()

        # Splitter
        pdf_container = QWidget(); pdf_container.setLayout(pdf_layout)
        right_container = QWidget(); right_container.setLayout(right_layout)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(pdf_container)
        splitter.addWidget(right_container)
        splitter.setSizes([700, 200])
        main_layout.addWidget(splitter)

        self.setLayout(main_layout)
        self.update_question_ui()
        self.update_timer()

        # Zoom hookup
        self.zoom_slider.valueChanged.connect(lambda val: self.pdf_viewer.set_zoom(val / 100.0))
        self.pdf_viewer.set_zoom(self.zoom_slider.value() / 100.0)

        # Initial visibility for inputs
        self._apply_answer_type_ui()

    def save_and_next(self):
        self.save_current_answer()
        self.review_flags[self.current_question] = False
        self._update_state_for_current()
        if self.current_question < self.num_questions - 1:
            self.current_question += 1
        self.update_question_ui()

    def save_and_mark_for_review(self):
        self.save_current_answer()
        self.review_flags[self.current_question] = True
        self.question_states[self.current_question] = "review"
        self.update_question_ui()

    def mark_for_review_and_next(self):
        self.save_current_answer()
        self.review_flags[self.current_question] = True
        self.question_states[self.current_question] = "review"
        self.update_question_ui()
        if self.current_question < self.num_questions - 1:
            self.current_question += 1
            self.update_question_ui()

    def clear_response(self):
        # Clear MCQ
        self.button_group.setExclusive(False)
        for btn in self.options:
            btn.setChecked(False)
        self.button_group.setExclusive(True)
        # Clear text/numeric
        self.numeric_input.clear()
        self.text_input.clear()
        # Clear stored answer
        self.answers[self.current_question] = None
        self._update_state_for_current()
        self.update_question_ui()

    def go_to_question(self, idx):
        self.save_current_answer()
        self.review_flags[self.current_question] = False
        if not self.question_states[self.current_question] == "review":
            self._update_state_for_current()
        self.current_question = idx
        self.update_question_ui()

    def start_timer(self):
        self.timer.start(1000)

    def update_timer(self):
        if self.time_left == QTime(0, 0, 0):
            self.timer_label.setText("Time's up!")
            self.timer.stop()
            self.submit_test(auto=True)
            self.disable_test_ui()
        else:
            self.timer_label.setText(f"Timleft: {self.time_left.toString('hh:mm:ss')}")
            self.time_left = self.time_left.addSecs(-1)

    def disable_test_ui(self):
        for btn in self.options:
            btn.setEnabled(False)

    def update_question_ui(self):
        self.question_number_label.setText(f"Question {self.current_question + 1} of {self.num_questions}")

        # Set type selector from per-question type
        type_idx = {"mcq": 0, "numeric": 1, "text": 2}[self.question_types[self.current_question]]
        self.answer_type_selector.blockSignals(True)
        self.answer_type_selector.setCurrentIndex(type_idx)
        self.answer_type_selector.blockSignals(False)
        self._apply_answer_type_ui()

        # Populate inputs from stored answer
        current = self.answers[self.current_question]
        # Reset inputs
        self.button_group.setExclusive(False)
        for btn in self.options: btn.setChecked(False)
        self.button_group.setExclusive(True)
        self.numeric_input.blockSignals(True); self.text_input.blockSignals(True)
        self.numeric_input.clear(); self.text_input.clear()

        if isinstance(current, dict):
            if current.get("type") == "mcq":
                val = current.get("value", None)
                if isinstance(val, int) and 0 <= val <= 3:
                    self.options[val].setChecked(True)
            elif current.get("type") == "numeric":
                self.numeric_input.setText(str(current.get("value", "")))
            elif current.get("type") == "text":
                self.text_input.setText(str(current.get("value", "")))
        self.numeric_input.blockSignals(False); self.text_input.blockSignals(False)

        # Palette styling
        for idx, btn in enumerate(self.question_palette):
            color = STATE_COLORS[self.question_states[idx]]
            border_width = "2px" if idx == self.current_question else "1px"
            border_color = "#000" if idx == self.current_question else "#888"
            btn.setStyleSheet(
                f"background-color: {color}; border-radius: 15px; font-weight: bold; "
                f"border-width: {border_width}; border-style: solid; border-color: {border_color};"
            )
            btn.setChecked(idx == self.current_question)

    def next_question(self):
        self.save_current_answer()
        if self.current_question < self.num_questions - 1:
            self.current_question += 1
            self.update_question_ui()

    def prev_question(self):
        self.save_current_answer()
        if self.current_question > 0:
            self.current_question -= 1
            self.update_question_ui()

    def save_current_answer(self):
        qtype = self.question_types[self.current_question]
        if qtype == "mcq":
            checked_id = self.button_group.checkedId()
            if checked_id != -1:
                self.answers[self.current_question] = {"type": "mcq", "value": checked_id}
            else:
                self.answers[self.current_question] = None
        elif qtype == "numeric":
            val = self.numeric_input.text().strip()
            # allow empty -> None
            if val == "":
                self.answers[self.current_question] = None
            else:
                self.answers[self.current_question] = {"type": "numeric", "value": val}
        else:  # text
            val = self.text_input.text().strip()
            if val == "":
                self.answers[self.current_question] = None
            else:
                self.answers[self.current_question] = {"type": "text", "value": val}
        self._update_state_for_current()

    def _on_answer_type_changed(self, idx):
        # Update per-question type
        new_type = {0: "mcq", 1: "numeric", 2: "text"}[idx]
        self.question_types[self.current_question] = new_type
        # When switching types, clear previous selection to avoid stale data
        self.answers[self.current_question] = None
        # Update UI and state
        self._apply_answer_type_ui()
        self._update_state_for_current()

    def _apply_answer_type_ui(self):
        # Show/hide inputs based on current question type
        qtype = self.question_types[self.current_question]
        is_mcq = (qtype == "mcq")
        is_num = (qtype == "numeric")
        is_text = (qtype == "text")
        for btn in self.options: btn.setVisible(is_mcq)
        # group box title reflects type
        self.palette_box.setTitle("Question Palette")
        self.numeric_input.setVisible(is_num)
        self.text_input.setVisible(is_text)

    def _on_text_numeric_changed(self):
        # Live save for text/numeric
        self.save_current_answer()

    def _update_state_for_current(self):
        ans = self.answers[self.current_question]
        if ans is None:
            self.question_states[self.current_question] = "not_answered"
        else:
            # Any non-None answer counts as answered
            if not self.review_flags[self.current_question]:
                self.question_states[self.current_question] = "answered"

    def submit_test(self, auto=False):
        self.save_current_answer()
        
        if auto:
            QMessageBox.information(self, "Test Auto-Submitted", "Time is up! Your test has been auto-submitted.")
        else:
            reply = QMessageBox.question(
                self,
                "Submit Test",
                "Are you sure you want to submit the test?\nYou will not be able to change your answers after submission.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        self.timer.stop()
        self.disable_test_ui()
        
        initial_time_seconds = self.time_limit * 60
        remaining_time_seconds = self.time_left.hour() * 3600 + self.time_left.minute() * 60 + self.time_left.second()
        time_taken_seconds = initial_time_seconds - remaining_time_seconds
        
        answer_dialog = AnswerKeyDialog(self.num_questions, self, question_types=self.question_types)
        if answer_dialog.exec_() == QDialog.Accepted:
            correct_answers, method = answer_dialog.get_answers()
            # correct_answers is now a list of dicts: {"type": "...", "value": ...}
            # For DB logging, store only MCQ indices (others None):
            correct_idx = [ca["value"] if isinstance(ca, dict) and ca.get("type") == "mcq" else None
                           for ca in correct_answers]
            # use correct_idx for DB storage; keep full correct_answers for future results processing

            # Log to DB: only MCQ selected_answer fits current schema; numeric/text logged as None for selected_answer
            try:
                for i in range(self.num_questions):
                    sel = self.answers[i] if i < len(self.answers) else None
                    if isinstance(sel, dict) and sel.get("type") == "mcq":
                        selected_value = sel.get("value", None)
                    else:
                        selected_value = None  # extend schema later for numeric/text if desired
                    correct = correct_answers[i] if i < len(correct_answers) else None
                    hint_count = 0
                    if hasattr(self, "hints_used"):
                        hint_count = getattr(self, "hints_used", {}).get(i, 0) or 0
                    storage.log_attempt(
                        attempt_uuid=self.attempt_uuid,
                        question_index=i,
                        selected_answer=selected_value,
                        correct_answer=correct,
                        time_spent_sec=0,
                        hint_count=hint_count
                    )
            except Exception:
                pass

            if method == "skip":
                self.close()
                return

            self.results_window = ResultsWindow(
                answers=self.answers,
                correct_answers=correct_answers,
                time_taken=time_taken_seconds,
                total_time=initial_time_seconds
            )
            self.results_window.show()
        else:
            QMessageBox.information(self, "Test Completed", "Your test has been submitted successfully!")
        self.close()

    def render_pdf_pages(self, zoom_factor):
        # Remove old widgets
        for i in reversed(range(self.pdf_vbox.count())):
            widget = self.pdf_vbox.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        if not self.pdf_path:
            return
        doc = fitz.open(self.pdf_path)
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            matrix = fitz.Matrix(zoom_factor / 100, zoom_factor / 100)
            pix = page.get_pixmap(matrix=matrix)
            img_format = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
            img = QImage(bytes(pix.samples), pix.width, pix.height, pix.stride, img_format)
            lbl = QLabel()
            lbl.setPixmap(QPixmap.fromImage(img))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.pdf_vbox.addWidget(lbl)
        doc.close()
