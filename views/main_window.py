from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QStackedWidget, QLabel
from PyQt5.QtCore import QDateTime, QTimer, Qt

from .home_view import HomeView
from .equipment_form import EquipmentForm
from .hull_form import HullForm
from .design_view import DesignView
from .fleet_view import FleetView
from .settings_view import SettingsView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Naval Design System")
        self.setFixedSize(800, 600)  # Windows 95アプリは通常固定サイズ

        # メインウィジェットとレイアウトの設定
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)

        # サイドメニューの作成
        self.side_menu = QListWidget()
        self.side_menu.addItems(["ホーム", "装備登録", "船体登録", "船体設計", "艦隊配備", "設定"])
        self.side_menu.setFixedWidth(200)  # サイドメニューの幅を固定

        # メインビューの作成
        self.main_view = QStackedWidget()

        # 各画面を作成してスタックに追加
        self.home_view = HomeView()
        self.equipment_form = EquipmentForm()
        self.hull_form = HullForm()
        self.design_view = DesignView()
        self.fleet_view = FleetView()
        self.settings_view = SettingsView()

        self.main_view.addWidget(self.home_view)
        self.main_view.addWidget(self.equipment_form)
        self.main_view.addWidget(self.hull_form)
        self.main_view.addWidget(self.design_view)
        self.main_view.addWidget(self.fleet_view)
        self.main_view.addWidget(self.settings_view)

        # サイドメニューの選択変更シグナルを接続
        self.side_menu.currentRowChanged.connect(self.main_view.setCurrentIndex)

        # レイアウトにウィジェットを追加
        main_layout.addWidget(self.side_menu)
        main_layout.addWidget(self.main_view)

        self.setCentralWidget(central_widget)

        # Windows 95スタイルを適用
        self.setStyleSheet("""
            QMainWindow {
                background-color: #c0c0c0;
            }
            QListWidget {
                background-color: #cccccc;
                border: 2px solid #808080;
                border-style: inset;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #0a246a;
                color: white;
            }
            QLabel {
                color: black;
                font-family: "MS Sans Serif", Arial;
            }
            QWidget {
                background-color: #cccccc;
            }
            QPushButton {
                background-color: #cccccc;
                border: 2px solid #808080;
                border-style: outset;
                padding: 5px;
            }
            QPushButton:pressed {
                border-style: inset;
            }
            QLineEdit, QTextEdit {
                background-color: white;
                border: 2px solid #808080;
                border-style: inset;
            }
        """)

        # 初期選択をホームにする
        self.side_menu.setCurrentRow(0)