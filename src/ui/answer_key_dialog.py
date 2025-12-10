from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QGroupBox, QGridLayout, QComboBox, QMessageBox, QScrollArea, QWidget,
    QFileDialog, QInputDialog, QLineEdit, QApplication, QProgressDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QDoubleValidator
import os

class ExtractWorker(QThread):
    finished = pyqtSignal(object)   # emits raw answers list on success
    error = pyqtSignal(str)         # emits error message on failure

    def __init__(self, pdf_path, api_key, num_questions, question_types):
        super().__init__()
        self.pdf_path = pdf_path
        self.api_key = api_key
        self.num_questions = num_questions
        self.question_types = question_types

    def run(self):
        try:
            from scripts.fetch_answers_openai import extract_answers_from_pdf
            raw = extract_answers_from_pdf(
                self.pdf_path,
                api_key=self.api_key,
                num_questions=self.num_questions,
                question_types=self.question_types
            )
            self.finished.emit(raw)
        except Exception as e:
            self.error.emit(str(e))

class AnswerKeyDialog(QDialog):
    def __init__(self, num_questions, parent=None, question_types=None):
        super().__init__(parent)
        self.num_questions = num_questions
        # question_types: list[str] of "mcq" | "numeric" | "text"
        self.question_types = question_types if question_types and len(question_types) == num_questions else ["mcq"] * num_questions
        # answers will be a list[dict] with {"type": "...", "value": ...}
        self.answers = [{"type": t, "value": None} for t in self.question_types]
        self.method = None
        self.setWindowTitle("Enter Answer Key")
        self.setModal(True)
        self.resize(700, 800)
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
        
        subtitle = QLabel("Provide the correct answers for each question. Inputs will match the question type (MCQ/Numeric/Text).")
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
        manual_desc = QLabel("• Enter answers manually per question type\n• MCQ → choose A/B/C/D\n• Numeric → enter value (e.g., 3.14)\n• Text → enter a word/phrase")
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
        auto_box = QGroupBox("Auto Extract")
        auto_box.setStyleSheet("QGroupBox { font-weight: bold; color: #ff9800; }")
        auto_layout = QVBoxLayout()
        auto_desc = QLabel("• Extract from answer key PDF\n• May have accuracy issues\n• Requires OpenAI API")
        auto_desc.setFont(QFont("Arial", 11))
        auto_desc.setStyleSheet("color: #666; margin: 10px;")
        auto_layout.addWidget(auto_desc)
        
        auto_btn = QPushButton("Use Auto Extract")
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
        instructions = QLabel("Enter the correct answer for each question:")
        instructions.setFont(QFont("Arial", 12, QFont.Bold))
        instructions.setStyleSheet("color: #333; margin: 10px 0;")
        layout.addWidget(instructions)
        
        # Scrollable area for answers
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QGridLayout(scroll_widget)
        scroll_layout.setSpacing(10)
        
        # Keep references to per-question input widgets and labels
        self.input_widgets = []  # list of tuples: (type, widget)
        questions_per_row = 3
        
        for i in range(self.num_questions):
            q_type = self.question_types[i]  # "mcq" | "numeric" | "text"
            # Question label with type
            q_label = QLabel(f"Q{i+1} ({q_type.upper()}):")
            q_label.setFont(QFont("Arial", 11, QFont.Bold))
            q_label.setAlignment(Qt.AlignLeft)
            
            # Input widget based on type
            if q_type == "mcq":
                widget = QComboBox()
                widget.addItems(["--", "A", "B", "C", "D"])
                widget.setFont(QFont("Arial", 11))
                widget.setStyleSheet("""
                    QComboBox {
                        padding: 5px;
                        border: 2px solid #e0e0e0;
                        border-radius: 4px;
                        min-width: 70px;
                    }
                    QComboBox:focus { border-color: #1976d2; }
                """)
            elif q_type == "numeric":
                widget = QLineEdit()
                widget.setPlaceholderText("e.g., 3.14, -2, 1/3")
                # Soft validation: allow digits, signs, dot; leave exact parsing to evaluation time
                # (QDoubleValidator is too strict for fractions like 1/3)
                widget.setFont(QFont("Arial", 11))
                widget.setStyleSheet("""
                    QLineEdit {
                        padding: 6px;
                        border: 2px solid #e0e0e0;
                        border-radius: 4px;
                        min-width: 120px;
                    }
                    QLineEdit:focus { border-color: #1976d2; }
                """)
            else:  # text
                widget = QLineEdit()
                widget.setPlaceholderText("Enter text (case-insensitive compare)")
                widget.setFont(QFont("Arial", 11))
                widget.setStyleSheet("""
                    QLineEdit {
                        padding: 6px;
                        border: 2px solid #e0e0e0;
                        border-radius: 4px;
                        min-width: 160px;
                    }
                    QLineEdit:focus { border-color: #1976d2; }
                """)
            
            row = i // questions_per_row
            col = (i % questions_per_row) * 2  # label + input side by side
            
            scroll_layout.addWidget(q_label, row, col, alignment=Qt.AlignLeft)
            scroll_layout.addWidget(widget, row, col + 1, alignment=Qt.AlignLeft)
            
            self.input_widgets.append((q_type, widget))
        
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(360)
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
            QPushButton:hover { background-color: #bdbdbd; }
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
            QPushButton:hover { background-color: #1565c0; }
        """)
        save_btn.clicked.connect(self.save_manual_answers)
        
        manual_buttons.addStretch()
        manual_buttons.addWidget(cancel_btn)
        manual_buttons.addWidget(save_btn)
        layout.addLayout(manual_buttons)
    
    def use_manual_entry(self):
        self.method = "manual"
        self.manual_entry_widget.show()
        self.resize(700, 900)
    
    def use_auto_extract(self):
        # Ask user to select the answer key PDF
        pdf_path, _ = QFileDialog.getOpenFileName(self, "Select Answer Key PDF", "", "PDF Files (*.pdf);;All Files (*)")
        if not pdf_path:
            return

        # Try environment variable first, else ask for API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            from PyQt5.QtWidgets import QInputDialog
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
        self._worker = ExtractWorker(pdf_path, api_key, self.num_questions, self.question_types)
        self._worker.finished.connect(self._on_extract_success)
        self._worker.error.connect(self._on_extract_error)
        self._worker.start()

    def _on_extract_success(self, raw_answers):
        try:
            mapping = {"A": 0, "B": 1, "C": 2, "D": 3}

            def normalize_item(it, qtype):
                qt = qtype or "mcq"
                if qt == "mcq":
                    if isinstance(it, dict):
                        v = it.get("value", None)
                        if isinstance(v, int) and 0 <= v <= 3:
                            return {"type": "mcq", "value": v}
                        if isinstance(v, str):
                            return {"type": "mcq", "value": mapping.get(v.strip().upper()[:1], None)}
                    if isinstance(it, (list, tuple)):
                        first = it[0] if it else None
                        if isinstance(first, str):
                            return {"type": "mcq", "value": mapping.get(first.strip().upper()[:1], None)}
                    if isinstance(it, str):
                        return {"type": "mcq", "value": mapping.get(it.strip().upper()[:1], None)}
                    if isinstance(it, int) and 0 <= it <= 3:
                        return {"type": "mcq", "value": it}
                    return {"type": "mcq", "value": None}
                if qt == "numeric":
                    if isinstance(it, dict):
                        v = it.get("value", None)
                        return {"type": "numeric", "value": None if v is None else str(v).strip()}
                    return {"type": "numeric", "value": None if it is None else str(it).strip()}
                if qt == "text":
                    if isinstance(it, dict):
                        v = it.get("value", None)
                        return {"type": "text", "value": None if v is None else str(v).strip()}
                    return {"type": "text", "value": None if it is None else str(it).strip()}
                return {"type": qt, "value": None}
            
            structured = []
            for i in range(self.num_questions):
                qtype = self.question_types[i]
                if i < len(raw_answers):
                    structured.append(normalize_item(raw_answers[i], qtype))
                else:
                    structured.append({"type": qtype, "value": None})

            if len(structured) < self.num_questions:
                structured += [{"type": self.question_types[j], "value": None} for j in range(len(structured), self.num_questions)]
            elif len(structured) > self.num_questions:
                structured = structured[:self.num_questions]

            self.answers = structured
            # Prefill manual inputs and keep dialog open for review/edit
            self.populate_manual_inputs(structured)
            self.manual_entry_widget.show()
            self.resize(700, 900)
            self.method = "manual"  # final method set on Save
            if hasattr(self, "_progress"):
                self._progress.close()
            QMessageBox.information(self, "Review Answers", "Answers extracted and pre-filled.\nPlease review and edit if needed, then click Save Answers.")
        finally:
            try:
                self._worker.quit()
                self._worker.wait(100)
            except Exception:
                pass

    def populate_manual_inputs(self, structured):
        """Prefill manual entry widgets from structured answers."""
        for (qtype, widget), item in zip(self.input_widgets, structured):
            val = item.get("value") if isinstance(item, dict) else None
            if qtype == "mcq":
                # Combo items: ["--", "A", "B", "C", "D"]
                idx = 0 if val is None else min(max(int(val) + 1, 0), 4)
                widget.setCurrentIndex(idx)
            elif qtype == "numeric":
                widget.setText("" if val in (None, "") else str(val))
            else:  # text
                widget.setText("" if val in (None, "") else str(val))
    
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
            self.answers = [{"type": t, "value": None} for t in self.question_types]
            self.accept()
        # If No is selected, do nothing (stay on the dialog)
    
    def get_answers(self):
        # Returns a structured list of dicts for all types and the chosen method
        return self.answers, self.method
    
    def cancel_manual_entry(self):
        """Hide manual entry and clear method selection."""
        self.method = None
        self.manual_entry_widget.hide()
    def save_manual_answers(self):
        """Collect manual inputs into self.answers and close dialog."""
        mapping_idx = {1: 0, 2: 1, 3: 2, 4: 3}  # combo index -> mcq value
        collected = []
        for (qtype, widget) in self.input_widgets:
            if qtype == "mcq":
                idx = widget.currentIndex()
                val = mapping_idx.get(idx, None)
                collected.append({"type": "mcq", "value": val})
            elif qtype == "numeric":
                text = widget.text().strip()
                collected.append({"type": "numeric", "value": text if text else None})
            else:  # text
                text = widget.text().strip()
                collected.append({"type": "text", "value": text if text else None})

        self.answers = collected
        self.method = "manual"
        self.accept()
    def _on_extract_error(self, msg):
        if hasattr(self, "_progress"):
            self._progress.close()
        QMessageBox.warning(self, "Extraction Failed", f"Failed to extract answers:\n{msg}")
        try:
            self._worker.quit()
            self._worker.wait(100)
        except Exception:
            pass
    