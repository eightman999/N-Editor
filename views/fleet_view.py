from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QTreeWidget, QTreeWidgetItem, QListWidget,
                             QSplitter, QDialog, QLineEdit, QFormLayout,
                             QPushButton, QDoubleSpinBox, QCheckBox, QMessageBox,
                             QComboBox, QListWidgetItem)
from PyQt5.QtCore import Qt, QMimeData, QByteArray, QSize
from PyQt5.QtGui import QDrag, QIcon, QPixmap, QColor, QPainter, QPen
import json
import os
import logging
import time

# アイコンマネージャーのインポート
from utils.ship_icon_manager import ShipIconManager

# PIL のインポートを安全に行う
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("警告: PILがインストールされていません。画像機能は無効になります。")

# MapViewerのインポートを安全に行う
try:
    from utils.maptest2 import MapViewer

    MAP_VIEWER_AVAILABLE = True
except ImportError:
    MAP_VIEWER_AVAILABLE = False
    print("警告: MapViewerが利用できません。マップ機能は無効になります。")


    # MapViewerのダミークラス
    class MapViewer(QWidget):
        def __init__(self):
            super().__init__()
            layout = QVBoxLayout()
            layout.addWidget(QLabel("マップ機能は利用できません"))
            self.setLayout(layout)

        def load_map_data(self, mod_path):
            pass

        def draw_selected_country_naval_bases(self, pixmap, country_tag):
            pass


