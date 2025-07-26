from PyQt5.QtWidgets import (
    QMainWindow, QPushButton, QFileDialog, QLabel, QVBoxLayout, QWidget, QHBoxLayout, QFrame, QInputDialog, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from scanner.pdf_scanner import PDFScanner
from ui.test_window import TestWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Computer-Based Test Application")
        self.setGeometry(100, 100, 600, 400)
        self.setWindowIcon(QIcon())  # You can set a custom icon here

        self.uploaded_pdf_path = None  # Store uploaded PDF path

        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(25)

        self.label = QLabel("Welcome to the Computer-Based Test Application", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("Arial", 16, QFont.Bold))
        main_layout.addWidget(self.label)

        # Add a horizontal line separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)

        self.scan_button = QPushButton("Scan Question Paper", self)
        self.scan_button.setMinimumHeight(40)
        self.scan_button.setStyleSheet("background-color: #1976d2; color: white; font-size: 14px; border-radius: 8px;")
        self.scan_button.clicked.connect(self.scan_question_paper)
        button_layout.addWidget(self.scan_button)

        self.upload_button = QPushButton("Upload PDF", self)
        self.upload_button.setMinimumHeight(40)
        self.upload_button.setStyleSheet("background-color: #388e3c; color: white; font-size: 14px; border-radius: 8px;")
        self.upload_button.clicked.connect(self.upload_pdf)
        button_layout.addWidget(self.upload_button)

        self.take_test_button = QPushButton("Take Test", self)
        self.take_test_button.setMinimumHeight(40)
        self.take_test_button.setStyleSheet("background-color: #fbc02d; color: black; font-size: 14px; border-radius: 8px;")
        self.take_test_button.clicked.connect(self.take_test)
        button_layout.addWidget(self.take_test_button)

        main_layout.addLayout(button_layout)

        # Add a stretch to push content to the top
        main_layout.addStretch()

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def scan_question_paper(self):
        scanner = PDFScanner()
        scanned_file = scanner.scan()
        if scanned_file:
            self.label.setText(f"Scanned file saved as: {scanned_file}")

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

        # Ask for number of questions
        num_questions, ok1 = QInputDialog.getInt(
            self, "Number of Questions", "Enter the number of questions:", min=1, max=200, value=50
        )
        if not ok1:
            return

        # Ask for time limit
        time_limit, ok2 = QInputDialog.getInt(
            self, "Time Limit", "Enter the time limit (minutes):", min=1, max=300, value=60
        )
        if not ok2:
            return

        self.test_window = TestWindow(self.uploaded_pdf_path, time_limit, num_questions)
        self.test_window.show()