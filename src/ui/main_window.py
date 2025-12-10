from PyQt5.QtWidgets import (
    QMainWindow, QPushButton, QFileDialog, QLabel, QVBoxLayout, QWidget, QHBoxLayout, QFrame,
    QInputDialog, QMessageBox, QDialog, QFormLayout, QSpinBox, QDoubleSpinBox, QDialogButtonBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from ui.test_window import TestWindow

class ExamConfigDialog(QDialog):
    def __init__(self, exam_type, def_q, def_t, def_marks, def_neg, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Configure {exam_type} Test")
        self.setModal(True)
        self.resize(420, 220)

        form = QFormLayout(self)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)

        self.q_spin = QSpinBox()
        self.q_spin.setRange(1, 300)
        self.q_spin.setValue(def_q)

        self.t_spin = QSpinBox()
        self.t_spin.setRange(1, 600)
        self.t_spin.setSuffix(" min")
        self.t_spin.setValue(def_t)

        self.marks_spin = QDoubleSpinBox()
        self.marks_spin.setRange(0.0, 100.0)
        self.marks_spin.setDecimals(2)
        self.marks_spin.setSingleStep(0.5)
        self.marks_spin.setValue(def_marks)

        self.neg_spin = QDoubleSpinBox()
        self.neg_spin.setRange(-100.0, 0.0)  # negative marking as a negative value
        self.neg_spin.setDecimals(2)
        self.neg_spin.setSingleStep(0.5)
        self.neg_spin.setValue(def_neg)

        form.addRow("Number of Questions:", self.q_spin)
        form.addRow("Total Time:", self.t_spin)
        form.addRow("Marks per Correct:", self.marks_spin)
        form.addRow("Negative Marks per Incorrect:", self.neg_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def get_values(self):
        return (
            int(self.q_spin.value()),
            int(self.t_spin.value()),
            float(self.marks_spin.value()),
            float(self.neg_spin.value()),
        )

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TestMocker")
        self.setGeometry(100, 100, 600, 400)
        self.setWindowIcon(QIcon())  # You can set a custom icon here

        self.uploaded_pdf_path = None  # Store uploaded PDF path

        self.initUI()

    def initUI(self):
        # Set a modern color scheme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333;
            }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(60, 50, 60, 50)
        main_layout.setSpacing(40)

        # Hero section with app title and subtitle
        title_layout = QVBoxLayout()
        title_layout.setSpacing(10)
        
        title_label = QLabel("TestMocker")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 32, QFont.Bold))
        title_label.setStyleSheet("color: #1976d2; margin-bottom: 5px;")
        title_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Your Digital Testing Companion")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setFont(QFont("Arial", 14))
        subtitle_label.setStyleSheet("color: #666; margin-bottom: 20px;")
        title_layout.addWidget(subtitle_label)
        
        main_layout.addLayout(title_layout)

        # Status/feedback area
        self.label = QLabel("Welcome! Upload a PDF or scan a question paper to get started.")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("Arial", 12))
        self.label.setStyleSheet("""
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #e0e0e0;
            color: #555;
        """)
        self.label.setWordWrap(True)
        main_layout.addWidget(self.label)

        # Button layout with cards
        button_layout = QVBoxLayout()
        button_layout.setSpacing(15)

        # Create card-style buttons (scanner removed)

        self.upload_button = self.create_card_button(
            "Upload PDF", 
            "Select a PDF file from your computer",
            "#388e3c"
        )
        self.upload_button.clicked.connect(self.upload_pdf)
        button_layout.addWidget(self.upload_button)

        self.take_test_button = self.create_card_button(
            "Take Test", 
            "Start your test session",
            "#f57c00"
        )
        self.take_test_button.clicked.connect(self.take_test)
        button_layout.addWidget(self.take_test_button)

        # Separate Learning Mode entry
        self.learning_mode_button = self.create_card_button(
            "Learning Mode",
            "Practice with hints and get a learning report",
            "#6a1b9a"
        )
        self.learning_mode_button.clicked.connect(self.start_learning_mode)
        button_layout.addWidget(self.learning_mode_button)

        main_layout.addLayout(button_layout)
        main_layout.addStretch()

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def create_card_button(self, title, description, color):
        button = QPushButton()
        button.setMinimumHeight(80)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                border: 2px solid {color};
                border-radius: 12px;
                padding: 20px;
                text-align: left;
                font-size: 16px;
                font-weight: bold;
                color: {color};
            }}
            QPushButton:hover {{
                background-color: {color};
                color: white;
            }}
            QPushButton:pressed {{
                background-color: {color};
                color: white;
            }}
        """)
        
        # Create button text with title and description
        button_text = f"{title}\n{description}"
        button.setText(button_text)
        
        return button

    def upload_pdf(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Upload PDF", "", "PDF Files (*.pdf);;All Files (*)", options=options)
        if file_name:
            self.uploaded_pdf_path = file_name  # Save the uploaded file path
            self.label.setText(f"Uploaded file: {file_name}")

    def take_test(self):
        if not self.uploaded_pdf_path:
            self.label.setText("Please upload a PDF before taking the test.")
            return

        exam_options = ["JEE Mains", "JEE Advanced", "NEET", "Other"]
        exam_type, ok_exam = QInputDialog.getItem(
            self, "Exam Type", "Select exam type:", exam_options, current=0, editable=False
        )
        if not ok_exam or not exam_type:
            return

        EXAM_DEFAULTS = {
            "JEE Mains":   {"q": 75,  "t": 180, "marks": 4.0, "neg": -1.0},
            "JEE Advanced":{"q": 108, "t": 360, "marks": 3.0, "neg": -1.0},
            "NEET":        {"q": 180, "t": 200, "marks": 4.0, "neg": -1.0},
            "Other":       {"q": 50,  "t": 60,  "marks": 1.0, "neg":  0.0},
        }
        defs = EXAM_DEFAULTS.get(exam_type, EXAM_DEFAULTS["Other"])

        dlg = ExamConfigDialog(exam_type, defs["q"], defs["t"], defs["marks"], defs["neg"], parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        num_questions, time_limit, marks_per_correct, negative_mark = dlg.get_values()

        self.test_window = TestWindow(
            self.uploaded_pdf_path,
            time_limit=time_limit,
            num_questions=num_questions,
            exam_type=exam_type,
            marks_per_correct=marks_per_correct,
            negative_mark=negative_mark,
        )
        self.test_window.show()

    def start_learning_mode(self):
        if not self.uploaded_pdf_path:
            self.label.setText("Please upload a PDF before starting Learning Mode.")
            return

        exam_options = ["JEE Mains", "JEE Advanced", "NEET", "Other"]
        exam_type, ok_exam = QInputDialog.getItem(
            self, "Exam Type (Learning Mode)", "Select exam type:", exam_options, current=0, editable=False
        )
        if not ok_exam or not exam_type:
            return

        EXAM_DEFAULTS = {
            "JEE Mains":   {"q": 75,  "t": 180, "marks": 4.0, "neg": -1.0},
            "JEE Advanced":{"q": 108, "t": 360, "marks": 3.0, "neg": -1.0},
            "NEET":        {"q": 180, "t": 180, "marks": 4.0, "neg": -1.0},
            "Other":       {"q": 30,  "t": 45,  "marks": 1.0, "neg":  0.0},
        }
        defs = EXAM_DEFAULTS.get(exam_type, EXAM_DEFAULTS["Other"])

        dlg = ExamConfigDialog(exam_type, defs["q"], defs["t"], defs["marks"], defs["neg"], parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        num_questions, time_limit, marks_per_correct, negative_mark = dlg.get_values()

        from ui.learning_window import LearningWindow
        self.learning_window = LearningWindow(
            self.uploaded_pdf_path,
            time_limit=time_limit,
            num_questions=num_questions,
            exam_type=exam_type,
            marks_per_correct=marks_per_correct,
            negative_mark=negative_mark,
        )
        self.learning_window.show()