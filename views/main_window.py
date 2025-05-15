import datetime
import json
import os
import sys

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QStackedWidget,
                             QLabel, QFrame, QApplication, QStatusBar, QListWidget)
from PyQt5.QtCore import Qt, QDateTime, QTimer
from PyQt5.QtGui import QCloseEvent, QFont

# 自作モジュールのインポート
from views.equipment_form import EquipmentForm
from views.equipment_view import EquipmentView

class NavalDesignSystem(QMainWindow):
    """Naval Design Systemのメインウィンドウ"""

    def __init__(self):
        super().__init__()

        # アプリケーション設定の読み込み
        self.load_config()

        # UIの初期化
        self.init_ui()

        # 最初のページを表示
        self.show_home_page()

    def load_config(self):
        """設定ファイルを読み込む"""
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'config.json')

        # デフォルト設定
        self.config = {
            "app_name": "Naval Design System",
            "version": "1.0.0",
            "display": {
                "width": 800,
                "height": 600,
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
        width = self.config.get("display", {}).get("width", 800)
        height = self.config.get("display", {}).get("height", 600)
        self.setFixedSize(width, height)

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
        sidebar_widget.setFixedWidth(150)  # サイドバーの幅
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(5, 10, 5, 10)
        sidebar_layout.setSpacing(5)

        # メニューリスト
        self.menu_list = QListWidget()
        self.menu_list.addItems([
            "ホーム",
            "装備登録",
            "船体登録",
            "船体設計",
            "艦隊配備",
            "設定"
        ])

        # スタイルの設定
        self.menu_list.setFont(QFont("MS Gothic", 10))

        # 選択時の処理
        self.menu_list.currentRowChanged.connect(self.on_menu_changed)

        sidebar_layout.addWidget(QLabel("<b>Naval Design System</b>"))
        sidebar_layout.addWidget(self.menu_list)
        sidebar_layout.addStretch(1)

        # バージョン情報
        version_text = f"Version {self.config.get('version', '1.0.0')}"
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
        self.add_home_page()
        self.add_equipment_page()
        self.add_hull_page()
        self.add_design_page()
        self.add_fleet_page()
        self.add_settings_page()

        parent_layout.addWidget(main_view_widget)

    def add_home_page(self):
        """ホームページの追加"""
        home_page = QWidget()
        layout = QVBoxLayout(home_page)

        welcome_label = QLabel("Naval Design Systemへようこそ")
        welcome_label.setFont(QFont("MS Gothic", 16))
        welcome_label.setAlignment(Qt.AlignCenter)

        # 現在時刻
        time_label = QLabel(f"現在時刻: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
        time_label.setAlignment(Qt.AlignCenter)

        # 概要
        description = """
        <p>このアプリケーションは、Hearts of Iron IVのmod支援用艦艇設計ツールです。</p>
        <p>以下の機能を提供します：</p>
        <ul>
            <li>装備データの登録と管理</li>
            <li>船体情報の登録</li>
            <li>艦艇の設計とパラメータ計算</li>
            <li>設計データのエクスポート/インポート</li>
            <li>艦隊構成の管理</li>
        </ul>
        <p>左側のメニューから各機能にアクセスできます。</p>
        """
        desc_label = QLabel(description)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)

        layout.addWidget(welcome_label)
        layout.addWidget(time_label)
        layout.addWidget(desc_label)
        layout.addStretch(1)

        self.stacked_widget.addWidget(home_page)

    def add_equipment_page(self):
        """装備ページの追加"""
        self.equipment_view = EquipmentView()
        self.stacked_widget.addWidget(self.equipment_view)

    def add_hull_page(self):
        """船体ページの追加"""
        hull_page = QWidget()
        layout = QVBoxLayout(hull_page)

        # 仮のプレースホルダーラベル
        label = QLabel("船体登録ページ（開発中）")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.stacked_widget.addWidget(hull_page)

    def add_design_page(self):
        """設計ページの追加"""
        design_page = QWidget()
        layout = QVBoxLayout(design_page)

        # 仮のプレースホルダーラベル
        label = QLabel("船体設計ページ（開発中）")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.stacked_widget.addWidget(design_page)

    def add_fleet_page(self):
        """艦隊ページの追加"""
        fleet_page = QWidget()
        layout = QVBoxLayout(fleet_page)

        # 仮のプレースホルダーラベル
        label = QLabel("艦隊配備ページ（開発中）")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.stacked_widget.addWidget(fleet_page)

    def add_settings_page(self):
        """設定ページの追加"""
        settings_page = QWidget()
        layout = QVBoxLayout(settings_page)

        # 仮のプレースホルダーラベル
        label = QLabel("設定ページ（開発中）")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.stacked_widget.addWidget(settings_page)

    def on_menu_changed(self, index):
        """メニュー選択時の処理"""
        # スタックウィジェットのページを切り替え
        self.stacked_widget.setCurrentIndex(index)

        # ステータスバーにメッセージを表示
        menu_texts = ["ホーム", "装備登録", "船体登録", "船体設計", "艦隊配備", "設定"]
        if 0 <= index < len(menu_texts):
            self.statusBar.showMessage(f"{menu_texts[index]}ページを表示しています")

    def show_home_page(self):
        """ホームページを表示"""
        self.menu_list.setCurrentRow(0)
        self.stacked_widget.setCurrentIndex(0)

def main():
    # アプリケーションの起動
    app = QApplication(sys.argv)

    # スタイルシートの適用（Windows95風）
    app.setStyle("Fusion")

    # メインウィンドウを作成
    window = NavalDesignSystem()
    window.show()

    # イベントループの開始
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()