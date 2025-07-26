from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QHBoxLayout, QRadioButton,
    QPushButton, QButtonGroup, QSizePolicy, QGroupBox
)
from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5.QtGui import QPixmap, QImage, QFont
import fitz  # PyMuPDF

class TestWindow(QWidget):
    def __init__(self, pdf_path, time_limit=60, num_questions=10):
        super().__init__()
        self.time_limit = time_limit
        self.num_questions = num_questions
        self.current_question = 0
        self.answers = [None] * num_questions  # Store user answers

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
        main_layout.addLayout(pdf_layout, 2)
        # --------------------------------------

        # --- Right: Question/Answer UI ---
        right_layout = QVBoxLayout()
        right_layout.setSpacing(20)

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

        right_layout.addStretch()
        main_layout.addLayout(right_layout, 1)
        self.setLayout(main_layout)
        self.update_question_ui()
        self.update_timer()  # Show initial time

    def start_timer(self):
        self.timer.start(1000)  # 1 second interval

    def update_timer(self):
        if self.time_left == QTime(0, 0, 0):
            self.timer_label.setText("Time's up!")
            self.timer.stop()
            self.disable_test_ui()
        else:
            self.timer_label.setText(f"Timleft: {self.time_left.toString('hh:mm:ss')}")
            self.time_left = self.time_left.addSecs(-1)

    def disable_test_ui(self):
        for btn in self.options:
            btn.setEnabled(False)
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)

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
        self.prev_button.setEnabled(self.current_question > 0)
        self.next_button.setEnabled(self.current_question < self.num_questions - 1)

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
        self.answers[self.current_question] = checked_id if checked_id != -1 else None