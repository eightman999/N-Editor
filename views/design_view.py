from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
                             QLabel, QLineEdit, QComboBox, QPushButton, QGroupBox,
                             QDialog, QListWidget, QTableWidget, QTableWidgetItem,
                             QScrollArea, QMessageBox, QHeaderView)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette

class DesignView(QWidget):
    def __init__(self, parent=None, app_controller=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.current_hull = None  # 現在選択されている船体データ
        self.initUI()

    def initUI(self):
        # メインレイアウト
        main_layout = QVBoxLayout(self)

        # 上部：艦種と船体選択
        top_layout = QHBoxLayout()

        # 艦種選択
        ship_type_layout = QHBoxLayout()
        ship_type_layout.addWidget(QLabel("艦種 ▷"))
        self.ship_type_combo = QComboBox()
        # 艦種の選択肢はHullModel.ship_type_mappingから動的に取得
        self.ship_type_combo.addItem("選択してください")
        if self.app_controller:
            try:
                # HullModelのship_type_mappingを使用
                from models.hull_model import HullModel
                for key, value in HullModel.ship_type_mapping.items():
                    self.ship_type_combo.addItem(value)
            except:
                # 何らかの理由で取得できない場合はハードコードしたリストを使用
                ship_types = ["DD - 駆逐艦", "CL - 軽巡洋艦", "CA - 重巡洋艦", "BB - 戦艦", "CV - 航空母艦", "SS - 潜水艦"]
                self.ship_type_combo.addItems(ship_types)
        ship_type_layout.addWidget(self.ship_type_combo)
        top_layout.addLayout(ship_type_layout)

        # スペーサー
        top_layout.addStretch()

        # 船体選択
        hull_layout = QHBoxLayout()
        hull_layout.addWidget(QLabel("船体 ▷"))
        self.hull_select_button = QPushButton("選択する")
        self.hull_select_button.clicked.connect(self.select_hull)
        hull_layout.addWidget(self.hull_select_button)
        top_layout.addLayout(hull_layout)

        main_layout.addLayout(top_layout)

        # 船体表示
        hull_info_layout = QHBoxLayout()
        hull_info_layout.addWidget(QLabel("選択中の船体:"))
        self.selected_hull_label = QLabel("なし")
        hull_info_layout.addWidget(self.selected_hull_label)
        hull_info_layout.addStretch()
        main_layout.addLayout(hull_info_layout)

        # 艦級名入力
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("艦級名:"))
        self.design_name_edit = QLineEdit()
        name_layout.addWidget(self.design_name_edit)
        main_layout.addLayout(name_layout)

        # 中央部：スロットと性能表示
        central_layout = QHBoxLayout()

        # 左側：スロット部分
        slots_group = QGroupBox("プレイヤー設定可能スロット (6枠固定)")
        slots_layout = QVBoxLayout()

        # スロット定義
        slot_types = ["PA", "SA", "PSA", "SSA", "PLA", "SLA"]
        self.slot_combos = {}
        self.slot_category_combos = {}

        for slot_type in slot_types:
            slot_layout = QHBoxLayout()

            # スロットタイプラベル
            slot_layout.addWidget(QLabel(f"スロット {slot_type} ▷"))

            # カテゴリー選択コンボボックス（どの種類の装備を入れるか）
            category_combo = QComboBox()
            category_combo.addItem("カテゴリー選択")
            self.slot_category_combos[slot_type] = category_combo

            # 装備選択コンボボックス
            equipment_combo = QComboBox()
            equipment_combo.addItem("選択する")
            self.slot_combos[slot_type] = equipment_combo

            # スロットのカテゴリーが変更されたときの処理
            category_combo.currentIndexChanged.connect(
                lambda idx, s_type=slot_type: self.on_slot_category_changed(s_type, idx)
            )

            # レイアウトに追加
            slot_layout.addWidget(category_combo)
            slot_layout.addWidget(equipment_combo)
            slots_layout.addLayout(slot_layout)

        slots_group.setLayout(slots_layout)
        central_layout.addWidget(slots_group)

        # 内部スロット部分
        internal_slots_layout = QHBoxLayout()
        internal_slots_layout.addWidget(QLabel("内部スロット"))
        add_button = QPushButton("+ 追加")
        add_button.clicked.connect(self.add_internal_slot)
        internal_slots_layout.addWidget(add_button)
        remove_button = QPushButton("- 削除")
        remove_button.clicked.connect(self.remove_internal_slot)
        internal_slots_layout.addWidget(remove_button)
        internal_slots_layout.addStretch()
        slots_layout.addLayout(internal_slots_layout)

        # 右側：性能表示
        stats_group = QGroupBox("性能表示枠 (2列表示)")
        self.stats_layout = QGridLayout()

        # 性能パラメータの定義
        # 将来的に動的にするための準備として、辞書を使用
        self.stats_labels = {}

        # スータス一覧からパラメータを動的に読み込む
        self.load_stats_definitions()

        # ステータスがまだ定義されていない場合はデフォルト値を使用
        if not self.stats_labels:
            default_stats = [
                ("build_cost_ic", "Production Cost", "0.4 IC"),
                ("manpower", "Manpower", "300"),
                ("reliability", "Reliability", "90%"),
                ("naval_speed", "Speed", "28 km/h"),
                ("lg_attack", "Light Gun Attack", "18"),
                ("lg_armor_piercing", "Light Gun Piercing", "12"),
                ("hg_attack", "Heavy Gun Attack", "12"),
                ("hg_armor_piercing", "Heavy Gun Piercing", "25"),
                ("torpedo_attack", "Torpedo Attack", "1"),
                ("anti_air_attack", "Anti-Air Attack", "5"),
                ("shore_bombardment", "Shore Bombardment", "8"),
                ("evasion", "Evasion", "15"),
                ("surface_detection", "Surface Detection", "12"),
                ("sub_attack", "Sub Attack", "10"),
                ("sub_detection", "Sub Detection", "5"),
                ("surface_visibility", "Surface Visibility", "25"),
                ("sub_visibility", "Submarine Visibility", "20"),
                ("naval_range", "Naval Range", "3000 km"),
                ("port_capacity_usage", "Port Capacity Usage", "1"),
                ("search_and_destroy_coordination", "Search & Destroy Coord", "0.1"),
                ("convoy_raiding_coordination", "Convoy Raiding Coord", "0.1")
            ]

            for key, name, value in default_stats:
                label = QLabel(value)
                self.stats_labels[key] = (name, label)

        # グリッドに配置
        stats_items = list(self.stats_labels.items())
        mid_point = (len(stats_items) + 1) // 2
        for i, (key, (name, label)) in enumerate(stats_items):
            row = i % mid_point
            col = i // mid_point * 2  # 間隔を空けるため*2
            self.stats_layout.addWidget(QLabel(f"{name}:"), row, col)
            self.stats_layout.addWidget(label, row, col + 1)

        stats_group.setLayout(self.stats_layout)
        central_layout.addWidget(stats_group)

        main_layout.addLayout(central_layout)

        # 下部：船体基礎情報
        hull_base_group = QGroupBox("船体基礎情報")
        self.hull_base_layout = QGridLayout()

        # 船体情報のラベル定義
        self.hull_info_labels = {
            "name": ("艦級名", QLabel("-")),
            "id": ("システム名称", QLabel("-")),
            "weight": ("重量", QLabel("-")),
            "length": ("長さ", QLabel("-")),
            "width": ("幅", QLabel("-")),
            "power": ("出力", QLabel("-")),
            "speed": ("速力", QLabel("-")),
            "range": ("航続距離", QLabel("-")),
            "cruise_speed": ("巡航速力", QLabel("-")),
            "fuel_type": ("燃料種別", QLabel("-")),
            "fuel_capacity": ("燃料容量", QLabel("-")),
            "armor_max": ("装甲最大", QLabel("-")),
            "armor_min": ("装甲最小", QLabel("-")),
            "hull_structure": ("船殻構造", QLabel("-")),
            "armor_type": ("装甲種別", QLabel("-")),
            "crew": ("乗員", QLabel("-")),
            "country": ("建造国", QLabel("-")),
            "class": ("種別", QLabel("-")),
            "year": ("年代", QLabel("-")),
            "archetype": ("Archetype", QLabel("-"))
        }

        # グリッド状に情報を配置
        hull_items = list(self.hull_info_labels.items())
        for i, (key, (name, label)) in enumerate(hull_items):
            row = i // 5  # 1行に5項目
            col = (i % 5) * 2  # 間隔を空けるため*2
            self.hull_base_layout.addWidget(QLabel(f"{name}:"), row, col)
            self.hull_base_layout.addWidget(label, row, col + 1)

        hull_base_group.setLayout(self.hull_base_layout)
        main_layout.addWidget(hull_base_group)

        # 下部：ボタン
        button_layout = QHBoxLayout()
        save_button = QPushButton("保存")
        save_button.clicked.connect(self.save_design)
        button_layout.addWidget(save_button)

        load_button = QPushButton("読み込み")
        load_button.clicked.connect(self.load_design)
        button_layout.addWidget(load_button)

        close_button = QPushButton("閉じる")
        close_button.clicked.connect(self.close_design)
        button_layout.addWidget(close_button)

        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # 装備カテゴリーを読み込み
        self.load_equipment_categories()

    def load_stats_definitions(self):
        """スータス一覧からパラメータを読み込む"""
        try:
            if self.app_controller:
                # アプリコントローラーから設定ファイルのパスを取得
                import os
                root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                stats_file = os.path.join(root_dir, 'スーテータス一覧.txt')

                if os.path.exists(stats_file):
                    with open(stats_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                        # ヘッダー行をスキップ
                        for line in lines[2:]:  # 最初の2行はヘッダーなのでスキップ
                            if '=' in line and '#' in line:
                                parts = line.split('=')
                                stat_name = parts[0].strip()
                                comment_parts = parts[1].split('#')
                                if len(comment_parts) > 1:
                                    stat_desc = comment_parts[1].strip()
                                    # 値部分を取得
                                    value_part = comment_parts[0].strip()
                                    # 空の場合はデフォルト値を設定
                                    value = value_part if value_part else "0"

                                    # ラベルを作成して辞書に追加
                                    label = QLabel(str(value))
                                    self.stats_labels[stat_name] = (stat_desc, label)
        except Exception as e:
            print(f"ステータス定義の読み込みエラー: {e}")

    def load_equipment_categories(self):
        """装備カテゴリーを読み込む"""
        try:
            # 全スロットのカテゴリーコンボボックスを初期化
            for slot_type, combo in self.slot_category_combos.items():
                combo.clear()
                combo.addItem("カテゴリー選択")

                # 装備タイプを追加
                if self.app_controller:
                    equipment_types = self.app_controller.get_equipment_types()
                    combo.addItems(equipment_types)
                else:
                    # デフォルトのカテゴリーを追加
                    default_categories = [
                        "小口径砲", "中口径砲", "大口径砲", "超大口径砲", "対空砲",
                        "魚雷", "潜水艦魚雷", "対艦ミサイル", "対空ミサイル",
                        "水上機", "艦上偵察機", "回転翼機", "対潜哨戒機", "大型飛行艇",
                        "爆雷投射機", "爆雷", "対潜迫撃砲",
                        "ソナー", "大型ソナー", "小型電探", "大型電探", "測距儀",
                        "機関", "増設バルジ(中型艦)", "増設バルジ(大型艦)", "格納庫", "その他"
                    ]
                    combo.addItems(default_categories)
        except Exception as e:
            print(f"装備カテゴリー読み込みエラー: {e}")

    def on_slot_category_changed(self, slot_type, index):
        """スロットのカテゴリーが変更されたときの処理"""
        try:
            category_combo = self.slot_category_combos[slot_type]
            equipment_combo = self.slot_combos[slot_type]

            # カテゴリー選択の場合は装備コンボボックスをクリア
            if index == 0:
                equipment_combo.clear()
                equipment_combo.addItem("選択する")
                return

            # 選択されたカテゴリー
            category = category_combo.currentText()

            # 装備コンボボックスをカテゴリーに合わせて更新
            equipment_combo.clear()
            equipment_combo.addItem("選択する")

            if self.app_controller:
                # 現在選択されている船体の排水量を取得
                displacement = 0
                if self.current_hull:
                    displacement = self.current_hull.get("weight", 0)

                # カテゴリーに対応する装備を取得
                equipments = self.app_controller.get_all_equipment(category)

                # 派生タイプを考慮して装備を表示
                for eq in equipments:
                    eq_id = eq.get('common', {}).get('ID', '')
                    eq_name = eq.get('common', {}).get('名前', '')

                    if eq_id and eq_name:
                        # 排水量による派生タイプを考慮（将来的な実装）
                        # 現在は通常の装備をそのまま表示
                        equipment_combo.addItem(f"{eq_name} ({eq_id})")

        except Exception as e:
            print(f"スロットカテゴリー変更エラー: {e}")

    def select_hull(self):
        """船体選択ダイアログを表示"""
        if not self.app_controller:
            QMessageBox.warning(self, "エラー", "アプリケーションコントローラーが設定されていません。")
            return

        try:
            # app_controllerから船体リストを取得
            hulls = self.app_controller.get_all_hulls()

            if not hulls:
                QMessageBox.information(self, "情報", "船体データがありません。先に船体を登録してください。")
                return

            # 船体選択ダイアログを表示
            dialog = QDialog(self)
            dialog.setWindowTitle("船体選択")
            dialog.setMinimumWidth(500)
            dialog.setMinimumHeight(300)

            dialog_layout = QVBoxLayout()

            # 船体一覧テーブル
            hull_table = QTableWidget()
            hull_table.setColumnCount(4)  # ID, 艦級名, 種別, 排水量
            hull_table.setHorizontalHeaderLabels(["ID", "艦級名", "種別", "排水量"])
            hull_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # 艦級名列を拡大

            # 船体データをテーブルに追加
            for i, hull in enumerate(hulls):
                hull_table.insertRow(i)
                hull_table.setItem(i, 0, QTableWidgetItem(hull.get("id", "")))
                hull_table.setItem(i, 1, QTableWidgetItem(hull.get("name", "")))
                hull_table.setItem(i, 2, QTableWidgetItem(hull.get("type", "")))
                hull_table.setItem(i, 3, QTableWidgetItem(str(hull.get("weight", ""))))

            dialog_layout.addWidget(hull_table)

            button_layout = QHBoxLayout()
            select_button = QPushButton("選択")

            # 選択ボタンがクリックされたときの処理
            def on_select():
                current_row = hull_table.currentRow()
                if current_row >= 0 and current_row < len(hulls):
                    self.on_hull_selected(hulls[current_row])
                    dialog.accept()
                else:
                    QMessageBox.warning(dialog, "警告", "船体を選択してください。")

            select_button.clicked.connect(on_select)
            button_layout.addWidget(select_button)

            cancel_button = QPushButton("キャンセル")
            cancel_button.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_button)

            dialog_layout.addLayout(button_layout)
            dialog.setLayout(dialog_layout)

            # ダブルクリックでも選択できるようにする
            hull_table.doubleClicked.connect(on_select)

            dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"船体データの取得中にエラーが発生しました: {e}")

    def on_hull_selected(self, hull_data):
        """船体が選択された時の処理"""
        try:
            self.current_hull = hull_data

            # 船体名を表示
            self.selected_hull_label.setText(hull_data.get("name", "不明"))

            # 艦級名フィールドにデフォルト値を設定
            self.design_name_edit.setText(hull_data.get("name", "") + " 級")

            # 艦種コンボボックスを更新
            ship_type = hull_data.get("type", "")
            index = self.ship_type_combo.findText(ship_type)
            if index >= 0:
                self.ship_type_combo.setCurrentIndex(index)

            # 船体基礎情報を更新
            self.update_hull_info(hull_data)

            # スロット情報を取得し、開放状況に応じてUIを更新
            self.update_slot_availability()

            # 性能表示も更新（ただし今は計算なしでダミーデータ）
            # 性能計算部分はまだ実装していないためコメントアウト
            # self.update_stats(hull_data)

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"船体データの設定中にエラーが発生しました: {e}")

    def update_hull_info(self, hull_data):
        """船体基礎情報を更新"""
        try:
            # 船体情報を更新
            for key, (_, label) in self.hull_info_labels.items():
                value = hull_data.get(key, "-")

                # 特殊なフォーマット処理
                if key == "weight":
                    label.setText(f"{value}t")
                elif key == "length" or key == "width":
                    label.setText(f"{value}m")
                elif key == "power":
                    label.setText(f"{value}hp")
                elif key == "speed" or key == "cruise_speed":
                    label.setText(f"{value}kn")
                elif key == "range":
                    label.setText(f"{value}km")
                elif key == "fuel_capacity":
                    label.setText(f"{value}t")
                elif key == "armor_max" or key == "armor_min":
                    label.setText(f"{value}mm")
                elif key == "crew":
                    label.setText(f"{value}名")
                else:
                    label.setText(str(value))

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"船体情報の更新中にエラーが発生しました: {e}")

    def update_slot_availability(self):
        """スロットの開放状況を更新"""
        try:
            # 船体が選択されていない場合は何もしない
            if not self.current_hull:
                return

            # スロット状態を船体データから取得
            slots = self.current_hull.get("slots", {})

            # 各スロットの有効/無効を確認
            for slot_type in ["PA", "SA", "PSA", "SSA", "PLA", "SLA"]:
                category_combo = self.slot_category_combos[slot_type]
                equipment_combo = self.slot_combos[slot_type]

                # スロットの状態を確認
                slot_status = slots.get(slot_type, " ")

                if slot_status == "-":
                    # 無効なスロット
                    category_combo.setEnabled(False)
                    equipment_combo.setEnabled(False)

                    # グレーアウト表示
                    palette = category_combo.palette()
                    palette.setColor(QPalette.Base, QColor(200, 200, 200))  # 淡いグレー
                    category_combo.setPalette(palette)
                    equipment_combo.setPalette(palette)

                    # デフォルトテキスト
                    category_combo.clear()
                    category_combo.addItem("(使用不可)")
                    equipment_combo.clear()
                    equipment_combo.addItem("(使用不可)")
                elif slot_status == "=":
                    # 有効化可能なスロット
                    category_combo.setEnabled(True)
                    equipment_combo.setEnabled(True)

                    # デフォルトパレットに戻す
                    category_combo.setPalette(QPalette())
                    equipment_combo.setPalette(QPalette())

                    # 初期化
                    if category_combo.currentIndex() == 0:
                        self.load_equipment_categories()  # カテゴリーを再ロード
                    equipment_combo.clear()
                    equipment_combo.addItem("(有効化可能)")
                else:
                    # 有効なスロット
                    category_combo.setEnabled(True)
                    equipment_combo.setEnabled(True)

                    # デフォルトパレットに戻す
                    category_combo.setPalette(QPalette())
                    equipment_combo.setPalette(QPalette())

                    # 初期化
                    if category_combo.currentIndex() == 0:
                        self.load_equipment_categories()  # カテゴリーを再ロード
                    equipment_combo.clear()
                    equipment_combo.addItem("選択する")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"スロット情報の更新中にエラーが発生しました: {e}")

    def add_internal_slot(self):
        """内部スロットの追加"""
        # 現時点では実装保留
        QMessageBox.information(self, "情報", "内部スロット追加機能は現在開発中です。")

    def remove_internal_slot(self):
        """内部スロットの削除"""
        # 現時点では実装保留
        QMessageBox.information(self, "情報", "内部スロット削除機能は現在開発中です。")

    def save_design(self):
        """設計の保存"""
        # 船体が選択されていない場合はエラー
        if not self.current_hull:
            QMessageBox.warning(self, "警告", "船体が選択されていません。")
            return

        # 艦級名が入力されていない場合はエラー
        design_name = self.design_name_edit.text().strip()
        if not design_name:
            QMessageBox.warning(self, "警告", "艦級名を入力してください。")
            return

        try:
            # 設計データの構築
            design_data = {
                "design_name": design_name,
                "ship_type": self.ship_type_combo.currentText(),
                "hull_id": self.current_hull.get("id", ""),
                "hull_name": self.current_hull.get("name", ""),
                "slots": {},
                "slot_categories": {},  # スロットに割り当てられたカテゴリー
                "internal_slots": []
            }

            # スロット装備とカテゴリーの取得
            for slot_type in ["PA", "SA", "PSA", "SSA", "PLA", "SLA"]:
                category_combo = self.slot_category_combos[slot_type]
                equipment_combo = self.slot_combos[slot_type]

                # カテゴリーが選択されている場合は保存
                if category_combo.currentIndex() > 0:
                    category = category_combo.currentText()
                    design_data["slot_categories"][slot_type] = category

                # 装備が選択されている場合は保存
                current_text = equipment_combo.currentText()
                if current_text != "選択する" and "使用不可" not in current_text and "有効化可能" not in current_text:
                    # 括弧内のIDを抽出（例: "装備名 (ID)"）
                    import re
                    id_match = re.search(r'\(([^)]+)\)', current_text)
                    if id_match:
                        equipment_id = id_match.group(1)
                        design_data["slots"][slot_type] = equipment_id

            # 排水量による派生タイプの保存
            design_data["displacement"] = self.current_hull.get("weight", 0)

            # コントローラーを使用して保存
            if self.app_controller:
                success = self.app_controller.save_design(design_data)
                if success:
                    QMessageBox.information(self, "保存成功", f"艦級「{design_name}」の設計を保存しました。")
                else:
                    QMessageBox.critical(self, "保存エラー", "設計の保存に失敗しました。")
            else:
                QMessageBox.warning(self, "警告", "アプリケーションコントローラーが設定されていません。")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設計の保存中にエラーが発生しました: {e}")

    def load_design(self):
        """設計の読み込み"""
        if not self.app_controller:
            QMessageBox.warning(self, "警告", "アプリケーションコントローラーが設定されていません。")
            return

        try:
            # 全ての設計データを取得
            designs = self.app_controller.get_all_designs()

            if not designs:
                QMessageBox.information(self, "情報", "保存された設計データがありません。")
                return

            # 設計選択ダイアログを表示
            dialog = QDialog(self)
            dialog.setWindowTitle("設計選択")
            dialog.setMinimumWidth(500)
            dialog.setMinimumHeight(300)

            dialog_layout = QVBoxLayout()

            # 設計一覧テーブル
            design_table = QTableWidget()
            design_table.setColumnCount(4)  # ID, 艦級名, 船体, 艦種
            design_table.setHorizontalHeaderLabels(["ID", "艦級名", "船体", "艦種"])
            design_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # 艦級名列を拡大

            # 設計データをテーブルに追加
            for i, design in enumerate(designs):
                design_table.insertRow(i)
                design_table.setItem(i, 0, QTableWidgetItem(design.get("id", "")))
                design_table.setItem(i, 1, QTableWidgetItem(design.get("design_name", "")))
                design_table.setItem(i, 2, QTableWidgetItem(design.get("hull_name", "")))
                design_table.setItem(i, 3, QTableWidgetItem(design.get("ship_type", "")))

            dialog_layout.addWidget(design_table)

            button_layout = QHBoxLayout()
            select_button = QPushButton("選択")

            # 選択ボタンがクリックされたときの処理
            def on_select():
                current_row = design_table.currentRow()
                if current_row >= 0 and current_row < len(designs):
                    self.load_design_data(designs[current_row])
                    dialog.accept()
                else:
                    QMessageBox.warning(dialog, "警告", "設計を選択してください。")

            select_button.clicked.connect(on_select)
            button_layout.addWidget(select_button)

            cancel_button = QPushButton("キャンセル")
            cancel_button.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_button)

            dialog_layout.addLayout(button_layout)
            dialog.setLayout(dialog_layout)

            # ダブルクリックでも選択できるようにする
            design_table.doubleClicked.connect(on_select)

            dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設計データの取得中にエラーが発生しました: {e}")

    def load_design_data(self, design_data):
        """設計データを読み込んで画面に反映"""
        try:
            # 船体データを読み込み
            hull_id = design_data.get("hull_id", "")
            if hull_id and self.app_controller:
                hull_data = self.app_controller.load_hull(hull_id)
                if hull_data:
                    # 船体を選択
                    self.current_hull = hull_data
                    self.selected_hull_label.setText(hull_data.get("name", "不明"))

                    # 艦級名を設定
                    self.design_name_edit.setText(design_data.get("design_name", ""))

                    # 艦種を更新
                    ship_type = design_data.get("ship_type", "")
                    index = self.ship_type_combo.findText(ship_type)
                    if index >= 0:
                        self.ship_type_combo.setCurrentIndex(index)

                    # 船体基礎情報を更新
                    self.update_hull_info(hull_data)

                    # スロット開放状況を更新
                    self.update_slot_availability()

                    # カテゴリーと装備を設定
                    self.set_slot_categories(design_data.get("slot_categories", {}))
                    self.set_slot_equipment(design_data.get("slots", {}))

                    # 性能表示を更新
                    # self.update_stats()

                    QMessageBox.information(self, "読み込み完了", f"艦級「{design_data.get('design_name', '')}」の設計を読み込みました。")
                else:
                    QMessageBox.warning(self, "警告", f"船体ID '{hull_id}' のデータが見つかりません。")
            else:
                QMessageBox.warning(self, "警告", "有効な船体IDがありません。")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設計データの読み込み中にエラーが発生しました: {e}")

    def set_slot_categories(self, slot_categories):
        """スロットカテゴリーを設定"""
        for slot_type, category in slot_categories.items():
            if slot_type in self.slot_category_combos:
                combo = self.slot_category_combos[slot_type]
                index = combo.findText(category)
                if index >= 0:
                    combo.setCurrentIndex(index)
                    # カテゴリー変更イベントを発火
                    self.on_slot_category_changed(slot_type, index)

    def set_slot_equipment(self, slots):
        """スロット装備を設定"""
        for slot_type, equipment_id in slots.items():
            if slot_type in self.slot_combos and self.app_controller:
                combo = self.slot_combos[slot_type]

                # 装備データを取得
                equipment_data = self.app_controller.load_equipment(equipment_id)
                if equipment_data:
                    equipment_name = equipment_data.get('common', {}).get('名前', '')

                    # 装備名とIDを組み合わせたテキスト
                    text = f"{equipment_name} ({equipment_id})"

                    # コンボボックスで検索
                    index = combo.findText(text)
                    if index >= 0:
                        combo.setCurrentIndex(index)

    def close_design(self):
        """設計画面を閉じる"""
        reply = QMessageBox.question(self, "確認", "設計画面を閉じますか？\n保存していない変更は失われます。",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            # 親ウィンドウのホーム画面などに戻る
            if self.parent() and hasattr(self.parent(), 'show_view'):
                self.parent().show_view("home")

    def update_stats(self, hull_data=None):
        """設計性能を計算して表示を更新する

        注: この機能は将来実装される予定です
        """
        # 現時点では実装保留
        # 後で実装される性能計算機能のための枠組みのみ提供
        pass