class FleetView(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.current_country = None
        self.countries = {}  # 国家データを保持
        self.app_controller = parent.app_controller if parent else None

        # アイコンマネージャーを追加
        self.ship_icon_manager = ShipIconManager()
        self.ship_icon_manager.ensure_default_icons()

        # ロガーの設定
        self.logger = logging.getLogger('FleetView')
        self.logger.setLevel(logging.DEBUG)

        # ログディレクトリの作成
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)

        # ファイルハンドラーの設定
        try:
            file_handler = logging.FileHandler(
                os.path.join(self.log_dir, f"fleet_view_{time.strftime('%Y%m%d_%H%M%S')}.log"),
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)

            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
        except Exception as e:
            print(f"ログ設定エラー: {e}")

        self.initUI()
        self.load_countries()
        self.logger.info("FleetViewの初期化が完了しました")

        # MODの変更を監視（安全に接続）
        if self.app_controller and hasattr(self.app_controller, 'mod_changed'):
            try:
                self.app_controller.mod_changed.connect(self.on_mod_changed)
                self.logger.info("mod_changedシグナルに接続しました")
            except Exception as e:
                self.logger.warning(f"mod_changedシグナルの接続に失敗: {e}")

    def initUI(self):
        # メインレイアウト
        main_layout = QVBoxLayout(self)

        # ツールバーの追加
        self.add_toolbar()

        # 上下のスプリッター
        splitter = QSplitter(Qt.Vertical)

        # 上部の編成エリア
        formation_widget = QWidget()
        formation_layout = QHBoxLayout(formation_widget)

        # 左側の編成ツリー（編集可能）
        self.fleet_tree = QTreeWidget()
        self.fleet_tree.setHeaderLabels(["編成ツリー"])
        self.fleet_tree.setDragEnabled(True)
        self.fleet_tree.setAcceptDrops(True)
        self.fleet_tree.setDropIndicatorShown(True)
        self.fleet_tree.setDragDropMode(QTreeWidget.InternalMove)
        self.fleet_tree.keyPressEvent = self.fleet_tree_key_press_event
        self.fleet_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #ffffff;
                border: 1px solid #cccccc;
            }
        """)

        # 右側のMOD内編成ツリー（読み取り専用）
        self.mod_fleet_tree = QTreeWidget()
        self.mod_fleet_tree.setHeaderLabels(["MOD内編成"])
        self.mod_fleet_tree.setDragEnabled(False)
        self.mod_fleet_tree.setAcceptDrops(False)
        self.mod_fleet_tree.setEnabled(True)  # 表示は有効
        self.mod_fleet_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                color: #666666;
            }
            QTreeWidget::item {
                padding: 2px;
            }
            QTreeWidget::item:selected {
                background-color: #e0e0e0;
                color: #000000;
            }
        """)

        # 中央の設計一覧
        self.design_list = QListWidget()
        self.design_list.setDragEnabled(True)
        self.design_list.setStyleSheet("""
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #cccccc;
            }
        """)

        # 右側の港湾一覧
        self.port_tree = QTreeWidget()
        self.port_tree.setHeaderLabels(["港湾一覧"])
        self.port_tree.setDragEnabled(False)
        self.port_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #ffffff;
                border: 1px solid #cccccc;
            }
        """)
        # ダブルクリックイベントを追加
        self.port_tree.itemDoubleClicked.connect(self.on_port_item_double_clicked)

        # 編成エリアに追加
        formation_layout.addWidget(self.fleet_tree, 1)
        formation_layout.addWidget(self.mod_fleet_tree, 1)
        formation_layout.addWidget(self.design_list, 1)
        formation_layout.addWidget(self.port_tree, 1)

        # 下部のマップエリア
        self.map_widget = MapViewer()

        # スプリッターに追加（マップの比率を下げる）
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(formation_widget)  # 編成エリア
        splitter.addWidget(self.map_widget)   # マップエリア
        
        # スプリッターの比率を設定
        splitter.setSizes([600, 300])  # 編成エリア:マップエリア = 2:1

        # メインレイアウトに追加
        main_layout.addWidget(splitter)

        # シグナルとスロットの接続
        self.connect_signals()

        # 設計データの読み込み
        self.load_designs()

    def add_toolbar(self):
        toolbar_layout = QHBoxLayout()

        # 国家選択コンボボックス
        self.country_combo = QComboBox()
        self.country_combo.currentIndexChanged.connect(self.on_country_changed)
        toolbar_layout.addWidget(QLabel("国家:"))
        toolbar_layout.addWidget(self.country_combo)

        # 更新ボタン
        refresh_btn = QPushButton("更新")
        refresh_btn.clicked.connect(self.refresh_countries)
        toolbar_layout.addWidget(refresh_btn)

        # 艦隊追加ボタン
        add_fleet_btn = QPushButton("艦隊追加")
        add_fleet_btn.clicked.connect(self.add_fleet)
        toolbar_layout.addWidget(add_fleet_btn)

        # 任務部隊追加ボタン
        add_task_force_btn = QPushButton("任務部隊追加")
        add_task_force_btn.clicked.connect(self.add_task_force)
        toolbar_layout.addWidget(add_task_force_btn)

        # 保存ボタン
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_fleet_data)
        toolbar_layout.addWidget(save_btn)

        # 艦隊表示切り替えボタン
        self.show_fleet_btn = QPushButton("艦隊表示")
        self.show_fleet_btn.setCheckable(True)
        self.show_fleet_btn.setStyleSheet("""
            QPushButton:checked {
                background-color: #4CAF50;
                color: white;
            }
        """)
        self.show_fleet_btn.clicked.connect(self.toggle_fleet_display)
        toolbar_layout.addWidget(self.show_fleet_btn)

        # MOD内の艦隊表示切り替えボタン
        self.show_mod_fleet_btn = QPushButton("MOD内の艦隊")
        self.show_mod_fleet_btn.setCheckable(True)
        self.show_mod_fleet_btn.setStyleSheet("""
            QPushButton:checked {
                background-color: #2196F3;
                color: white;
            }
        """)
        self.show_mod_fleet_btn.clicked.connect(self.toggle_mod_fleet_display)
        toolbar_layout.addWidget(self.show_mod_fleet_btn)

        toolbar_layout.addStretch()

        # ツールバーをレイアウトに追加
        self.layout().insertLayout(0, toolbar_layout)

    def connect_signals(self):
        self.fleet_tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.design_list.itemDoubleClicked.connect(self.on_design_double_clicked)
        self.fleet_tree.itemClicked.connect(self.on_fleet_item_clicked)
        self.port_tree.itemClicked.connect(self.on_port_item_clicked)

        # ドラッグ&ドロップのシグナル接続
        self.design_list.mouseMoveEvent = self.design_list_mouse_move_event
        self.fleet_tree.dragEnterEvent = self.fleet_tree_drag_enter_event
        self.fleet_tree.dropEvent = self.fleet_tree_drop_event
        self.fleet_tree.dragMoveEvent = self.fleet_tree_drag_move_event

    def load_designs(self):
        """設計データを読み込む"""
        self.design_list.clear()

        if not self.app_controller:
            QMessageBox.warning(self, "警告", "アプリケーションコントローラーが設定されていません。")
            return

        # 現在のMODを取得
        try:
            current_mod = self.app_controller.get_current_mod()
        except Exception as e:
            self.logger.error(f"現在のMOD取得エラー: {e}")
            current_mod = None

        if not current_mod or "path" not in current_mod:
            QMessageBox.warning(self, "警告", "MODが選択されていません。\nホーム画面からMODを選択してください。")
            return

        # 現在選択されている国家のタグを取得
        if not self.current_country:
            self.logger.warning("国家が選択されていません")
            return

        try:
            # 全国家モードの場合は全ての国家の設計を表示
            if self.current_country == "ALL":
                # 全ての国家の設計データを取得
                for nation_tag in self.countries.keys():
                    design_data = self.app_controller.get_nation_designs(nation_tag)
                    if design_data:
                        for item in design_data:
                            list_item = QListWidgetItem()
                            year = item.get('year', '')
                            year_str = f" ({year})" if year else ""
                            design_name = item.get('design_name', item.get('hull_name', '不明'))
                            ship_type = item.get('ship_type', item.get('hull', '不明'))
                            file_name = item.get('id', '不明')
                            if design_name == '不明' or ship_type == '不明':
                                list_item.setText(f"{file_name} - データ構造エラー [{nation_tag}]")
                            else:
                                list_item.setText(f"{design_name} - {ship_type}{year_str} [{nation_tag}]")
                            list_item.setData(Qt.UserRole, item)
                            self.design_list.addItem(list_item)
            else:
                # 通常の国家選択の場合
                design_data = self.app_controller.get_nation_designs(self.current_country)
                if not design_data:
                    self.logger.info("ローカル設計データが見つかりませんでした")

                # 設計データをリストに追加
                for item in design_data:
                    list_item = QListWidgetItem()
                    year = item.get('year', '')
                    year_str = f" ({year})" if year else ""
                    design_name = item.get('design_name', item.get('hull_name', '不明'))
                    ship_type = item.get('ship_type', item.get('hull', '不明'))
                    file_name = item.get('id', '不明')
                    if design_name == '不明' or ship_type == '不明':
                        list_item.setText(f"{file_name} - データ構造エラー")
                    else:
                        list_item.setText(f"{design_name} - {ship_type}{year_str}")
                    list_item.setData(Qt.UserRole, item)
                    self.design_list.addItem(list_item)

            # mod内の設計データも取得
            try:
                if self.current_country == "ALL":
                    # 全国家モードの場合は全ての国家のMOD設計を表示
                    for nation_tag in self.countries.keys():
                        mod_design_data = self.app_controller.get_nation_mod_designs(nation_tag)
                        if mod_design_data:
                            for item in mod_design_data:
                                list_item = QListWidgetItem()
                                year = item.get('year', '')
                                year_str = f" ({year})" if year else ""
                                design_name = item.get('design_name', item.get('hull_name', item.get('name', '不明')))
                                ship_type = item.get('ship_type', item.get('hull', '不明'))
                                file_name = item.get('id', '不明')
                                if design_name == '不明' or ship_type == '不明':
                                    list_item.setText(f"{file_name} - データ構造エラー [MOD] [{nation_tag}]")
                                else:
                                    list_item.setText(f"{design_name} - {ship_type}{year_str} [MOD] [{nation_tag}]")
                                list_item.setData(Qt.UserRole, item)
                                self.design_list.addItem(list_item)
                else:
                    # 通常の国家選択の場合
                    mod_design_data = self.app_controller.get_nation_mod_designs(self.current_country)
                    if mod_design_data:
                        for item in mod_design_data:
                            list_item = QListWidgetItem()
                            year = item.get('year', '')
                            year_str = f" ({year})" if year else ""
                            design_name = item.get('design_name', item.get('hull_name', item.get('name', '不明')))
                            ship_type = item.get('ship_type', item.get('hull', '不明'))
                            file_name = item.get('id', '不明')
                            if design_name == '不明' or ship_type == '不明':
                                list_item.setText(f"{file_name} - データ構造エラー [MOD]")
                            else:
                                list_item.setText(f"{design_name} - {ship_type}{year_str} [MOD]")
                            list_item.setData(Qt.UserRole, item)
                            self.design_list.addItem(list_item)
            except Exception as e:
                self.logger.warning(f"MOD設計データの読み込みエラー: {e}")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設計データの読み込み中にエラーが発生しました：\n{str(e)}")
            self.logger.error(f"設計データ読み込みエラー: {e}")

    def load_countries(self):
        """国家データを読み込む（全国家モード対応）"""
        self.country_combo.clear()

        if not self.app_controller:
            QMessageBox.warning(self, "警告", "アプリケーションコントローラーが設定されていません。")
            return

        try:
            # 現在のMODを取得
            current_mod = self.app_controller.get_current_mod()
            if not current_mod or "path" not in current_mod:
                QMessageBox.warning(self, "警告", "MODが選択されていません。")
                return

            # 全国家オプションを追加
            self.country_combo.addItem("全国家", "ALL")

            # 国家リストを取得
            nations = self.app_controller.get_nations(current_mod["path"])
            if not nations:
                QMessageBox.warning(self, "警告", "国家情報が見つかりません。")
                return

            # データが存在する国家のみをフィルタリング
            nations_with_data = []
            for nation in nations:
                if self.has_nation_data(nation['tag']):
                    nations_with_data.append(nation)

            # 優先順位の高い国家タグ
            priority_tags = ['ENG', 'JAP', 'JPN', 'GER', 'DEU', 'FRA', 'ITA', 'USA']

            # 優先順位の高い国家を先に追加
            added_tags = set()
            for tag in priority_tags:
                for nation in nations_with_data:
                    if nation['tag'] == tag and tag not in added_tags:
                        self.add_nation_to_combo(nation)
                        added_tags.add(tag)
                        break

            # 残りの国家を追加
            for nation in nations_with_data:
                if nation['tag'] not in added_tags:
                    self.add_nation_to_combo(nation)
                    added_tags.add(nation['tag'])

            # 国家データを保持
            self.countries = {nation["tag"]: nation for nation in nations_with_data}

            # 初期値を全国家に設定
            self.country_combo.setCurrentIndex(0)

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"国家データの読み込み中にエラーが発生しました：\n{str(e)}")
            self.logger.error(f"国家データ読み込みエラー: {e}")

    def has_nation_data(self, nation_tag):
        """指定された国家にデータが存在するかチェック（軽量版）"""
        if not self.app_controller:
            return False

        try:
            # 設計データディレクトリチェック
            designs_dir = self.app_controller.app_settings.design_dir
            if os.path.exists(designs_dir):
                for filename in os.listdir(designs_dir):
                    if filename.endswith('.json'):
                        if nation_tag in filename:
                            return True

            # mod内の編成データをチェック
            current_mod = self.app_controller.get_current_mod()
            if current_mod and "path" in current_mod:
                units_path = os.path.join(current_mod["path"], "history", "units")
                if os.path.exists(units_path):
                    import re
                    pattern = re.compile(f"{nation_tag}_\\d{{4}}_(?:naval|Naval|Navy|navy)(?:_mtg)?\\.txt$")
                    try:
                        for filename in os.listdir(units_path):
                            if pattern.match(filename):
                                return True
                    except:
                        pass

            return False

        except Exception as e:
            print(f"国家データチェック中にエラー: {e}")
            return False

    def add_nation_to_combo(self, nation):
        """国家をコンボボックスに追加（軽量版）"""
        try:
            tag = nation["tag"]
            name = nation["name"]
            flag_path = nation.get("flag_path")

            # コンボボックスアイテムの作成
            self.country_combo.addItem(f"{tag}: {name}", tag)

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
                            self.country_combo.setItemIcon(self.country_combo.count() - 1, QIcon(pixmap))
                except Exception as e:
                    # 国旗読み込みエラーは無視して続行
                    pass

        except Exception as e:
            print(f"国家追加エラー: {e}")

    def on_country_changed(self, index):
        """国家が変更された時の処理"""
        if index >= 0:
            tag = self.country_combo.itemData(index)
            self.current_country = tag
            self.logger.info(f"国家が変更されました: {tag}")

            # 国家が変更されたら艦隊ツリーをクリア
            self.fleet_tree.clear()
            # 設計リストを更新
            self.load_designs()
            # 艦隊データを読み込み
            self.load_fleet_data()
            # 港湾一覧を更新
            self.update_port_list()

            # マップデータを読み込み（MapViewerが利用可能な場合）
            if MAP_VIEWER_AVAILABLE and self.app_controller:
                try:
                    current_mod = self.app_controller.get_current_mod()
                    if current_mod and "path" in current_mod:
                        self.map_widget.load_map_data(current_mod["path"])
                        # 選択された国家の海軍基地を赤色で描画
                        if hasattr(self.map_widget, 'map_image_item') and hasattr(self.map_widget.map_image_item,
                                                                                  'pixmap'):
                            try:
                                if tag != "ALL":  # 全国家モードの場合は基地を描画しない
                                    self.map_widget.draw_selected_country_naval_bases(
                                        self.map_widget.map_image_item.pixmap(), tag)
                                self.logger.info(f"マップデータを読み込みました: {current_mod['path']}")
                            except Exception as e:
                                self.logger.warning(f"マップ描画エラー: {e}")
                    else:
                        self.logger.warning("MODが選択されていません。マップデータを読み込めません。")
                except Exception as e:
                    self.logger.error(f"マップデータ読み込みエラー: {e}")

    def update_port_list(self):
        """港湾一覧を更新（アイコン対応版）"""
        if not self.current_country or not self.app_controller:
            return

        try:
            # 港湾ツリーをクリア
            self.port_tree.clear()

            # 既存の処理...
            current_mod = self.app_controller.get_current_mod()
            if not current_mod or "path" not in current_mod:
                return

            # 艦艇が存在する港湾を収集
            ports_with_ships = {}  # province_id -> composition
            
            # 編集可能な艦隊ツリーから情報を収集
            for i in range(self.fleet_tree.topLevelItemCount()):
                fleet_item = self.fleet_tree.topLevelItem(i)
                fleet_data = fleet_item.data(0, Qt.UserRole)
                if fleet_data and "province_id" in fleet_data:
                    prov_id = fleet_data["province_id"]
                    if prov_id not in ports_with_ships:
                        ports_with_ships[prov_id] = {}
                    
                    # 任務部隊の艦種別構成を集計
                    for j in range(fleet_item.childCount()):
                        task_force_item = fleet_item.child(j)
                        task_force_data = task_force_item.data(0, Qt.UserRole)
                        if task_force_data and "province_id" in task_force_data:
                            tf_prov_id = task_force_data["province_id"]
                            if tf_prov_id not in ports_with_ships:
                                ports_with_ships[tf_prov_id] = {}
                            
                            # 艦艇の艦種を集計
                            for k in range(task_force_item.childCount()):
                                ship_item = task_force_item.child(k)
                                ship_data = ship_item.data(0, Qt.UserRole)
                                if ship_data:
                                    ship_type = ship_data.get("ship_type", "UNKNOWN")
                                    ports_with_ships[tf_prov_id][ship_type] = ports_with_ships[tf_prov_id].get(ship_type, 0) + 1

            # MOD内の艦隊データも収集
            if self.show_mod_fleet_btn.isChecked():
                for i in range(self.mod_fleet_tree.topLevelItemCount()):
                    fleet_item = self.mod_fleet_tree.topLevelItem(i)
                    fleet_data = fleet_item.data(0, Qt.UserRole)
                    if fleet_data and "province_id" in fleet_data:
                        prov_id = fleet_data["province_id"]
                        composition = fleet_data.get("composition", {})
                        
                        if prov_id not in ports_with_ships:
                            ports_with_ships[prov_id] = {}
                        
                        for ship_type, count in composition.items():
                            ports_with_ships[prov_id][ship_type] = ports_with_ships[prov_id].get(ship_type, 0) + count

            # ステートごとに港湾をグループ化
            state_ports = {}
            for prov_id, level in self.map_widget.naval_base_locations.items():
                if prov_id in self.map_widget.provinces_data_by_id:
                    prov_obj = self.map_widget.provinces_data_by_id[prov_id]
                    if prov_obj.state_id is not None:
                        # ステートの所有者を確認
                        state_owner = self.map_widget.get_state_owner(prov_obj.state_id)
                        if state_owner == self.current_country or self.current_country == "ALL":
                            if prov_obj.state_id not in state_ports:
                                state_ports[prov_obj.state_id] = []
                            state_ports[prov_obj.state_id].append((prov_id, level))

            # ステートごとにツリーアイテムを作成
            for state_id, ports in state_ports.items():
                state_info = self.map_widget.states_data.get(state_id)
                if state_info:
                    # StateParserを使用してステート名を取得
                    state_name = self._get_state_name(state_id, current_mod["path"])
                    
                    state_item = QTreeWidgetItem(self.port_tree)
                    state_item.setText(0, f"{state_name} ({state_id})")
                    
                    # ステートアイコン（港湾アイコン）
                    port_icon = self.ship_icon_manager.get_ship_icon("PL", QSize(16, 16))  # 港湾アイコン
                    state_item.setIcon(0, port_icon)
                    
                    # 港湾を追加
                    for prov_id, level in ports:
                        port_item = QTreeWidgetItem(state_item)
                        
                        # 港湾の艦種別構成を取得
                        ship_composition = ports_with_ships.get(prov_id, {})
                        has_ships = bool(ship_composition)
                        
                        # 港湾名とレベル情報
                        port_name = f"{prov_id}-Lv{level}"
                        
                        if has_ships:
                            # 艦隊情報を追加
                            fleet_count = len([comp for comp in ship_composition.values() if comp > 0])
                            total_ships = sum(ship_composition.values())
                            port_name += f"-{total_ships}隻"
                            
                            # 主要艦種のアイコンを設定
                            primary_ship_type = self._get_primary_ship_type(ship_composition)
                            if primary_ship_type and primary_ship_type != "UNKNOWN":
                                ship_icon = self.ship_icon_manager.get_ship_icon(primary_ship_type, QSize(16, 16))
                                port_item.setIcon(0, ship_icon)
                        else:
                            # 空の港湾のデフォルトアイコン
                            empty_port_icon = self.ship_icon_manager.get_ship_icon("PL", QSize(16, 16))
                            port_item.setIcon(0, empty_port_icon)
                        
                        port_item.setText(0, port_name)
                        
                        # 港湾規模に応じた色を設定
                        if has_ships:
                            # 艦艇が存在する場合は濃く表示
                            if level >= 10:
                                port_color = QColor(255, 0, 0)  # 赤（大規模）
                            elif level >= 7:
                                port_color = QColor(255, 255, 0)  # 黄色（中規模）
                            elif level >= 4:
                                port_color = QColor(0, 255, 0)  # 緑（小規模）
                            else:
                                port_color = QColor(0, 0, 255)  # 青（最小規模）
                            port_color.setAlpha(255)
                        else:
                            # 艦艇が存在しない場合は薄く表示
                            if level >= 10:
                                port_color = QColor(255, 0, 0)
                            elif level >= 7:
                                port_color = QColor(255, 255, 0)
                            elif level >= 4:
                                port_color = QColor(0, 255, 0)
                            else:
                                port_color = QColor(0, 0, 255)
                            port_color.setAlpha(150)
                        
                        port_item.setForeground(0, port_color)
                        port_item.setData(0, Qt.UserRole, {
                            "province_id": prov_id,
                            "level": level,
                            "has_ships": has_ships,
                            "composition": ship_composition
                        })

            self.logger.info(f"港湾一覧を更新: {self.current_country}")

        except Exception as e:
            self.logger.error(f"港湾一覧の更新中にエラーが発生しました: {e}")

    def _get_state_name(self, state_id, mod_path):
        """StateParserを使用してステート名を取得"""
        try:
            # ステートファイルのパスを構築
            state_file_path = os.path.join(mod_path, "history", "states", f"{state_id}.txt")
            if not os.path.exists(state_file_path):
                return f"State_{state_id}"

            # StateParserを使用してステート名を取得
            with open(state_file_path, 'r', encoding='utf-8') as f:
                from parser.StateParser import StateParser
                parser = StateParser(f.read())
                state_data = parser.parse()
                
                # ステート名を取得
                if state_data and 'name' in state_data:
                    return state_data['name']
                return f"State_{state_id}"

        except Exception as e:
            self.logger.error(f"ステート名の取得中にエラーが発生しました: {e}")
            return f"State_{state_id}"

    def design_list_mouse_move_event(self, event):
        """設計リストのドラッグ開始イベント"""
        if event.buttons() == Qt.LeftButton:
            item = self.design_list.currentItem()
            if item:
                drag = QDrag(self.design_list)
                mime_data = QMimeData()
                mime_data.setData("application/x-design", QByteArray(item.text().encode()))
                drag.setMimeData(mime_data)
                drag.exec_(Qt.CopyAction)

    def fleet_tree_drag_enter_event(self, event):
        """艦隊ツリーのドラッグ開始イベント"""
        if event.mimeData().hasFormat("application/x-design"):
            event.acceptProposedAction()

    def fleet_tree_drag_move_event(self, event):
        """艦隊ツリーのドラッグ移動イベント"""
        if event.mimeData().hasFormat("application/x-design"):
            event.acceptProposedAction()
            return

        target_item = self.fleet_tree.itemAt(event.pos())
        if not target_item:
            event.ignore()
            return

        source_item = self.fleet_tree.currentItem()
        if not source_item:
            event.ignore()
            return

        source_data = source_item.data(0, Qt.UserRole)
        target_data = target_item.data(0, Qt.UserRole)

        if not source_data or not target_data:
            event.ignore()
            return

        # 移動の制限を設定
        source_type = source_data.get("type")
        target_type = target_data.get("type")

        # 階層の深さをチェック
        source_depth = self.get_item_depth(source_item)
        target_depth = self.get_item_depth(target_item)

        # 艦隊は最上位のみ
        if source_type == "fleet" and source_depth != 0:
            event.ignore()
            return

        # 任務部隊は艦隊の直下のみ
        if source_type == "task_force" and source_depth != 1:
            event.ignore()
            return

        # 艦艇は任務部隊の直下のみ
        if source_type == "ship" and source_depth != 2:
            event.ignore()
            return

        # 艦隊には任務部隊のみ追加可能
        if target_type == "fleet" and source_type != "task_force":
            event.ignore()
            return

        # 任務部隊には艦艇のみ追加可能
        if target_type == "task_force" and source_type != "ship":
            event.ignore()
            return

        # 任務部隊の中に任務部隊を入れられないように制限
        if target_type == "task_force" and source_type == "task_force":
            event.ignore()
            return

        # 艦艇を艦隊に直接追加できないように制限
        if target_type == "fleet" and source_type == "ship":
            event.ignore()
            return

        event.acceptProposedAction()

    def get_item_depth(self, item):
        """アイテムの階層の深さを取得"""
        depth = 0
        while item.parent():
            depth += 1
            item = item.parent()
        return depth

    def fleet_tree_drop_event(self, event):
        """艦隊ツリーのドロップイベント"""
        if event.mimeData().hasFormat("application/x-design"):
            design_name = event.mimeData().data("application/x-design").data().decode()
            target_item = self.fleet_tree.itemAt(event.pos())

            if target_item:
                data = target_item.data(0, Qt.UserRole)
                if data and data.get("type") == "task_force":
                    # 任務部隊にのみ艦艇を追加可能
                    dialog = ShipDialog(self)
                    if dialog.exec_():
                        name, exp, is_pride = dialog.get_data()
                        new_item = QTreeWidgetItem(target_item)
                        new_item.setText(0, f"艦艇: {name} (Exp: {exp:.2f}, Pride: {is_pride})")
                        new_item.setData(0, Qt.UserRole, {
                            "type": "ship",
                            "name": name,
                            "exp": exp,
                            "is_pride": is_pride,
                            "design": design_name
                        })
                else:
                    QMessageBox.warning(self, "警告", "艦艇は任務部隊にのみ追加できます。")
            event.acceptProposedAction()
        else:
            # ツリー内の移動処理
            source_item = self.fleet_tree.currentItem()
            target_item = self.fleet_tree.itemAt(event.pos())

            if source_item and target_item:
                source_data = source_item.data(0, Qt.UserRole)
                target_data = target_item.data(0, Qt.UserRole)

                if source_data and target_data:
                    source_type = source_data.get("type")
                    target_type = target_data.get("type")

                    # 階層の深さをチェック
                    source_depth = self.get_item_depth(source_item)
                    target_depth = self.get_item_depth(target_item)

                    # 艦隊は最上位のみ
                    if source_type == "fleet" and source_depth != 0:
                        QMessageBox.warning(self, "警告", "艦隊は最上位にのみ配置できます。")
                        event.ignore()
                        return

                    # 任務部隊は艦隊の直下のみ
                    if source_type == "task_force" and source_depth != 1:
                        QMessageBox.warning(self, "警告", "任務部隊は艦隊の直下にのみ配置できます。")
                        event.ignore()
                        return

                    # 艦艇は任務部隊の直下のみ
                    if source_type == "ship" and source_depth != 2:
                        QMessageBox.warning(self, "警告", "艦艇は任務部隊の直下にのみ配置できます。")
                        event.ignore()
                        return

                    # 移動の制限を確認
                    if (target_type == "fleet" and source_type == "task_force") or \
                            (target_type == "task_force" and source_type == "ship"):
                        # 任務部隊の中に任務部隊を入れられないように制限
                        if target_type == "task_force" and source_type == "task_force":
                            QMessageBox.warning(self, "警告", "任務部隊の中に任務部隊を入れることはできません。")
                            event.ignore()
                            return

                        # 艦艇を艦隊に直接追加できないように制限
                        if target_type == "fleet" and source_type == "ship":
                            QMessageBox.warning(self, "警告", "艦艇は艦隊に直接追加できません。")
                            event.ignore()
                            return

                        # 移動を実行（子要素を含めて）
                        self.move_tree_item(source_item, target_item)
                        event.acceptProposedAction()
                    else:
                        if target_type == "fleet":
                            QMessageBox.warning(self, "警告", "艦隊には任務部隊のみ追加できます。")
                        elif target_type == "task_force":
                            QMessageBox.warning(self, "警告", "任務部隊には艦艇のみ追加できます。")
                        event.ignore()

    def move_tree_item(self, source_item, target_item):
        """ツリーアイテムを移動（子要素を含めて）"""
        # 一時的なリストに子要素を保存
        children = []
        while source_item.childCount() > 0:
            child = source_item.takeChild(0)
            children.append(child)

        # 親から移動元を削除
        parent = source_item.parent()
        if parent:
            parent.removeChild(source_item)
        else:
            self.fleet_tree.takeTopLevelItem(self.fleet_tree.indexOfTopLevelItem(source_item))

        # 移動先に追加
        target_item.addChild(source_item)

        # 子要素を復元
        for child in children:
            source_item.addChild(child)

    def fleet_tree_key_press_event(self, event):
        """艦隊ツリーのキーイベント処理"""
        if event.key() == Qt.Key_Backspace:
            selected_items = self.fleet_tree.selectedItems()
            if selected_items:
                item = selected_items[0]
                data = item.data(0, Qt.UserRole)
                if data:
                    item_type = data.get("type")
                    if item_type in ["fleet", "task_force", "ship"]:
                        reply = QMessageBox.question(
                            self,
                            "確認",
                            f"{item_type}を削除してもよろしいですか？\n子要素も全て削除されます。",
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.No
                        )
                        if reply == QMessageBox.Yes:
                            parent = item.parent()
                            if parent:
                                parent.removeChild(item)
                            else:
                                self.fleet_tree.takeTopLevelItem(self.fleet_tree.indexOfTopLevelItem(item))
        else:
            QTreeWidget.keyPressEvent(self.fleet_tree, event)

    def add_fleet(self):
        """艦隊を追加"""
        dialog = FleetDialog(self)
        if dialog.exec_():
            name, province_id = dialog.get_data()
            try:
                province_id = int(province_id)
                # マップデータ検証をスキップ（MapViewerが利用できない場合）
                if MAP_VIEWER_AVAILABLE and hasattr(self.map_widget, 'map_data'):
                    if not self.map_widget.map_data.is_valid_deployment_location(province_id):
                        QMessageBox.warning(self, "警告", "艦隊は沿岸部の陸地にのみ配備できます。")
                        return

                item = QTreeWidgetItem(self.fleet_tree)
                item.setText(0, f"艦隊: {name} (Province: {province_id})")
                item.setData(0, Qt.UserRole, {"type": "fleet", "name": name, "province_id": province_id})
            except ValueError:
                QMessageBox.warning(self, "警告", "Province IDは数値で入力してください。")

    def add_task_force(self):
        """任務部隊を追加"""
        selected = self.fleet_tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "警告", "艦隊を選択してください。")
            return

        dialog = TaskForceDialog(self)
        if dialog.exec_():
            name, province_id = dialog.get_data()
            try:
                province_id = int(province_id)
                # マップデータ検証をスキップ（MapViewerが利用できない場合）
                if MAP_VIEWER_AVAILABLE and hasattr(self.map_widget, 'map_data'):
                    if not self.map_widget.map_data.is_valid_deployment_location(province_id):
                        QMessageBox.warning(self, "警告", "任務部隊は沿岸部の陸地にのみ配備できます。")
                        return

                item = QTreeWidgetItem(selected)
                item.setText(0, f"任務部隊: {name} (Province: {province_id})")
                item.setData(0, Qt.UserRole, {"type": "task_force", "name": name, "province_id": province_id})
                # 艦隊を展開
                selected.setExpanded(True)
            except ValueError:
                QMessageBox.warning(self, "警告", "Province IDは数値で入力してください。")

    def on_item_double_clicked(self, item, column):
        """ツリーアイテムがダブルクリックされた時の処理"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return

        item_type = data.get("type")
        if item_type == "fleet":
            # 艦隊の編集
            dialog = FleetDialog(self)
            dialog.name_edit.setText(data["name"])
            dialog.province_edit.setText(str(data["province_id"]))
            if dialog.exec_():
                name, province_id = dialog.get_data()
                try:
                    province_id = int(province_id)
                    item.setText(0, f"艦隊: {name} (Province: {province_id})")
                    item.setData(0, Qt.UserRole, {
                        "type": "fleet",
                        "name": name,
                        "province_id": province_id
                    })
                except ValueError:
                    QMessageBox.warning(self, "警告", "Province IDは数値で入力してください。")

        elif item_type == "task_force":
            # 任務部隊の編集
            dialog = TaskForceDialog(self)
            dialog.name_edit.setText(data["name"])
            dialog.province_edit.setText(str(data["province_id"]))
            if dialog.exec_():
                name, province_id = dialog.get_data()
                try:
                    province_id = int(province_id)
                    item.setText(0, f"任務部隊: {name} (Province: {province_id})")
                    item.setData(0, Qt.UserRole, {
                        "type": "task_force",
                        "name": name,
                        "province_id": province_id
                    })
                except ValueError:
                    QMessageBox.warning(self, "警告", "Province IDは数値で入力してください。")

        elif item_type == "ship":
            # 艦艇の編集
            dialog = ShipDialog(self)
            dialog.name_edit.setText(data["name"])
            dialog.exp_spin.setValue(data["exp"])
            dialog.pride_check.setChecked(data["is_pride"])
            if dialog.exec_():
                name, exp, is_pride = dialog.get_data()
                item.setText(0, f"艦艇: {name} (Exp: {exp:.2f}, Pride: {is_pride})")
                item.setData(0, Qt.UserRole, {
                    "type": "ship",
                    "name": name,
                    "exp": exp,
                    "is_pride": is_pride,
                    "design": data["design"]
                })

    def on_design_double_clicked(self, item):
        """設計アイテムがダブルクリックされた時の処理"""
        try:
            if not self.app_controller:
                return

            design_data = item.data(Qt.UserRole)
            if design_data:
                selected = self.fleet_tree.currentItem()
                if selected:
                    data = selected.data(0, Qt.UserRole)
                    if data and data.get("type") == "task_force":
                        # 艦艇追加ダイアログを表示
                        dialog = ShipDialog(self)
                        if dialog.exec_():
                            name, exp, is_pride = dialog.get_data()
                            new_item = QTreeWidgetItem(selected)
                            year = design_data.get('year', '')
                            year_str = f" ({year})" if year else ""
                            design_name = design_data.get('design_name',
                                                          design_data.get('hull_name', design_data.get('name', '不明')))
                            ship_type = design_data.get('ship_type', design_data.get('hull', '不明'))
                            new_item.setText(0,
                                             f"艦艇: {name} (Exp: {exp:.2f}, Pride: {is_pride}) - {design_name} - {ship_type}{year_str}")
                            new_item.setData(0, Qt.UserRole, {
                                "type": "ship",
                                "name": name,
                                "exp": exp,
                                "is_pride": is_pride,
                                "design": design_data
                            })
                            # 任務部隊を展開
                            selected.setExpanded(True)
                    else:
                        QMessageBox.warning(self, "警告", "任務部隊を選択してください。")
                else:
                    QMessageBox.warning(self, "警告", "任務部隊を選択してください。")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"艦艇の追加中にエラーが発生しました：\n{str(e)}")
            self.logger.error(f"艦艇追加エラー: {e}")

    def save_fleet_data(self):
        """艦隊データを保存"""
        if not self.current_country:
            QMessageBox.warning(self, "警告", "国家が選択されていません。")
            return

        try:
            # 艦隊ツリーからデータを収集
            fleet_data = {
                "country": self.current_country,
                "fleets": []
            }

            # トップレベルのアイテム（艦隊）を処理
            for i in range(self.fleet_tree.topLevelItemCount()):
                fleet_item = self.fleet_tree.topLevelItem(i)
                fleet_data_item = fleet_item.data(0, Qt.UserRole)

                fleet = {
                    "name": fleet_data_item["name"],
                    "province_id": fleet_data_item["province_id"],
                    "task_forces": []
                }

                # 任務部隊を処理
                for j in range(fleet_item.childCount()):
                    task_force_item = fleet_item.child(j)
                    task_force_data = task_force_item.data(0, Qt.UserRole)

                    task_force = {
                        "name": task_force_data["name"],
                        "province_id": task_force_data["province_id"],
                        "ships": []
                    }

                    # 艦艇を処理
                    for k in range(task_force_item.childCount()):
                        ship_item = task_force_item.child(k)
                        ship_data = ship_item.data(0, Qt.UserRole)

                        ship = {
                            "name": ship_data["name"],
                            "exp": ship_data["exp"],
                            "is_pride": ship_data["is_pride"],
                            "design": ship_data["design"]
                        }
                        task_force["ships"].append(ship)

                    fleet["task_forces"].append(task_force)

                fleet_data["fleets"].append(fleet)

            # コントローラーを通じて保存
            if self.app_controller:
                if self.app_controller.save_fleet_data(fleet_data):
                    QMessageBox.information(self, "成功", "艦隊データを保存しました。")
                    self.logger.info(f"艦隊データを保存: {self.current_country}")
                    # 艦隊表示を更新
                    if self.show_fleet_btn.isChecked():
                        self.update_fleet_display()
                else:
                    QMessageBox.warning(self, "警告", "艦隊データの保存に失敗しました。")
            else:
                QMessageBox.warning(self, "警告", "アプリケーションコントローラーが設定されていません。")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"艦隊データの保存中にエラーが発生しました：\n{str(e)}")
            self.logger.error(f"艦隊データ保存エラー: {e}")

    def load_fleet_data(self):
        """艦隊データを読み込み（全国家モード対応）"""
        if not self.current_country:
            self.logger.warning("国家が選択されていません")
            return

        try:
            # 既存の読み込み処理...
            current_mod = self.app_controller.get_current_mod()
            if not current_mod or "path" not in current_mod:
                self.logger.warning("MODが選択されていません")
                return

            units_path = os.path.join(current_mod["path"], "history", "units")
            if not os.path.exists(units_path):
                self.logger.warning(f"編成ファイルのパスが存在しません: {units_path}")
                return

            # 設計データを取得（艦艇名の参照用）
            designs_path = os.path.join(current_mod["path"], "common", "scripted_effects", "NAVY_Designs.txt")
            designs_data = {}
            if os.path.exists(designs_path):
                with open(designs_path, 'r', encoding='utf-8') as f:
                    from parser.EffectParser import EffectParser
                    parser = EffectParser(f.read(), filename=designs_path)
                    designs_data.update(parser.parse_designs())
                    self.logger.info(f"設計データを読み込み: {len(designs_data)}件")

            # 艦隊ツリーをクリア
            self.fleet_tree.clear()
            self.mod_fleet_tree.clear()

            # 全国家モードの場合は全ての国家の艦隊データを読み込む
            if self.current_country == "ALL":
                for nation_tag in self.countries.keys():
                    self._load_nation_fleet_data(nation_tag, units_path, designs_data)
            else:
                self._load_nation_fleet_data(self.current_country, units_path, designs_data)

            # 艦隊表示を更新
            if self.show_fleet_btn.isChecked():
                self.logger.info("艦隊表示を更新")
                self.update_fleet_display()

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"艦隊データの読み込み中にエラーが発生しました：\n{str(e)}")
            self.logger.error(f"艦隊データ読み込みエラー: {e}")

    def _load_nation_fleet_data(self, nation_tag, units_path, designs_data):
        """特定の国家の艦隊データを読み込む"""
        try:
            # ファイルパターンに一致するファイルを検索
            import re
            pattern = re.compile(f"{nation_tag}_\\d{{4}}_(?:naval|Naval|Navy|navy)(?:_mtg)?\\.txt$")
            found_files = []

            for filename in os.listdir(units_path):
                if pattern.match(filename):
                    found_files.append(filename)
                    file_path = os.path.join(units_path, filename)
                    self.logger.info(f"艦隊ファイルを処理: {filename}")
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            from parser.NavalOOBParser import NavalOOBParser
                            parser = NavalOOBParser(f.read())
                            fleets = parser.extract_fleets()
                            self.logger.info(f"艦隊データを抽出: {len(fleets)}件")

                            # ファイル名から日付を抽出
                            date_match = re.search(r'(\d{4})', filename)
                            date = date_match.group(1) if date_match else "不明"

                            # 日付でソート
                            fleets.sort(key=lambda x: x.get('date', '0000'))

                            for fleet in fleets:
                                # 艦隊の艦種別構成を計算
                                fleet_composition = self._calculate_fleet_composition_from_oob([fleet])
                                
                                # 艦隊アイテムを作成（アイコン付き）
                                fleet_item = QTreeWidgetItem(self.mod_fleet_tree)
                                fleet_name = fleet.get('name', '不明')
                                if isinstance(fleet_name, dict) and 'override' in fleet_name:
                                    fleet_name = fleet_name['override']
                                
                                naval_base = fleet.get('naval_base', '不明')
                                task_forces = fleet.get('task_force', [])
                                if isinstance(task_forces, dict):
                                    task_forces = [task_forces]

                                total_ships = sum(len(tf.get('ship', [])) for tf in task_forces)
                                
                                # 主要艦種のアイコンを設定
                                primary_ship_type = self._get_primary_ship_type(fleet_composition)
                                if primary_ship_type:
                                    fleet_icon = self.ship_icon_manager.get_ship_icon(primary_ship_type, QSize(16, 16))
                                    fleet_item.setIcon(0, fleet_icon)
                                
                                fleet_item.setText(0, f"{fleet_name} - {naval_base} - {len(task_forces)}TF - {total_ships}隻 [{nation_tag}]")
                                fleet_item.setData(0, Qt.UserRole, {
                                    "type": "fleet",
                                    "name": fleet_name,
                                    "province_id": naval_base,
                                    "date": date,
                                    "file": filename,
                                    "is_mod": True,
                                    "composition": fleet_composition,
                                    "nation_tag": nation_tag
                                })

                                # 任務部隊を追加
                                for task_force in task_forces:
                                    task_force_item = QTreeWidgetItem(fleet_item)
                                    task_force_name = task_force.get('name', '不明')
                                    if isinstance(task_force_name, dict) and 'override' in task_force_name:
                                        task_force_name = task_force_name['override']
                                    
                                    location = task_force.get('location', '不明')
                                    ships = task_force.get('ship', [])
                                    if isinstance(ships, dict):
                                        ships = [ships]

                                    # 任務部隊の艦種別構成を計算
                                    tf_composition = self._calculate_ships_composition(ships, designs_data)
                                    tf_primary_type = self._get_primary_ship_type(tf_composition)
                                    
                                    if tf_primary_type:
                                        tf_icon = self.ship_icon_manager.get_ship_icon(tf_primary_type, QSize(16, 16))
                                        task_force_item.setIcon(0, tf_icon)

                                    task_force_item.setText(0, f"{task_force_name} - {location} - {len(ships)}隻")
                                    task_force_item.setData(0, Qt.UserRole, {
                                        "type": "task_force",
                                        "name": task_force_name,
                                        "province_id": location,
                                        "is_mod": True,
                                        "composition": tf_composition,
                                        "nation_tag": nation_tag
                                    })

                                    # 艦艇を追加
                                    for ship in ships:
                                        ship_item = QTreeWidgetItem(task_force_item)
                                        ship_name = ship.get('name', '不明')
                                        if isinstance(ship_name, dict) and 'override' in ship_name:
                                            ship_name = ship_name['override']
                                        
                                        definition = ship.get('definition', '不明')
                                        exp_factor = ship.get('start_experience_factor', 0.0)

                                        # 設計データから表示名と艦種を取得
                                        version_name = self.get_display_name_from_design(definition, designs_data, nation_tag, ship)
                                        ship_type = self._get_ship_type_from_design_name(definition)
                                        
                                        if ship_type:
                                            ship_icon = self.ship_icon_manager.get_ship_icon(ship_type, QSize(16, 16))
                                            ship_item.setIcon(0, ship_icon)

                                        ship_item.setText(0, f"{ship_name} - {definition} - {version_name} - Exp:{exp_factor}")
                                        ship_item.setData(0, Qt.UserRole, {
                                            "type": "ship",
                                            "name": ship_name,
                                            "exp": exp_factor,
                                            "is_pride": self.check_pride_in_data(ship),
                                            "design": definition,
                                            "is_mod": True,
                                            "ship_type": ship_type,
                                            "nation_tag": nation_tag
                                        })

                                # 艦隊アイテムを展開
                                fleet_item.setExpanded(True)

                    except Exception as e:
                        self.logger.error(f"ファイル {filename} のパース中にエラーが発生しました: {str(e)}")
                        continue

            self.logger.info(f"艦隊ファイルの検索結果: {len(found_files)}件")
            
            # 艦隊表示を更新
            if self.show_fleet_btn.isChecked():
                self.logger.info("艦隊表示を更新")
                self.update_fleet_display()

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"艦隊データの読み込み中にエラーが発生しました：\n{str(e)}")
            self.logger.error(f"艦隊データ読み込みエラー: {e}")

    def _calculate_fleet_composition_from_oob(self, fleets: list) -> dict:
        """
        OOBデータから艦隊の艦種別構成を計算
        
        Args:
            fleets: 艦隊データのリスト
            
        Returns:
            dict: 艦種別隻数 {"DD": 3, "CA": 2, ...}
        """
        composition = {}
        
        for fleet in fleets:
            task_forces = fleet.get('task_force', [])
            if isinstance(task_forces, dict):
                task_forces = [task_forces]
            
            for task_force in task_forces:
                ships = task_force.get('ship', [])
                if isinstance(ships, dict):
                    ships = [ships]
                
                for ship in ships:
                    ship_type = self._get_ship_type_from_design_name(ship.get('definition', ''))
                    if ship_type:
                        composition[ship_type] = composition.get(ship_type, 0) + 1
        
        return composition

    def _calculate_ships_composition(self, ships: list, designs_data: dict) -> dict:
        """
        艦艇リストから艦種別構成を計算
        
        Args:
            ships: 艦艇データのリスト
            designs_data: 設計データ
            
        Returns:
            dict: 艦種別隻数
        """
        composition = {}
        
        for ship in ships:
            ship_type = self._get_ship_type_from_design_name(ship.get('definition', ''))
            if ship_type:
                composition[ship_type] = composition.get(ship_type, 0) + 1
        
        return composition

    def _get_ship_type_from_design_name(self, design_name: str) -> str:
        """
        設計名から艦種を推定
        
        Args:
            design_name: 設計名
            
        Returns:
            str: 艦種略号
        """
        if not design_name:
            return "UNKNOWN"
        
        design_lower = design_name.lower()
        
        # 設計名パターンマッチング
        type_patterns = {
            'DD': ['destroyer', 'dd_', '_dd', '駆逐'],
            'CA': ['heavy_cruiser', 'ca_', '_ca', '重巡'],
            'CL': ['light_cruiser', 'cl_', '_cl', '軽巡'],
            'BB': ['battleship', 'bb_', '_bb', '戦艦'],
            'BC': ['battlecruiser', 'bc_', '_bc', '巡洋戦艦'],
            'CV': ['carrier', 'cv_', '_cv', '空母'],
            'CVL': ['light_carrier', 'cvl_', '_cvl', '軽空母'],
            'SS': ['submarine', 'ss_', '_ss', '潜水艦'],
            'AM': ['minesweeper', 'am_', '_am', '掃海'],
            'PC': ['patrol', 'pc_', '_pc', '哨戒']
        }
        
        for ship_type, patterns in type_patterns.items():
            for pattern in patterns:
                if pattern in design_lower:
                    return ship_type
        
        return "UNKNOWN"

    def _get_primary_ship_type(self, composition: dict) -> str:
        """
        艦種別構成から主要艦種を取得
        
        Args:
            composition: 艦種別隻数の辞書
            
        Returns:
            str: 主要艦種の略号
        """
        if not composition:
            return "UNKNOWN"
        
        # 隻数が最も多い艦種を返す
        return max(composition.items(), key=lambda x: x[1])[0]

    def get_display_name_from_design(self, definition, designs_data, nation_tag, ship_data):
        """設計データから表示名を取得"""
        try:
            # 1. 設計データから検索
            design_display_name = None
            ship_version_name = None

            if nation_tag in designs_data:
                # 完全一致で検索
                if definition in designs_data[nation_tag]:
                    design_data = designs_data[nation_tag][definition]
                    design_display_name = self.extract_design_override_name(design_data)

                # typeフィールドで検索（完全一致が見つからない場合）
                if not design_display_name:
                    for design_key, design_data in designs_data[nation_tag].items():
                        if design_data.get('type', '').strip('"') == definition:
                            design_display_name = self.extract_design_override_name(design_data)
                            break

            # 2. 船体データからversion_nameを取得
            equipment = ship_data.get('equipment', {})
            for equipment_type, equipment_data in equipment.items():
                if isinstance(equipment_data, dict):
                    version_name = equipment_data.get('version_name', '')
                    if version_name:
                        ship_version_name = version_name.strip('"')
                        break

            # 3. 表示名を組み合わせ
            if design_display_name and ship_version_name:
                return f"{design_display_name}({ship_version_name})"
            elif design_display_name:
                return design_display_name
            elif ship_version_name:
                return ship_version_name
            else:
                return definition

        except Exception as e:
            self.logger.error(f"表示名取得エラー: {e}")
            return definition

    def extract_design_override_name(self, design_data):
        """設計データからoverride名のみを抽出"""
        try:
            # オーバーライドされている場合はoverride名を返す
            if design_data.get('name_overridden', False):
                return design_data.get('name', '').strip('"')

            # オーバーライドされていない場合は通常の名前を返す
            return design_data.get('name', '').strip('"')

        except Exception as e:
            self.logger.error(f"override名抽出エラー: {e}")
            return ""

    def check_pride_in_data(self, data_dict):
        """データ内にpride_of_the_fleetが含まれているかチェック"""
        try:
            if isinstance(data_dict, dict):
                for key, value in data_dict.items():
                    if key == 'pride_of_the_fleet' or (isinstance(value, str) and 'pride_of_the_fleet' in value):
                        return True
                    elif isinstance(value, (dict, list)):
                        if self.check_pride_in_data(value):
                            return True
            elif isinstance(data_dict, list):
                for item in data_dict:
                    if self.check_pride_in_data(item):
                        return True
            return False
        except:
            return False

    def refresh_countries(self):
        """設計データから国家タグを再収集"""
        try:
            # 現在選択されている国家タグを保存
            current_tag = self.country_combo.currentData() if self.country_combo.currentIndex() >= 0 else None

            # 国家リストを再読み込み
            self.load_countries()

            # 前回選択していた国家があれば、その国家を選択
            if current_tag:
                index = self.country_combo.findData(current_tag)
                if index >= 0:
                    self.country_combo.setCurrentIndex(index)
                else:
                    # 前回の国家が存在しない場合は、最初の国家を選択
                    if self.country_combo.count() > 0:
                        self.country_combo.setCurrentIndex(0)

            QMessageBox.information(self, "成功", "国家リストを更新しました。")
            self.logger.info("国家リストを更新")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"国家リストの更新中にエラーが発生しました：\n{str(e)}")
            self.logger.error(f"国家リスト更新エラー: {e}")

    def on_mod_changed(self, mod_path):
        """MODが変更された時の処理"""
        self.logger.info(f"MODが変更されました: {mod_path}")
        try:
            # 国家リストを再読み込み
            self.load_countries()
            # 艦隊データをクリア
            self.fleet_tree.clear()
            # 設計リストをクリア
            self.design_list.clear()
            # 港湾一覧をクリア
            self.port_tree.clear()
            # 現在の国家をリセット
            self.current_country = None
            self.country_combo.setCurrentIndex(-1)

            # マップデータを再読み込み（MapViewerが利用可能な場合）
            if MAP_VIEWER_AVAILABLE and mod_path:
                try:
                    self.map_widget.load_map_data(mod_path)
                    self.logger.info(f"マップデータを再読み込み: {mod_path}")
                except Exception as e:
                    self.logger.warning(f"マップデータ再読み込みエラー: {e}")
        except Exception as e:
            self.logger.error(f"MOD変更処理エラー: {e}")

    def toggle_fleet_display(self):
        """艦隊表示の切り替え"""
        if self.show_fleet_btn.isChecked():
            self.update_fleet_display()
        else:
            self.map_widget.show_fleet_info = False
            self.map_widget.render_map()

    def toggle_mod_fleet_display(self):
        """MOD内の艦隊表示を切り替え"""
        if self.show_mod_fleet_btn.isChecked():
            self.logger.info("MOD内編成の表示を有効化")
            # 艦隊表示ボタンがオンの場合は艦隊表示を更新
            if self.show_fleet_btn.isChecked():
                self.update_fleet_display()
        else:
            self.logger.info("MOD内編成の表示を無効化")
            # 艦隊表示ボタンがオンの場合は艦隊表示を更新
            if self.show_fleet_btn.isChecked():
                self.update_fleet_display()

    def update_fleet_display(self):
        """艦隊表示を更新"""
        if not self.current_country:
            self.logger.warning("国家が選択されていません")
            return

        try:
            # 艦隊データをプロビンスごとに整理
            fleet_data_by_province = {}
            self.logger.info("艦隊表示の更新を開始")
            
            # 編集可能な艦隊ツリーからデータを収集
            for i in range(self.fleet_tree.topLevelItemCount()):
                fleet_item = self.fleet_tree.topLevelItem(i)
                fleet_data = fleet_item.data(0, Qt.UserRole)
                
                if not fleet_data or "province_id" not in fleet_data:
                    self.logger.warning(f"無効な艦隊データ: {fleet_data}")
                    continue
                
                self.logger.info(f"艦隊データを処理: {fleet_data}")
                prov_id = fleet_data["province_id"]
                
                if prov_id not in fleet_data_by_province:
                    fleet_data_by_province[prov_id] = []
                
                fleet_info = {
                    "name": fleet_data["name"],
                    "province_id": prov_id,
                    "task_forces": []
                }
                
                # 任務部隊を収集
                for j in range(fleet_item.childCount()):
                    task_force_item = fleet_item.child(j)
                    task_force_data = task_force_item.data(0, Qt.UserRole)
                    
                    if not task_force_data or "province_id" not in task_force_data:
                        self.logger.warning(f"無効な任務部隊データ: {task_force_data}")
                        continue
                    
                    self.logger.info(f"任務部隊データを処理: {task_force_data}")
                    task_force_info = {
                        "name": task_force_data["name"],
                        "province_id": task_force_data["province_id"],
                        "ships": []
                    }
                    
                    # 艦艇を収集
                    for k in range(task_force_item.childCount()):
                        ship_item = task_force_item.child(k)
                        ship_data = ship_item.data(0, Qt.UserRole)
                        
                        if not ship_data:
                            self.logger.warning(f"無効な艦艇データ: {ship_data}")
                            continue
                        
                        self.logger.info(f"艦艇データを処理: {ship_data}")
                        ship_info = {
                            "name": ship_data["name"],
                            "exp": ship_data["exp"],
                            "is_pride": ship_data["is_pride"],
                            "design": ship_data["design"]
                        }
                        task_force_info["ships"].append(ship_info)
                    
                    fleet_info["task_forces"].append(task_force_info)
                
                fleet_data_by_province[prov_id].append(fleet_info)

            # MOD内編成が有効な場合、MOD内の艦隊データも収集
            if self.show_mod_fleet_btn.isChecked():
                self.logger.info("MOD内編成のデータを収集")
                for i in range(self.mod_fleet_tree.topLevelItemCount()):
                    fleet_item = self.mod_fleet_tree.topLevelItem(i)
                    fleet_data = fleet_item.data(0, Qt.UserRole)
                    
                    if not fleet_data or "province_id" not in fleet_data:
                        self.logger.warning(f"無効なMOD内艦隊データ: {fleet_data}")
                        continue
                    
                    self.logger.info(f"MOD内艦隊データを処理: {fleet_data}")
                    prov_id = fleet_data["province_id"]
                    
                    if prov_id not in fleet_data_by_province:
                        fleet_data_by_province[prov_id] = []
                    
                    fleet_info = {
                        "name": fleet_data["name"],
                        "province_id": prov_id,
                        "task_forces": [],
                        "is_mod": True  # MOD内の編成であることを示すフラグ
                    }
                    
                    # 任務部隊を収集
                    for j in range(fleet_item.childCount()):
                        task_force_item = fleet_item.child(j)
                        task_force_data = task_force_item.data(0, Qt.UserRole)
                        
                        if not task_force_data or "province_id" not in task_force_data:
                            self.logger.warning(f"無効なMOD内任務部隊データ: {task_force_data}")
                            continue
                        
                        self.logger.info(f"MOD内任務部隊データを処理: {task_force_data}")
                        task_force_info = {
                            "name": task_force_data["name"],
                            "province_id": task_force_data["province_id"],
                            "ships": [],
                            "is_mod": True
                        }
                        
                        # 艦艇を収集
                        for k in range(task_force_item.childCount()):
                            ship_item = task_force_item.child(k)
                            ship_data = ship_item.data(0, Qt.UserRole)
                            
                            if not ship_data:
                                self.logger.warning(f"無効なMOD内艦艇データ: {ship_data}")
                                continue
                            
                            self.logger.info(f"MOD内艦艇データを処理: {ship_data}")
                            ship_info = {
                                "name": ship_data["name"],
                                "exp": ship_data["exp"],
                                "is_pride": ship_data["is_pride"],
                                "design": ship_data["design"],
                                "is_mod": True
                            }
                            task_force_info["ships"].append(ship_info)
                        
                        fleet_info["task_forces"].append(task_force_info)
                    
                    fleet_data_by_province[prov_id].append(fleet_info)
            
            self.logger.info(f"収集した艦隊データ: {fleet_data_by_province}")
            
            # マップに艦隊情報を表示
            if self.map_widget:
                self.map_widget.set_fleet_data(
                    fleet_data_by_province,
                    self.current_country,
                    self.show_mod_fleet_btn.isChecked()
                )
                self.logger.info("艦隊表示の更新が完了")
            else:
                self.logger.warning("map_widgetが設定されていません")
            
        except Exception as e:
            self.logger.error(f"艦隊表示の更新中にエラーが発生しました: {e}")
            QMessageBox.critical(self, "エラー", f"艦隊表示の更新中にエラーが発生しました：\n{str(e)}")

    def show_fleet_details(self, province_id):
        """艦隊の詳細情報を表示する"""
        if province_id in self.map_widget.fleet_data:
            fleet_info = self.map_widget.fleet_data[province_id]
            details = "艦隊編成:\n\n"
            
            for fleet in fleet_info:
                # MOD内編成かどうかを表示
                mod_prefix = "[MOD] " if fleet.get('is_mod', False) else ""
                details += f"{mod_prefix}艦隊: {fleet['name']}\n"
                
                for task_force in fleet.get('task_forces', []):
                    mod_prefix = "[MOD] " if task_force.get('is_mod', False) else ""
                    details += f"  {mod_prefix}任務部隊: {task_force['name']}\n"
                    
                    # 艦艇タイプごとの集計
                    ship_counts = {}
                    for ship in task_force.get('ships', []):
                        ship_type = ship.get('design', 'unknown')
                        if isinstance(ship_type, dict):
                            ship_type = ship_type.get('name', 'unknown')
                        ship_counts[ship_type] = ship_counts.get(ship_type, 0) + 1
                    
                    # 艦艇タイプごとの情報を表示
                    for ship_type, count in ship_counts.items():
                        mod_prefix = "[MOD] " if ship.get('is_mod', False) else ""
                        details += f"    {mod_prefix}{ship_type}: {count}隻\n"
                details += "\n"
            
            QMessageBox.information(self, "艦隊情報", details)

    def on_fleet_item_clicked(self, item, column):
        """艦隊ツリーのアイテムがクリックされた時の処理"""
        data = item.data(0, Qt.UserRole)
        if data and "province_id" in data:
            # 地図を該当のプロビンスに移動
            if MAP_VIEWER_AVAILABLE and self.map_widget:
                # 修正: クリック時は移動のみ、ズームは変更しない
                self.map_widget.move_to_province(data["province_id"])

    def on_port_item_clicked(self, item, column):
        """港湾ツリーのアイテムがクリックされた時の処理"""
        data = item.data(0, Qt.UserRole)
        if data and "province_id" in data:
            # 地図を該当のプロビンスに移動
            if MAP_VIEWER_AVAILABLE and self.map_widget:
                # 修正: クリック時は移動のみ、ズームは変更しない
                self.map_widget.move_to_province(data["province_id"])

    def on_port_item_double_clicked(self, item, column):
        """港湾ツリーのアイテムがダブルクリックされた時の処理（アイコン対応版）"""
        data = item.data(0, Qt.UserRole)
        if data and "province_id" in data:
            if MAP_VIEWER_AVAILABLE and self.map_widget:
                province_id = data["province_id"]
                self.logger.info(f"港湾一覧からプロビンス {province_id} に移動")
                
                # 艦種別構成があれば詳細を表示
                composition = data.get("composition", {})
                if composition:
                    # 艦種別構成の詳細をツールチップとして表示
                    composition_text = "艦種別構成:\n"
                    for ship_type, count in composition.items():
                        ship_name = self.ship_icon_manager._abbreviation_to_display.get(ship_type, ship_type)
                        composition_text += f"  {ship_name} ({ship_type}): {count}隻\n"
                    
                    item.setToolTip(0, composition_text)
                
                # 固定ズームレベルでプロビンスに移動
                self.map_widget.move_to_province_with_zoom(province_id, zoom_level=3.0)

    def search_province(self):
        """検索機能の修正版"""
        search_text = self.search_input.text().strip()
        if not search_text:
            self.search_result_label.setText("")
            return

        try:
            search_id = int(search_text)
            if MAP_VIEWER_AVAILABLE and self.map_widget:
                # 修正: 検索時も固定ズームレベルを使用
                success = self.map_widget.move_to_province_with_zoom(search_id, zoom_level=4.0)
                if success:
                    self.search_result_label.setText(f"プロビンス {search_id} に移動しました")
                else:
                    self.search_result_label.setText(f"プロビンス {search_id} は見つかりませんでした")
            else:
                self.search_result_label.setText("マップが利用できません")
        except ValueError:
            self.search_result_label.setText("有効なIDを入力してください")

    def on_port_item_double_clicked_improved(self, item, column):
        """改善版: 港湾ツリーのダブルクリック処理"""
        data = item.data(0, Qt.UserRole)
        if data and "province_id" in data:
            if MAP_VIEWER_AVAILABLE and self.map_widget:
                province_id = data["province_id"]
                self.logger.info(f"港湾一覧からプロビンス {province_id} に移動")
                
                # デバウンス処理付きで移動
                self.map_widget.move_to_province_debounced(
                    province_id, 
                    zoom_level=3.0, 
                    delay_ms=150
                )

    def update_port_list_with_enhanced_info(self):
        """港湾一覧の表示を改善（座標情報付き）"""
        if not self.current_country or not self.app_controller:
            return

        try:
            self.port_tree.clear()
            
            # 現在のMODを取得
            current_mod = self.app_controller.get_current_mod()
            if not current_mod or "path" not in current_mod:
                return

            # 港湾情報を座標付きで表示
            for prov_id, level in self.map_widget.naval_base_locations.items():
                if prov_id in self.province_centroids and self.province_centroids[prov_id] is not None:
                    # プロビンスが所属するステートを確認
                    province = self.provinces_data_by_id.get(prov_id)
                    if province and province.state_id:
                        state_data = self.states_data.get(province.state_id)
                        if state_data and state_data['raw_data'].get('owner') == self.current_country:
                            center_x, center_y = self.province_centroids[prov_id]
                            
                            port_item = QTreeWidgetItem(self.port_tree)
                            port_name = f"{prov_id}-Lv{level} (座標: {int(center_x)}, {int(center_y)})"
                            port_item.setText(0, port_name)
                            port_item.setData(0, Qt.UserRole, {
                                "province_id": prov_id,
                                "level": level,
                                "coordinates": (center_x, center_y)
                            })

            self.logger.info(f"座標情報付き港湾一覧を更新: {self.current_country}")

        except Exception as e:
            self.logger.error(f"港湾一覧の更新中にエラー: {e}")


