from PyQt5.QtCore import QThread, pyqtSignal
import os
import openai

class HintWorker(QThread):
    """
    QThread worker that produces a short hint for a question.
    Signals:
      finished(str) -> emits the hint text on success
      error(str)    -> emits an error message on failure
    """
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, question_text, options=None, api_key=None, model="gpt-3.5-turbo"):
        super().__init__()
        self.question_text = question_text or ""
        self.options = options or []
        self.api_key = api_key
        self.model = model

    def run(self):
        try:
            key = self.api_key or os.getenv("OPENAI_API_KEY", "")
            if not key:
                self.error.emit("OPENAI_API_KEY not set.")
                return
            openai.api_key = key

            opts_text = ""
            if self.options:
                opts_text = "\nOptions:\n" + "\n".join(self.options)

            prompt = (
                "Provide a concise (<=2 sentences) pedagogical hint for the question below. "
                "Do NOT reveal the final answer. Avoid stating which option is correct.\n\n"
                f"Question:\n{self.question_text}\n\n{opts_text}\n\nHint:"
            )

            resp = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You generate short hints without revealing answers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=120
            )

            try:
                hint = resp.choices[0].message.content.strip()
            except Exception:
                hint = str(resp)

            if not hint:
                self.error.emit("Empty hint from API.")
                return

            self.finished.emit(hint)
        except Exception as e:
            self.error.emit(str(e))