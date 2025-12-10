from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QGroupBox, QProgressBar, QHBoxLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
import os
import openai
import json
import io
import math
import fitz  # PyMuPDF

try:
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False


class TopicAnalysisWorker(QThread):
    """Worker thread to fetch topic breakdown from OpenAI."""
    finished = pyqtSignal(dict)  # emits {"topics": [{"name": "...", "count": N}, ...], ...}
    error = pyqtSignal(str)

    def __init__(self, pdf_path, exam_type, num_questions, api_key=None):
        super().__init__()
        self.pdf_path = pdf_path
        self.exam_type = exam_type
        self.num_questions = num_questions
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")

    def run(self):
        try:
            if not self.api_key:
                raise ValueError("OpenAI API key not found.")

            openai.api_key = self.api_key

            # Extract text from PDF
            doc = fitz.open(self.pdf_path)
            full_text = []
            for page_num in range(min(len(doc), 20)):  # Limit to first 20 pages for performance
                page = doc.load_page(page_num)
                try:
                    full_text.append(page.get_text("text"))
                except Exception:
                    continue
            doc.close()
            
            pdf_text = "\n\n".join(full_text)
            # Truncate to avoid token limits (keep first 15000 chars)
            pdf_text = pdf_text[:15000]

            if not pdf_text.strip():
                raise ValueError("No extractable text found in PDF.")

            # Build prompt based on exam type
            exam_context = ""
            if self.exam_type == "JEE Mains":
                exam_context = "This is a JEE Mains exam. Common chapters: Mechanics, Thermodynamics, Waves & Oscillations, Electrostatics, Current Electricity, Magnetism, Optics, Modern Physics (Physics); General Organic & Inorganic Chemistry, Physical Chemistry (Chemistry); Algebra, Trigonometry, Coordinate Geometry, Calculus (Mathematics)."
            elif self.exam_type == "JEE Advanced":
                exam_context = "This is a JEE Advanced exam. Similar to JEE Mains with common chapters: Mechanics, Thermodynamics, Waves & Oscillations, Electrostatics, Current Electricity, Magnetism, Optics, Modern Physics (Physics); General Organic & Inorganic Chemistry, Physical Chemistry (Chemistry); Algebra, Trigonometry, Coordinate Geometry, Calculus (Mathematics)."
            elif self.exam_type == "NEET":
                exam_context = "This is a NEET exam. Topics: Biology (Cell Biology, Genetics, Ecology, Human Physiology, Plant Physiology, etc.), Physics (Mechanics, Thermodynamics, Waves, Electromagnetism, Modern Physics), Chemistry (Organic, Inorganic, Physical)."

            prompt = f"""Analyze the following question paper text and identify the topics/chapters covered.

{exam_context}

Question Paper Content:
{pdf_text}

Based on the content above, identify the main topics/chapters and estimate how many questions belong to each topic.
Total questions in paper: {self.num_questions}

Return a JSON object with this exact structure:
{{
  "topics": [
    {{"name": "Topic/Chapter Name", "count": N, "section": "Section Name"}},
    ...
  ]
}}

Rules:
- "name": specific chapter/topic name (e.g., "Mechanics", "Organic Chemistry", "Cell Biology")
- "count": estimated number of questions from this topic (must sum to approximately {self.num_questions})
- "section": broader category (e.g., "Physics", "Chemistry", "Mathematics", "Biology")
- Identify 5-12 main topics based on actual content
- Return only valid JSON, no explanations.
"""

            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.3
            )

            result_text = response.choices[0].message.content.strip()
            # Extract JSON
            start = result_text.find('{')
            end = result_text.rfind('}') + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON found in response.")
            json_str = result_text[start:end]
            data = json.loads(json_str)
            
            # Validate and normalize counts
            topics = data.get("topics", [])
            total_count = sum(t.get("count", 0) for t in topics)
            if total_count != self.num_questions and total_count > 0:
                # Normalize to match num_questions
                scale = self.num_questions / total_count
                for t in topics:
                    t["count"] = max(1, round(t.get("count", 0) * scale))
            
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))


