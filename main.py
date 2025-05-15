import os
import sys
import datetime
import json
from pathlib import Path
import platform

os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ".venv/lib/python3.13/site-packages/PyQt5/Qt5/plugins/platforms"

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QStackedWidget,
                             QLabel, QFrame, QApplication, QStatusBar, QListWidget,
                             QFileDialog, QMessageBox, QListWidgetItem)
from PyQt5.QtCore import Qt, QDateTime, QTimer, QSize
from PyQt5.QtGui import QCloseEvent, QFont, QIcon, QPixmap

# 自作モジュールのインポート
from views.equipment_form import EquipmentForm
from views.equipment_view import EquipmentView
from views.hull_form import HullForm
from views.design_view import DesignView
from views.fleet_view import FleetView
from views.settings_view import SettingsView
from models.app_settings import AppSettings

class ModItem:
    """MODの情報を保持するクラス"""
    def __init__(self, name, version, supported_version, path, thumbnail_path=None):
        self.name = name
        self.version = version
        self.supported_version = supported_version
        self.path = path
        self.thumbnail_path = thumbnail_path

    def to_dict(self):
        """辞書形式に変換"""
        return {
            "name": self.name,
            "version": self.version,
            "supported_version": self.supported_version,
            "path": self.path,
            "thumbnail_path": self.thumbnail_path
        }

    @classmethod
    def from_dict(cls, data):
        """辞書からModItemを生成"""
        return cls(
            name=data.get("name", "不明"),
            version=data.get("version", "不明"),
            supported_version=data.get("supported_version", "不明"),
            path=data.get("path", ""),
            thumbnail_path=data.get("thumbnail_path")
        )

