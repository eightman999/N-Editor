from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QListWidget, QListWidgetItem,
                             QSizePolicy, QMessageBox, QTabWidget, QComboBox,
                             QTreeWidget, QTreeWidgetItem, QLineEdit, QCompleter)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QFont
import os
from parser.EffectParser import EffectParser
from parser.NavalOOBParser import NavalOOBParser

# PIL のインポートを安全に行う
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("警告: PILがインストールされていません。国旗表示機能は無効になります。")


class NationDetailsView(QWidget):
    """国家詳細画面のビュー"""

    def __init__(self, parent=None, app_controller=None):
        super(NationDetailsView, self).__init__(parent)
        self.app_controller = app_controller
        self.current_nation_tag = None
        self.all_nations = []  # 全国家データを保持
        self.filtered_nations = []  # フィルタリングされた国家データを保持
        self.init_ui()

    def init_ui(self):
        """UIの初期化"""
        # メインレイアウト
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # ヘッダー部分
        header_layout = QVBoxLayout()

        # タイトル行
        title_layout = QHBoxLayout()
        self.title_label = QLabel("国家詳細")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_layout.addWidget(self.title_label)

        # 戻るボタン
        self.back_button = QPushButton("戻る")
        self.back_button.clicked.connect(self.go_back)
        title_layout.addWidget(self.back_button)
        title_layout.addStretch()

        header_layout.addLayout(title_layout)

        # 国家選択行
        nation_select_layout = QHBoxLayout()

        # 国家検索欄
        nation_select_layout.addWidget(QLabel("国家検索:"))
        self.nation_search = QLineEdit()
        self.nation_search.setPlaceholderText("国家名またはタグで検索...")
        nation_select_layout.addWidget(self.nation_search)

        # 国家選択コンボボックス
        nation_select_layout.addWidget(QLabel("国家選択:"))
        self.nation_combo = QComboBox()
        self.nation_combo.setMinimumWidth(250)
        nation_select_layout.addWidget(self.nation_combo)

        nation_select_layout.addStretch()
        header_layout.addLayout(nation_select_layout)

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
        self.tab_widget.addTab(self.equipment_list, "装備")

        # 船体タブ
        self.hull_list = QListWidget()
        self.hull_list.setStyleSheet(self.equipment_list.styleSheet())
        self.tab_widget.addTab(self.hull_list, "船体")

        # 設計タブ
        self.design_list = QListWidget()
        self.design_list.setStyleSheet(self.equipment_list.styleSheet())
        self.tab_widget.addTab(self.design_list, "設計")

        # mod内の設計タブ
        self.mod_design_list = QListWidget()
        self.mod_design_list.setStyleSheet(self.equipment_list.styleSheet())
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
        self.mod_formation_tree = QTreeWidget()
        self.mod_formation_tree.setHeaderLabels(["編成"])
        self.mod_formation_tree.setStyleSheet(self.formation_tree.styleSheet())
        self.tab_widget.addTab(self.mod_formation_tree, "mod内の編成")

        main_layout.addWidget(self.tab_widget)

        # シグナルとスロットの接続（メソッド定義後に実行）
        self.setup_connections()

        # 初期データの読み込み
        self.load_nation_list()

    def setup_connections(self):
        """シグナルとスロットの接続を設定"""
        self.nation_search.textChanged.connect(self.on_search_text_changed)
        self.nation_combo.currentIndexChanged.connect(self.on_nation_selected)
        self.equipment_list.itemDoubleClicked.connect(self.on_equipment_double_clicked)
        self.hull_list.itemDoubleClicked.connect(self.on_hull_double_clicked)
        self.design_list.itemDoubleClicked.connect(self.on_design_double_clicked)
        self.mod_design_list.itemDoubleClicked.connect(self.on_mod_design_double_clicked)
        self.mod_formation_tree.itemDoubleClicked.connect(self.on_mod_formation_double_clicked)

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

    def has_nation_data(self, nation_tag):
        """指定された国家にデータが存在するかチェック（軽量版）"""
        if not self.app_controller:
            return False

        try:
            # 軽量チェック: ファイル存在のみ確認

            # 設計データディレクトリチェック（最も軽い）
            designs_dir = self.app_controller.app_settings.design_dir
            if os.path.exists(designs_dir):
                for filename in os.listdir(designs_dir):
                    if filename.endswith('.json'):
                        # ファイル名から国家タグを推測（ファイルを開かずに）
                        if nation_tag in filename:
                            return True

            # mod内の編成データをチェック（ファイル名のみ）
            current_mod = self.app_controller.get_current_mod()
            if current_mod and "path" in current_mod:
                units_path = os.path.join(current_mod["path"], "history", "units")
                if os.path.exists(units_path):
                    # ファイル名パターンチェックのみ（ファイルを開かない）
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

            # データが存在する国家のみをフィルタリング（軽量版チェック）
            nations_with_data = []
            for nation in nations:
                if self.has_nation_data(nation['tag']):
                    nations_with_data.append(nation)

            self.all_nations = nations_with_data
            self.filtered_nations = nations_with_data  # 初期値として設定
            self.update_nation_combo()

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"国家リストの読み込み中にエラーが発生しました：\n{str(e)}")

    def update_nation_combo(self):
        """コンボボックスを更新（軽量版）"""
        try:
            # 現在選択されている国家タグを保存
            current_tag = self.nation_combo.currentData() if self.nation_combo.currentIndex() >= 0 else None

            # プルダウンをクリアして再設定
            self.nation_combo.clear()

            # 使用する国家リスト（フィルタリング済みまたは全体）
            nations_to_show = self.filtered_nations if hasattr(self, 'filtered_nations') else self.all_nations

            # 優先順位の高い国家タグ
            priority_tags = ['ENG', 'JAP', 'JPN', 'GER', 'DEU', 'FRA', 'ITA', 'USA']

            # 優先順位の高い国家を先に追加
            added_tags = set()
            for tag in priority_tags:
                for nation in nations_to_show:
                    if nation['tag'] == tag and tag not in added_tags:
                        self.add_nation_to_combo(nation)
                        added_tags.add(tag)
                        break

            # 残りの国家を追加（最初の50件のみ表示して軽量化）
            count = 0
            max_nations = 100  # 表示する最大国家数を制限
            for nation in nations_to_show:
                if nation['tag'] not in added_tags:
                    self.add_nation_to_combo(nation)
                    added_tags.add(nation['tag'])
                    count += 1
                    if count >= max_nations:
                        break

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
        """国家をコンボボックスに追加（軽量版）"""
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
                    design_name = item.get('design_name', item.get('name', '不明'))
                    ship_type = item.get('ship_type', item.get('hull', '不明'))
                    list_item.setText(f"{design_name} ({ship_type})")
                    list_item.setData(Qt.UserRole, item)
                    self.design_list.addItem(list_item)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設計データの読み込み中にエラーが発生しました：\n{str(e)}")

    def load_mod_designs(self, nation_tag):
        """mod内の設計データを読み込む（重複排除）"""
        try:
            self.mod_design_list.clear()
            if not self.app_controller:
                return

            current_mod = self.app_controller.get_current_mod()
            if not current_mod or "path" not in current_mod:
                return

            # 設計ファイルのパス
            designs_path = os.path.join(current_mod["path"], "common", "scripted_effects", "NAVY_Designs.txt")

            # 設計データを読み込む
            designs_data = {}

            # 設計ファイルを読み込む
            if os.path.exists(designs_path):
                with open(designs_path, 'r', encoding='utf-8') as f:
                    parser = EffectParser(f.read(), filename=designs_path)
                    designs_data.update(parser.parse_designs())

            # 指定された国家の設計データを表示
            if nation_tag in designs_data:
                # 重複排除のため、表示名をキーとする辞書を使用
                unique_designs = {}

                for design_name, design_data in designs_data[nation_tag].items():
                    # 設計名の処理（新しいシンプル形式）
                    display_name = self.extract_display_name_simple(design_data)
                    design_type = design_data.get('type', '不明')

                    # 一意キーを作成（表示名 + タイプ）
                    unique_key = f"{display_name}_{design_type}"

                    # 重複していない場合のみ追加
                    if unique_key not in unique_designs:
                        unique_designs[unique_key] = {
                            'display_name': display_name,
                            'design_type': design_type,
                            'design_data': design_data
                        }

                # 一意化された設計データを表示
                for unique_design in unique_designs.values():
                    list_item = QListWidgetItem()

                    # 表示テキストの設定
                    list_item.setText(f"{unique_design['display_name']} (タイプ: {unique_design['design_type']})")
                    list_item.setData(Qt.UserRole, unique_design['design_data'])
                    self.mod_design_list.addItem(list_item)

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
                            task_force_item.setText(0,
                                                    f"任務部隊: {task_force['name']} (Province: {task_force['province_id']})")
                            task_force_item.setData(0, Qt.UserRole, task_force)

                            # 艦艇を追加
                            for ship in task_force.get("ships", []):
                                ship_item = QTreeWidgetItem(task_force_item)
                                ship_item.setText(0,
                                                  f"艦艇: {ship['name']} (Exp: {ship['exp']:.2f}, Pride: {ship['is_pride']})")
                                ship_item.setData(0, Qt.UserRole, ship)

                        # 艦隊アイテムを展開
                        fleet_item.setExpanded(True)

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"編成データの読み込み中にエラーが発生しました：\n{str(e)}")

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

            # 3. 艦艇名のオーバーライドを確認
            ship_name = ship_data.get('name', '')
            if isinstance(ship_name, dict) and 'override' in ship_name:
                ship_name = ship_name['override']
            else:
                ship_name = ship_name.strip('"')

            # 4. 表示名を組み合わせ
            if design_display_name and ship_version_name:
                return f"{ship_name} - {design_display_name}({ship_version_name})"
            elif design_display_name:
                return f"{ship_name} - {design_display_name}"
            elif ship_version_name:
                return f"{ship_name} - {ship_version_name}"
            else:
                return f"{ship_name} - {definition}"

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
            print(f"override名抽出エラー: {e}")
            return ""

    def extract_display_name_simple(self, design_data):
        """設計データから表示名を抽出（新しいシンプル形式）"""
        try:
            # 基本の表示名を取得
            display_name = design_data.get('name', '').strip('"')

            # オーバーライドされているかチェック（新しい形式）
            if design_data.get('name_overridden', False):
                # override値が直接nameに保存されている
                override_name = design_data.get('name', '').strip('"')
                original_name = design_data.get('original_name', '').strip('"')

                if override_name and original_name:
                    display_name = f"{override_name}({original_name})"
                elif override_name:
                    display_name = override_name

            return display_name if display_name else design_data.get('type', '不明').strip('"')

        except Exception as e:
            print(f"表示名抽出エラー: {e}")
            return '抽出エラー'

    def get_override_name_from_design(self, definition, designs_data, nation_tag):
        """設計データからoverride名を取得"""
        try:
            print(f"\n--- override名検索開始 ---")
            print(f"検索対象definition: '{definition}'")
            print(f"検索対象nation_tag: '{nation_tag}'")

            if nation_tag in designs_data:
                print(f"国家 {nation_tag} の設計データが存在します")
                available_keys = list(designs_data[nation_tag].keys())
                print(f"利用可能な設計キー: {available_keys}")

                # まず完全一致を試す
                if definition in designs_data[nation_tag]:
                    print(f"完全一致で設計データが見つかりました: '{definition}'")
                    design_data = designs_data[nation_tag][definition]
                    result = self.extract_display_name(design_data)
                    print(f"抽出結果: '{result}'")
                    return result

                # 完全一致しない場合、部分一致を試す
                for design_key, design_data in designs_data[nation_tag].items():
                    print(f"設計キー '{design_key}' をチェック中...")

                    # typeフィールドが一致するかチェック
                    design_type = design_data.get('type', '').strip('"')
                    print(f"  design_type: '{design_type}'")
                    if design_type == definition:
                        print(f"typeフィールドで一致: '{design_type}' == '{definition}'")
                        result = self.extract_display_name(design_data)
                        print(f"抽出結果: '{result}'")
                        return result

                    # nameフィールドが一致するかチェック
                    design_name = design_data.get('name', '').strip('"')
                    print(f"  design_name: '{design_name}'")
                    if design_name == definition:
                        print(f"nameフィールドで一致: '{design_name}' == '{definition}'")
                        result = self.extract_display_name(design_data)
                        print(f"抽出結果: '{result}'")
                        return result

                print("部分一致でも見つかりませんでした")

                # 前方一致でも試す
                for design_key, design_data in designs_data[nation_tag].items():
                    if definition.startswith(design_key) or design_key.startswith(definition):
                        print(f"前方一致で見つかりました: '{design_key}' ⇔ '{definition}'")
                        result = self.extract_display_name(design_data)
                        print(f"抽出結果: '{result}'")
                        return result

                print("前方一致でも見つかりませんでした")
            else:
                print(f"国家 {nation_tag} の設計データが存在しません")
                if designs_data:
                    print(f"利用可能な国家: {list(designs_data.keys())}")

            print("設計データが見つかりませんでした")
            return "設計なし"

        except Exception as e:
            print(f"設計override名取得エラー: {e}")
            import traceback
            traceback.print_exc()
            return "設計なし"

    def get_version_name_from_ship_data(self, ship_data):
        """船体データからversion_nameを抽出"""
        try:
            print(f"\n--- 船体データからversion_name抽出開始 ---")
            equipment = ship_data.get('equipment', {})
            print(f"equipment data: {equipment}")

            if not equipment:
                print("equipmentデータがありません")
                return "装備なし"

            # 複数の装備がある場合は最初の装備のversion_nameを取得
            # または最も重要な船体装備（ship_hullで始まるもの）を優先
            version_names = []

            for equipment_type, equipment_data in equipment.items():
                print(f"装備タイプ: '{equipment_type}'")
                print(f"装備データ: {equipment_data}")

                if isinstance(equipment_data, dict):
                    version_name = equipment_data.get('version_name', '')
                    print(f"  version_name: '{version_name}'")

                    if version_name:
                        cleaned_name = version_name.strip('"')
                        version_names.append(cleaned_name)
                        print(f"  クリーンアップ後: '{cleaned_name}'")

                        # 船体関連の装備を優先
                        if equipment_type.startswith('ship_hull'):
                            print(f"  船体装備のため優先返却: '{cleaned_name}'")
                            return cleaned_name

            # 船体装備がない場合は最初に見つかったversion_nameを返す
            if version_names:
                result = version_names[0]
                print(f"最初のversion_nameを返却: '{result}'")
                return result

            print("有効なversion_nameが見つかりませんでした")
            return "バージョン名なし"

        except Exception as e:
            print(f"version_name抽出エラー: {e}")
            import traceback
            traceback.print_exc()
            return "抽出エラー"

    def get_version_name_from_design(self, definition, designs_data, nation_tag):
        """設計データから表示名を取得（旧版・使用停止予定）"""
        # この関数は使用されなくなりました
        # 実際のversion_nameは船体データのequipmentブロック内にあります
        return "設計データ参照"

    def extract_display_name(self, design_data):
        """設計データから表示名を抽出（改良版・デバッグ付き）"""
        try:
            print(f"デバッグ: extract_display_name - 設計データ: {design_data}")

            if 'override_name' in design_data:
                override_info = design_data['override_name']
                print(f"デバッグ: override_name情報: {override_info}")

                if isinstance(override_info, dict):
                    override_name = override_info.get('value', '').strip('"')
                else:
                    override_name = str(override_info).strip('"')

                original_name = design_data.get('name', '').strip('"')

                print(f"デバッグ: override_name='{override_name}', original_name='{original_name}'")

                if override_name and original_name:
                    result = f"{override_name}({original_name})"
                    print(f"デバッグ: 結合された名前: '{result}'")
                    return result
                elif override_name:
                    print(f"デバッグ: override_nameのみ: '{override_name}'")
                    return override_name
                elif original_name:
                    print(f"デバッグ: original_nameのみ: '{original_name}'")
                    return original_name
            else:
                original_name = design_data.get('name', '').strip('"')
                if original_name:
                    print(f"デバッグ: 通常のname: '{original_name}'")
                    return original_name

            design_type = design_data.get('type', '不明').strip('"')
            print(f"デバッグ: type情報を使用: '{design_type}'")
            return design_type

        except Exception as e:
            print(f"デバッグ: extract_display_name エラー: {e}")
            import traceback
            traceback.print_exc()
            return '抽出エラー'

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

    def add_star_icon(self, item):
        """アイテムに黄色い星マークを追加"""
        try:
            current_text = item.text(0)
            if not current_text.startswith("⭐"):
                item.setText(0, f"⭐ {current_text}")
                # 黄色のスタイルを設定
                item.setForeground(0, Qt.darkYellow)
        except:
            pass

    def load_mod_formations(self, nation_tag):
        """mod内の編成データを読み込む（改良版）"""
        try:
            self.mod_formation_tree.clear()
            if not self.app_controller:
                return

            current_mod = self.app_controller.get_current_mod()
            if not current_mod or "path" not in current_mod:
                return

            # 編成ファイルのパス
            units_path = os.path.join(current_mod["path"], "history", "units")
            if not os.path.exists(units_path):
                return

            # 設計データを取得（艦艇名の参照用）
            designs_path = os.path.join(current_mod["path"], "common", "scripted_effects", "NAVY_Designs.txt")
            designs_data = {}
            if os.path.exists(designs_path):
                with open(designs_path, 'r', encoding='utf-8') as f:
                    parser = EffectParser(f.read(), filename=designs_path)
                    designs_data.update(parser.parse_designs())

            # ファイルパターンに一致するファイルを検索
            import re
            pattern = re.compile(f"{nation_tag}_\\d{{4}}_(?:naval|Naval|Navy|navy)(?:_mtg)?\\.txt$")

            for filename in os.listdir(units_path):
                if pattern.match(filename):
                    file_path = os.path.join(units_path, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            parser = NavalOOBParser(f.read())
                            fleets = parser.extract_fleets()

                            # ファイル名から日付を抽出
                            date_match = re.search(r'(\d{4})', filename)
                            date = date_match.group(1) if date_match else "不明"

                            for fleet in fleets:
                                # 艦隊アイテムを作成
                                fleet_item = QTreeWidgetItem(self.mod_formation_tree)
                                fleet_name = fleet.get('name', '不明')
                                naval_base = fleet.get('naval_base', '不明')
                                task_forces = fleet.get('task_force', [])
                                if isinstance(task_forces, dict):
                                    task_forces = [task_forces]

                                total_ships = sum(len(tf.get('ship', [])) for tf in task_forces)
                                fleet_item.setText(0,
                                                   f"{fleet_name} - {naval_base} - {len(task_forces)}TF - {total_ships}隻")
                                fleet_item.setData(0, Qt.UserRole,
                                                   {'type': 'fleet', 'data': fleet, 'date': date, 'file': filename})

                                # 艦隊レベルでpride_of_the_fleetをチェック
                                fleet_has_pride = self.check_pride_in_data(fleet)

                                # 任務部隊を追加
                                for task_force in task_forces:
                                    task_force_item = QTreeWidgetItem(fleet_item)
                                    task_force_name = task_force.get('name', '不明')
                                    location = task_force.get('location', '不明')
                                    ships = task_force.get('ship', [])
                                    if isinstance(ships, dict):
                                        ships = [ships]

                                    task_force_item.setText(0, f"{task_force_name} - {location} - {len(ships)}隻")
                                    task_force_item.setData(0, Qt.UserRole, {'type': 'task_force', 'data': task_force})

                                    # 任務部隊レベルでpride_of_the_fleetをチェック
                                    task_force_has_pride = self.check_pride_in_data(task_force)

                                    # 艦艇を追加
                                    for ship in ships:
                                        ship_item = QTreeWidgetItem(task_force_item)
                                        ship_name = ship.get('name', '不明')
                                        definition = ship.get('definition', '不明')
                                        exp_factor = ship.get('start_experience_factor', '不明')

                                        # 設計データから表示名を取得（シンプル版）
                                        version_name = self.get_display_name_from_design(definition, designs_data,
                                                                                         nation_tag, ship)

                                        ship_item.setText(0,
                                                          f"{ship_name} - {definition} - {version_name} - Exp:{exp_factor}")
                                        ship_item.setData(0, Qt.UserRole, {'type': 'ship', 'data': ship})

                                        # 艦艇レベルでpride_of_the_fleetをチェック
                                        ship_has_pride = self.check_pride_in_data(ship)
                                        if ship_has_pride:
                                            self.add_star_icon(ship_item)
                                            task_force_has_pride = True
                                            fleet_has_pride = True

                                    # 任務部隊にprideがある場合は星マークを追加
                                    if task_force_has_pride:
                                        self.add_star_icon(task_force_item)

                                # 建造キューのヘッダーを追加
                                queue_items = []
                                instant_effects = fleet.get('instant_effect', [])
                                if isinstance(instant_effects, dict):
                                    instant_effects = [instant_effects]

                                for effect in instant_effects:
                                    if 'add_equipment_production' in effect:
                                        production = effect['add_equipment_production']
                                        if isinstance(production, dict):
                                            production = [production]

                                        for prod in production:
                                            if prod.get('type') == 'ship':
                                                queue_items.append(prod)

                                # 建造キューが存在する場合のみヘッダーを追加
                                if queue_items:
                                    # 建造キューヘッダー
                                    queue_header = QTreeWidgetItem(fleet_item)
                                    queue_header.setText(0, f"建造キュー ({len(queue_items)}隻)")
                                    queue_header.setData(0, Qt.UserRole, {'type': 'queue_header'})

                                    # ヘッダーのフォントを太字にする
                                    font = QFont()
                                    font.setBold(True)
                                    queue_header.setFont(0, font)

                                    # 建造キューの艦艇を追加
                                    for prod in queue_items:
                                        queue_item = QTreeWidgetItem(queue_header)
                                        ship_name = prod.get('name', '不明')
                                        definition = prod.get('definition', '不明')
                                        factories = prod.get('requested_factories', '不明')
                                        progress = prod.get('progress', '不明')

                                        # 建造キューからも表示名を取得
                                        version_name = self.get_display_name_from_design(definition, designs_data,
                                                                                         nation_tag, prod)

                                        queue_item.setText(0,
                                                           f"{ship_name} - {definition} - {version_name} - 工場:{factories} - 進捗:{progress}")
                                        queue_item.setData(0, Qt.UserRole, {'type': 'queue', 'data': prod})

                                # 艦隊にprideがある場合は星マークを追加
                                if fleet_has_pride:
                                    self.add_star_icon(fleet_item)

                                # 艦隊アイテムを展開
                                fleet_item.setExpanded(True)

                    except Exception as e:
                        print(f"ファイル {filename} のパース中にエラーが発生しました: {str(e)}")
                        continue

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"mod内の編成データの読み込み中にエラーが発生しました：\n{str(e)}")

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
                if key not in ['name', 'type', 'modules', 'upgrades', 'override_name'] and not key.startswith(
                        'original_'):
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

    def on_mod_formation_double_clicked(self, item):
        """mod内の編成アイテムがダブルクリックされた時の処理"""
        try:
            if not self.app_controller:
                return

            data = item.data(0, Qt.UserRole)
            if not data:
                return

            item_type = data.get('type')
            item_data = data.get('data')

            if item_type == 'fleet':
                details = []
                details.append(f"日付: {data['date']}")
                details.append(f"ファイル: {data['file']}")
                details.append(f"艦隊名: {item_data.get('name', '不明')}")
                details.append(f"海軍基地: {item_data.get('naval_base', '不明')}")
                QMessageBox.information(self, "艦隊詳細", "\n".join(details))

            elif item_type == 'task_force':
                details = []
                details.append(f"任務部隊名: {item_data.get('name', '不明')}")
                details.append(f"位置: {item_data.get('location', '不明')}")
                QMessageBox.information(self, "任務部隊詳細", "\n".join(details))

            elif item_type == 'ship':
                details = []
                details.append(f"艦艇名: {item_data.get('name', '不明')}")
                details.append(f"定義: {item_data.get('definition', '不明')}")
                details.append(f"経験値係数: {item_data.get('start_experience_factor', '不明')}")

                # pride_of_the_fleetの確認
                if self.check_pride_in_data(item_data):
                    details.append("特殊: 艦隊の誇り")

                QMessageBox.information(self, "艦艇詳細", "\n".join(details))

            elif item_type == 'queue':
                details = []
                details.append(f"艦艇名: {item_data.get('name', '不明')}")
                details.append(f"定義: {item_data.get('definition', '不明')}")
                details.append(f"要求工場数: {item_data.get('requested_factories', '不明')}")
                details.append(f"進捗: {item_data.get('progress', '不明')}%")
                QMessageBox.information(self, "建造キュー詳細", "\n".join(details))

            elif item_type == 'queue_header':
                QMessageBox.information(self, "建造キュー", "この艦隊の建造キューです。")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"編成詳細の表示中にエラーが発生しました：\n{str(e)}")

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