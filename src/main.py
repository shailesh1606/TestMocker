import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from db.storage import init_db
from dotenv import load_dotenv  # add

def main():
    load_dotenv()  # load .env so OPENAI_API_KEY becomes available
    init_db()  # ensure DB/tables exist
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()