import os

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from .mod_selector_widget import ModSelectorWidget

class HomeView(QWidget):
    """ホーム画面のビュー"""
    def __init__(self, parent=None, app_settings=None, app_controller=None):
        super().__init__(parent)
        self.app_settings = app_settings
        self.app_controller = app_controller
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # ウェルカムメッセージ
        welcome_label = QLabel("Naval Design System へようこそ", self)
        welcome_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(welcome_label)

        description_label = QLabel("Hearts of Iron IV向け艦艇設計ツール", self)
        layout.addWidget(description_label)

        # 現在のMOD表示
        self.current_mod_label = QLabel("", self)
        self.current_mod_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        layout.addWidget(self.current_mod_label)

        # MOD選択リストを追加
        mod_label = QLabel("編集対象MODを選択", self)
        mod_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(mod_label)

        # アプリケーションコントローラー状態の確認
        print(f"HomeView.initUI: app_controller = {self.app_controller}")

        # コントローラーをModSelectorWidgetに渡す
        self.mod_selector = ModSelectorWidget(self, app_settings=self.app_settings, app_controller=self.app_controller)
        layout.addWidget(self.mod_selector)

        # デバッグボタンを追加（開発時のみ表示）
        debug_button = QPushButton("デバッグ情報", self)
        debug_button.clicked.connect(self.show_debug_info)
        layout.addWidget(debug_button)

        # データディレクトリ情報
        if self.app_settings:
            data_dir_label = QLabel(f"データ保存先: {self.app_settings.data_dir}", self)
            data_dir_label.setStyleSheet("font-size: 10px; color: gray; margin-top: 10px;")
            layout.addWidget(data_dir_label)

        self.setLayout(layout)

        # 現在のMOD情報を更新
        self.update_current_mod_info()

    def show_debug_info(self):
        """デバッグ情報を表示"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit

        dialog = QDialog(self)
        dialog.setWindowTitle("デバッグ情報")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)

        layout = QVBoxLayout()
        dialog.setLayout(layout)

        # 情報表示用テキストエディタ
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        layout.addWidget(info_text)

        # 情報収集
        debug_info = "HomeView デバッグ情報:\n\n"

        # コントローラー情報
        debug_info += f"app_controller: {self.app_controller}\n"

        # 設定情報
        if self.app_settings:
            debug_info += f"app_settings: {self.app_settings}\n"
            debug_info += f"設定ファイルパス: {self.app_settings.settings_file}\n"
            debug_info += f"設定ディレクトリ: {self.app_settings.settings_dir}\n"
            debug_info += f"データディレクトリ: {self.app_settings.data_dir}\n\n"

            debug_info += "現在の設定:\n"
            for key, value in self.app_settings.settings.items():
                debug_info += f"  {key}: {value}\n"
        else:
            debug_info += "app_settings: None\n"

        # MOD情報
        debug_info += "\nMOD情報:\n"
        if self.app_controller:
            current_mod = self.app_controller.get_current_mod()
            debug_info += f"コントローラのcurrent_mod: {current_mod}\n"
        else:
            debug_info += "app_controller: None\n"

        if self.app_settings:
            current_mod_path = self.app_settings.get_setting("current_mod_path")
            current_mod_name = self.app_settings.get_setting("current_mod_name")
            debug_info += f"app_settingsのcurrent_mod_path: {current_mod_path}\n"
            debug_info += f"app_settingsのcurrent_mod_name: {current_mod_name}\n"

        # ModSelector情報
        debug_info += "\nModSelector情報:\n"
        debug_info += f"mod_selector.app_controller: {self.mod_selector.app_controller}\n"
        debug_info += f"MODリスト数: {len(self.mod_selector.mod_list)}\n"

        # 選択中のMOD
        current_row = self.mod_selector.list_widget.currentRow()
        if current_row >= 0 and current_row < len(self.mod_selector.mod_list):
            selected_mod = self.mod_selector.mod_list[current_row]
            debug_info += f"選択中のMOD: {selected_mod.name} (path: {selected_mod.path})\n"
        else:
            debug_info += "選択中のMOD: なし\n"

        # 設定ファイルの存在確認
        if self.app_settings:
            if os.path.exists(self.app_settings.settings_file):
                debug_info += f"設定ファイルのサイズ: {os.path.getsize(self.app_settings.settings_file)}バイト\n"
                try:
                    with open(self.app_settings.settings_file, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                        debug_info += f"設定ファイル内容: {file_content}\n"
                except Exception as e:
                    debug_info += f"設定ファイル読み込みエラー: {e}\n"
            else:
                debug_info += "設定ファイルが存在しません\n"

        # 情報を表示
        info_text.setText(debug_info)

        # 閉じるボタン
        close_button = QPushButton("閉じる")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.exec_()

    def showEvent(self, event):
        """ビューが表示される際に呼ばれるメソッド"""
        super().showEvent(event)
        # 現在のMOD情報を更新
        self.update_current_mod_info()

    def update_current_mod_info(self):
        """現在選択中のMOD情報を表示更新"""
        if self.app_controller:
            current_mod = self.app_controller.get_current_mod()
            if current_mod and current_mod.get("name"):
                self.current_mod_label.setText(f"現在のMOD: {current_mod.get('name')}")
            else:
                self.current_mod_label.setText("MODが選択されていません")
        else:
            # コントローラーがない場合は設定から直接取得
            if self.app_settings:
                mod_name = self.app_settings.get_setting("current_mod_name")
                if mod_name:
                    self.current_mod_label.setText(f"現在のMOD: {mod_name}")
                else:
                    self.current_mod_label.setText("MODが選択されていません")