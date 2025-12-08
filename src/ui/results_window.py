from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QGroupBox, QScrollArea
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap

class ResultsWindow(QWidget):
    def __init__(self, answers, correct_answers=None, time_taken=0, total_time=60):
        super().__init__()
        self.answers = answers
        self.correct_answers = correct_answers or [0] * len(answers)  # Default correct answers
        self.time_taken = time_taken
        self.total_time = total_time
        self.num_questions = len(answers)
        
        self.setWindowTitle('Test Results')
        self.setGeometry(200, 200, 800, 600)
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
        
        # Summary section
        summary_box = QGroupBox("Test Summary")
        summary_box.setFont(QFont("Arial", 14, QFont.Bold))
        summary_layout = QVBoxLayout()
        
        # Calculate statistics
        attempted = sum(1 for ans in self.answers if ans is not None)
        correct = sum(1 for i, ans in enumerate(self.answers) 
                     if ans is not None and ans == self.correct_answers[i])
        incorrect = attempted - correct
        not_attempted = self.num_questions - attempted
        skipped = not_attempted  # alias for clarity
        overall_accuracy = (correct / self.num_questions * 100.0) if self.num_questions > 0 else 0.0
        attempted_accuracy = (correct / attempted * 100.0) if attempted > 0 else 0.0
        
        # Summary labels
        stats_layout_top = QHBoxLayout()
        total_label = QLabel(f"Total Questions: {self.num_questions}")
        total_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout_top.addWidget(total_label)

        attempted_label = QLabel(f"Attempted: {attempted}")
        attempted_label.setFont(QFont("Arial", 12, QFont.Bold))
        attempted_label.setStyleSheet("color: #1976d2;")
        stats_layout_top.addWidget(attempted_label)

        not_attempted_label = QLabel(f"Unattempted: {not_attempted}")
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
        score_label = QLabel(f"Score: {correct}/{self.num_questions}")
        score_label.setFont(QFont("Arial", 16, QFont.Bold))
        score_label.setStyleSheet("color: #1976d2;")
        score_time_layout.addWidget(score_label)
        
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

        table = QTableWidget(self.num_questions, 3)
        table.setHorizontalHeaderLabels(["Question", "Your Answer", "Correct Answer"])
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.verticalHeader().setVisible(False)

        answer_map = {None: "--", 0: "A", 1: "B", 2: "C", 3: "D"}

        for i in range(self.num_questions):
            # Question number
            q_item = QTableWidgetItem(f"Q{i+1}")
            q_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 0, q_item)

            # User answer
            user_ans = answer_map.get(self.answers[i], "--")
            user_item = QTableWidgetItem(user_ans)
            user_item.setTextAlignment(Qt.AlignCenter)

            # Correct answer
            correct_ans = answer_map.get(self.correct_answers[i], "--")
            correct_item = QTableWidgetItem(correct_ans)
            correct_item.setTextAlignment(Qt.AlignCenter)

            # Highlighting
            if self.answers[i] is not None and self.answers[i] == self.correct_answers[i]:
                user_item.setBackground(Qt.green)
                user_item.setForeground(Qt.white)
            elif self.answers[i] is not None and self.correct_answers[i] is not None:
                user_item.setBackground(Qt.red)
                user_item.setForeground(Qt.white)
                correct_item.setBackground(Qt.green)
                correct_item.setForeground(Qt.white)
            elif self.answers[i] is None:
                user_item.setBackground(Qt.lightGray)

            table.setItem(i, 1, user_item)
            table.setItem(i, 2, correct_item)

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