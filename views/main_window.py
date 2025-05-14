from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QStackedWidget,
                             QLabel, QFrame)
from PyQt5.QtCore import Qt, QDateTime, QTimer
from PyQt5.QtGui import QCloseEvent, QFont

class MainWindow(QMainWindow):
    """アプリケーションのメインウィンドウ"""
    def __init__(self, controller, app_settings):
        super().__init__()
        self.controller = controller
        self.app_settings = app_settings
        self.initUI()

        # 時計更新用タイマー
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)  # 1秒ごとに更新

    def initUI(self):
        """UIの初期化"""
        self.setWindowTitle("Naval Design System")
        self.setMinimumSize(800, 600)

        # メインウィジェット
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # メインレイアウト
        main_layout = QHBoxLayout(main_widget)

        # サイドバー
        sidebar = QFrame()
        sidebar.setFrameShape(QFrame.StyledPanel)
        sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)

        # タイトルラベル
        title_label = QLabel("Naval Design System")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title_label)

        # 時計表示
        self.clock_label = QLabel()
        self.clock_label.setAlignment(Qt.AlignCenter)
        self.update_clock()  # 初期表示
        sidebar_layout.addWidget(self.clock_label)

        # メニューボタン
        self.create_menu_button("ホーム", "home", sidebar_layout)
        self.create_menu_button("装備登録", "equipment", sidebar_layout)
        self.create_menu_button("船体登録", "hull", sidebar_layout)
        self.create_menu_button("船体設計", "design", sidebar_layout)
        self.create_menu_button("艦隊配備", "fleet", sidebar_layout)

        # スペーサー
        sidebar_layout.addStretch(1)

        # 設定ボタン
        self.create_menu_button("設定", "settings", sidebar_layout)

        # スタックウィジェット（メインコンテンツ表示用）
        self.stack = QStackedWidget()

        # レイアウトに追加
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stack)

    def create_menu_button(self, text, view_name, layout):
        """メニューボタンを作成してレイアウトに追加"""
        button = QPushButton(text)
        button.setFixedHeight(40)
        button.clicked.connect(lambda: self.controller.navigate_to(view_name))
        layout.addWidget(button)
        return button

    def add_view(self, name, widget):
        """ビューをスタックウィジェットに追加"""
        self.stack.addWidget(widget)
        setattr(self, f"{name}_index", self.stack.count() - 1)

    def show_view(self, name):
        """指定した名前のビューを表示"""
        index = getattr(self, f"{name}_index", -1)
        if index >= 0:
            self.stack.setCurrentIndex(index)

    def update_clock(self):
        """時計表示を更新"""
        current_time = QDateTime.currentDateTime()
        time_str = current_time.toString("yyyy/MM/dd HH:mm:ss")
        self.clock_label.setText(time_str)

    def closeEvent(self, event: QCloseEvent):
        """ウィンドウが閉じられるときの処理"""
        self.controller.on_quit()
        event.accept()