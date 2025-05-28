from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QListWidget, QListWidgetItem,
                             QSizePolicy, QMessageBox, QTabWidget)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QSize

import os
import time

class NationView(QWidget):
    """国家確認画面のビュー（キャッシュ最適化版）"""

    def __init__(self, parent=None, app_controller=None):
        super(NationView, self).__init__(parent)
        self.app_controller = app_controller
        
        # キャッシュ用変数を追加
        self.nations_cache = None
        self.cache_timestamp = 0
        self.cache_timeout = 300  # 5分間キャッシュ
        
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
        self.nation_list.itemClicked.connect(self.on_nation_clicked)  # クリックイベントを追加
        main_layout.addWidget(self.nation_list)

    def on_nation_clicked(self, item):
        """国家リストの要素がクリックされた時の処理"""
        if not self.app_controller:
            return

        # 選択された国家のタグを取得
        nation_tag = item.text().split(":")[0].strip()
        
        # 国家情報を取得
        current_mod = self.app_controller.get_current_mod()
        if current_mod and "path" in current_mod:
            nations = self.app_controller.get_nations(current_mod["path"])
            nation_info = next((n for n in nations if n["tag"] == nation_tag), None)
            
            if nation_info:
                # コントローラを通じて新しい画面を表示
                self.app_controller.show_nation_details(nation_tag)
            else:
                QMessageBox.warning(self, "警告", f"国家情報 '{nation_tag}' が見つかりません。")
        else:
            QMessageBox.warning(self, "警告", "MODが選択されていません。")

    def refresh_nation_list(self):
        """国家リストを更新（キャッシュ最適化版）"""
        # 現在のMODを取得
        if self.app_controller:
            current_mod = self.app_controller.get_current_mod()
            if current_mod and "path" in current_mod:
                self.current_mod_label.setText(f"現在のMOD: {current_mod.get('name', '')}")
                
                # キャッシュの有効性をチェック
                current_time = time.time()
                if (self.nations_cache is None or 
                    current_time - self.cache_timestamp > self.cache_timeout):
                    
                    # 国家情報を取得してキャッシュ
                    self.load_nations(current_mod["path"])
                    self.nations_cache = self.nations_cache or []
                    self.cache_timestamp = current_time
                else:
                    # キャッシュからデータを使用
                    if self.nations_cache:
                        self.display_cached_nations()
            else:
                self.current_mod_label.setText("MODが選択されていません")
                self.nation_list.clear()
                QMessageBox.warning(self, "警告", "MODが選択されていません。\nホーム画面からMODを選択してください。")

    def load_nations(self, mod_path):
        """MODから国家情報を読み込み（AppController経由でキャッシュ活用）"""
        self.nation_list.clear()

        if not self.app_controller:
            return

        # AppControllerから国家情報を取得（既にキャッシュ対応済み）
        nations = self.app_controller.get_nations(mod_path)

        if not nations:
            QMessageBox.information(self, "情報", f"国家情報が見つかりませんでした。\nMODのディレクトリ構造を確認してください。\n検索パス: {mod_path}/common/country_tags")
            self.nations_cache = []
            return

        # キャッシュに保存
        self.nations_cache = nations
        
        # 表示処理
        self.display_nations(nations)

    def display_nations(self, nations):
        """国家リストを表示"""
        self.nation_list.clear()
        
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

    def display_cached_nations(self):
        """キャッシュされた国家データを表示"""
        if self.nations_cache:
            self.display_nations(self.nations_cache)

    def clear_cache(self):
        """キャッシュをクリア"""
        self.nations_cache = None
        self.cache_timestamp = 0

    def showEvent(self, event):
        """表示時に呼ばれるイベント（キャッシュ考慮版）"""
        super().showEvent(event)
        # 表示時にキャッシュの有効性を確認して更新
        self.refresh_nation_list()