from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

class FleetView(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("艦隊配備画面"))
        layout.addStretch()