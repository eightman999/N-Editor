from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QListWidget, QListWidgetItem,
                             QSizePolicy, QMessageBox)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QSize

import os

class NationView(QWidget):
    """国家確認画面のビュー"""

    def __init__(self, parent=None, app_controller=None):
        super(NationView, self).__init__(parent)
        self.app_controller = app_controller
        self.init_ui()

    def init_ui(self):
        """UIの初期化"""
        # メインレイアウト
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # ヘッダー部分
        header_layout = QHBoxLayout()
        self.title_label = QLabel("国家リスト")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.title_label)

        # 現在のMOD表示
        self.current_mod_label = QLabel("")
        header_layout.addWidget(self.current_mod_label)

        # スペーサー
        header_layout.addStretch()

        # 更新ボタン
        self.refresh_button = QPushButton("更新")
        self.refresh_button.clicked.connect(self.refresh_nation_list)
        header_layout.addWidget(self.refresh_button)

        main_layout.addLayout(header_layout)

        # 国家リスト
        self.nation_list = QListWidget()
        self.nation_list.setIconSize(QSize(32, 20))  # 国旗サイズ
        main_layout.addWidget(self.nation_list)

    def refresh_nation_list(self):
        """国家リストを更新"""
        # 現在のMODを取得
        if self.app_controller:
            current_mod = self.app_controller.get_current_mod()
            if current_mod and "path" in current_mod:
                self.current_mod_label.setText(f"現在のMOD: {current_mod.get('name', '')}")
                # 国家情報を取得して表示
                self.load_nations(current_mod["path"])
            else:
                self.current_mod_label.setText("MODが選択されていません")
                self.nation_list.clear()
                QMessageBox.warning(self, "警告", "MODが選択されていません。\nホーム画面からMODを選択してください。")

    def load_nations(self, mod_path):
        """MODから国家情報を読み込み"""
        self.nation_list.clear()

        if not self.app_controller:
            return

        # コントローラから国家情報を取得
        nations = self.app_controller.get_nations(mod_path)

        if not nations:
            QMessageBox.information(self, "情報", f"国家情報が見つかりませんでした。\nMODのディレクトリ構造を確認してください。\n検索パス: {mod_path}/common/country_tags")
            return

        # リストに追加
        for nation in nations:
            tag = nation["tag"]
            name = nation["name"]
            flag_path = nation["flag_path"]

            # リストアイテムの作成
            item = QListWidgetItem()

            # 国旗画像の設定（存在する場合）
            if flag_path and os.path.exists(flag_path):
                try:
                    # TGAファイルの読み込み
                    # 注: PyQt5は直接TGAをサポートしていないため、
                    # 実際の実装ではPILなどを使った変換が必要
                    from PIL import Image
                    import io

                    img = Image.open(flag_path)
                    img_data = io.BytesIO()
                    img.save(img_data, format='PNG')
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data.getvalue())
                    pixmap = pixmap.scaled(32, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)

                    item.setIcon(QIcon(pixmap))
                except ImportError:
                    # PILがインストールされていない場合
                    print("PILライブラリがインストールされていません。国旗画像の表示にはPillowが必要です。")
                except Exception as e:
                    print(f"国旗画像の読み込みエラー: {e}")

            # テキスト設定
            item.setText(f"{tag}: {name}")

            # リストに追加
            self.nation_list.addItem(item)

        self.nation_list.sortItems()  # アルファベット順にソート

    def showEvent(self, event):
        """表示時に呼ばれるイベント"""
        super().showEvent(event)
        self.refresh_nation_list()