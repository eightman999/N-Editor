# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: nation_viewビュー
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
        """国家リストを表示（スプライトシート最適化版）"""
        self.nation_list.clear()
        
        # 国旗スプライトマネージャーを取得
        flag_sprite_manager = None
        if self.app_controller:
            flag_sprite_manager = self.app_controller.get_flag_sprite_manager()
        
        # リストに追加
        for nation in nations:
            tag = nation["tag"]
            name = nation["name"]
            flag_path = nation["flag_path"]

            # リストアイテムの作成
            item = QListWidgetItem()

            # 国旗画像の設定
            flag_icon = self._load_flag_icon(tag, flag_path, flag_sprite_manager)
            if flag_icon:
                item.setIcon(flag_icon)

            # テキスト設定
            item.setText(f"{tag}: {name}")

            # リストに追加
            self.nation_list.addItem(item)

        self.nation_list.sortItems()  # アルファベット順にソート

    def _load_flag_icon(self, nation_tag, flag_path, flag_sprite_manager):
        """
        国旗アイコンを読み込む（スプライトシート優先、フォールバック付き）
        
        Args:
            nation_tag: 国家タグ
            flag_path: 元の国旗ファイルパス
            flag_sprite_manager: スプライトマネージャー
            
        Returns:
            QIcon: 国旗アイコン、読み込み失敗時はNone
        """
        try:
            # 1. スプライトシートから国旗を取得を試行
            if flag_sprite_manager:
                flag_img = flag_sprite_manager.extract_flag(nation_tag)
                if flag_img:
                    # PIL ImageをQPixmapに変換
                    pixmap = self._pil_to_qpixmap(flag_img)
                    if pixmap:
                        return QIcon(pixmap)
            
            # 2. フォールバック: 個別ファイルから直接読み込み
            if flag_path and os.path.exists(flag_path):
                return self._load_flag_from_file(flag_path)
            
            # 3. デフォルト国旗アイコンを生成
            return self._create_default_flag_icon(nation_tag)
            
        except Exception as e:
            print(f"国旗アイコン読み込みエラー ({nation_tag}): {e}")
            return self._create_default_flag_icon(nation_tag)

    def _pil_to_qpixmap(self, pil_image):
        """
        PIL ImageをQPixmapに変換
        
        Args:
            pil_image: PIL Image
            
        Returns:
            QPixmap: 変換されたPixmap、失敗時はNone
        """
        try:
            import io
            
            # PIL ImageをPNG形式でバイトデータに変換
            img_data = io.BytesIO()
            pil_image.save(img_data, format='PNG')
            
            # QPixmapに読み込み
            pixmap = QPixmap()
            if pixmap.loadFromData(img_data.getvalue()):
                return pixmap
            
            return None
            
        except Exception as e:
            print(f"PIL -> QPixmap変換エラー: {e}")
            return None

    def _load_flag_from_file(self, flag_path):
        """
        ファイルから直接国旗を読み込み（従来の方法）
        
        Args:
            flag_path: 国旗ファイルのパス
            
        Returns:
            QIcon: 国旗アイコン、失敗時はNone
        """
        try:
            from PIL import Image
            import io

            img = Image.open(flag_path)
            
            # RGBA形式に変換
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # サイズを調整
            img = img.resize((32, 20), Image.LANCZOS)
            
            # QPixmapに変換
            pixmap = self._pil_to_qpixmap(img)
            if pixmap:
                return QIcon(pixmap)
                
        except ImportError:
            # PILがインストールされていない場合
            print("PILライブラリがインストールされていません。国旗画像の表示にはPillowが必要です。")
        except Exception as e:
            print(f"国旗画像の個別読み込みエラー: {e}")
        
        return None

    def _create_default_flag_icon(self, nation_tag):
        """
        デフォルト国旗アイコンを作成
        
        Args:
            nation_tag: 国家タグ
            
        Returns:
            QIcon: デフォルトアイコン
        """
        try:
            # グレーの背景でテキストを描画
            pixmap = QPixmap(32, 20)
            pixmap.fill(Qt.gray)
            
            from PyQt5.QtGui import QPainter, QFont
            painter = QPainter(pixmap)
            painter.setPen(Qt.white)
            
            # フォントサイズを調整
            font = QFont()
            font.setPixelSize(8)
            painter.setFont(font)
            
            # 国家タグを描画（最初の2文字）
            text = nation_tag[:2] if len(nation_tag) >= 2 else nation_tag
            painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
            painter.end()
            
            return QIcon(pixmap)
            
        except Exception as e:
            print(f"デフォルト国旗作成エラー ({nation_tag}): {e}")
            # 最後の手段として空のアイコンを返す
            return QIcon()

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