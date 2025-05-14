from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

class DesignView(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("船体設計画面"))
        layout.addStretch()