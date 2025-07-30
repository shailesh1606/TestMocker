from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QHBoxLayout, QRadioButton,
    QPushButton, QButtonGroup, QSizePolicy, QGroupBox, QGridLayout, QMessageBox,
    QSplitter, QWidget, QSlider
)
from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5.QtGui import QPixmap, QImage, QFont
import fitz  # PyMuPDF

STATE_COLORS = {
    "not_visited": "#bdbdbd",      # grey
    "current" : "#f9f9f9",         #white
    "not_answered": "#e57373",     # red
    "answered": "#66bb6a",         # green
    "review": "#7e57c2",           # purple
}
class TestWindow(QWidget):
    def __init__(self, pdf_path, time_limit=60, num_questions=10):
        super().__init__()
        self.time_limit = time_limit
        self.num_questions = num_questions
        self.current_question = 0
        self.answers = [None] * num_questions  # Store user answers
        self.question_states = ["not_visited"] * self.num_questions  # Tracks question status: 'not_visited', 'answered', 'not_answered', 'review'
        self.review_flags = [False] * self.num_questions             # Marks if question is flagged for review

        self.setWindowTitle('Take Test')
        self.setGeometry(150, 150, 1200, 800)
        self.timer = QTimer(self)
        # --- Fix: support time_limit >= 60 ---
        hours = self.time_limit // 60
        minutes = self.time_limit % 60
        self.time_left = QTime(hours, minutes, 0)
        # -------------------------------------
        self.timer.timeout.connect(self.update_timer)
        self.init_ui(pdf_path)
        self.start_timer()

    def init_ui(self, pdf_path):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(30)

        # --- Left: PDF Viewer using PyMuPDF ---
        pdf_layout = QVBoxLayout()
        pdf_layout.setSpacing(10)
        if not pdf_path:
            no_pdf_label = QLabel("No PDF uploaded.")
            no_pdf_label.setFont(QFont("Arial", 14, QFont.Bold))
            pdf_layout.addWidget(no_pdf_label)
        else:
            scroll = QScrollArea()
            pdf_widget = QWidget()
            pdf_vbox = QVBoxLayout()
            pdf_widget.setLayout(pdf_vbox)

            doc = fitz.open(pdf_path)
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                img_format = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
                img = QImage(bytes(pix.samples), pix.width, pix.height, pix.stride, img_format)
                lbl = QLabel()
                lbl.setPixmap(QPixmap.fromImage(img))
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                pdf_vbox.addWidget(lbl)
            doc.close()

            scroll.setWidget(pdf_widget)
            scroll.setWidgetResizable(True)
            scroll.setMinimumWidth(500)
            scroll.setStyleSheet("background: #f5f5f5; border: 1px solid #bdbdbd;")
            pdf_layout.addWidget(scroll)

            # Zoom slider
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

            self.pdf_vbox = pdf_vbox  # Save reference for later
            self.pdf_path = pdf_path  # Save reference for later

        # --------------------------------------

        # --- Right: Question/Answer UI ---
        right_layout = QVBoxLayout()
        right_layout.setSpacing(20)

        # --- Question palette (JEE Mains style) ---
        self.palette_box = QGroupBox("Question Palette")
        self.palette_box.setFont(QFont("Arial", 11, QFont.Bold))
        palette_vbox = QVBoxLayout()
        self.palette_grid = QGridLayout()
        self.question_palette = []
        questions_per_row = 5  # You can adjust this number

        for i in range(self.num_questions):
            btn = QPushButton(str(i + 1))
            btn.setCheckable(True)
            btn.setFixedSize(40, 36)
            btn.setFont(QFont("Arial", 12, QFont.Bold))
            btn.clicked.connect(lambda checked, idx=i: self.go_to_question(idx))  # Jump to question on click
            self.palette_grid.addWidget(btn, i // questions_per_row, i % questions_per_row)
            self.question_palette.append(btn)

        palette_vbox.addLayout(self.palette_grid)

        # Add a legend for colors
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

        # Add palette_box to the right_layout at the top
        right_layout.insertWidget(0, self.palette_box)

        # Timer display
        self.timer_label = QLabel()
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.timer_label.setStyleSheet("color: #d32f2f; background: #fffde7; border-radius: 8px; padding: 8px;")
        right_layout.addWidget(self.timer_label)

        # Question number display
        self.question_number_label = QLabel()
        self.question_number_label.setAlignment(Qt.AlignCenter)
        self.question_number_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.question_number_label.setStyleSheet("color: #1976d2;")
        right_layout.addWidget(self.question_number_label)

        # Question label
        self.question_label = QLabel("Select the answer for this question:")
        self.question_label.setWordWrap(True)
        self.question_label.setFont(QFont("Arial", 14))
        right_layout.addWidget(self.question_label)

        # Answer options
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

        '''
        # Navigation buttons
        nav_layout = QHBoxLayout()
        self.prev_button = QPushButton("← Previous")
        self.prev_button.setFont(QFont("Arial", 13, QFont.Bold))
        self.prev_button.setStyleSheet("background-color: #90caf9; color: #0d47a1; border-radius: 8px; padding: 8px 16px;")
        self.prev_button.clicked.connect(self.prev_question)
        nav_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Next →")
        self.next_button.setFont(QFont("Arial", 13, QFont.Bold))
        self.next_button.setStyleSheet("background-color: #a5d6a7; color: #1b5e20; border-radius: 8px; padding: 8px 16px;")
        self.next_button.clicked.connect(self.next_question)
        nav_layout.addWidget(self.next_button)
        right_layout.addLayout(nav_layout)
        '''
        #Action buttons for navigation
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

        # --- Add layouts to a splitter for adjustable space ---
        pdf_container = QWidget()
        pdf_container.setLayout(pdf_layout)
        right_container = QWidget()
        right_container.setLayout(right_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(pdf_container)
        splitter.addWidget(right_container)
        splitter.setSizes([700, 200])  # Initial sizes, adjust as needed

        main_layout.addWidget(splitter)

        self.setLayout(main_layout)
        self.update_question_ui()
        self.update_timer()  # Show initial time

        # Connect the slider to re-render PDF pages
        self.zoom_slider.valueChanged.connect(lambda val: self.render_pdf_pages(val))

        # Initial render
        self.render_pdf_pages(self.zoom_slider.value())

    def save_and_next(self):
        self.save_current_answer()
        #set review flag to False
        self.review_flags[self.current_question] = False
        
        #set question state based on answer
        if self.answers[self.current_question] is not None:
            self.question_states[self.current_question] = "answered"
        else:
            self.question_states[self.current_question] = "not_answered"
        if self.current_question < self.num_questions - 1:
            self.current_question += 1
        self.update_question_ui()

    def save_and_mark_for_review(self):
        self.save_current_answer()
        self.review_flags[self.current_question] = True
        self.question_states[self.current_question] = "review"
        self.update_question_ui()
        '''
        # Move to next question
        if self.current_question < self.num_questions - 1:
            self.current_question += 1
            self.update_question_ui()
        '''

    def mark_for_review_and_next(self):
        self.save_current_answer()
        self.review_flags[self.current_question] = True
        self.question_states[self.current_question] = "review"
        self.update_question_ui()
        if self.current_question < self.num_questions - 1:
            self.current_question += 1
            self.update_question_ui()

    def clear_response(self):
        self.button_group.setExclusive(False)
        for btn in self.options:
            btn.setChecked(False)
        self.button_group.setExclusive(True)
        self.save_current_answer()

    def go_to_question(self, idx):
        self.save_current_answer()
        #set review flag to False
        self.review_flags[self.current_question] = False
        
        #set question state based on answer
        if not self.question_states[self.current_question] == "review":
            if self.answers[self.current_question] is not None:
                self.question_states[self.current_question] = "answered"
            else:
                self.question_states[self.current_question] = "not_answered"
        self.current_question = idx
        self.update_question_ui()

    def start_timer(self):
        self.timer.start(1000)  # 1 second interval

    def update_timer(self):
        if self.time_left == QTime(0, 0, 0):
            self.timer_label.setText("Time's up!")
            self.timer.stop()
            self.submit_test(auto=True)  # Auto submit when time is up
            self.disable_test_ui()
        else:
            self.timer_label.setText(f"Timleft: {self.time_left.toString('hh:mm:ss')}")
            self.time_left = self.time_left.addSecs(-1)

    def disable_test_ui(self):
        for btn in self.options:
            btn.setEnabled(False)
        #self.prev_button.setEnabled(False)
        #self.next_button.setEnabled(False)

    def update_question_ui(self):
        self.question_number_label.setText(f"Question {self.current_question + 1} of {self.num_questions}")
        selected = self.answers[self.current_question]
        if selected is None:
            self.button_group.setExclusive(False)
            for btn in self.options:
                btn.setChecked(False)
            self.button_group.setExclusive(True)
        else:
            for i, btn in enumerate(self.options):
                btn.setChecked(selected == i)
        #self.prev_button.setEnabled(self.current_question > 0)
        #self.next_button.setEnabled(self.current_question < self.num_questions - 1)

        #set question palette button styles
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
        checked_id = self.button_group.checkedId()
        if checked_id != -1:
            self.answers[self.current_question] = checked_id
        else:
            self.answers[self.current_question] = None

    def submit_test(self, auto=False):
        if auto:
            QMessageBox.information(self, "Test Auto-Submitted", "Time is up! Your test has been auto-submitted.")
            self.disable_test_ui()
            # Add logic to process/store answers here
        else:
            reply = QMessageBox.question(
                self,
                "Submit Test",
                "Are you sure you want to submit the test?\nYou will not be able to change your answers after submission.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.timer.stop()
                self.disable_test_ui()
                # Add logic to process/store answers here
                QMessageBox.information(self, "Test Submitted", "Your test has been submitted successfully!")

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
