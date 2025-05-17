from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel, QStatusBar, QListWidget, QSizePolicy
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
from views.nation_details_view import NationDetailsView

class NavalDesignSystem(QMainWindow):
    """Naval Design Systemのメインウィンドウ"""

    def __init__(self, app_controller=None, app_settings=None):
        super().__init__()

        # コントローラーとアプリケーション設定
        self.app_controller = app_controller
        self.app_settings = app_settings

        # アプリケーションコントローラーの状態を確認
        print(f"NavalDesignSystem.__init__: app_controller = {self.app_controller}")

        # ビューマッピング
        self.views = {}

        # アプリケーション設定の読み込み
        self.load_config()

        # UIの初期化
        self.init_ui()

        # 現在のMODの状態を確認
        if self.app_controller:
            current_mod = self.app_controller.get_current_mod()
            print(f"NavalDesignSystem初期化: current_mod = {current_mod}")

            # デバッグ用メニューの追加
            self.add_debug_menu()

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
            width = self.config.get("display", {}).get("width", 1024)
            height = self.config.get("display", {}).get("height", 768)
            self.resize(width, height)  # setFixedSizeではなくresizeを使用
        else:
            # 全画面表示
            self.showFullScreen()

        # 残りの初期化コードは変更なし

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

        # タイトルラベル
        title_label = QLabel("<b>Naval Design System</b>")
        title_label.setFont(QFont("MS Gothic", 14))
        title_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title_label)

        # メニューリスト
        self.menu_list = QListWidget()
        self.menu_list.addItems([
            "ホーム",
            "装備登録",
            "船体リスト",
            "船体登録",
            "船体設計",
            "艦隊配備",
            "国家確認",
            "国家詳細",
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

        # メニューリストをサイドバーに追加（サイズポリシーを設定）
        self.menu_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sidebar_layout.addWidget(self.menu_list)

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
        # アプリケーションコントローラー状態の確認
        print(f"NavalDesignSystem.initialize_views: app_controller = {self.app_controller}")

        # ホームビュー
        home_view = HomeView(self, self.app_settings, self.app_controller)
        self.add_view("home", home_view)

        # 装備ビュー
        equipment_view = EquipmentView(self, self.app_controller)
        self.add_view("equipment", equipment_view)

        # 船体リストビュー
        hull_list_view = HullListView(self, self.app_controller)
        self.add_view("hull_list", hull_list_view)

        # 船体ビュー
        hull_view = HullForm(self, self.app_controller)
        self.add_view("hull", hull_view)

        # 設計ビュー
        design_view = DesignView(self)
        self.add_view("design", design_view)

        # 艦隊ビュー
        fleet_view = FleetView(self)
        self.add_view("fleet", fleet_view)

        # 国家ビュー
        nation_view = NationView(self, self.app_controller)
        self.add_view("nation", nation_view)

        # 国家詳細ビュー
        nation_details_view = NationDetailsView(self, self.app_controller)
        self.add_view("nation_details", nation_details_view)

        # 設定ビュー
        settings_view = SettingsView(self, self.app_settings)
        self.add_view("settings", settings_view)

        # 初期化後にapp_controllerが正しく渡されているか確認
        home_view_controller = getattr(home_view, 'app_controller', None)
        home_view_mod_selector = getattr(home_view, 'mod_selector', None)

        if home_view_mod_selector:
            mod_selector_controller = getattr(home_view_mod_selector, 'app_controller', None)
            print(f"ホームビューのModSelectorWidgetのapp_controller: {mod_selector_controller}")

    def add_view(self, view_name, view_widget):
        """ビューをスタックウィジェットに追加"""
        self.views[view_name] = view_widget
        self.stacked_widget.addWidget(view_widget)

    def on_menu_changed(self, index):
        """メニュー選択時の処理"""
        # スタックウィジェットのページを切り替え
        self.stacked_widget.setCurrentIndex(index)

        # ステータスバーにメッセージを表示
        menu_texts = ["ホーム", "装備登録", "船体リスト", "船体登録", "船体設計", "艦隊配備", "国家確認", "国家詳細", "設定"]
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
            "nation": 6,
            "nation_details": 7,
            "settings": 8
        }

        if view_name in view_mapping:
            index = view_mapping[view_name]
            self.menu_list.setCurrentRow(index)
            self.stacked_widget.setCurrentIndex(index)

            # ステータスバーにメッセージを表示
            menu_texts = ["ホーム", "装備登録", "船体リスト", "船体登録", "船体設計", "艦隊配備", "国家確認", "国家詳細", "設定"]
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

    def add_debug_menu(self):
        """デバッグ用メニューを追加"""
        from PyQt5.QtWidgets import QMenuBar, QMenu, QAction

        # メニューバーの作成
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        # デバッグメニュー
        debug_menu = QMenu("デバッグ", self)
        menubar.addMenu(debug_menu)

        # デバッグアクション
        check_app_controller_action = QAction("AppController確認", self)
        check_app_controller_action.triggered.connect(self.check_app_controller)
        debug_menu.addAction(check_app_controller_action)

        check_settings_action = QAction("設定確認", self)
        check_settings_action.triggered.connect(self.check_settings)
        debug_menu.addAction(check_settings_action)

        fix_mod_selector_action = QAction("ModSelector修復", self)
        fix_mod_selector_action.triggered.connect(self.fix_mod_selector)
        debug_menu.addAction(fix_mod_selector_action)

        reload_settings_action = QAction("設定再読み込み", self)
        reload_settings_action.triggered.connect(self.reload_settings)
        debug_menu.addAction(reload_settings_action)

    def check_app_controller(self):
        """AppControllerの状態を確認"""
        from PyQt5.QtWidgets import QMessageBox

        info = f"AppController: {self.app_controller}\n"

        if self.app_controller:
            current_mod = self.app_controller.get_current_mod()
            info += f"current_mod: {current_mod}\n"

            # AppControllerの他の属性も確認
            for attr_name in dir(self.app_controller):
                if not attr_name.startswith('_'):
                    try:
                        attr_value = getattr(self.app_controller, attr_name)
                        if not callable(attr_value):
                            info += f"{attr_name}: {attr_value}\n"
                    except Exception as e:
                        info += f"{attr_name}: エラー - {e}\n"

        QMessageBox.information(self, "AppController確認", info)

    def check_settings(self):
        """設定の状態を確認"""
        from PyQt5.QtWidgets import QMessageBox

        info = f"AppSettings: {self.app_settings}\n"

        if self.app_settings:
            info += f"設定ファイル: {self.app_settings.settings_file}\n"
            info += f"設定ディレクトリ: {self.app_settings.settings_dir}\n\n"

            # 現在の設定
            info += "現在の設定:\n"
            for key, value in self.app_settings.settings.items():
                info += f"{key}: {value}\n"

            # 設定ファイルの存在確認
            if os.path.exists(self.app_settings.settings_file):
                info += f"\n設定ファイルのサイズ: {os.path.getsize(self.app_settings.settings_file)} bytes\n"

                # ファイルの内容を読み込む
                try:
                    with open(self.app_settings.settings_file, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    info += f"ファイル内容:\n{file_content}\n"
                except Exception as e:
                    info += f"ファイル読み込みエラー: {e}\n"
            else:
                info += "\n設定ファイルが存在しません。\n"

        QMessageBox.information(self, "設定確認", info)

    def fix_mod_selector(self):
        """ModSelectorの修復"""
        from PyQt5.QtWidgets import QMessageBox

        if 'home' in self.views:
            home_view = self.views['home']

            if hasattr(home_view, 'mod_selector'):
                # ModSelectorのapp_controllerを設定
                home_view.mod_selector.app_controller = self.app_controller

                info = f"ModSelectorのapp_controllerを修復しました。\n"
                info += f"修復後: {home_view.mod_selector.app_controller}\n"

                # ModSelectorのリストを更新
                home_view.mod_selector.update_list_widget()
                info += "ModSelectorのリスト表示を更新しました。\n"

                QMessageBox.information(self, "ModSelector修復", info)
            else:
                QMessageBox.warning(self, "エラー", "HomeViewにmod_selectorがありません。")
        else:
            QMessageBox.warning(self, "エラー", "Homeビューが見つかりません。")

    def reload_settings(self):
        """設定を再読み込み"""
        from PyQt5.QtWidgets import QMessageBox

        if self.app_settings:
            # 設定を再読み込み
            old_settings = self.app_settings.settings.copy()
            self.app_settings.load_settings()

            info = "設定を再読み込みしました。\n\n"

            # 変更点を確認
            info += "変更された設定:\n"
            changes = False

            for key, new_value in self.app_settings.settings.items():
                if key in old_settings:
                    old_value = old_settings[key]
                    if old_value != new_value:
                        info += f"{key}: {old_value} -> {new_value}\n"
                        changes = True
                else:
                    info += f"{key}: 新規 -> {new_value}\n"
                    changes = True

            if not changes:
                info += "変更はありませんでした。\n"

            # 現在のMOD設定
            current_mod_path = self.app_settings.get_setting("current_mod_path")
            current_mod_name = self.app_settings.get_setting("current_mod_name")

            info += f"\n現在のMOD設定:\n"
            info += f"current_mod_path: {current_mod_path}\n"
            info += f"current_mod_name: {current_mod_name}\n"

            # AppControllerのcurrent_modも更新
            if self.app_controller and current_mod_path:
                self.app_controller.current_mod = {
                    "path": current_mod_path,
                    "name": current_mod_name
                }
                info += f"\nAppControllerのcurrent_modを更新しました。\n"

            # ホームビューのMOD情報を更新
            if 'home' in self.views:
                home_view = self.views['home']
                if hasattr(home_view, 'update_current_mod_info'):
                    home_view.update_current_mod_info()
                    info += "ホームビューのMOD情報を更新しました。\n"

                # ModSelectorのリスト表示も更新
                if hasattr(home_view, 'mod_selector') and hasattr(home_view.mod_selector, 'update_list_widget'):
                    home_view.mod_selector.update_list_widget()
                    info += "ModSelectorのリスト表示を更新しました。\n"

            QMessageBox.information(self, "設定再読み込み", info)
        else:
            QMessageBox.warning(self, "エラー", "AppSettingsがありません。")