class QPAnalysisWindow(QWidget):
    def __init__(self, pdf_path=None, exam_type="Other", num_questions=0, answers=None, correct_answers=None):
        super().__init__()
        self.pdf_path = pdf_path
        self.exam_type = exam_type
        self.num_questions = num_questions
        self.answers = answers or []
        self.correct_answers = correct_answers or []
        self.topic_data = None

        self.setWindowTitle(f"Question Paper Analysis — {self.exam_type}")
        self.setGeometry(250, 250, 900, 700)
        self.init_ui()
        if self.pdf_path:
            self.fetch_topic_analysis()
        else:
            self.on_topic_analysis_error("No PDF path provided")

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Title
        title = QLabel("Question Paper Analysis")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setStyleSheet("color:#1565c0; margin-bottom: 10px;")
        main_layout.addWidget(title)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setSpacing(16)

        # Topics section placeholder (will be filled on data arrival)
        self.topics_box = QGroupBox("Topics / Chapters")
        self.topics_box.setFont(QFont("Arial", 12, QFont.Bold))
        topics_layout = QVBoxLayout()
        loading_label = QLabel("Analyzing question paper...")
        loading_label.setAlignment(Qt.AlignCenter)
        loading_label.setStyleSheet("color:#999;")
        topics_layout.addWidget(loading_label)
        self.topics_box.setLayout(topics_layout)

        self.content_layout.addWidget(self.topics_box)
        self.content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def fetch_topic_analysis(self):
        """Fetch topic breakdown from OpenAI in a worker thread."""
        self.worker = TopicAnalysisWorker(self.pdf_path, self.exam_type, self.num_questions)
        self.worker.finished.connect(self.on_topic_analysis_ready)
        self.worker.error.connect(self.on_topic_analysis_error)
        self.worker.start()

    def on_topic_analysis_ready(self, data):
        """Called when topic data is received."""
        self.topic_data = data
        self.render_topics_section()

    def on_topic_analysis_error(self, error_msg):
        """Called on error."""
        topics_layout = self.topics_box.layout()
        # Clear existing
        while topics_layout.count():
            topics_layout.takeAt(0).widget().deleteLater()
        # Show error
        err_label = QLabel(f"Error: {error_msg}")
        err_label.setStyleSheet("color:#e53935;")
        topics_layout.addWidget(err_label)

    def render_topics_section(self):
        """Render the topics section with pie chart and table."""
        if not self.topic_data or "topics" not in self.topic_data:
            return

        topics = self.topic_data.get("topics", [])
        if not topics:
            return

        # Clear existing layout
        topics_layout = self.topics_box.layout()
        while topics_layout.count():
            topics_layout.takeAt(0).widget().deleteLater()

        # Pie chart (larger and clearer)
        if MATPLOTLIB_AVAILABLE:
            try:
                fig = Figure(figsize=(6.0, 6.0), dpi=100)
                ax = fig.add_subplot(111)
                names = [t["name"] for t in topics]
                counts = [t["count"] for t in topics]
                colors = self._get_colors(len(names))

                wedges, texts, autotexts = ax.pie(
                    counts,
                    labels=names,
                    colors=colors,
                    autopct="%1.1f%%",
                    startangle=90
                )
                ax.set_aspect("equal")
                for autotext in autotexts:
                    autotext.set_color("white")
                    autotext.set_fontsize(11)
                    autotext.set_weight("bold")
                for text in texts:
                    text.set_fontsize(10)
                    text.set_weight("bold")

                fig.tight_layout()
                buf = io.BytesIO()
                fig.savefig(buf, format="png", transparent=True, dpi=100)
                buf.seek(0)
                pix = QPixmap()
                if pix.loadFromData(buf.getvalue(), "PNG"):
                    img_lbl = QLabel()
                    img_lbl.setAlignment(Qt.AlignCenter)
                    img_lbl.setPixmap(pix.scaledToWidth(550, Qt.SmoothTransformation))
                    topics_layout.addWidget(img_lbl, alignment=Qt.AlignCenter)
            except Exception:
                pass

        # Topic list with bars
        topics_layout.addSpacing(20)
        list_label = QLabel("Topic Breakdown")
        list_label.setFont(QFont("Arial", 12, QFont.Bold))
        list_label.setStyleSheet("color:#333; margin-top: 10px;")
        topics_layout.addWidget(list_label)

        for i, topic in enumerate(topics):
            topic_row = QHBoxLayout()
            topic_row.setSpacing(10)
            
            # Topic name
            name_lbl = QLabel(topic["name"])
            name_lbl.setFont(QFont("Arial", 11, QFont.Bold))
            name_lbl.setMinimumWidth(150)
            name_lbl.setMaximumWidth(150)
            topic_row.addWidget(name_lbl)

            # Progress bar (visual representation)
            pct = (topic["count"] / self.num_questions * 100.0) if self.num_questions > 0 else 0
            bar = QProgressBar()
            bar.setValue(int(pct))
            bar.setMinimumHeight(24)
            bar.setStyleSheet(
                "QProgressBar { border: 1px solid #bbb; border-radius: 4px; }"
                "QProgressBar::chunk { background-color: " + self._get_color(i) + "; border-radius: 3px; }"
            )
            topic_row.addWidget(bar, stretch=1)

            # Count and percentage
            count_lbl = QLabel(f"{topic['count']} ({pct:.1f}%)")
            count_lbl.setFont(QFont("Arial", 11, QFont.Bold))
            count_lbl.setMinimumWidth(110)
            count_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            topic_row.addWidget(count_lbl)

            topics_layout.addLayout(topic_row)

        topics_layout.addSpacing(20)

    def _get_colors(self, n):
        """Generate n distinct colors."""
        colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8",
            "#6C5CE7", "#A29BFE", "#74B9FF", "#81ECEC", "#55EFC4",
            "#FD79A8", "#FDCB6E", "#6C7A89", "#00B894", "#FF7675"
        ]
        return [colors[i % len(colors)] for i in range(n)]

    def _get_color(self, index):
        """Get a specific color by index."""
        colors = self._get_colors(20)
        return colors[index % len(colors)]