class ModSelectorWidget(QWidget):
    """MOD選択リストを表示するウィジェット"""
    def __init__(self, parent=None, app_settings=None):
        super().__init__(parent)
        self.mod_list = []  # ModItemオブジェクトのリスト
        self.app_settings = app_settings
        self.initUI()

        # 保存済みのMODをロード
        if self.app_settings:
            self.load_mods_from_settings()

    def initUI(self):
        # メインレイアウト
        main_layout = QVBoxLayout(self)

        # ヘッダーラベル
        header_label = QLabel("MODリスト", self)
        header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        main_layout.addWidget(header_label)

        # リストウィジェット
        self.list_widget = QListWidget(self)
        self.list_widget.setIconSize(QSize(64, 64))
        self.list_widget.setSpacing(2)
        main_layout.addWidget(self.list_widget)

        # ボタン用レイアウト
        button_layout = QHBoxLayout()

        # 追加ボタン
        add_button = QPushButton("+", self)
        add_button.setFixedWidth(40)
        add_button.clicked.connect(self.add_mod)
        button_layout.addWidget(add_button)

        # 削除ボタン
        remove_button = QPushButton("-", self)
        remove_button.setFixedWidth(40)
        remove_button.clicked.connect(self.remove_mod)
        button_layout.addWidget(remove_button)

        # 開くボタン
        open_button = QPushButton("開く", self)
        open_button.clicked.connect(self.open_mod)
        button_layout.addWidget(open_button)

        # スペーサー
        button_layout.addStretch()

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def load_mods_from_settings(self):
        """設定から保存済みのMODをロード"""
        mods_data = self.app_settings.get_mods()
        for mod_data in mods_data:
            mod_item = ModItem.from_dict(mod_data)
            self.mod_list.append(mod_item)

        self.update_list_widget()

    def add_mod(self):
        """MODディレクトリを選択して追加"""
        mod_dir = QFileDialog.getExistingDirectory(
            self, "MODディレクトリを選択", "", QFileDialog.ShowDirsOnly
        )

        if not mod_dir:
            return

        # descriptor.modファイルの検索
        descriptor_path = os.path.join(mod_dir, "descriptor.mod")

        if not os.path.exists(descriptor_path):
            QMessageBox.warning(self, "エラー", "選択したディレクトリにdescriptor.modファイルが見つかりません。")
            return

        # descriptor.modファイルの解析
        mod_info = self.parse_descriptor_mod(descriptor_path)

        if not mod_info:
            QMessageBox.warning(self, "エラー", "descriptor.modファイルの解析に失敗しました。")
            return

        # サムネイル画像の検索
        thumbnail_path = os.path.join(mod_dir, "thumbnail.png")
        if not os.path.exists(thumbnail_path):
            thumbnail_path = None

        # MOD情報を保存
        mod_item = ModItem(
            name=mod_info.get("name", "不明"),
            version=mod_info.get("version", "不明"),
            supported_version=mod_info.get("supported_version", "不明"),
            path=mod_dir,
            thumbnail_path=thumbnail_path
        )

        self.mod_list.append(mod_item)

        # 設定に保存
        if self.app_settings:
            self.app_settings.add_mod(mod_item.to_dict())

        self.update_list_widget()

    def remove_mod(self):
        """選択したMODをリストから削除"""
        current_row = self.list_widget.currentRow()
        if current_row >= 0:
            mod_to_remove = self.mod_list[current_row]

            # 設定からも削除
            if self.app_settings:
                self.app_settings.remove_mod(mod_to_remove.path)

            del self.mod_list[current_row]
            self.update_list_widget()

    def open_mod(self):
        """選択したMODを開く処理（この部分はアプリケーションコントローラーへ通知する）"""
        current_row = self.list_widget.currentRow()
        if current_row >= 0:
            selected_mod = self.mod_list[current_row]

            # 最後に選択したMODを設定に保存
            if self.app_settings:
                self.app_settings.set_setting("last_mod_id", current_row)

            # ここで開く処理を実装（アプリケーションコントローラーへ通知など）
            QMessageBox.information(self, "MODを開く", f"MOD '{selected_mod.name}' を開きます。")

    def parse_descriptor_mod(self, file_path):
        """descriptor.modファイルを解析して情報を抽出"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 正規表現でパターンマッチ
            import re
            name_match = re.search(r'name\s*=\s*"([^"]+)"', content)
            version_match = re.search(r'version\s*=\s*"([^"]+)"', content)
            supported_version_match = re.search(r'supported_version\s*=\s*"([^"]+)"', content)

            result = {}

            if name_match:
                result["name"] = name_match.group(1)
            if version_match:
                result["version"] = version_match.group(1)
            if supported_version_match:
                result["supported_version"] = supported_version_match.group(1)

            return result

        except Exception as e:
            print(f"Error parsing descriptor.mod: {e}")
            return None

    def update_list_widget(self):
        """リストウィジェットを更新"""
        self.list_widget.clear()

        for mod in self.mod_list:
            item = QListWidgetItem()

            # サムネイル画像があれば設定
            if mod.thumbnail_path and os.path.exists(mod.thumbnail_path):
                item.setIcon(QIcon(mod.thumbnail_path))
            else:
                # デフォルトアイコン
                default_icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "default_mod_icon.png")
                if os.path.exists(default_icon_path):
                    item.setIcon(QIcon(default_icon_path))

            # テキスト設定（名前、バージョン、対応バージョン）
            item.setText(f"{mod.name}\nバージョン: {mod.version}\nHOI4対応: {mod.supported_version}")

            # 高さを調整
            item.setSizeHint(QSize(self.list_widget.width(), 80))

            self.list_widget.addItem(item)

        # 最後に選択したMODを選択
        if self.app_settings:
            last_mod_id = self.app_settings.get_setting("last_mod_id")
            if last_mod_id is not None and 0 <= last_mod_id < len(self.mod_list):
                self.list_widget.setCurrentRow(last_mod_id)

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

class NavalDesignSystem(QMainWindow):
    """Naval Design Systemのメインウィンドウ"""

    def __init__(self, app_settings=None):
        super().__init__()

        # アプリケーション設定
        self.app_settings = app_settings

        # アプリケーション設定の読み込み
        self.load_config()

        # UIの初期化
        self.init_ui()

        # 最初のページを表示
        self.show_home_page()

        # ウィンドウサイズとポジションを復元
        if self.app_settings:
            window_size = self.app_settings.get_setting("window_size")
            window_position = self.app_settings.get_setting("window_position")

            if window_size:
                self.resize(*window_size)
            if window_position:
                self.move(*window_position)

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
        sidebar_widget.setFixedWidth(200)  # 幅を150から200に拡大
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(5, 10, 5, 10)
        sidebar_layout.setSpacing(10)  # 間隔を拡大

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
        self.menu_list.setFont(QFont("MS Gothic", 12))  # フォントサイズを10から12に拡大
        self.menu_list.setIconSize(QSize(24, 24))
        self.menu_list.setStyleSheet("""
            QListWidget {
                background-color: #c0c0c0;
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
        self.home_view = HomeView(self, self.app_settings)
        self.stacked_widget.addWidget(self.home_view)

    def add_equipment_page(self):
        """装備ページの追加"""
        self.equipment_view = EquipmentView(self)
        self.stacked_widget.addWidget(self.equipment_view)

    def add_hull_page(self):
        """船体ページの追加"""
        self.hull_view = HullForm(self)
        self.stacked_widget.addWidget(self.hull_view)

    def add_design_page(self):
        """設計ページの追加"""
        self.design_view = DesignView(self)
        self.stacked_widget.addWidget(self.design_view)

    def add_fleet_page(self):
        """艦隊ページの追加"""
        self.fleet_view = FleetView(self)
        self.stacked_widget.addWidget(self.fleet_view)

    def add_settings_page(self):
        """設定ページの追加"""
        self.settings_view = SettingsView(self, self.app_settings)
        self.stacked_widget.addWidget(self.settings_view)

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

    def add_view(self, view_name, view_widget):
        """ビューをスタックウィジェットに追加（コントローラー用）"""
        self.stacked_widget.addWidget(view_widget)

    def show_view(self, view_name):
        """指定した名前のビューを表示（コントローラー用）"""
        view_mapping = {
            "home": 0,
            "equipment": 1,
            "hull": 2,
            "design": 3,
            "fleet": 4,
            "settings": 5
        }

        if view_name in view_mapping:
            index = view_mapping[view_name]
            self.menu_list.setCurrentRow(index)
            self.stacked_widget.setCurrentIndex(index)

    def closeEvent(self, event: QCloseEvent):
        """ウィンドウが閉じられる時の処理"""
        # ウィンドウサイズとポジションを保存
        if self.app_settings:
            size = self.size()
            pos = self.pos()

            self.app_settings.set_setting("window_size", [size.width(), size.height()])
            self.app_settings.set_setting("window_position", [pos.x(), pos.y()])

        event.accept()

def ensure_assets_directory():
    """assets ディレクトリが存在することを確認する"""
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)

    # デフォルトMODアイコンがなければサンプルを作成
    default_icon_path = os.path.join(assets_dir, "default_mod_icon.png")
    if not os.path.exists(default_icon_path):
        # 簡単な空のPNGファイルを作成（実際はもっと良いアイコンを用意すべき）
        # この部分は実際のプロジェクトではアイコンファイルを含めるべき
        with open(default_icon_path, 'wb') as f:
            # 最小限のPNGファイルのバイナリデータ
            png_data = bytes.fromhex(
                '89504E470D0A1A0A0000000D4948445200000040000000400806000000AA6971DE'
                '0000001C4944415478DA6364A031601CB560D45AA3160C5AB41683C5FF1F00A5051DC0F9E172FB0000000049454E44AE426082'
            )
            f.write(png_data)

