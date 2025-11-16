from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QGroupBox, QGridLayout, QComboBox, QMessageBox, QScrollArea, QWidget,
    QFileDialog, QInputDialog, QLineEdit, QApplication, QProgressDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import os

# Add worker thread class
class ExtractWorker(QThread):
    finished = pyqtSignal(object)   # emits raw answers list on success
    error = pyqtSignal(str)         # emits error message on failure

    def __init__(self, pdf_path, api_key, num_questions):
        super().__init__()
        self.pdf_path = pdf_path
        self.api_key = api_key
        self.num_questions = num_questions

    def run(self):
        try:
            # import here to keep main thread imports minimal
            from scripts.fetch_answers_openai import extract_answers_from_pdf
            raw = extract_answers_from_pdf(self.pdf_path, api_key=self.api_key, num_questions=self.num_questions)
            self.finished.emit(raw)
        except Exception as e:
            self.error.emit(str(e))

class AnswerKeyDialog(QDialog):
    def __init__(self, num_questions, parent=None):
        super().__init__(parent)
        self.num_questions = num_questions
        self.answers = [None] * num_questions
        self.method = None
        self.setWindowTitle("Enter Answer Key")
        self.setModal(True)
        self.resize(600, 700)
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Title
        title = QLabel("Answer Key Required")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setStyleSheet("color: #1976d2; margin-bottom: 10px;")
        main_layout.addWidget(title)
        
        subtitle = QLabel("To show detailed results, please provide the correct answers.")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setStyleSheet("color: #666; margin-bottom: 20px;")
        main_layout.addWidget(subtitle)
        
        # Method selection
        method_box = QGroupBox("Select Method")
        method_box.setFont(QFont("Arial", 14, QFont.Bold))
        method_layout = QVBoxLayout()
        
        # Manual method (recommended)
        manual_box = QGroupBox("Manual Entry (Recommended)")
        manual_box.setStyleSheet("QGroupBox { font-weight: bold; color: #43a047; }")
        manual_layout = QVBoxLayout()
        manual_desc = QLabel("• Enter answers manually\n• 100% accurate\n• Quick and reliable")
        manual_desc.setFont(QFont("Arial", 11))
        manual_desc.setStyleSheet("color: #666; margin: 10px;")
        manual_layout.addWidget(manual_desc)
        
        manual_btn = QPushButton("Use Manual Entry")
        manual_btn.setFont(QFont("Arial", 12, QFont.Bold))
        manual_btn.setStyleSheet("""
            QPushButton {
                background-color: #43a047;
                color: white;
                padding: 12px 20px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
        """)
        manual_btn.clicked.connect(self.use_manual_entry)
        manual_layout.addWidget(manual_btn)
        manual_box.setLayout(manual_layout)
        
        # Auto extract method
        auto_box = QGroupBox("Auto Extract (Experimental)")
        auto_box.setStyleSheet("QGroupBox { font-weight: bold; color: #ff9800; }")
        auto_layout = QVBoxLayout()
        auto_desc = QLabel("• Extract from answer key PDF\n• May have accuracy issues\n• Requires OpenAI API")
        auto_desc.setFont(QFont("Arial", 11))
        auto_desc.setStyleSheet("color: #666; margin: 10px;")
        auto_layout.addWidget(auto_desc)
        
        auto_btn = QPushButton("Try Auto Extract")
        auto_btn.setFont(QFont("Arial", 12, QFont.Bold))
        auto_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                padding: 12px 20px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        auto_btn.clicked.connect(self.use_auto_extract)
        auto_layout.addWidget(auto_btn)
        auto_box.setLayout(auto_layout)
        
        method_layout.addWidget(manual_box)
        method_layout.addWidget(auto_box)
        method_box.setLayout(method_layout)
        main_layout.addWidget(method_box)
        
        # Skip option
        skip_layout = QHBoxLayout()
        skip_btn = QPushButton("Skip (Do not show results)")
        skip_btn.setFont(QFont("Arial", 11))
        skip_btn.setStyleSheet("""
            QPushButton {
                background-color: #9e9e9e;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """)
        skip_btn.clicked.connect(self.skip_answer_key)
        skip_layout.addStretch()
        skip_layout.addWidget(skip_btn)
        skip_layout.addStretch()
        main_layout.addLayout(skip_layout)
        
        # Manual entry section (initially hidden)
        self.create_manual_entry_section()
        main_layout.addWidget(self.manual_entry_widget)
        self.manual_entry_widget.hide()
    
    def create_manual_entry_section(self):
        self.manual_entry_widget = QWidget()
        layout = QVBoxLayout(self.manual_entry_widget)
        
        # Instructions
        instructions = QLabel("Enter the correct answer (A, B, C, or D) for each question:")
        instructions.setFont(QFont("Arial", 12, QFont.Bold))
        instructions.setStyleSheet("color: #333; margin: 10px 0;")
        layout.addWidget(instructions)
        
        # Scrollable area for answers
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QGridLayout(scroll_widget)
        scroll_layout.setSpacing(10)
        
        self.answer_combos = []
        questions_per_row = 5
        
        for i in range(self.num_questions):
            # Question label
            q_label = QLabel(f"Q{i+1}:")
            q_label.setFont(QFont("Arial", 11, QFont.Bold))
            q_label.setAlignment(Qt.AlignCenter)
            
            # Answer combo box
            combo = QComboBox()
            combo.addItems(["--", "A", "B", "C", "D"])
            combo.setFont(QFont("Arial", 11))
            combo.setStyleSheet("""
                QComboBox {
                    padding: 5px;
                    border: 2px solid #e0e0e0;
                    border-radius: 4px;
                    min-width: 50px;
                }
                QComboBox:focus {
                    border-color: #1976d2;
                }
            """)
            
            row = i // questions_per_row
            col = i % questions_per_row
            
            scroll_layout.addWidget(q_label, row * 2, col)
            scroll_layout.addWidget(combo, row * 2 + 1, col)
            
            self.answer_combos.append(combo)
        
        scroll.setWidget(scroll_widget)
        scroll.setMaximumHeight(300)
        scroll.setStyleSheet("border: 1px solid #e0e0e0; border-radius: 4px;")
        layout.addWidget(scroll)
        
        # Manual entry buttons
        manual_buttons = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFont(QFont("Arial", 11))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                color: #333;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #bdbdbd;
            }
        """)
        cancel_btn.clicked.connect(self.cancel_manual_entry)
        
        save_btn = QPushButton("Save Answers")
        save_btn.setFont(QFont("Arial", 11, QFont.Bold))
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
        """)
        save_btn.clicked.connect(self.save_manual_answers)
        
        manual_buttons.addStretch()
        manual_buttons.addWidget(cancel_btn)
        manual_buttons.addWidget(save_btn)
        layout.addLayout(manual_buttons)
    
    def use_manual_entry(self):
        self.method = "manual"
        self.manual_entry_widget.show()
        self.resize(600, 800)
    
    def use_auto_extract(self):
        # Ask user to select the answer key PDF
        pdf_path, _ = QFileDialog.getOpenFileName(self, "Select Answer Key PDF", "", "PDF Files (*.pdf);;All Files (*)")
        if not pdf_path:
            return

        # Try environment variable first, else ask for API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            key_text, ok = QInputDialog.getText(self, "OpenAI API Key", "Enter OpenAI API Key (or set OPENAI_API_KEY env var):", QLineEdit.Normal)
            if not ok or not key_text.strip():
                QMessageBox.warning(self, "API Key Required", "OpenAI API key is required for auto-extract.")
                return
            api_key = key_text.strip()

        # Progress dialog (indeterminate)
        self._progress = QProgressDialog("Extracting answer key — please wait...", None, 0, 0, self)
        self._progress.setWindowModality(Qt.WindowModal)
        self._progress.setCancelButton(None)
        self._progress.setMinimumDuration(0)
        self._progress.show()
        QApplication.processEvents()

        # Start worker thread
        self._worker = ExtractWorker(pdf_path, api_key, self.num_questions)
        self._worker.finished.connect(self._on_extract_success)
        self._worker.error.connect(self._on_extract_error)
        self._worker.start()

    def _on_extract_success(self, raw_answers):
        # Called in main thread
        try:
            mapping = {"A": 0, "B": 1, "C": 2, "D": 3}
            normalized = []
            for it in raw_answers:
                if it is None:
                    normalized.append(None)
                elif isinstance(it, (list, tuple)):
                    first = it[0] if it else None
                    normalized.append(mapping.get(first.upper(), None) if isinstance(first, str) else None)
                elif isinstance(it, str):
                    s = it.strip().upper()
                    normalized.append(mapping.get(s[0] if s else s, None))
                else:
                    normalized.append(None)

            # adjust length
            if len(normalized) < self.num_questions:
                normalized += [None] * (self.num_questions - len(normalized))
            elif len(normalized) > self.num_questions:
                normalized = normalized[:self.num_questions]

            self.answers = normalized
            self.method = "auto"
            if hasattr(self, "_progress"):
                self._progress.close()
            QMessageBox.information(self, "Success", "Answer key extracted successfully.")
            self.accept()
        finally:
            # ensure thread cleaned up
            try:
                self._worker.quit()
                self._worker.wait(100)
            except Exception:
                pass

    def _on_extract_error(self, msg):
        if hasattr(self, "_progress"):
            self._progress.close()
        QMessageBox.warning(self, "Extraction Failed", f"Failed to extract answers:\n{msg}")
        try:
            self._worker.quit()
            self._worker.wait(100)
        except Exception:
            pass
    
    def cancel_manual_entry(self):
        self.manual_entry_widget.hide()
        self.method = None
        self.resize(600, 700)
    
    def save_manual_answers(self):
        # Convert combo box selections to answer format
        answer_mapping = {"--": None, "A": 0, "B": 1, "C": 2, "D": 3}
        
        for i, combo in enumerate(self.answer_combos):
            selected = combo.currentText()
            self.answers[i] = answer_mapping.get(selected, None)
        
        self.method = "manual"
        self.accept()
    
    def skip_answer_key(self):
        reply = QMessageBox.question(
            self,
            "Skip Results",
            "Are you sure? This will skip the results page.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.method = "skip"
            self.answers = [None] * self.num_questions
            self.accept()
        # If No is selected, do nothing (stay on the dialog)
    
    def get_answers(self):
        return self.answers, self.method