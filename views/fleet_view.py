from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QTreeWidget, QTreeWidgetItem, QListWidget,
                             QSplitter, QDialog, QLineEdit, QFormLayout,
                             QPushButton, QDoubleSpinBox, QCheckBox, QMessageBox,
                             QComboBox, QListWidgetItem)
from PyQt5.QtCore import Qt, QMimeData, QByteArray
from PyQt5.QtGui import QDrag, QIcon, QPixmap, QColor, QPainter, QPen
import json
import os
from PIL import Image
import io
from utils.maptest2 import MapViewer
import logging
import time

class FleetView(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.current_country = None
        self.countries = {}  # 国家データを保持
        self.app_controller = parent.app_controller if parent else None
        self.logger = logging.getLogger('FleetView')
        self.logger.setLevel(logging.DEBUG)
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(self.log_dir, f"fleet_view_{time.strftime('%Y%m%d_%H%M%S')}.log"))
        file_handler.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.initUI()
        self.load_countries()
        self.logger.info("FleetViewの初期化が完了しました")

        # MODの変更を監視
        if self.app_controller:
            self.app_controller.mod_changed.connect(self.on_mod_changed)

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
        
        # 左側の艦隊ツリー
        self.fleet_tree = QTreeWidget()
        self.fleet_tree.setHeaderLabels(["艦隊構成"])
        self.fleet_tree.setDragEnabled(True)
        self.fleet_tree.setAcceptDrops(True)
        self.fleet_tree.setDropIndicatorShown(True)
        self.fleet_tree.setDragDropMode(QTreeWidget.InternalMove)
        self.fleet_tree.keyPressEvent = self.fleet_tree_key_press_event
        
        # 右側の設計一覧
        self.design_list = QListWidget()
        self.design_list.setDragEnabled(True)
        
        # 編成エリアに追加
        formation_layout.addWidget(self.fleet_tree, 2)
        formation_layout.addWidget(self.design_list, 1)
        
        # 下部のマップエリア
        self.map_widget = MapViewer()
        
        # スプリッターに追加
        splitter.addWidget(formation_widget)
        splitter.addWidget(self.map_widget)
        
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
        
        toolbar_layout.addStretch()
        
        # ツールバーをレイアウトに追加
        self.layout().insertLayout(0, toolbar_layout)

    def connect_signals(self):
        self.fleet_tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.design_list.itemDoubleClicked.connect(self.on_design_double_clicked)
        
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
        current_mod = self.app_controller.get_current_mod()
        if not current_mod or "path" not in current_mod:
            QMessageBox.warning(self, "警告", "MODが選択されていません。\nホーム画面からMODを選択してください。")
            return

        # 現在選択されている国家のタグを取得
        if not self.current_country:
            QMessageBox.warning(self, "警告", "国家が選択されていません。")
            return

        try:
            # 設計データを取得
            design_data = self.app_controller.get_nation_designs(self.current_country)
            if not design_data:
                QMessageBox.information(self, "情報", "設計データが見つかりませんでした。")
                return

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
            mod_design_data = self.app_controller.get_nation_mod_designs(self.current_country)
            if mod_design_data:
                for item in mod_design_data:
                    list_item = QListWidgetItem()
                    year = item.get('year', '')
                    year_str = f" ({year})" if year else ""
                    design_name = item.get('design_name', item.get('hull_name', '不明'))
                    ship_type = item.get('ship_type', item.get('hull', '不明'))
                    file_name = item.get('id', '不明')
                    if design_name == '不明' or ship_type == '不明':
                        list_item.setText(f"{file_name} - データ構造エラー [MOD]")
                    else:
                        list_item.setText(f"{design_name} - {ship_type}{year_str} [MOD]")
                    list_item.setData(Qt.UserRole, item)
                    self.design_list.addItem(list_item)

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設計データの読み込み中にエラーが発生しました：\n{str(e)}")

    def load_countries(self):
        """国家データを読み込む"""
        self.country_combo.clear()
        
        if not self.app_controller:
            QMessageBox.warning(self, "警告", "アプリケーションコントローラーが設定されていません。")
            return

        try:
            # designsディレクトリから国家タグを収集
            designs_dir = os.path.join(self.app_controller.app_settings.data_dir, "designs")
            if not os.path.exists(designs_dir):
                QMessageBox.warning(self, "警告", "設計データディレクトリが見つかりません。")
                return

            # 国家タグとその設計データを収集
            country_designs = {}
            for filename in os.listdir(designs_dir):
                if not filename.endswith('.json'):
                    continue

                file_path = os.path.join(designs_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        design_data = json.load(f)
                        country_tag = design_data.get('country')
                        if country_tag:
                            if country_tag not in country_designs:
                                country_designs[country_tag] = []
                            country_designs[country_tag].append(design_data)
                except Exception as e:
                    print(f"設計ファイル '{filename}' の読み込みエラー: {e}")

            # 現在のMODを取得
            current_mod = self.app_controller.get_current_mod()
            if not current_mod or "path" not in current_mod:
                QMessageBox.warning(self, "警告", "MODが選択されていません。\nホーム画面からMODを選択してください。")
                return

            # 国家情報を取得
            nations = self.app_controller.get_nations(current_mod["path"])
            if not nations:
                QMessageBox.warning(self, "警告", "国家情報が見つかりません。")
                return

            # 設計データがある国家のみをコンボボックスに追加
            for nation in nations:
                tag = nation["tag"]
                if tag in country_designs:
                    name = nation["name"]
                    flag_path = nation["flag_path"]

                    # コンボボックスアイテムの作成
                    self.country_combo.addItem(name, tag)

                    # 国旗画像の設定（存在する場合）
                    if flag_path and os.path.exists(flag_path):
                        try:
                            img = Image.open(flag_path)
                            img_data = io.BytesIO()
                            img.save(img_data, format='PNG')
                            pixmap = QPixmap()
                            pixmap.loadFromData(img_data.getvalue())
                            pixmap = pixmap.scaled(32, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            
                            # 最後に追加したアイテムにアイコンを設定
                            self.country_combo.setItemIcon(self.country_combo.count() - 1, QIcon(pixmap))
                        except Exception as e:
                            print(f"国旗画像の読み込みエラー: {e}")

            # 国家データを保持
            self.countries = {nation["tag"]: nation for nation in nations if nation["tag"] in country_designs}

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"国家データの読み込み中にエラーが発生しました：\n{str(e)}")

    def on_country_changed(self, index):
        """国家が変更された時の処理"""
        if index >= 0:
            tag = self.country_combo.itemData(index)
            self.current_country = tag
            # 国家が変更されたら艦隊ツリーをクリア
            self.fleet_tree.clear()
            # 設計リストを更新
            self.load_designs()
            # 艦隊データを読み込み
            self.load_fleet_data()
            
            # マップデータを読み込み
            if self.app_controller:
                current_mod = self.app_controller.get_current_mod()
                if current_mod and "path" in current_mod:
                    self.map_widget.load_map_data(current_mod["path"])
                    # 選択された国家の海軍基地を赤色で描画
                    self.map_widget.draw_selected_country_naval_bases(self.map_widget.map_image_item.pixmap(), tag)
                    self.logger.info(f"マップデータを読み込みました: {current_mod['path']}")
                else:
                    self.logger.warning("MODが選択されていません。マップデータを読み込めません。")

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

        # 艦隊には任務部隊のみ追加可能
        if target_type == "fleet" and source_type != "task_force":
            QMessageBox.warning(self, "警告", "艦隊には任務部隊のみ追加できます。")
            event.ignore()
            return

        # 任務部隊には艦艇のみ追加可能
        if target_type == "task_force" and source_type != "ship":
            QMessageBox.warning(self, "警告", "任務部隊には艦艇のみ追加できます。")
            event.ignore()
            return

        event.acceptProposedAction()

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
                    
                    # 移動の制限を確認
                    if (target_type == "fleet" and source_type == "task_force") or \
                       (target_type == "task_force" and source_type == "ship"):
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
        dialog = FleetDialog(self)
        if dialog.exec_():
            name, province_id = dialog.get_data()
            try:
                province_id = int(province_id)
                if not self.map_widget.map_data.is_valid_deployment_location(province_id):
                    QMessageBox.warning(self, "警告", "艦隊は沿岸部の陸地にのみ配備できます。")
                    return
                item = QTreeWidgetItem(self.fleet_tree)
                item.setText(0, f"艦隊: {name} (Province: {province_id})")
                item.setData(0, Qt.UserRole, {"type": "fleet", "name": name, "province_id": province_id})
            except ValueError:
                QMessageBox.warning(self, "警告", "Province IDは数値で入力してください。")

    def add_task_force(self):
        selected = self.fleet_tree.currentItem()
        if not selected:
            QMessageBox.warning(self, "警告", "艦隊を選択してください。")
            return
            
        dialog = TaskForceDialog(self)
        if dialog.exec_():
            name, province_id = dialog.get_data()
            try:
                province_id = int(province_id)
                if not self.map_widget.map_data.is_valid_deployment_location(province_id):
                    QMessageBox.warning(self, "警告", "任務部隊は沿岸部の陸地にのみ配備できます。")
                    return
                item = QTreeWidgetItem(selected)
                item.setText(0, f"任務部隊: {name} (Province: {province_id})")
                item.setData(0, Qt.UserRole, {"type": "task_force", "name": name, "province_id": province_id})
            except ValueError:
                QMessageBox.warning(self, "警告", "Province IDは数値で入力してください。")

    def on_item_double_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        if data and data.get("type") in ["fleet", "task_force"]:
            QMessageBox.information(self, "情報", f"選択: {data['name']}")

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
                            design_name = design_data.get('design_name', design_data.get('hull_name', '不明'))
                            ship_type = design_data.get('ship_type', design_data.get('hull', '不明'))
                            new_item.setText(0, f"艦艇: {name} (Exp: {exp:.2f}, Pride: {is_pride}) - {design_name} - {ship_type}{year_str}")
                            new_item.setData(0, Qt.UserRole, {
                                "type": "ship",
                                "name": name,
                                "exp": exp,
                                "is_pride": is_pride,
                                "design": design_data
                            })
                    else:
                        QMessageBox.warning(self, "警告", "任務部隊を選択してください。")
                else:
                    QMessageBox.warning(self, "警告", "任務部隊を選択してください。")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"艦艇の追加中にエラーが発生しました：\n{str(e)}")

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
                else:
                    QMessageBox.warning(self, "警告", "艦隊データの保存に失敗しました。")
            else:
                QMessageBox.warning(self, "警告", "アプリケーションコントローラーが設定されていません。")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"艦隊データの保存中にエラーが発生しました：\n{str(e)}")

    def load_fleet_data(self):
        """艦隊データを読み込み"""
        if not self.current_country:
            return

        try:
            # コントローラーから艦隊データを取得
            if self.app_controller:
                fleet_data = self.app_controller.load_fleet_data(self.current_country)
                if fleet_data:
                    # 艦隊ツリーをクリア
                    self.fleet_tree.clear()

                    # 艦隊データをツリーに追加
                    for fleet in fleet_data.get("fleets", []):
                        fleet_item = QTreeWidgetItem(self.fleet_tree)
                        fleet_item.setText(0, f"艦隊: {fleet['name']} (Province: {fleet['province_id']})")
                        fleet_item.setData(0, Qt.UserRole, {
                            "type": "fleet",
                            "name": fleet["name"],
                            "province_id": fleet["province_id"]
                        })

                        # 任務部隊を追加
                        for task_force in fleet.get("task_forces", []):
                            task_force_item = QTreeWidgetItem(fleet_item)
                            task_force_item.setText(0, f"任務部隊: {task_force['name']} (Province: {task_force['province_id']})")
                            task_force_item.setData(0, Qt.UserRole, {
                                "type": "task_force",
                                "name": task_force["name"],
                                "province_id": task_force["province_id"]
                            })

                            # 艦艇を追加
                            for ship in task_force.get("ships", []):
                                ship_item = QTreeWidgetItem(task_force_item)
                                ship_item.setText(0, f"艦艇: {ship['name']} (Exp: {ship['exp']:.2f}, Pride: {ship['is_pride']})")
                                ship_item.setData(0, Qt.UserRole, {
                                    "type": "ship",
                                    "name": ship["name"],
                                    "exp": ship["exp"],
                                    "is_pride": ship["is_pride"],
                                    "design": ship["design"]
                                })

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"艦隊データの読み込み中にエラーが発生しました：\n{str(e)}")

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
            
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"国家リストの更新中にエラーが発生しました：\n{str(e)}")

    def draw_naval_bases(self, target_pixmap: QPixmap):
        painter = QPainter(target_pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # 固定の円のサイズを使用
        circle_radius = 8

        for prov_id, level in self.naval_base_locations.items():
            if prov_id in self.province_centroids and self.province_centroids[prov_id] is not None:
                center_x, center_y = self.province_centroids[prov_id]

                # 外側の円（青い輪郭）
                painter.setPen(QPen(QColor(0, 0, 255, 200), 2))
                painter.setBrush(QColor(0, 0, 255, 100))
                painter.drawEllipse(QPointF(center_x, center_y), circle_radius, circle_radius)

                # 内側の円（白い輪郭）
                inner_radius = circle_radius * 0.7
                painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
                painter.setBrush(QColor(255, 255, 255, 150))
                painter.drawEllipse(QPointF(center_x, center_y), inner_radius, inner_radius)

        painter.end()

    def draw_selected_country_naval_bases(self, target_pixmap: QPixmap, country_tag: str):
        """選択された国家の海軍基地を赤色で描画"""
        if not country_tag or not self.states_data:
            return

        painter = QPainter(target_pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # 固定の円のサイズを使用
        circle_radius = 10  # 通常の海軍基地より少し大きく

        # 選択された国家のステートを特定
        selected_country_states = []
        for state_id, state_data in self.states_data.items():
            if state_data['raw_data'].get('owner') == country_tag:
                selected_country_states.append(state_id)

        # 選択された国家のステートに属する海軍基地を描画
        for prov_id, level in self.naval_base_locations.items():
            if prov_id in self.province_centroids and self.province_centroids[prov_id] is not None:
                # プロビンスが選択された国家のステートに属しているか確認
                prov_obj = self.provinces_data_by_id.get(prov_id)
                if prov_obj and prov_obj.state_id in selected_country_states:
                    center_x, center_y = self.province_centroids[prov_id]

                    # 外側の円（赤い輪郭）
                    painter.setPen(QPen(QColor(255, 0, 0, 200), 2))
                    painter.setBrush(QColor(255, 0, 0, 100))
                    painter.drawEllipse(QPointF(center_x, center_y), circle_radius, circle_radius)

                    # 内側の円（白い輪郭）
                    inner_radius = circle_radius * 0.7
                    painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
                    painter.setBrush(QColor(255, 255, 255, 150))
                    painter.drawEllipse(QPointF(center_x, center_y), inner_radius, inner_radius)

        painter.end()

    def on_mod_changed(self, mod_path):
        """MODが変更された時の処理"""
        self.logger.info(f"MODが変更されました: {mod_path}")
        # マップデータを再読み込み
        self.load_map_data()
        # 国家リストを再読み込み
        self.load_countries()
        # 艦隊データをクリア
        self.fleet_tree.clear()
        # 設計リストをクリア
        self.design_list.clear()
        # 現在の国家をリセット
        self.current_country = None
        self.country_combo.setCurrentIndex(-1)

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
        
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)

    def get_data(self):
        return self.name_edit.text(), self.province_edit.text()

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
        
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)

    def get_data(self):
        return self.name_edit.text(), self.province_edit.text()

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
        
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)

    def get_data(self):
        return self.name_edit.text(), self.exp_spin.value(), self.pride_check.isChecked()

    def load_map_data(self):
        """マップデータを読み込む"""
        # App Controllerから現在のMODパスを取得
        if self.app_controller:
            current_mod = self.app_controller.get_current_mod()
            
            if current_mod and "path" in current_mod:
                # マップデータを読み込む
                self.map_widget.load_map_data(current_mod["path"])
            else:
                QMessageBox.warning(self, "警告", "MODが選択されていません。\nホーム画面からMODを選択してください。")
        else:
            QMessageBox.warning(self, "警告", "App Controllerが設定されていません。")
    