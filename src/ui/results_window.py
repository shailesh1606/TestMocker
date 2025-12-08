from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import math
from fractions import Fraction

MCQ_MAP_IDX_TO_LETTER = {0: "A", 1: "B", 2: "C", 3: "D"}
MCQ_MAP_LETTER_TO_IDX = {"A": 0, "B": 1, "C": 2, "D": 3}

def _normalize_answer_item(item):
    """
    Normalize an answer record to {"type": "mcq"|"numeric"|"text", "value": ...} or None.
    Accepts legacy formats: None, int (MCQ index), or string.
    """
    if item is None:
        return None

    # Already structured
    if isinstance(item, dict) and "type" in item:
        t = str(item.get("type", "")).lower()
        v = item.get("value", None)
        if t == "mcq":
            # Normalize mcq value to 0..3
            if isinstance(v, int):
                return {"type": "mcq", "value": v if 0 <= v <= 3 else None}
            if isinstance(v, str):
                s = v.strip().upper()
                if s in MCQ_MAP_LETTER_TO_IDX:
                    return {"type": "mcq", "value": MCQ_MAP_LETTER_TO_IDX[s]}
                # try first char
                return {"type": "mcq", "value": MCQ_MAP_LETTER_TO_IDX.get(s[:1], None)}
            return {"type": "mcq", "value": None}
        if t == "numeric":
            # Keep string form; strip spaces
            if v is None:
                return {"type": "numeric", "value": None}
            return {"type": "numeric", "value": str(v).strip()}
        if t == "text":
            if v is None:
                return {"type": "text", "value": None}
            return {"type": "text", "value": str(v).strip()}
        # Unknown type -> None
        return None

    # Legacy: int -> MCQ index
    if isinstance(item, int):
        return {"type": "mcq", "value": item if 0 <= item <= 3 else None}
    # Legacy: string value (assume text)
    if isinstance(item, str):
        s = item.strip()
        # If single letter A-D, treat as MCQ
        if len(s) == 1 and s.upper() in MCQ_MAP_LETTER_TO_IDX:
            return {"type": "mcq", "value": MCQ_MAP_LETTER_TO_IDX[s.upper()]}
        return {"type": "text", "value": s}

    return None

def _display_value(item):
    """Return a user-friendly string for table display."""
    if item is None:
        return "--"
    t = item.get("type")
    v = item.get("value")
    if v is None:
        return "--"
    if t == "mcq":
        return MCQ_MAP_IDX_TO_LETTER.get(v, "--")
    return str(v)

def _parse_numeric(s):
    """Parse numeric string to float; supports integers, decimals, and simple fractions like 1/3."""
    if s is None:
        return None
    s = str(s).strip().replace(" ", "")
    if s == "":
        return None
    try:
        if "/" in s:
            # Handle simple fraction a/b (no mixed numbers)
            return float(Fraction(s))
        return float(s)
    except Exception:
        return None

def _compare_answers(user_item, correct_item, numeric_tol=1e-3):
    """
    Compare user vs correct.
    Returns (is_attempted, is_correct, has_correct_key).
    - is_attempted: user has a non-None value
    - is_correct: based on type-specific comparison
    - has_correct_key: correct key exists (type+value present)
    """
    u = _normalize_answer_item(user_item)
    c = _normalize_answer_item(correct_item)

    # Attempted?
    is_attempted = (u is not None and u.get("value") is not None)

    # Correct key presence?
    has_correct_key = (c is not None and c.get("value") is not None)

    # If user not attempted, incorrect by definition (for stats), no score change
    if not is_attempted:
        return False, False, has_correct_key

    # If no correct key provided, we can't judge correctness.
    if not has_correct_key:
        return True, False, False

    ut, uv = u.get("type"), u.get("value")
    ct, cv = c.get("type"), c.get("value")

    # If types mismatch, treat as incorrect
    if ut != ct:
        return True, False, True

    if ut == "mcq":
        return True, (uv == cv), True

    if ut == "numeric":
        u_num = _parse_numeric(uv)
        c_num = _parse_numeric(cv)
        if u_num is None or c_num is None:
            # Fall back to string match if parsing fails
            return True, (str(uv).strip() == str(cv).strip()), True
        # Absolute or relative tolerance
        if math.isclose(u_num, c_num, rel_tol=1e-6, abs_tol=numeric_tol):
            return True, True, True
        return True, False, True

    if ut == "text":
        # Case-insensitive, collapse whitespace
        u_norm = " ".join(str(uv).split()).strip().lower()
        c_norm = " ".join(str(cv).split()).strip().lower()
        return True, (u_norm == c_norm), True

    return True, False, True


