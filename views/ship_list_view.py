from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                            QPushButton, QLabel, QComboBox, QHeaderView, QTreeWidget, QTreeWidgetItem,
                            QSplitter, QLineEdit, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap
import logging
import os
import time
from parser.NavalOOBParser import NavalOOBParser
from utils.ship_icon_manager import ShipIconManager

# PIL のインポートを安全に行う
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("警告: PILがインストールされていません。国旗表示機能は無効になります。")

class ShipListView(QWidget):
    """艦艇一覧ビュー（キャッシュ最適化版）"""

    def __init__(self, parent=None, app_controller=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.logger = logging.getLogger('ShipListView')
        self.all_nations = []  # 全国家データを保持
        self.filtered_nations = []  # フィルタリングされた国家データを保持
        
        # キャッシュ用の変数を追加
        self.nations_ship_cache = {}  # 国家別の艦艇データキャッシュ
        self.last_cache_update = {}  # 国家別の最終キャッシュ更新時刻
        
        # 艦種アイコン管理を初期化
        self.ship_icon_manager = ShipIconManager()
        
        self.init_ui()

    def has_nation_data(self, nation_tag):
        """指定された国家にデータが存在するかチェック（キャッシュ活用版）"""
        if not self.app_controller:
            return False

        try:
            # キャッシュを確認
            current_time = time.time()
            if (nation_tag in self.nations_ship_cache and 
                nation_tag in self.last_cache_update and
                current_time - self.last_cache_update[nation_tag] < 300):  # 5分間キャッシュ
                return len(self.nations_ship_cache[nation_tag]) > 0

            # キャッシュが無効な場合は軽量チェック
            ships = self.app_controller.refresh_mod_ships(nation_tag)
            
            # 結果をキャッシュ
            self.nations_ship_cache[nation_tag] = ships
            self.last_cache_update[nation_tag] = current_time
            
            return len(ships) > 0

        except Exception as e:
            print(f"国家データチェック中にエラー: {e}")
            return False

    def init_ui(self):
        """UIの初期化"""
        # メインレイアウト
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # 上部のコントロールパネル
        control_panel = QHBoxLayout()
        
        # 国家検索欄
        control_panel.addWidget(QLabel("国家検索:"))
        self.nation_search = QLineEdit()
        self.nation_search.setPlaceholderText("国家名またはタグで検索...")
        self.nation_search.textChanged.connect(self.on_search_text_changed)
        control_panel.addWidget(self.nation_search)
        
        # 国家選択コンボボックス
        control_panel.addWidget(QLabel("国家選択:"))
        self.nation_combo = QComboBox()
        self.nation_combo.setMinimumWidth(250)
        self.nation_combo.currentIndexChanged.connect(self.on_nation_changed)
        control_panel.addWidget(self.nation_combo)
        
        # 艦種フィルターコンボボックス
        control_panel.addWidget(QLabel("艦種:"))
        self.ship_type_combo = QComboBox()
        self.ship_type_combo.setMinimumWidth(150)
        self.ship_type_combo.currentIndexChanged.connect(self.on_ship_type_changed)
        control_panel.addWidget(self.ship_type_combo)
        
        # 設計名フィルター
        self.design_filter = QLineEdit()
        self.design_filter.setPlaceholderText("設計名で検索...")
        self.design_filter.textChanged.connect(self.on_design_filter_changed)
        control_panel.addWidget(QLabel("設計名:"))
        control_panel.addWidget(self.design_filter)
        
        # グルーピングモード選択
        control_panel.addWidget(QLabel("表示モード:"))
        self.grouping_mode = QComboBox()
        self.grouping_mode.addItem("設計名のみ", "design_only")
        self.grouping_mode.addItem("設計名＋国家", "design_nation")
        self.grouping_mode.currentIndexChanged.connect(self.on_grouping_mode_changed)
        control_panel.addWidget(self.grouping_mode)
        
        # スペーサー
        control_panel.addStretch()
        
        # 新規作成ボタン
        self.create_button = QPushButton("新規作成")
        self.create_button.clicked.connect(self.on_create_clicked)
        control_panel.addWidget(self.create_button)
        
        # 編集ボタン
        self.edit_button = QPushButton("編集")
        self.edit_button.clicked.connect(self.on_edit_clicked)
        control_panel.addWidget(self.edit_button)
        
        # 削除ボタン
        self.delete_button = QPushButton("削除")
        self.delete_button.clicked.connect(self.on_delete_clicked)
        control_panel.addWidget(self.delete_button)

        main_layout.addLayout(control_panel)

        # スプリッターで左右に分割
        splitter = QSplitter(Qt.Horizontal)
        
        # 左側：実装中の艦艇
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_label = QLabel("実装中の艦艇")
        left_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(left_label)
        
        self.implemented_ships_tree = QTreeWidget()
        self.implemented_ships_tree.setHeaderLabels(["艦艇名", "艦種", "設計名", "所属艦隊", "状態"])
        self.implemented_ships_tree.setColumnWidth(0, 200)
        self.implemented_ships_tree.setColumnWidth(1, 100)
        self.implemented_ships_tree.setColumnWidth(2, 150)
        self.implemented_ships_tree.setColumnWidth(3, 100)
        self.implemented_ships_tree.setColumnWidth(4, 100)
        left_layout.addWidget(self.implemented_ships_tree)
        
        # 右側：MOD内の艦艇
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_label = QLabel("MOD内の艦艇")
        right_label.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(right_label)
        
        self.mod_ships_tree = QTreeWidget()
        self.mod_ships_tree.setHeaderLabels(["艦艇名", "艦種", "設計名", "所属艦隊", "所属国家"])
        self.mod_ships_tree.setColumnWidth(0, 200)
        self.mod_ships_tree.setColumnWidth(1, 100)
        self.mod_ships_tree.setColumnWidth(2, 150)
        self.mod_ships_tree.setColumnWidth(3, 100)
        self.mod_ships_tree.setColumnWidth(4, 100)
        right_layout.addWidget(self.mod_ships_tree)
        
        # スプリッターに追加
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 400])  # 初期サイズを設定
        
        main_layout.addWidget(splitter)

        # 初期データの読み込み
        self.load_nation_list()
        self.load_ship_types()
        self.refresh_ship_list()

    def on_search_text_changed(self, text):
        """検索テキストが変更された時の処理"""
        try:
            # 検索テキストを小文字に変換
            search_text = text.lower()

            # 検索テキストが空の場合は全国家を表示
            if not search_text:
                self.filtered_nations = self.all_nations
            else:
                # 検索テキストに一致する国家をフィルタリング
                self.filtered_nations = [
                    nation for nation in self.all_nations
                    if search_text in nation['tag'].lower() or
                       search_text in nation['name'].lower()
                ]

            # コンボボックスを更新
            self.update_nation_combo()

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"検索処理中にエラーが発生しました：\n{str(e)}")

    def load_nation_list(self):
        """国家リストを読み込む"""
        try:
            if not self.app_controller:
                QMessageBox.warning(self, "警告", "アプリケーションコントローラーが初期化されていません。")
                return

            current_mod = self.app_controller.get_current_mod()
            if not current_mod or "path" not in current_mod:
                QMessageBox.warning(self, "警告", "MODが選択されていません。")
                return

            # 国家リストを取得
            nations = self.app_controller.get_nations(current_mod["path"])
            if not nations:
                QMessageBox.warning(self, "警告", "国家情報が見つかりません。")
                return

            self.all_nations = nations
            self.filtered_nations = nations  # 初期値として設定
            self.update_nation_combo()

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"国家リストの読み込み中にエラーが発生しました：\n{str(e)}")

    def update_nation_combo(self):
        """コンボボックスを更新（キャッシュ最適化版）"""
        try:
            # 現在選択されている国家タグを保存
            current_tag = self.nation_combo.currentData() if self.nation_combo.currentIndex() >= 0 else None

            # プルダウンをクリアして再設定
            self.nation_combo.clear()

            # 全国家の選択肢を追加
            self.nation_combo.addItem("全国家", None)

            # 使用する国家リスト（フィルタリング済みまたは全体）
            nations_to_show = self.filtered_nations if hasattr(self, 'filtered_nations') else self.all_nations

            # 艦艇データを持つ国家のみをフィルタリング（キャッシュ活用）
            nations_with_ships = []
            for nation in nations_to_show:
                try:
                    if self.has_nation_data(nation['tag']):
                        nations_with_ships.append(nation)
                except Exception:
                    continue

            # 優先順位の高い国家タグ
            priority_tags = ['ENG', 'JAP', 'JPN', 'GER', 'DEU', 'FRA', 'ITA', 'USA']

            # 優先順位の高い国家を先に追加
            added_tags = set()
            for tag in priority_tags:
                for nation in nations_with_ships:
                    if nation['tag'] == tag and tag not in added_tags:
                        self.add_nation_to_combo(nation)
                        added_tags.add(tag)
                        break

            # 残りの国家を追加
            for nation in nations_with_ships:
                if nation['tag'] not in added_tags:
                    self.add_nation_to_combo(nation)
                    added_tags.add(nation['tag'])

            # 前回選択していた国家があれば再選択
            if current_tag:
                index = self.nation_combo.findData(current_tag)
                if index >= 0:
                    self.nation_combo.setCurrentIndex(index)
            elif self.nation_combo.count() > 0:
                # 初期値として最初の国家を選択
                self.nation_combo.setCurrentIndex(0)

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"コンボボックス更新中にエラーが発生しました：\n{str(e)}")

    def add_nation_to_combo(self, nation):
        """国家をコンボボックスに追加"""
        try:
            tag = nation["tag"]
            name = nation["name"]
            flag_path = nation.get("flag_path")

            # コンボボックスアイテムの作成
            self.nation_combo.addItem(f"{tag}: {name}", tag)

            # 国旗画像の設定（PILが利用可能で、ファイルサイズが小さい場合のみ）
            if PIL_AVAILABLE and flag_path and os.path.exists(flag_path):
                try:
                    # ファイルサイズチェック（1MB以下のみ処理）
                    file_size = os.path.getsize(flag_path)
                    if file_size < 1024 * 1024:  # 1MB
                        img = Image.open(flag_path)
                        # 画像サイズチェック
                        if img.size[0] <= 256 and img.size[1] <= 256:
                            import io
                            img_data = io.BytesIO()
                            img.save(img_data, format='PNG')
                            pixmap = QPixmap()
                            pixmap.loadFromData(img_data.getvalue())
                            pixmap = pixmap.scaled(24, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)

                            # 最後に追加したアイテムにアイコンを設定
                            self.nation_combo.setItemIcon(self.nation_combo.count() - 1, QIcon(pixmap))
                except Exception as e:
                    # 国旗読み込みエラーは無視して続行
                    pass

        except Exception as e:
            print(f"国家追加エラー: {e}")

    def load_ship_types(self):
        """艦種リストを読み込む"""
        self.ship_type_combo.clear()
        self.ship_type_combo.addItem("全て", None)
        
        if self.app_controller:
            ship_types = self.app_controller.get_ship_types()
            for ship_type in ship_types:
                self.ship_type_combo.addItem(ship_type, ship_type)

    def refresh_ship_list(self):
        """艦艇一覧を更新（キャッシュクリア付き）"""
        # キャッシュをクリアして最新データを取得
        self.clear_cache()
        
        # 実装中の艦艇ツリーをクリア
        self.implemented_ships_tree.clear()
        
        # 選択された国家と艦種を取得
        nation_tag = self.nation_combo.currentData()
        ship_type = self.ship_type_combo.currentData()
        design_filter = self.design_filter.text().lower()
        
        if self.app_controller:
            # 艦艇データを取得
            ships = self.app_controller.get_ships(nation_tag, ship_type)
            
            # 国家ごとにグループ化
            nation_groups = {}
            for ship in ships:
                nation = ship.get("nation", "不明")
                if nation not in nation_groups:
                    nation_groups[nation] = []
                nation_groups[nation].append(ship)
            
            # ツリーに追加
            for nation, nation_ships in nation_groups.items():
                nation_item = QTreeWidgetItem(self.implemented_ships_tree)
                nation_item.setText(0, nation)
                
                # 設計名でフィルタリング
                filtered_ships = [s for s in nation_ships if design_filter in s.get("design", "").lower()]
                
                for ship in filtered_ships:
                    ship_item = QTreeWidgetItem(nation_item)
                    ship_item.setText(0, ship.get("name", ""))
                    ship_item.setText(1, ship.get("type", ""))
                    ship_item.setText(2, ship.get("design", ""))
                    ship_item.setText(3, ship.get("fleet", ""))
                    ship_item.setText(4, ship.get("status", ""))
            
            # すべての項目を展開
            self.implemented_ships_tree.expandAll()
            
            # MOD内の艦艇も更新
            self.refresh_mod_ships()

    def refresh_mod_ships(self):
        """MOD内の艦艇一覧を更新（キャッシュ最適化版）"""
        self.mod_ships_tree.clear()
        
        if not self.app_controller or not self.app_controller.current_mod:
            self.logger.warning("アプリケーションコントローラーまたはMODが設定されていません")
            return
            
        # 選択された国家を取得
        nation_tag = self.nation_combo.currentData()
        
        try:
            # 設計名でフィルタリング
            design_filter = self.design_filter.text().lower()
            
            # 全国家が選択されている場合
            if nation_tag is None:
                # 全国家の艦艇データを取得（キャッシュ活用）
                all_ships = []
                for nation in self.all_nations:
                    # キャッシュから取得または新規取得
                    if nation['tag'] in self.nations_ship_cache:
                        ships = self.nations_ship_cache[nation['tag']]
                    else:
                        ships = self.app_controller.refresh_mod_ships(nation['tag'])
                        self.nations_ship_cache[nation['tag']] = ships
                        self.last_cache_update[nation['tag']] = time.time()
                    
                    if ships:
                        # 各艦艇に国家情報を追加
                        for ship in ships:
                            ship['nation'] = nation
                        all_ships.extend(ships)
                ships = all_ships
            else:
                # 特定の国家の艦艇データを取得（キャッシュ活用）
                if nation_tag in self.nations_ship_cache:
                    ships = self.nations_ship_cache[nation_tag]
                else:
                    ships = self.app_controller.refresh_mod_ships(nation_tag)
                    self.nations_ship_cache[nation_tag] = ships
                    self.last_cache_update[nation_tag] = time.time()
                
                # 国家情報を追加
                nation = next((n for n in self.all_nations if n['tag'] == nation_tag), None)
                if nation:
                    for ship in ships:
                        ship['nation'] = nation
            
            self.logger.info(f"取得された艦艇数: {len(ships)}")
            
            # 設計名でフィルタリング
            if design_filter:
                ships = [s for s in ships if design_filter in s.get('design', '').lower()]
                self.logger.info(f"フィルタリング後の艦艇数: {len(ships)}")
            
            # グルーピングモードに応じて艦艇をグループ化
            grouping_mode = self.grouping_mode.currentData()
            
            if grouping_mode == "design_only":
                # 設計名のみでグループ化
                design_groups = {}
                for ship in ships:
                    design_name = ship.get('design', '未分類')
                    if design_name not in design_groups:
                        design_groups[design_name] = []
                    design_groups[design_name].append(ship)
                
                # ツリーに追加
                for design_name, design_ships in design_groups.items():
                    # 設計グループの親アイテムを作成
                    design_item = QTreeWidgetItem(self.mod_ships_tree)
                    design_item.setText(0, design_name)
                    design_item.setExpanded(True)
                    
                    # 設計グループ内の艦艇を追加
                    self._add_ships_to_tree(design_item, design_ships)
                    
            else:  # design_nation
                # 設計名と国家でグループ化
                design_nation_groups = {}
                for ship in ships:
                    design_name = ship.get('design', '未分類')
                    nation = ship.get('nation', {})
                    nation_name = nation.get('name', '未分類')
                    
                    if design_name not in design_nation_groups:
                        design_nation_groups[design_name] = {}
                    if nation_name not in design_nation_groups[design_name]:
                        design_nation_groups[design_name][nation_name] = []
                    
                    design_nation_groups[design_name][nation_name].append(ship)
                
                # ツリーに追加
                for design_name, nation_groups in design_nation_groups.items():
                    # 設計グループの親アイテムを作成
                    design_item = QTreeWidgetItem(self.mod_ships_tree)
                    design_item.setText(0, design_name)
                    design_item.setExpanded(True)
                    
                    # 国家グループを追加
                    for nation_name, nation_ships in nation_groups.items():
                        nation_item = QTreeWidgetItem(design_item)
                        nation_item.setText(0, nation_name)
                        nation_item.setExpanded(True)
                        
                        # 国家グループ内の艦艇を追加
                        self._add_ships_to_tree(nation_item, nation_ships)
            
            self.logger.info("艦艇一覧の更新が完了しました")
            
        except Exception as e:
            self.logger.error(f"MOD内艦艇の更新中にエラーが発生しました: {e}", exc_info=True)
            QMessageBox.critical(self, "エラー", f"MOD内艦艇の更新中にエラーが発生しました：\n{str(e)}")

    def _add_ships_to_tree(self, parent_item, ships):
        """艦艇をツリーに追加する共通メソッド"""
        # 重複チェック用の辞書
        duplicate_check = {}
        
        for ship in ships:
            ship_name = ship.get('name', '')
            ship_type = ship.get('type', '')
            ship_item = QTreeWidgetItem(parent_item)
            
            # 艦種アイコンを設定
            icon = self.ship_icon_manager.get_ship_icon(ship_type)
            if not icon.isNull():
                ship_item.setIcon(0, icon)
            
            ship_item.setText(0, ship_name)
            ship_item.setText(1, ship_type)
            ship_item.setText(2, ship.get('design', ''))
            ship_item.setText(3, ship.get('fleet', ''))
            
            # 所属国家の表示（国旗＋国名）
            nation = ship.get('nation', {})
            nation_name = nation.get('name', '')
            if PIL_AVAILABLE and nation.get('flag_path') and os.path.exists(nation['flag_path']):
                try:
                    img = Image.open(nation['flag_path'])
                    if img.size[0] <= 256 and img.size[1] <= 256:
                        import io
                        img_data = io.BytesIO()
                        img.save(img_data, format='PNG')
                        pixmap = QPixmap()
                        pixmap.loadFromData(img_data.getvalue())
                        pixmap = pixmap.scaled(24, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        ship_item.setIcon(4, QIcon(pixmap))
                except Exception:
                    pass
            ship_item.setText(4, nation_name)
            
            # 艦艇データを保存
            ship_data = {
                'name': ship_name,
                'type': ship_type,
                'design': ship.get('design', ''),
                'nation': nation,
                'data': ship.get('data', {})
            }
            ship_item.setData(0, Qt.UserRole, ship_data)
            
            # 重複チェック
            key = f"{ship.get('design', '')}_{ship_name}"
            if key in duplicate_check:
                # 重複が見つかった場合、両方のアイテムに赤背景を設定
                duplicate_check[key].setBackground(0, Qt.red)
                ship_item.setBackground(0, Qt.red)
            else:
                duplicate_check[key] = ship_item

    def on_nation_changed(self, index):
        """国家選択変更時の処理"""
        self.refresh_ship_list()

    def on_ship_type_changed(self, index):
        """艦種選択変更時の処理"""
        self.refresh_ship_list()

    def on_design_filter_changed(self, text):
        """設計名フィルター変更時の処理"""
        self.refresh_ship_list()

    def on_grouping_mode_changed(self, index):
        """グルーピングモード変更時の処理"""
        self.refresh_ship_list()

    def on_selection_changed(self):
        """選択変更時の処理"""
        has_selection = (len(self.implemented_ships_tree.selectedItems()) > 0 or 
                        len(self.mod_ships_tree.selectedItems()) > 0)
        self.edit_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def on_create_clicked(self):
        """新規作成ボタンクリック時の処理"""
        # TODO: 新規作成ダイアログを表示
        pass

    def on_edit_clicked(self):
        """編集ボタンクリック時の処理"""
        selected_items = (self.implemented_ships_tree.selectedItems() + 
                         self.mod_ships_tree.selectedItems())
        if not selected_items:
            return
            
        item = selected_items[0]
        # TODO: 編集ダイアログを表示

    def on_delete_clicked(self):
        """削除ボタンクリック時の処理"""
        selected_items = (self.implemented_ships_tree.selectedItems() + 
                         self.mod_ships_tree.selectedItems())
        if not selected_items:
            return
            
        item = selected_items[0]
        # TODO: 削除確認ダイアログを表示

    def clear_cache(self):
        """艦艇データキャッシュをクリア"""
        self.nations_ship_cache.clear()
        self.last_cache_update.clear()
        self.logger.info("艦艇データキャッシュをクリアしました") 