# ダイアログクラス群
class FleetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("艦隊追加")
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.province_edit = QLineEdit()

        layout.addRow("艦隊名:", self.name_edit)
        layout.addRow("Province ID:", self.province_edit)

        buttons = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("キャンセル")

        ok_button.clicked.connect(self.validate_and_accept)
        cancel_button.clicked.connect(self.reject)

        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)

    def validate_and_accept(self):
        """入力値の検証を行い、問題がなければダイアログを閉じる"""
        name = self.name_edit.text().strip()
        province_id = self.province_edit.text().strip()

        if not name:
            QMessageBox.warning(self, "警告", "艦隊名を入力してください。")
            return

        if not province_id:
            QMessageBox.warning(self, "警告", "Province IDを入力してください。")
            return

        try:
            province_id = int(province_id)
            if province_id <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "警告", "Province IDは正の整数で入力してください。")
            return

        self.accept()

    def get_data(self):
        return self.name_edit.text().strip(), self.province_edit.text().strip()


class TaskForceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("任務部隊追加")
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.province_edit = QLineEdit()

        layout.addRow("任務部隊名:", self.name_edit)
        layout.addRow("Province ID:", self.province_edit)

        buttons = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("キャンセル")

        ok_button.clicked.connect(self.validate_and_accept)
        cancel_button.clicked.connect(self.reject)

        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)

    def validate_and_accept(self):
        """入力値の検証を行い、問題がなければダイアログを閉じる"""
        name = self.name_edit.text().strip()
        province_id = self.province_edit.text().strip()

        if not name:
            QMessageBox.warning(self, "警告", "任務部隊名を入力してください。")
            return

        if not province_id:
            QMessageBox.warning(self, "警告", "Province IDを入力してください。")
            return

        try:
            province_id = int(province_id)
            if province_id <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "警告", "Province IDは正の整数で入力してください。")
            return

        self.accept()

    def get_data(self):
        return self.name_edit.text().strip(), self.province_edit.text().strip()


class ShipDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("艦艇追加")
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.exp_spin = QDoubleSpinBox()
        self.exp_spin.setRange(0, 1)
        self.exp_spin.setSingleStep(0.1)
        self.exp_spin.setValue(0)
        self.pride_check = QCheckBox()

        layout.addRow("艦名:", self.name_edit)
        layout.addRow("経験値:", self.exp_spin)
        layout.addRow("艦隊の誇り:", self.pride_check)

        buttons = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("キャンセル")

        ok_button.clicked.connect(self.validate_and_accept)
        cancel_button.clicked.connect(self.reject)

        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)

    def validate_and_accept(self):
        """入力値の検証を行い、問題がなければダイアログを閉じる"""
        name = self.name_edit.text().strip()

        if not name:
            QMessageBox.warning(self, "警告", "艦名を入力してください。")
            return

        self.accept()

    def get_data(self):
        return self.name_edit.text().strip(), self.exp_spin.value(), self.pride_check.isChecked()