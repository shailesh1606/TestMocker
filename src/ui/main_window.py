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

        # Create card-style buttons
        self.scan_button = self.create_card_button(
            "Scan Question Paper", 
            "Capture and digitize physical question papers",
            "#1976d2"
        )
        self.scan_button.clicked.connect(self.scan_question_paper)
        button_layout.addWidget(self.scan_button)

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