from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import QDateTime, QTimer

class HomeView(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # 時刻表示
        self.time_label = QLabel()
        self.updateTime()  # 初期時刻設定

        # 時刻更新用タイマー
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateTime)
        self.timer.start(1000)  # 1秒ごとに更新

        # ようこそメッセージ
        welcome_label = QLabel("ようこそ Naval Design System へ")
        welcome_label.setStyleSheet("font-size: 18px;")

        description_label = QLabel("Hearts of Iron IVのmod支援用艦艇設計ツールです。このアプリケーションで、リアルなデータに基づいた艦艇設計が可能です。")
        description_label.setWordWrap(True)

        layout.addWidget(self.time_label)
        layout.addWidget(welcome_label)
        layout.addWidget(description_label)
        layout.addStretch()  # 残りのスペースを埋める

    def updateTime(self):
        current_time = QDateTime.currentDateTime()
        formatted_time = current_time.toString("yyyy/MM/dd hh:mm:ss")
        self.time_label.setText(f"現在時刻: {formatted_time}")