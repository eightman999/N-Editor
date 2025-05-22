from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QListWidget, QListWidgetItem,
                             QSizePolicy, QMessageBox, QTabWidget, QComboBox,
                             QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt
import os
from parser.EffectParser import EffectParser
from parser.DivisionNameParser import DivisionNameParser
from parser.PersonNameParser import PersonNameParser
from parser.ShipNameParser import ShipNameParser

class NationDetailsView(QWidget):
    """国家詳細画面のビュー"""

    def __init__(self, parent=None, app_controller=None):
        super(NationDetailsView, self).__init__(parent)
        self.app_controller = app_controller
        self.current_nation_tag = None
        self.init_ui()

    def init_ui(self):
        """UIの初期化"""
        # メインレイアウト
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # ヘッダー部分
        header_layout = QHBoxLayout()
        self.title_label = QLabel("国家詳細")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.title_label)

        # 国家選択プルダウン
        self.nation_combo = QComboBox()
        self.nation_combo.setMinimumWidth(200)
        self.nation_combo.currentIndexChanged.connect(self.on_nation_selected)
        header_layout.addWidget(self.nation_combo)

        # 戻るボタン
        self.back_button = QPushButton("戻る")
        self.back_button.clicked.connect(self.go_back)
        header_layout.addWidget(self.back_button)

        main_layout.addLayout(header_layout)

        # タブウィジェット
        self.tab_widget = QTabWidget()
        
        # 装備タブ
        self.equipment_list = QListWidget()
        self.equipment_list.setStyleSheet("""
            QListWidget {
                font-size: 12px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #ddd;
            }
            QListWidget::item:selected {
                background-color: #e0e0e0;
            }
        """)
        self.equipment_list.itemDoubleClicked.connect(self.on_equipment_double_clicked)
        self.tab_widget.addTab(self.equipment_list, "装備")
        
        # 船体タブ
        self.hull_list = QListWidget()
        self.hull_list.setStyleSheet(self.equipment_list.styleSheet())
        self.hull_list.itemDoubleClicked.connect(self.on_hull_double_clicked)
        self.tab_widget.addTab(self.hull_list, "船体")
        
        # 設計タブ
        self.design_list = QListWidget()
        self.design_list.setStyleSheet(self.equipment_list.styleSheet())
        self.design_list.itemDoubleClicked.connect(self.on_design_double_clicked)
        self.tab_widget.addTab(self.design_list, "設計")

        # mod内の設計タブ
        self.mod_design_list = QListWidget()
        self.mod_design_list.setStyleSheet(self.equipment_list.styleSheet())
        self.mod_design_list.itemDoubleClicked.connect(self.on_mod_design_double_clicked)
        self.tab_widget.addTab(self.mod_design_list, "mod内の設計")

        # 編成タブ
        self.formation_tree = QTreeWidget()
        self.formation_tree.setHeaderLabels(["編成"])
        self.formation_tree.setStyleSheet("""
            QTreeWidget {
                font-size: 12px;
                padding: 5px;
            }
            QTreeWidget::item {
                padding: 5px;
                border-bottom: 1px solid #ddd;
            }
            QTreeWidget::item:selected {
                background-color: #e0e0e0;
            }
        """)
        self.tab_widget.addTab(self.formation_tree, "編成")

        # mod内の編成タブ
        self.mod_formation_list = QListWidget()
        self.mod_formation_list.setStyleSheet(self.equipment_list.styleSheet())
        self.mod_formation_list.itemDoubleClicked.connect(self.on_mod_formation_double_clicked)
        self.tab_widget.addTab(self.mod_formation_list, "mod内の編成")

        # 名前リストタブ
        self.name_tab = QTabWidget()
        
        # 人名リスト
        self.person_name_list = QListWidget()
        self.person_name_list.setStyleSheet(self.equipment_list.styleSheet())
        self.person_name_list.itemDoubleClicked.connect(self.on_person_name_double_clicked)
        self.name_tab.addTab(self.person_name_list, "人名")
        
        # 艦名リスト
        self.ship_name_list = QListWidget()
        self.ship_name_list.setStyleSheet(self.equipment_list.styleSheet())
        self.ship_name_list.itemDoubleClicked.connect(self.on_ship_name_double_clicked)
        self.name_tab.addTab(self.ship_name_list, "艦名")
        
        # 師団名リスト
        self.division_name_list = QListWidget()
        self.division_name_list.setStyleSheet(self.equipment_list.styleSheet())
        self.division_name_list.itemDoubleClicked.connect(self.on_division_name_double_clicked)
        self.name_tab.addTab(self.division_name_list, "師団名")
        
        self.tab_widget.addTab(self.name_tab, "名前リスト")

        main_layout.addWidget(self.tab_widget)

        # 初期データの読み込み
        self.load_nation_list()

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

            # プルダウンをクリアして再設定
            self.nation_combo.clear()
            
            # 優先順位の高い国家タグ
            priority_tags = ['ENG', 'JAP', 'JPN', 'GER', 'DEU', 'FRA', 'ITA', 'USA']
            
            # 優先順位の高い国家を先に追加
            added_tags = set()
            for tag in priority_tags:
                for nation in nations:
                    if nation['tag'] == tag and tag not in added_tags:
                        self.nation_combo.addItem(f"{nation['tag']}: {nation['name']}", nation['tag'])
                        added_tags.add(tag)
                        break
            
            # 残りの国家を追加
            for nation in nations:
                if nation['tag'] not in added_tags:
                    self.nation_combo.addItem(f"{nation['tag']}: {nation['name']}", nation['tag'])
                    added_tags.add(nation['tag'])

            # 優先順位の高い国家の最初のものを選択
            for tag in priority_tags:
                index = self.nation_combo.findData(tag)
                if index >= 0:
                    self.nation_combo.setCurrentIndex(index)
                    break

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"国家リストの読み込み中にエラーが発生しました：\n{str(e)}")

    def on_nation_selected(self, index):
        """国家が選択された時の処理"""
        try:
            if index < 0:
                return

            nation_tag = self.nation_combo.currentData()
            if nation_tag:
                self.load_nation_data(nation_tag)

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"国家データの読み込み中にエラーが発生しました：\n{str(e)}")

    def load_nation_data(self, nation_tag):
        """国家データを読み込む"""
        try:
            if not self.app_controller:
                return

            self.current_nation_tag = nation_tag
            # タイトルを更新
            self.title_label.setText(f"国家詳細: {nation_tag}")

            # 各タブのデータを読み込む
            self.load_equipment(nation_tag)
            self.load_hulls(nation_tag)
            self.load_designs(nation_tag)
            self.load_mod_designs(nation_tag)
            self.load_formations(nation_tag)
            self.load_mod_formations(nation_tag)
            self.load_person_names(nation_tag)
            self.load_ship_names(nation_tag)
            self.load_division_names(nation_tag)

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"国家データの読み込み中にエラーが発生しました：\n{str(e)}")

    def load_equipment(self, nation_tag):
        """装備データを読み込む"""
        try:
            self.equipment_list.clear()
            if self.app_controller:
                equipment_data = self.app_controller.get_nation_equipment(nation_tag)
                for item in equipment_data:
                    list_item = QListWidgetItem()
                    list_item.setText(f"{item['name']} ({item['type']})")
                    list_item.setData(Qt.UserRole, item)
                    self.equipment_list.addItem(list_item)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"装備データの読み込み中にエラーが発生しました：\n{str(e)}")

    def load_hulls(self, nation_tag):
        """船体データを読み込む"""
        try:
            self.hull_list.clear()
            if self.app_controller:
                hull_data = self.app_controller.get_nation_hulls(nation_tag)
                for item in hull_data:
                    list_item = QListWidgetItem()
                    list_item.setText(f"{item['name']} ({item['type']})")
                    list_item.setData(Qt.UserRole, item)
                    self.hull_list.addItem(list_item)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"船体データの読み込み中にエラーが発生しました：\n{str(e)}")

    def load_designs(self, nation_tag):
        """設計データを読み込む"""
        try:
            self.design_list.clear()
            if self.app_controller:
                design_data = self.app_controller.get_nation_designs(nation_tag)
                for item in design_data:
                    list_item = QListWidgetItem()
                    list_item.setText(f"{item['name']} (船体: {item['hull']})")
                    list_item.setData(Qt.UserRole, item)
                    self.design_list.addItem(list_item)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設計データの読み込み中にエラーが発生しました：\n{str(e)}")

    def load_mod_designs(self, nation_tag):
        """mod内の設計データを読み込む"""
        try:
            self.mod_design_list.clear()
            if not self.app_controller:
                return

            current_mod = self.app_controller.get_current_mod()
            if not current_mod or "path" not in current_mod:
                QMessageBox.warning(self, "警告", "MODが選択されていません。")
                return

            # 設計ファイルのパス
            designs_path = os.path.join(current_mod["path"], "common", "scripted_effects", "NAVY_Designs.txt")

            # デバッグ情報を表示
            print(f"MODパス: {current_mod['path']}")
            print(f"設計ファイルパス: {designs_path}")

            # 設計データを読み込む
            designs_data = {}
            
            # 設計ファイルを読み込む
            if os.path.exists(designs_path):
                with open(designs_path, 'r', encoding='utf-8') as f:
                    parser = EffectParser(f.read(), filename=designs_path)
                    designs_data.update(parser.parse_designs())
            else:
                QMessageBox.warning(self, "警告", "設計ファイルが見つかりません。\n以下のパスを確認してください：\n" + 
                                  f"\n{designs_path}")
                return

            # 指定された国家の設計データを表示
            if nation_tag in designs_data:
                for design_name, design_data in designs_data[nation_tag].items():
                    list_item = QListWidgetItem()
                    
                    # 設計名の処理
                    display_name = design_name
                    if 'override_name' in design_data:
                        override_name = design_data['override_name'].get('value', '').strip('"')
                        original_name = design_data.get('name', '').strip('"')
                        if override_name and original_name:
                            display_name = f"{override_name}({original_name})"
                    
                    # 設計タイプの取得
                    design_type = design_data.get('type', '不明')
                    
                    # 表示テキストの設定
                    list_item.setText(f"{display_name} (タイプ: {design_type})")
                    list_item.setData(Qt.UserRole, design_data)
                    self.mod_design_list.addItem(list_item)
            else:
                QMessageBox.information(self, "情報", f"国家 {nation_tag} の設計データが見つかりません。")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"mod内の設計データの読み込み中にエラーが発生しました：\n{str(e)}")

    def load_formations(self, nation_tag):
        """編成データを読み込む"""
        try:
            self.formation_tree.clear()
            if self.app_controller:
                formation_data = self.app_controller.load_fleet_data(nation_tag)
                if formation_data:
                    for fleet in formation_data.get("fleets", []):
                        # 艦隊アイテムを作成
                        fleet_item = QTreeWidgetItem(self.formation_tree)
                        fleet_item.setText(0, f"艦隊: {fleet['name']} (Province: {fleet['province_id']})")
                        fleet_item.setData(0, Qt.UserRole, fleet)

                        # 任務部隊を追加
                        for task_force in fleet.get("task_forces", []):
                            task_force_item = QTreeWidgetItem(fleet_item)
                            task_force_item.setText(0, f"任務部隊: {task_force['name']} (Province: {task_force['province_id']})")
                            task_force_item.setData(0, Qt.UserRole, task_force)

                            # 艦艇を追加
                            for ship in task_force.get("ships", []):
                                ship_item = QTreeWidgetItem(task_force_item)
                                ship_item.setText(0, f"艦艇: {ship['name']} (Exp: {ship['exp']:.2f}, Pride: {ship['is_pride']})")
                                ship_item.setData(0, Qt.UserRole, ship)

                        # 艦隊アイテムを展開
                        fleet_item.setExpanded(True)

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"編成データの読み込み中にエラーが発生しました：\n{str(e)}")

    def load_mod_formations(self, nation_tag):
        """mod内の編成データを読み込む"""
        try:
            self.mod_formation_list.clear()
            if self.app_controller:
                # TODO: app_controllerに実装が必要
                mod_formation_data = self.app_controller.get_nation_mod_formations(nation_tag)
                for item in mod_formation_data:
                    list_item = QListWidgetItem()
                    list_item.setText(f"{item['name']}")
                    list_item.setData(Qt.UserRole, item)
                    self.mod_formation_list.addItem(list_item)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"mod内の編成データの読み込み中にエラーが発生しました：\n{str(e)}")

    def load_person_names(self, nation_tag):
        """人名データを読み込む"""
        try:
            self.person_name_list.clear()
            if not self.app_controller:
                return

            current_mod = self.app_controller.get_current_mod()
            if not current_mod or "path" not in current_mod:
                QMessageBox.warning(self, "警告", "MODが選択されていません。")
                return

            # 名前ファイルのディレクトリパス
            names_dir = os.path.join(current_mod["path"], "common", "characters")
            
            # ディレクトリ内の全ファイルを処理
            if os.path.exists(names_dir):
                for filename in os.listdir(names_dir):
                    if filename.endswith('.txt'):
                        file_path = os.path.join(names_dir, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            parser = PersonNameParser(f.read(), filename=file_path)
                            names_data = parser.parse()

                            if nation_tag in names_data:
                                tag_data = names_data[nation_tag]
                                
                                # 男性名の表示
                                for name in tag_data['male_name']:
                                    list_item = QListWidgetItem()
                                    list_item.setText(f"男性名: {name}")
                                    list_item.setData(Qt.UserRole, {'name': name, 'type': 'male_name'})
                                    self.person_name_list.addItem(list_item)

                                # 女性名の表示
                                for name in tag_data['female_name']:
                                    list_item = QListWidgetItem()
                                    list_item.setText(f"女性名: {name}")
                                    list_item.setData(Qt.UserRole, {'name': name, 'type': 'female_name'})
                                    self.person_name_list.addItem(list_item)

                                # 姓の表示
                                for name in tag_data['surname']:
                                    list_item = QListWidgetItem()
                                    list_item.setText(f"姓: {name}")
                                    list_item.setData(Qt.UserRole, {'name': name, 'type': 'surname'})
                                    self.person_name_list.addItem(list_item)

                                # コールサインの表示
                                for name in tag_data['callsign']:
                                    list_item = QListWidgetItem()
                                    list_item.setText(f"コールサイン: {name}")
                                    list_item.setData(Qt.UserRole, {'name': name, 'type': 'callsign'})
                                    self.person_name_list.addItem(list_item)
            else:
                QMessageBox.information(self, "情報", f"名前ディレクトリが見つかりません：\n{names_dir}")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"人名データの読み込み中にエラーが発生しました：\n{str(e)}")

    def load_ship_names(self, nation_tag):
        """艦名データを読み込む"""
        try:
            self.ship_name_list.clear()
            if not self.app_controller:
                return

            current_mod = self.app_controller.get_current_mod()
            if not current_mod or "path" not in current_mod:
                QMessageBox.warning(self, "警告", "MODが選択されていません。")
                return

            # 艦名ファイルのディレクトリパス
            ship_names_dir = os.path.join(current_mod["path"], "common", "units", "names_ships")
            
            # ディレクトリ内の全ファイルを処理
            if os.path.exists(ship_names_dir):
                for filename in os.listdir(ship_names_dir):
                    if filename.endswith('.txt'):
                        file_path = os.path.join(ship_names_dir, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            parser = ShipNameParser(f.read(), filename=file_path)
                            ship_names = parser.parse()

                            for ship_name in ship_names:
                                list_item = QListWidgetItem()
                                list_item.setText(f"{ship_name['name']} ({ship_name['type']})")
                                list_item.setData(Qt.UserRole, ship_name)
                                self.ship_name_list.addItem(list_item)
            else:
                QMessageBox.information(self, "情報", f"艦名ディレクトリが見つかりません：\n{ship_names_dir}")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"艦名データの読み込み中にエラーが発生しました：\n{str(e)}")

    def load_division_names(self, nation_tag):
        """師団名データを読み込む"""
        try:
            self.division_name_list.clear()
            if not self.app_controller:
                return

            current_mod = self.app_controller.get_current_mod()
            if not current_mod or "path" not in current_mod:
                QMessageBox.warning(self, "警告", "MODが選択されていません。")
                return

            # 師団名ファイルのディレクトリパス
            division_names_dir = os.path.join(current_mod["path"], "common", "units", "names_divisions")
            
            # ディレクトリ内の全ファイルを処理
            if os.path.exists(division_names_dir):
                for filename in os.listdir(division_names_dir):
                    if filename.endswith('.txt'):
                        file_path = os.path.join(division_names_dir, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            parser = DivisionNameParser(f.read(), filename=file_path)
                            division_names = parser.parse()

                            for name_data in division_names:
                                list_item = QListWidgetItem()
                                list_item.setText(f"{name_data['name']} ({name_data['category']}) - No.{name_data['number']}")
                                list_item.setData(Qt.UserRole, name_data)
                                self.division_name_list.addItem(list_item)
            else:
                QMessageBox.information(self, "情報", f"師団名ディレクトリが見つかりません：\n{division_names_dir}")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"師団名データの読み込み中にエラーが発生しました：\n{str(e)}")

    def on_equipment_double_clicked(self, item):
        """装備アイテムがダブルクリックされた時の処理"""
        try:
            if not self.app_controller:
                return

            equipment_data = item.data(Qt.UserRole)
            if equipment_data:
                self.app_controller.show_equipment_form(equipment_data)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"装備フォームの表示中にエラーが発生しました：\n{str(e)}")

    def on_hull_double_clicked(self, item):
        """船体アイテムがダブルクリックされた時の処理"""
        try:
            if not self.app_controller:
                return

            hull_data = item.data(Qt.UserRole)
            if hull_data:
                self.app_controller.show_hull_form(hull_data)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"船体フォームの表示中にエラーが発生しました：\n{str(e)}")

    def on_design_double_clicked(self, item):
        """設計アイテムがダブルクリックされた時の処理"""
        try:
            if not self.app_controller:
                return

            design_data = item.data(Qt.UserRole)
            if design_data:
                self.app_controller.show_design_view(design_data)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設計ビューの表示中にエラーが発生しました：\n{str(e)}")

    def on_mod_design_double_clicked(self, item):
        """mod内の設計アイテムがダブルクリックされた時の処理"""
        try:
            if not self.app_controller:
                return

            design_data = item.data(Qt.UserRole)
            if not design_data:
                return

            # 設計の詳細情報を収集
            details = []
            
            # 設計名の処理
            if 'override_name' in design_data:
                override_name = design_data['override_name'].get('value', '').strip('"')
                original_name = design_data.get('name', '').strip('"')
                if override_name and original_name:
                    details.append(f"設計名: {override_name}({original_name})")
                else:
                    details.append(f"設計名: {original_name}")
            else:
                details.append(f"設計名: {design_data.get('name', '不明')}")
            
            details.append(f"タイプ: {design_data.get('type', '不明')}")
            
            # 船体情報
            hull = design_data.get('type', '不明')
            details.append(f"船体: {hull}")
            
            # モジュール情報
            modules = design_data.get('modules', {})
            if modules:
                details.append("\nモジュール:")
                for module_type, module_data in modules.items():
                    if isinstance(module_data, dict):
                        module_name = module_data.get('name', '不明')
                        details.append(f"- {module_type}: {module_name}")
                    else:
                        details.append(f"- {module_type}: {module_data}")

            # アップグレード情報
            upgrades = design_data.get('upgrades', {})
            if upgrades:
                details.append("\nアップグレード:")
                for upgrade_type, upgrade_level in upgrades.items():
                    details.append(f"- {upgrade_type}: {upgrade_level}")

            # その他の重要な情報
            for key, value in design_data.items():
                if key not in ['name', 'type', 'modules', 'upgrades', 'override_name'] and not key.startswith('original_'):
                    if isinstance(value, dict):
                        details.append(f"\n{key}:")
                        for sub_key, sub_value in value.items():
                            details.append(f"- {sub_key}: {sub_value}")
                    else:
                        details.append(f"\n{key}: {value}")

            # 詳細情報をダイアログで表示
            QMessageBox.information(self, "設計詳細", "\n".join(details))

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設計詳細の表示中にエラーが発生しました：\n{str(e)}")

    def on_formation_double_clicked(self, item):
        """編成アイテムがダブルクリックされた時の処理"""
        try:
            if not self.app_controller:
                return

            data = item.data(0, Qt.UserRole)
            if not data:
                return

            # アイテムの種類に応じて詳細を表示
            if "task_forces" in data:  # 艦隊
                details = []
                details.append(f"艦隊名: {data['name']}")
                details.append(f"Province ID: {data['province_id']}")
                details.append(f"\n任務部隊数: {len(data['task_forces'])}")
                QMessageBox.information(self, "艦隊詳細", "\n".join(details))

            elif "ships" in data:  # 任務部隊
                details = []
                details.append(f"任務部隊名: {data['name']}")
                details.append(f"Province ID: {data['province_id']}")
                details.append(f"\n艦艇数: {len(data['ships'])}")
                QMessageBox.information(self, "任務部隊詳細", "\n".join(details))

            else:  # 艦艇
                details = []
                details.append(f"艦艇名: {data['name']}")
                details.append(f"経験値: {data['exp']:.2f}")
                details.append(f"艦隊の誇り: {'あり' if data['is_pride'] else 'なし'}")
                if isinstance(data['design'], dict):
                    details.append(f"\n設計名: {data['design'].get('design_name', '不明')}")
                    details.append(f"艦種: {data['design'].get('ship_type', '不明')}")
                QMessageBox.information(self, "艦艇詳細", "\n".join(details))

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"編成データの表示中にエラーが発生しました：\n{str(e)}")

    def on_mod_formation_double_clicked(self, item):
        """mod内の編成アイテムがダブルクリックされた時の処理"""
        try:
            if not self.app_controller:
                return

            mod_formation_data = item.data(Qt.UserRole)
            if mod_formation_data:
                # TODO: app_controllerに実装が必要
                self.app_controller.show_mod_formation_view(mod_formation_data)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"mod内の編成ビューの表示中にエラーが発生しました：\n{str(e)}")

    def on_person_name_double_clicked(self, item):
        """人名アイテムがダブルクリックされた時の処理"""
        try:
            if not self.app_controller:
                return

            name_data = item.data(Qt.UserRole)
            if name_data:
                # 名前の詳細情報を表示
                details = []
                details.append(f"名前: {name_data.get('name', '不明')}")
                details.append(f"タイプ: {name_data.get('type', '不明')}")

                QMessageBox.information(self, "人名詳細", "\n".join(details))

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"人名詳細の表示中にエラーが発生しました：\n{str(e)}")

    def on_ship_name_double_clicked(self, item):
        """艦名アイテムがダブルクリックされた時の処理"""
        try:
            if not self.app_controller:
                return

            ship_data = item.data(Qt.UserRole)
            if ship_data:
                # 艦名の詳細情報を表示
                details = []
                details.append(f"艦名: {ship_data.get('name', '不明')}")
                details.append(f"タイプ: {ship_data.get('type', '不明')}")

                QMessageBox.information(self, "艦名詳細", "\n".join(details))

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"艦名詳細の表示中にエラーが発生しました：\n{str(e)}")

    def on_division_name_double_clicked(self, item):
        """師団名アイテムがダブルクリックされた時の処理"""
        try:
            if not self.app_controller:
                return

            name_data = item.data(Qt.UserRole)
            if name_data:
                # 師団名の詳細情報を表示
                details = []
                details.append(f"師団名: {name_data.get('name', '不明')}")
                details.append(f"カテゴリー: {name_data.get('category', '不明')}")
                details.append(f"タイプ: {name_data.get('type', '不明')}")

                QMessageBox.information(self, "師団名詳細", "\n".join(details))

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"師団名詳細の表示中にエラーが発生しました：\n{str(e)}")

    def go_back(self):
        """前の画面に戻る"""
        try:
            if self.app_controller:
                self.app_controller.show_nation_list()
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"画面遷移中にエラーが発生しました：\n{str(e)}")

    def showEvent(self, event):
        """表示時に呼ばれるイベント"""
        super().showEvent(event)
        # 表示時に国家リストを更新
        self.load_nation_list()
        # 前回選択していた国家があれば、その国家を選択
        if self.current_nation_tag:
            index = self.nation_combo.findData(self.current_nation_tag)
            if index >= 0:
                self.nation_combo.setCurrentIndex(index) 