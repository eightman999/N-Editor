from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

class SettingsView(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("設定画面"))
        layout.addStretch()