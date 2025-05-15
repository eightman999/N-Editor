from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

class HullForm(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("船体登録画面"))
        layout.addStretch()