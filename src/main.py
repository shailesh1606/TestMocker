import os
import sys
from PyQt5.QtCore import Qt, QCoreApplication
from dotenv import load_dotenv
from db.storage import init_db

def main():
    # Load .env (API keys etc.)
    load_dotenv()

    # Force software rendering to avoid GPU channel failures
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")
    os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
    # If running as root, disable sandbox (required by Chromium)
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

    # Must be set BEFORE creating QApplication and before importing WebEngine
    QCoreApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, on=True)

    from PyQt5.QtWidgets import QApplication
    from ui.main_window import MainWindow

    init_db()
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()