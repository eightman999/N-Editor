from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel, QStatusBar, QListWidget
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QCloseEvent

import os
import json

from views.home_view import HomeView
from views.equipment_view import EquipmentView
from views.hull_form import HullForm
from views.hull_list_view import HullListView
from views.design_view import DesignView
from views.fleet_view import FleetView
from views.settings_view import SettingsView
from views.nation_view import NationView

class NavalDesignSystem(QMainWindow):
    """Naval Design Systemのメインウィンドウ"""

    def __init__(self, app_controller=None, app_settings=None):
        super().__init__()

        # コントローラーとアプリケーション設定
        self.app_controller = app_controller
        self.app_settings = app_settings

        # ビューマッピング
        self.views = {}

        # アプリケーション設定の読み込み
        self.load_config()

        # UIの初期化
        self.init_ui()

    def load_config(self):
        """設定ファイルを読み込む"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'config.json')

        # デフォルト設定
        self.config = {
            "app_name": "Naval Design System",
            "version": "β0.0.1",
            "display": {
                "width": 1080,
                "height": 720,
                "fullscreen": False
            }
        }

        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config.update(json.load(f))
        except Exception as e:
            print(f"設定ファイルの読み込みに失敗しました: {e}")

    def init_ui(self):
        """UIの初期化"""
        # ウィンドウの基本設定
        self.setWindowTitle(self.config.get("app_name", "Naval Design System"))

        # 全画面表示の設定を読み込み
        is_fullscreen = self.config.get("display", {}).get("fullscreen", False)

        if not is_fullscreen:
            # 通常サイズで表示する場合
            width = self.config.get("display", {}).get("width", 800)
            height = self.config.get("display", {}).get("height", 600)
            self.resize(width, height)  # setFixedSizeの代わりにresizeを使用
        else:
            # 全画面表示
            self.showFullScreen()

        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # メインレイアウト
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # サイドバーメニュー
        self.create_sidebar(main_layout)

        # メインビュー
        self.create_main_view(main_layout)

        # ステータスバー
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("準備完了")

    def create_sidebar(self, parent_layout):
        """サイドバーメニューの作成"""
        # サイドバーウィジェット
        sidebar_widget = QWidget()
        sidebar_widget.setFixedWidth(200)  # サイドバーの幅
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(5, 10, 5, 10)
        sidebar_layout.setSpacing(10)


        # メニューリスト
        self.menu_list = QListWidget()
        self.menu_list.addItems([
            "ホーム",
            "装備登録",
            "船体リスト",
            "船体登録",
            "船体設計",
            "艦隊配備",
            "国家確認",  # 追加
            "設定"
        ])

        # スタイルの設定
        self.menu_list.setFont(QFont("MS Gothic", 12))
        self.menu_list.setIconSize(QSize(24, 24))
        self.menu_list.setStyleSheet("""
            QListWidget {
                background-color: #e6e6e6;
                border: 2px inset #808080;
            }
            QListWidget::item {
                height: 30px;
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #000080;
                color: white;
            }
        """)

        # 選択時の処理
        self.menu_list.currentRowChanged.connect(self.on_menu_changed)

        # タイトルラベル
        title_label = QLabel("<b>Naval Design System</b>")
        title_label.setFont(QFont("MS Gothic", 14))
        title_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title_label)

        sidebar_layout.addWidget(self.menu_list)
        sidebar_layout.addStretch(1)

        # バージョン情報
        version_text = f"Version {self.config.get('version', '0.0.0')}"
        version_label = QLabel(version_text)
        version_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(version_label)

        parent_layout.addWidget(sidebar_widget)

    def create_main_view(self, parent_layout):
        """メインビューの作成"""
        # メインビューウィジェット
        main_view_widget = QWidget()
        main_layout = QVBoxLayout(main_view_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # スタック型ウィジェット（ページ切り替え用）
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # 各ページの追加
        self.initialize_views()

        parent_layout.addWidget(main_view_widget)

    def initialize_views(self):
        """各ビューを初期化して登録"""
        # ホームビュー
        home_view = HomeView(self, self.app_settings)
        self.add_view("home", home_view)

        # 装備ビュー
        equipment_view = EquipmentView(self)
        self.add_view("equipment", equipment_view)
        # 船体リストビュー
        hull_list_view = HullListView(self, self.app_controller)
        self.add_view("hull_list", hull_list_view)
        # 船体ビュー
        hull_view = HullForm(self)
        self.add_view("hull", hull_view)

        nation_view = NationView(self, self.app_controller)
        self.add_view("nation", nation_view)
        # 設計ビュー
        design_view = DesignView(self)
        self.add_view("design", design_view)

        # 艦隊ビュー
        fleet_view = FleetView(self)
        self.add_view("fleet", fleet_view)

        # 設定ビュー
        settings_view = SettingsView(self, self.app_settings)
        self.add_view("settings", settings_view)

    def add_view(self, view_name, view_widget):
        """ビューをスタックウィジェットに追加"""
        self.views[view_name] = view_widget
        self.stacked_widget.addWidget(view_widget)

    def on_menu_changed(self, index):
        """メニュー選択時の処理"""
        # スタックウィジェットのページを切り替え
        self.stacked_widget.setCurrentIndex(index)

        # ステータスバーにメッセージを表示
        menu_texts = ["ホーム", "装備登録", "船体リスト", "船体登録", "船体設計", "艦隊配備", "国家確認", "設定"]
        if 0 <= index < len(menu_texts):
            self.statusBar.showMessage(f"{menu_texts[index]}ページを表示しています")

    # show_view メソッド内の対応も修正
    def show_view(self, view_name):
        """指定した名前のビューを表示"""
        view_mapping = {
            "home": 0,
            "equipment": 1,
            "hull_list": 2,
            "hull_form": 3,
            "design": 4,
            "fleet": 5,
            "nation": 6,  # 追加
            "settings": 7
        }

        if view_name in view_mapping:
            index = view_mapping[view_name]
            self.menu_list.setCurrentRow(index)
            self.stacked_widget.setCurrentIndex(index)

            # ステータスバーにメッセージを表示
            menu_texts = ["ホーム", "装備登録", "船体リスト", "船体登録", "船体設計", "艦隊配備", "国家確認", "設定"]
            if 0 <= index < len(menu_texts):
                self.statusBar.showMessage(f"{menu_texts[index]}ページを表示しています")

    def closeEvent(self, event: QCloseEvent):
        """ウィンドウが閉じられる時の処理"""
        if self.app_controller:
            self.app_controller.on_quit()
        event.accept()

    def toggle_fullscreen(self):
        """全画面表示と通常表示を切り替え"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()