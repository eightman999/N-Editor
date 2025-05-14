import os
import re
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
                             QPushButton, QLabel, QFileDialog, QMessageBox)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QSize

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