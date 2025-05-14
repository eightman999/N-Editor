from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from .mod_selector_widget import ModSelectorWidget

class HomeView(QWidget):
    """ホーム画面のビュー"""
    def __init__(self, parent=None, app_settings=None):
        super().__init__(parent)
        self.app_settings = app_settings
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # ウェルカムメッセージ
        welcome_label = QLabel("Naval Design System へようこそ", self)
        welcome_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(welcome_label)

        description_label = QLabel("Hearts of Iron IV向け艦艇設計ツール", self)
        layout.addWidget(description_label)

        # MOD選択リストを追加
        mod_label = QLabel("編集対象MODを選択", self)
        mod_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(mod_label)

        self.mod_selector = ModSelectorWidget(self, app_settings=self.app_settings)
        layout.addWidget(self.mod_selector)

        self.setLayout(layout)