class ResultsWindow(QWidget):
    def __init__(self, answers, correct_answers=None, time_taken=0, total_time=60,
                 marks_per_correct=1.0, negative_mark=0.0, exam_type="Other"):
        super().__init__()
        # Store as provided; normalization happens in comparison and display
        self.answers = answers or []
        self.correct_answers = correct_answers or [None] * len(self.answers)
        self.time_taken = time_taken
        self.total_time = total_time
        self.num_questions = len(self.answers)
        self.marks_per_correct = float(marks_per_correct)
        self.negative_mark = float(negative_mark)
        self.exam_type = exam_type
        
        self.setWindowTitle('Test Results')
        self.setGeometry(200, 200, 900, 640)
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Title
        title_label = QLabel("Test Results")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 24, QFont.Bold))
        title_label.setStyleSheet("color: #1976d2; margin-bottom: 20px;")
        main_layout.addWidget(title_label)
        
        # Compute statistics
        attempted = 0
        correct = 0
        incorrect_scored = 0
        questions_with_key = 0
        for i in range(self.num_questions):
            is_attempted, is_correct, has_key = _compare_answers(self.answers[i], self.correct_answers[i])
            if is_attempted:
                attempted += 1
            if is_correct:
                correct += 1
            if has_key:
                questions_with_key += 1
                # Count incorrect only when a correct key exists and user attempted but was wrong
                if is_attempted and not is_correct:
                    incorrect_scored += 1

        incorrect = max(0, attempted - correct)
        not_attempted = max(0, self.num_questions - attempted)
        overall_accuracy = (correct / self.num_questions * 100.0) if self.num_questions > 0 else 0.0
        attempted_accuracy = (correct / attempted * 100.0) if attempted > 0 else 0.0
        # Score using marking scheme
        total_score = (correct * self.marks_per_correct) + (incorrect_scored * self.negative_mark)
        max_score = self.num_questions * self.marks_per_correct  # simple max assuming uniform marks
        
        # Summary section
        summary_box = QGroupBox("Test Summary")
        summary_box.setFont(QFont("Arial", 14, QFont.Bold))
        summary_layout = QVBoxLayout()
        
        stats_layout_top = QHBoxLayout()
        total_label = QLabel(f"Total Questions: {self.num_questions}")
        total_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout_top.addWidget(total_label)

        attempted_label = QLabel(f"Attempted: {attempted}")
        attempted_label.setFont(QFont("Arial", 12, QFont.Bold))
        attempted_label.setStyleSheet("color: #1976d2;")
        stats_layout_top.addWidget(attempted_label)

        not_attempted_label = QLabel(f"Unattempted (Skipped): {not_attempted}")
        not_attempted_label.setFont(QFont("Arial", 12, QFont.Bold))
        not_attempted_label.setStyleSheet("color: #9e9e9e;")
        stats_layout_top.addWidget(not_attempted_label)

        summary_layout.addLayout(stats_layout_top)

        stats_layout_bottom = QHBoxLayout()
        correct_label = QLabel(f"Correct: {correct}")
        correct_label.setFont(QFont("Arial", 12, QFont.Bold))
        correct_label.setStyleSheet("color: #43a047;")
        stats_layout_bottom.addWidget(correct_label)
        
        incorrect_label = QLabel(f"Incorrect: {incorrect}")
        incorrect_label.setFont(QFont("Arial", 12, QFont.Bold))
        incorrect_label.setStyleSheet("color: #e53935;")
        stats_layout_bottom.addWidget(incorrect_label)

        accuracy_label = QLabel(f"Overall Accuracy: {overall_accuracy:.1f}%")
        accuracy_label.setFont(QFont("Arial", 12, QFont.Bold))
        accuracy_label.setStyleSheet("color: #1976d2;")
        stats_layout_bottom.addWidget(accuracy_label)

        attempted_acc_label = QLabel(f"Accuracy on Attempted: {attempted_accuracy:.1f}%")
        attempted_acc_label.setFont(QFont("Arial", 12, QFont.Bold))
        attempted_acc_label.setStyleSheet("color: #00796b;")
        stats_layout_bottom.addWidget(attempted_acc_label)

        summary_layout.addLayout(stats_layout_bottom)
        
        # Score and time
        score_time_layout = QHBoxLayout()
        score_label = QLabel(f"Score: {total_score:.2f} / {max_score:.2f}")
        score_label.setFont(QFont("Arial", 16, QFont.Bold))
        score_label.setStyleSheet("color: #1976d2;")
        score_time_layout.addWidget(score_label)
        scheme_label = QLabel(f"Marking: +{self.marks_per_correct} per correct, {self.negative_mark} per incorrect")
        scheme_label.setFont(QFont("Arial", 11))
        score_time_layout.addWidget(scheme_label)
        
        time_label = QLabel(f"Time Taken: {self.format_time(self.time_taken)} / {self.format_time(self.total_time)}")
        time_label.setFont(QFont("Arial", 12))
        score_time_layout.addWidget(time_label)
        
        summary_layout.addLayout(score_time_layout)
        summary_box.setLayout(summary_layout)
        main_layout.addWidget(summary_box)
        
        # Question-wise analysis
        analysis_box = QGroupBox("Question Analysis")
        analysis_box.setFont(QFont("Arial", 14, QFont.Bold))
        analysis_layout = QVBoxLayout()

        table = QTableWidget(self.num_questions, 4)
        table.setHorizontalHeaderLabels(["Question", "Type", "Your Answer", "Correct Answer"])
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.verticalHeader().setVisible(False)

        for i in range(self.num_questions):
            # Normalize items
            u_item = _normalize_answer_item(self.answers[i])
            c_item = _normalize_answer_item(self.correct_answers[i])

            # Question number
            q_item = QTableWidgetItem(f"Q{i+1}")
            q_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 0, q_item)

            # Type
            typ = (u_item or c_item or {"type": None}).get("type")
            type_str = typ.upper() if typ else "--"
            type_item = QTableWidgetItem(type_str)
            type_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 1, type_item)

            # Answers (display)
            user_disp = _display_value(u_item)
            correct_disp = _display_value(c_item)
            user_item = QTableWidgetItem(user_disp)
            user_item.setTextAlignment(Qt.AlignCenter)
            correct_item = QTableWidgetItem(correct_disp)
            correct_item.setTextAlignment(Qt.AlignCenter)

            # Correctness
            is_attempted, is_correct, has_key = _compare_answers(self.answers[i], self.correct_answers[i])

            if is_correct:
                user_item.setBackground(Qt.green)
                user_item.setForeground(Qt.white)
            elif is_attempted and has_key:
                user_item.setBackground(Qt.red)
                user_item.setForeground(Qt.white)
                correct_item.setBackground(Qt.green)
                correct_item.setForeground(Qt.white)
            else:
                # Not attempted
                user_item.setBackground(Qt.lightGray)

            table.setItem(i, 2, user_item)
            table.setItem(i, 3, correct_item)

        table.resizeColumnsToContents()
        analysis_layout.addWidget(table)
        analysis_box.setLayout(analysis_layout)
        main_layout.addWidget(analysis_box)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        close_btn = QPushButton("Close")
        close_btn.setFont(QFont("Arial", 12, QFont.Bold))
        close_btn.setStyleSheet("background-color: #e53935; color: white; padding: 10px 20px; border-radius: 5px;")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
    
    def format_time(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"