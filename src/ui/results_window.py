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
        
        # Summary labels
        stats_layout = QHBoxLayout()
        
        total_label = QLabel(f"Total Questions: {self.num_questions}")
        total_label.setFont(QFont("Arial", 12, QFont.Bold))
        stats_layout.addWidget(total_label)
        
        attempted_label = QLabel(f"Attempted: {attempted}")
        attempted_label.setFont(QFont("Arial", 12, QFont.Bold))
        attempted_label.setStyleSheet("color: #1976d2;")
        stats_layout.addWidget(attempted_label)
        
        correct_label = QLabel(f"Correct: {correct}")
        correct_label.setFont(QFont("Arial", 12, QFont.Bold))
        correct_label.setStyleSheet("color: #43a047;")
        stats_layout.addWidget(correct_label)
        
        incorrect_label = QLabel(f"Incorrect: {incorrect}")
        incorrect_label.setFont(QFont("Arial", 12, QFont.Bold))
        incorrect_label.setStyleSheet("color: #e53935;")
        stats_layout.addWidget(incorrect_label)
        
        not_attempted_label = QLabel(f"Not Attempted: {not_attempted}")
        not_attempted_label.setFont(QFont("Arial", 12, QFont.Bold))
        not_attempted_label.setStyleSheet("color: #9e9e9e;")
        stats_layout.addWidget(not_attempted_label)
        
        summary_layout.addLayout(stats_layout)
        
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
        
        # Question-wise analysis (placeholder for now)
        analysis_box = QGroupBox("Question Analysis")
        analysis_box.setFont(QFont("Arial", 14, QFont.Bold))
        analysis_layout = QVBoxLayout()
        
        analysis_label = QLabel("Detailed question-wise analysis will be shown here.")
        analysis_label.setFont(QFont("Arial", 12))
        analysis_label.setStyleSheet("color: #666; padding: 20px;")
        analysis_layout.addWidget(analysis_label)
        
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