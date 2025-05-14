from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

class EquipmentForm(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("装備登録画面"))
        layout.addStretch()