def main():
    # アプリケーションの起動
    app = QApplication(sys.argv)

    # Windows 95風スタイルの適用
    app.setStyle("Windows")  # Windowsクラシックスタイルを使用

    # Windows 95風のグローバルスタイルシート
    app.setStyleSheet("""
        QMainWindow, QDialog, QWidget {
            background-color: #c0c0c0;
            color: black;
        }
        QPushButton {
            background-color: #c0c0c0;
            border: 2px outset #d4d0c8;
            border-top-color: white;
            border-left-color: white;
            padding: 4px;
            min-width: 80px;
            min-height: 24px;
        }
        QPushButton:pressed {
            border: 2px inset #808080;
            border-bottom-color: white;
            border-right-color: white;
        }
        QLineEdit, QTextEdit, QComboBox {
            background-color: white;
            border: 2px inset #808080;
        }
        QGroupBox {
            border: 2px groove #c0c0c0;
            border-top: 1px solid #808080;
            border-left: 1px solid #808080;
            border-bottom: 1px solid white;
            border-right: 1px solid white;
            margin-top: 12px;
            padding-top: 10px;
        }
        QTabWidget::pane {
            border: 2px outset #d4d0c8;
        }
        QTabBar::tab {
            background-color: #c0c0c0;
            border: 2px outset #d4d0c8;
            border-bottom: none;
            padding: 4px 8px;
        }
        QTabBar::tab:selected {
            background-color: #c0c0c0;
            border-bottom: 2px solid #c0c0c0;
        }
        QHeaderView::section {
            background-color: #c0c0c0;
            border: 2px outset #d4d0c8;
            padding: 4px;
        }
    """)

    # メインウィンドウを作成
    window = NavalDesignSystem()
    window.show()

    # イベントループの開始
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()