import json
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QStackedWidget
)
from PySide6.QtCore import Qt
import sys
import datetime

def load_equipment_definition(name: str) -> dict:
    path = Path(__file__).resolve().parent / "data" / f"{name}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Naval Design System")
        self.setFixedSize(800, 600)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            * {
                font-family: "MS UI Gothic";
                font-size: 14pt;
            }
            QListWidget {
                background-color: #F0F0F0;
                border: 1px solid gray;
            }
            QLabel {
                margin: 4px;
            }
        """)

        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)

        self.menu = QListWidget()
        self.menu.addItems(["ホーム", "装備登録", "船体登録", "船体設計", "艦隊配備", "設定"])
        self.menu.setFixedWidth(200)

        self.stack = QStackedWidget()
        self.home_view = self.create_home_view()
        self.stack.addWidget(self.home_view)

        self.menu.currentRowChanged.connect(self.stack.setCurrentIndex)

        main_layout.addWidget(self.menu)
        main_layout.addWidget(self.stack)
        self.setCentralWidget(main_widget)

    def create_home_view(self):
        home = QWidget()
        layout = QVBoxLayout()
        welcome = QLabel("ようこそ")
        now = QLabel(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        layout.addWidget(welcome)
        layout.addWidget(now)
        layout.addStretch()
        home.setLayout(layout)
        return home

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
