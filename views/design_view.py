# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: design_viewビュー
from typing import Dict, Any

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
                             QLabel, QLineEdit, QComboBox, QPushButton, QGroupBox,
                             QDialog, QListWidget, QTableWidget, QTableWidgetItem,
                             QScrollArea, QMessageBox, QHeaderView, QListWidgetItem,
                             QCheckBox, QSlider)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QPalette
from utils.path_utils import get_data_dir
from utils.ship_icon_manager import ShipIconManager
from utils.web_search_widget import WebSearchButton
from utils.ship_role_constraints import get_ship_type_from_role_display


class DesignView(QWidget):
    def __init__(self, parent=None, app_controller=None, hull_data=None):
        super().__init__(parent)
        # app_controllerがNoneの場合、親ウィンドウから取得を試みる
        if app_controller is None and parent is not None:
            if hasattr(parent, 'app_controller'):
                app_controller = parent.app_controller
            elif hasattr(parent, 'parent') and hasattr(parent.parent(), 'app_controller'):
                app_controller = parent.parent().app_controller
        
        self.app_controller = app_controller
        if self.app_controller is None:
            print("警告: app_controllerが設定されていません。")
            
        self.current_hull = None  # 現在選択されている船体データ
        self.stats_labels = {}    # 性能ラベル用の辞書を初期化
        self.internal_slots = []  # 内部スロットのリストを初期化
        self.slot_category_selections = {}  # スロットカテゴリー選択を初期化
        self.stat_widgets: Dict[str, Dict[str, QWidget]] = {}

        # 装備表示用の年代フィルタ（デフォルトは +10 / -25 年）
        self.year_range_plus = 10
        self.year_range_minus = 25

        # アイコンマネージャーを追加
        self.ship_icon_manager = ShipIconManager()
        self.ship_icon_manager.ensure_default_icons()

        self.initUI()

        # 船体データが渡された場合は初期化
        if hull_data:
            self.on_hull_selected(hull_data)
    
    def update_search_query(self, archetype_text):
        """archetype選択に基づいて検索クエリを更新"""
        if archetype_text and archetype_text != "選択してください":
            # archetypeから英語検索用語へのマッピング
            archetype_search_mapping = {
                "BB": "battleship",
                "BC": "battlecruiser", 
                "CA": "heavy cruiser",
                "CL": "light cruiser",
                "DD": "destroyer",
                "CV": "aircraft carrier",
                "CVL": "light carrier",
                "SS": "submarine",
                "SF": "fleet submarine",
                "FF": "frigate",
                "DE": "destroyer escort"
            }
            
            english_type = archetype_search_mapping.get(archetype_text, archetype_text.lower())
            search_query = f"{english_type} warship design"
            self.web_search_button.set_default_search(search_query)

    def initUI(self):
        # メインレイアウト
        main_layout = QVBoxLayout(self)

        # 上部：艦種と船体選択
        top_layout = QHBoxLayout()

        # 艦種選択（archetype対応版）
        ship_type_layout = QHBoxLayout()
        ship_type_layout.addWidget(QLabel("艦種 ▷"))
        self.ship_type_combo = QComboBox()
        
        # archetypeの選択肢を追加（アイコン付き）
        self.ship_type_combo.addItem("選択してください")
        
        # pdx_toolsからarchetypeのリストを取得してアイコン付きで追加
        import pdx_tools.pdx_ssw
        for archetype in pdx_tools.pdx_ssw.ship_types:
            # archetypeに対応するアイコンを取得
            icon = self.ship_icon_manager.get_ship_icon(archetype, QSize(24, 24))
            # 表示名は archetype をそのまま使用
            self.ship_type_combo.addItem(icon, archetype, archetype)

        ship_type_layout.addWidget(self.ship_type_combo)
        top_layout.addLayout(ship_type_layout)

        # スペーサー
        top_layout.addStretch()
        
        # Web検索ボタン
        self.web_search_button = WebSearchButton(self, "warship design")
        top_layout.addWidget(self.web_search_button)
        
        # 艦種変更時に検索クエリを更新
        self.ship_type_combo.currentTextChanged.connect(self.update_search_query)

        # 船体選択
        hull_layout = QHBoxLayout()
        hull_layout.addWidget(QLabel("船体 ▷"))
        self.hull_select_button = QPushButton("選択する")
        self.hull_select_button.clicked.connect(self.select_hull)
        hull_layout.addWidget(self.hull_select_button)
        top_layout.addLayout(hull_layout)

        main_layout.addLayout(top_layout)

        # 船体表示（アイコン対応）
        hull_info_layout = QHBoxLayout()
        
        # 船体アイコン表示用ラベル
        self.hull_icon_label = QLabel()
        self.hull_icon_label.setFixedSize(32, 32)
        self.hull_icon_label.setStyleSheet("border: 1px solid gray; background-color: white;")
        hull_info_layout.addWidget(self.hull_icon_label)
        
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
        slots_container = QWidget()
        slots_layout = QVBoxLayout(slots_container)

        # プレイヤースロット部分
        player_slots_group = QGroupBox("プレイヤー設定可能スロット (6枠固定)")
        player_slots_layout = QVBoxLayout()

        # スロット定義
        slot_types = ["PA", "SA", "PSA", "SSA", "PLA", "SLA"]
        self.slot_combos = {}
        self.slot_category_combos = {}

        for slot_type in slot_types:
            slot_layout = QHBoxLayout()
            slot_layout.addWidget(QLabel(f"スロット {slot_type} ▷"))

            # カテゴリー選択ボタン
            category_button = QPushButton("カテゴリー選択")
            category_button.setFixedWidth(120)
            category_button.clicked.connect(
                lambda _, s_type=slot_type: self.show_category_selection_dialog(s_type)
            )
            slot_layout.addWidget(category_button)
            self.slot_category_combos[slot_type] = category_button

            # 装備選択コンボボックス
            equipment_combo = QComboBox()
            equipment_combo.addItem("選択する")
            self.slot_combos[slot_type] = equipment_combo
            slot_layout.addWidget(equipment_combo)

            player_slots_layout.addLayout(slot_layout)

        player_slots_group.setLayout(player_slots_layout)
        slots_layout.addWidget(player_slots_group)

        # 内部スロット部分（ゲーム内部の設定）
        internal_slots_group = QGroupBox("内部スロット設定")
        internal_slots_layout = QVBoxLayout()

        # 内部スロットの説明
        internal_slots_layout.addWidget(QLabel("内部スロットはゲーム内部の設定に使用します"))

        # 内部スロットの操作ボタン
        button_layout = QHBoxLayout()
        add_button = QPushButton("+ 追加")
        add_button.clicked.connect(self.add_internal_slot)
        button_layout.addWidget(add_button)

        remove_button = QPushButton("- 削除")
        remove_button.clicked.connect(self.remove_internal_slot)
        button_layout.addWidget(remove_button)

        button_layout.addStretch()
        internal_slots_layout.addLayout(button_layout)

        # 内部スロットの表示エリア
        internal_slots_scroll = QScrollArea()
        internal_slots_scroll.setWidgetResizable(True)
        # 入力欄のキー入力がスクロールエリアに奪われないようにする
        internal_slots_scroll.setFocusPolicy(Qt.NoFocus)
        internal_slots_scroll.viewport().setFocusPolicy(Qt.NoFocus)

        self.internal_slots_container = QWidget()
        self.internal_slots_grid = QGridLayout(self.internal_slots_container)
        self.internal_slots_grid.setSpacing(5)

        internal_slots_scroll.setWidget(self.internal_slots_container)
        internal_slots_layout.addWidget(internal_slots_scroll)

        internal_slots_group.setLayout(internal_slots_layout)
        slots_layout.addWidget(internal_slots_group)

        # スロット部分をスクロール可能に
        slots_scroll = QScrollArea()
        slots_scroll.setWidgetResizable(True)
        # 入力欄のキー入力がスクロールエリアに奪われないようにする
        slots_scroll.setFocusPolicy(Qt.NoFocus)
        slots_scroll.viewport().setFocusPolicy(Qt.NoFocus)
        slots_scroll.setWidget(slots_container)
        slots_scroll.setMinimumWidth(400)  # 最小幅を設定
        slots_scroll.setMaximumWidth(600)  # 最大幅を設定

        central_layout.addWidget(slots_scroll)

        # 右側：性能表示
        # 性能表示部分の初期化を変更
        stats_group = QGroupBox("性能表示")
        self.stats_layout = QGridLayout()
        stats_group.setLayout(self.stats_layout)
        stats_group.setMinimumWidth(300)

        # 初期表示を行う
        self.update_stats_display()

        # グリッドに配置
        stats_items = list(self.stats_labels.items())
        mid_point = (len(stats_items) + 1) // 2
        for i, (key, (name, label)) in enumerate(stats_items):
            row = i % mid_point
            col = i // mid_point * 2  # 間隔を空けるため*2
            self.stats_layout.addWidget(QLabel(f"{name}:"), row, col)
            self.stats_layout.addWidget(label, row, col + 1)

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

    def update_stats_display(self, design_data: Dict[str, Any] = None):
        """
        ステータス表示を動的に更新

        Args:
            design_data: 現在の設計データ
        """
        global all_crew
        try:
            # 既存のウィジェットをクリア
            while self.stats_layout.count():
                child = self.stats_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            self.stat_widgets.clear()

            # AppControllerからステータス定義を取得
            if not self.app_controller:
                print("警告: app_controllerが設定されていません")
                return

            status_definitions = self.app_controller._get_default_status_definitions()

            # 設計データがある場合は実際の値を取得
            stats_values = {}
            if design_data:
                stats_values = self.app_controller.get_design_stats(design_data)
            else:
                # デフォルト値を取得
                stats_values = self.app_controller.get_design_stats(None)

            # 船体重量を取得（重量比率表示用）
            hull_weight = 0.0
            if design_data and 'hull' in design_data:
                hull_weight = float(design_data['hull'].get('weight', 0))
                #hull_weightは[t]なので[kg]に変換
                hull_weight *= 1000.0  # トンからキログラムに変換
            # 人員数を取得
            all_crew = 0
            if design_data and 'hull' in design_data:
                all_crew = design_data['hull'].get('crew', 0)
                stats_values['crew'] = all_crew


            # UI要素を動的に生成
            for i, stat_def in enumerate(status_definitions):
                stat_id = stat_def['id']
                japanese_name = stat_def['japanese']
                # english_name = stat_def['english']

                # ラベルの作成（新しい形式: 日本語名 (--English-- / ID)）
                label_text = f"{japanese_name} ( {stat_id})"
                label = QLabel(label_text + ":")
                label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

                # 値表示用ウィジェット
                value = stats_values.get(stat_id, 0)
                
                # 特別な表示形式を適用
                if stat_id == 'weight_ratio':
                    # 重量比率の特別表示
                    equipment_weight = stats_values.get('equipment_weight', 0)
                    if hull_weight > 0:
                        value_text = f"{equipment_weight/1000:.1f}t / {hull_weight/1000:.0f}t ({equipment_weight/hull_weight*100}%)"
                    else:
                        value_text = f"{equipment_weight/1000:.1f}t / 0t (0.0%)"
                    value_widget = QLabel(value_text)
                elif stat_id == 'equipment_weight':
                    # 装備重量の表示
                    value_text = f"{value:.1f}kg"
                    value_widget = QLabel(value_text)
                elif stat_id == 'manpower':
                    # 総人員数
                    # 人員の表示
                    percentage = int(value/all_crew*100) if all_crew > 0 else 0
                    value_text = f"{int(value)}名({percentage}%)"
                    value_widget = QLabel(value_text)
                elif stat_id in ['lg_attack', 'hg_attack', 'lg_armor_piercing', 'hg_armor_piercing', 'anti_air_attack']:
                    # 砲系統ステータスの表示（小数点1位まで）
                    value_text = f"{value:.1f}"
                    value_widget = QLabel(value_text)
                elif stat_id == 'build_cost_ic':
                    # 建造コストの表示（整数）
                    value_text = f"{int(value)} IC"
                    value_widget = QLabel(value_text)
                elif isinstance(value, float):
                    # その他の数値（小数点2位まで）
                    value_text = f"{value:.2f}"
                    value_widget = QLabel(value_text)
                else:
                    # その他
                    value_text = str(value)
                    value_widget = QLabel(value_text)
                
                value_widget.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                value_widget.setStyleSheet("QLabel { border: 1px solid gray; padding: 2px; background-color: white; }")

                # レイアウトに追加（2列表示）
                col_pair = i // 15  # 15行ごとに新しい列ペア
                row = i % 15
                col_offset = col_pair * 2

                self.stats_layout.addWidget(label, row, col_offset)
                self.stats_layout.addWidget(value_widget, row, col_offset + 1)

                # ウィジェット参照を保存
                self.stat_widgets[stat_id] = {
                    'label': label,
                    'value': value_widget
                }

            print(f"ステータス表示を更新しました（{len(status_definitions)}項目）")

        except Exception as e:
            print(f"ステータス表示更新エラー: {e}")
            import traceback
            traceback.print_exc()

    def load_equipment_categories(self):
        """装備カテゴリーを読み込む"""
        try:
            # カテゴリー選択状態をリセット
            if hasattr(self, 'slot_category_selections'):
                self.slot_category_selections.clear()

            # 全スロットのカテゴリーボタンを初期化
            for slot_type in ["PA", "SA", "PSA", "SSA", "PLA", "SLA"]:
                if slot_type in self.slot_category_combos:
                    button = self.slot_category_combos[slot_type]
                    # QPushButtonの場合は、テキストのみ設定
                    button.setText("カテゴリー選択")
                
                # 装備選択コンボボックスも初期化
                if slot_type in self.slot_combos:
                    combo = self.slot_combos[slot_type]
                    combo.clear()
                    combo.addItem("選択する")

            # 内部スロットがある場合も同様に処理
            if hasattr(self, 'internal_slots'):
                for slot_info in self.internal_slots:
                    slot_id = slot_info.get("id")
                    if slot_id:
                        # カテゴリーボタンの初期化
                        if "category_button" in slot_info:
                            slot_info["category_button"].setText("カテゴリー選択")
                        
                        # 装備コンボボックスの初期化
                        if "equipment_combo" in slot_info:
                            combo = slot_info["equipment_combo"]
                            combo.clear()
                            combo.addItem("選択する")
                            
        except Exception as e:
            print(f"装備カテゴリー読み込みエラー: {e}")
            import traceback
            traceback.print_exc()

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
        """船体選択ダイアログを表示（アイコン対応版）"""
        try:
            # 艦種でフィルタリング
            selected_ship_type_index = self.ship_type_combo.currentIndex()
            if selected_ship_type_index <= 0:
                # 艦種が選択されていない場合は、最初の有効な艦種を選択
                for i in range(1, self.ship_type_combo.count()):
                    self.ship_type_combo.setCurrentIndex(i)
                    selected_ship_type_index = i
                    break

            # 選択されたarchetypeの情報を取得
            selected_archetype_data = self.ship_type_combo.itemData(selected_ship_type_index)
            selected_archetype_text = self.ship_type_combo.itemText(selected_ship_type_index)

            # JSONファイルから直接船体データを読み込む
            import os
            import json

            # データディレクトリのパスを取得
            hulls_dir = get_data_dir('hulls')

            # 船体データを格納するリスト
            hulls = []

            # ディレクトリ内のJSONファイルを読み込む
            if os.path.exists(hulls_dir):
                for file_name in os.listdir(hulls_dir):
                    if file_name.endswith('.json'):
                        file_path = os.path.join(hulls_dir, file_name)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                hull_data = json.load(f)
                                hulls.append(hull_data)
                        except Exception as e:
                            print(f"船体データ読み込みエラー ({file_name}): {e}")

            if not hulls:
                QMessageBox.information(self, "情報", "船体データがありません。先に船体を登録してください。")
                return

            # 選択されたarchetypeでフィルタリング（制約適用）
            filtered_hulls = []
            
            # 選択されたarchetypeのIDでSHIP_ROLE_CONSTRAINTSから利用可能なship_typeリストを取得
            from utils.ship_role_constraints import get_ship_types_for_role
            
            # 表示名からIDを抽出（例: "BB - 一等戦艦" → "BB"）
            print(f"デバッグ: selected_archetype_text='{selected_archetype_text}'")
            print(f"デバッグ: selected_archetype_data='{selected_archetype_data}'")
            
            # pdx_tools.pdx_ssw.ship_typesが表示名を返している場合、IDを抽出
            if selected_archetype_data and selected_archetype_data != selected_archetype_text:
                selected_archetype_id = selected_archetype_data
            else:
                # 表示名からIDを抽出（"BB - 一等戦艦" → "BB"）
                if " - " in selected_archetype_text:
                    selected_archetype_id = selected_archetype_text.split(" - ")[0]
                else:
                    selected_archetype_id = selected_archetype_text
            
            if not selected_archetype_id or selected_archetype_id == "選択してください":
                print("選択されたarchetypeが無効です")
                return
                
            allowed_ship_types = get_ship_types_for_role(selected_archetype_id)

            print(f"選択archetype表示名: '{selected_archetype_text}'")
            print(f"選択archetypeID: '{selected_archetype_id}'")
            print(f"利用可能なship_type: {allowed_ship_types}")
            
            for hull in hulls:
                hull_type = hull.get("type", "")
                hull_archetype = hull.get("archetype", "")
                
                # 船体種別から略称を抽出
                hull_ship_type = get_ship_type_from_role_display(hull_type)
                
                # 制約チェック: 船体のtypeが選択されたarchetypeで利用可能なship_typeに含まれているか
                type_allowed = hull_ship_type in allowed_ship_types
                
                print(f"デバッグ: {hull.get('name', '不明')} - ship_type: {hull_ship_type}, archetype: {hull_archetype}")
                print(f"  選択archetypeID '{selected_archetype_id}' で利用可能なship_type: {allowed_ship_types}")
                print(f"  船体のship_type '{hull_ship_type}' が許可されているか: {type_allowed}")
                
                if type_allowed:
                    filtered_hulls.append(hull)
                    print(f"適合: {hull.get('name', '不明')} (ship_type: {hull_ship_type}, archetype: {hull_archetype})")
                else:
                    print(f"除外: {hull.get('name', '不明')} - "
                          f"type許可: {type_allowed} "
                          f"(ship_type: {hull_ship_type}, archetype: {hull_archetype})")

            if not filtered_hulls:
                QMessageBox.information(self, "情報", f"選択されたarchetype「{selected_archetype_text}」の船体データがありません。")
                return

            # 船体選択ダイアログを表示（アイコン対応版）
            dialog = QDialog(self)
            dialog.setWindowTitle(f"船体選択 - {selected_archetype_text}")
            dialog.setMinimumWidth(600)
            dialog.setMinimumHeight(400)

            dialog_layout = QVBoxLayout()

            # 船体一覧テーブル（アイコン列を追加）
            hull_table = QTableWidget()
            hull_table.setColumnCount(5)  # アイコン, ID, 艦級名, 種別, 排水量
            hull_table.setHorizontalHeaderLabels(["アイコン", "ID", "艦級名", "種別", "排水量"])
            hull_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)  # 艦級名列を拡大
            hull_table.setColumnWidth(0, 60)  # アイコン列の幅を固定

            # 船体データをテーブルに追加
            for i, hull in enumerate(filtered_hulls):
                hull_table.insertRow(i)
                
                # アイコンセル
                icon_item = QTableWidgetItem()
                hull_type = hull.get("type", "")
                if hull_type:
                    hull_icon = self.ship_icon_manager.get_ship_icon(hull_type, QSize(32, 32))
                    icon_item.setIcon(hull_icon)
                hull_table.setItem(i, 0, icon_item)
                
                # その他のセル
                hull_table.setItem(i, 1, QTableWidgetItem(hull.get("id", "")))
                hull_table.setItem(i, 2, QTableWidgetItem(hull.get("name", "")))
                hull_table.setItem(i, 3, QTableWidgetItem(hull.get("type", "")))
                hull_table.setItem(i, 4, QTableWidgetItem(str(hull.get("weight", ""))))

            dialog_layout.addWidget(hull_table)

            button_layout = QHBoxLayout()
            select_button = QPushButton("選択")

            # 選択ボタンがクリックされたときの処理
            def on_select():
                current_row = hull_table.currentRow()
                if current_row >= 0 and current_row < len(filtered_hulls):
                    self.on_hull_selected(filtered_hulls[current_row])
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
            import traceback
            traceback.print_exc()

    def on_hull_selected(self, hull_data):
        """船体が選択された時の処理（アイコン対応版）"""
        try:
            self.current_hull = hull_data

            # 船体名を表示
            hull_name = hull_data.get("name", "不明")
            self.selected_hull_label.setText(hull_name)

            # 船体アイコンを表示
            hull_type = hull_data.get("type", "")
            if hull_type:
                hull_icon = self.ship_icon_manager.get_ship_icon(hull_type, QSize(32, 32))
                self.hull_icon_label.setPixmap(hull_icon.pixmap(32, 32))
            else:
                # デフォルトアイコン
                self.hull_icon_label.clear()
                self.hull_icon_label.setText("?")

            # 艦級名フィールドにデフォルト値を設定
            self.design_name_edit.setText(hull_name)

            # archetypeコンボボックスを更新
            hull_archetype = hull_data.get("archetype", "")
            for i in range(self.ship_type_combo.count()):
                item_data = self.ship_type_combo.itemData(i)
                if item_data == hull_archetype:
                    self.ship_type_combo.setCurrentIndex(i)
                    break
                # 表示名での一致も試行
                item_text = self.ship_type_combo.itemText(i)
                if item_text == hull_archetype:
                    self.ship_type_combo.setCurrentIndex(i)
                    break

            # 船体基礎情報を更新
            self.update_hull_info(hull_data)

            # スロット情報を取得し、開放状況に応じてUIを更新
            self.update_slot_availability()

            # デフォルト内部スロットを自動追加
            self.ensure_default_internal_slots()

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
                category_button = self.slot_category_combos[slot_type]
                equipment_combo = self.slot_combos[slot_type]

                # スロットの状態を確認
                slot_status = slots.get(slot_type, " ")

                if slot_status == "-":
                    # 無効なスロット
                    category_button.setEnabled(False)
                    equipment_combo.setEnabled(False)

                    # グレーアウト表示
                    palette = category_button.palette()
                    palette.setColor(QPalette.Base, QColor(200, 200, 200))  # 淡いグレー
                    category_button.setPalette(palette)
                    equipment_combo.setPalette(palette)

                    # デフォルトテキスト
                    category_button.setText("(使用不可)")
                    equipment_combo.clear()
                    equipment_combo.addItem("(使用不可)")
                elif slot_status == "=":
                    # 有効化可能なスロット
                    category_button.setEnabled(True)
                    equipment_combo.setEnabled(True)

                    # デフォルトパレットに戻す
                    category_button.setPalette(QPalette())
                    equipment_combo.setPalette(QPalette())

                    # 初期化
                    category_button.setText("カテゴリー選択")
                    equipment_combo.clear()
                    equipment_combo.addItem("(有効化可能)")
                else:
                    # 有効なスロット
                    category_button.setEnabled(True)
                    equipment_combo.setEnabled(True)

                    # デフォルトパレットに戻す
                    category_button.setPalette(QPalette())
                    equipment_combo.setPalette(QPalette())

                    # 初期化
                    category_button.setText("カテゴリー選択")
                    equipment_combo.clear()
                    equipment_combo.addItem("選択する")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"スロット情報の更新中にエラーが発生しました: {e}")

    def load_design(self):
        """設計の読み込み"""
        try:
            import os
            import json

            # 設計データのディレクトリパス
            base_dir = get_data_dir('designs')

            # ディレクトリが存在しない場合はエラー
            if not os.path.exists(base_dir):
                QMessageBox.warning(self, "警告", "設計データのディレクトリが存在しません。")
                return

            # 設計ファイルの一覧を取得
            design_files = [f for f in os.listdir(base_dir) if f.endswith('.json')]

            if not design_files:
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

            # 設計データをテーブルに追加（ヘッダーチェック付き）
            designs = []
            from utils.design_file_validator import load_design_file_with_validation
            skipped_count = 0
            
            for file_name in design_files:
                try:
                    file_path = os.path.join(base_dir, file_name)
                    design_data = load_design_file_with_validation(file_path)
                    
                    if design_data is not None:
                        designs.append(design_data)

                        # テーブルに行を追加
                        row = design_table.rowCount()
                        design_table.insertRow(row)
                        design_table.setItem(row, 0, QTableWidgetItem(design_data.get("id", "")))
                        design_table.setItem(row, 1, QTableWidgetItem(design_data.get("design_name", "")))
                        design_table.setItem(row, 2, QTableWidgetItem(design_data.get("hull_name", "")))
                        design_table.setItem(row, 3, QTableWidgetItem(design_data.get("ship_type", "")))
                    else:
                        skipped_count += 1
                        print(f"設計ファイルをスキップしました（ヘッダー不正）: {file_name}")
                except Exception as e:
                    skipped_count += 1
                    print(f"設計データ読み込みエラー ({file_name}): {e}")
            
            if skipped_count > 0:
                print(f"設計読み込み完了: {len(designs)}個のファイルを読み込み、{skipped_count}個をスキップしました")

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
            import traceback
            traceback.print_exc()

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

    def get_current_design_data(self) -> Dict[str, Any]:
        """現在の設計データを取得"""
        design_data = {}
        
        try:
            # 基本情報
            design_data['design_name'] = self.design_name_edit.text()
            design_data['ship_type'] = self.ship_type_combo.currentText()
            
            # 船体情報
            if self.current_hull:
                design_data['hull'] = self.current_hull
            
            # メインスロット情報
            design_data['main_slots'] = {}
            for slot_type in ["PA", "SA", "PSA", "SSA", "PLA", "SLA"]:
                if slot_type in self.slot_combos:
                    combo = self.slot_combos[slot_type]
                    current_text = combo.currentText()
                    if current_text != "選択する" and "使用不可" not in current_text:
                        # 装備IDを抽出
                        import re
                        id_match = re.search(r'\(([^)]+)\)', current_text)
                        if id_match:
                            design_data['main_slots'][slot_type] = id_match.group(1)
            
            # 内部スロット情報
            design_data['internal_slots'] = []
            for slot_info in self.internal_slots:
                slot_data = {
                    'slot_id': slot_info['id'],
                    'categories': self.slot_category_selections.get(slot_info['id'], []),
                    'equipment_id': None
                }
                
                # 選択された装備があれば取得（安全チェック付き）
                try:
                    combo = slot_info.get('equipment_combo')
                    if combo:
                        current_text = combo.currentText()
                        if current_text != "選択する":
                            import re
                            id_match = re.search(r'\(([^)]+)\)', current_text)
                            if id_match:
                                slot_data['equipment_id'] = id_match.group(1)
                except (RuntimeError, AttributeError):
                    # ウィジェットが削除されている場合は無視
                    pass
                
                design_data['internal_slots'].append(slot_data)
            
            return design_data
            
        except Exception as e:
            print(f"設計データ取得エラー: {e}")
            return {}

    def update_equipment_combo(self, slot_id):
        """装備コンボボックスを選択されたカテゴリーに基づいて更新"""
        try:
            if not hasattr(self, 'slot_category_selections') or slot_id not in self.slot_category_selections:
                return

            if slot_id not in self.slot_combos:
                return

            equipment_combo = self.slot_combos[slot_id]
            selected_categories = self.slot_category_selections[slot_id]

            # コンボボックスをクリア（安全チェック付き）
            try:
                if equipment_combo:
                    equipment_combo.clear()
                    equipment_combo.addItem("選択する")
                else:
                    return
            except (RuntimeError, AttributeError):
                return

            # カテゴリーが選択されていない場合は終了
            if not selected_categories:
                return

            # 該当するすべての装備を取得
            all_equipment = []

            for category in selected_categories:
                if self.app_controller:
                    # アプリコントローラーを使用して装備を取得
                    equipment_list = self.app_controller.get_all_equipment(category)
                    all_equipment.extend(equipment_list)
                else:
                    # 直接モデルを使用
                    try:
                        from models.equipment_model import EquipmentModel
                        equipment_model = EquipmentModel()
                        equipment_list = equipment_model.get_all_equipment(category)
                        all_equipment.extend(equipment_list)
                    except Exception as e:
                        print(f"装備データ取得エラー: {e}")

            # 船体の開発年に基づき装備をフィルタリング
            hull_year = 0
            if self.current_hull:
                hull_year = int(self.current_hull.get("year", 0))
            min_year = hull_year - getattr(self, "year_range_minus", 25)
            max_year = hull_year + getattr(self, "year_range_plus", 10)

            # 装備をコンボボックスに追加
            for equipment in all_equipment:
                eq_id = equipment.get('common', {}).get('ID', '')
                eq_name = equipment.get('common', {}).get('名前', '')
                eq_type = equipment.get('equipment_type', '')
                eq_year = equipment.get('common', {}).get('開発年')
                if eq_year is None:
                    eq_year = equipment.get('common', {}).get('year')
                try:
                    eq_year = int(eq_year)
                except (TypeError, ValueError):
                    eq_year = None

                if eq_year is not None and not (min_year <= eq_year <= max_year):
                    continue

                if eq_id and eq_name:
                    # 表示形式は「装備名 (ID) - カテゴリー」
                    display_text = f"{eq_name} ({eq_id}) - {eq_type}"
                    try:
                        equipment_combo.addItem(display_text)
                    except (RuntimeError, AttributeError):
                        continue

            # 装備選択変更時のイベントハンドラーを接続（安全チェック付き）
            try:
                equipment_combo.currentTextChanged.connect(
                    lambda: self.on_equipment_selection_changed(slot_id)
                )
            except (RuntimeError, AttributeError):
                pass

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"装備コンボボックス更新中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()

    def add_internal_slot(self):
        """内部スロットの追加"""
        try:
            # 内部スロットの最大数チェック
            if len(self.internal_slots) >= 50:  # 最大50個まで
                QMessageBox.warning(self, "警告", "内部スロットは最大50個までです。")
                return

            # 船体が選択されていない場合はエラー
            if not self.current_hull:
                QMessageBox.warning(self, "警告", "先に船体を選択してください。")
                return

            # 新しい内部スロットの表示行番号を計算
            row = len(self.internal_slots) // 2  # 2列表示の場合
            col = len(self.internal_slots) % 2 * 3  # 各スロットは3セル使用

            # スロット番号ラベル
            slot_num = len(self.internal_slots) + 1
            slot_label = QLabel(f"内部 {slot_num}:")
            self.internal_slots_grid.addWidget(slot_label, row, col)

            # カテゴリー選択ボタン
            slot_id = f"INT{slot_num}"
            category_button = QPushButton("カテゴリー選択")
            category_button.setFixedWidth(120)
            category_button.clicked.connect(
                lambda _, s_id=slot_id: self.show_category_selection_dialog(s_id)
            )
            self.internal_slots_grid.addWidget(category_button, row, col + 1)

            # 装備選択コンボボックス
            equipment_combo = QComboBox()
            equipment_combo.addItem("選択する")
            self.internal_slots_grid.addWidget(equipment_combo, row, col + 2)

            # 内部スロット情報を格納
            slot_info = {
                "id": slot_id,
                "category_button": category_button,
                "equipment_combo": equipment_combo,
                "selected_categories": [],  # 選択されたカテゴリーのリスト
                "label": slot_label
            }

            # スロットリストに追加
            self.internal_slots.append(slot_info)

            # 辞書にも追加してスロット操作を統一
            self.slot_category_combos[slot_id] = category_button
            self.slot_combos[slot_id] = equipment_combo

            print(f"内部スロット {slot_id} を追加しました。")

            # スロット追加後にステータス表示を更新
            current_design_data = self.get_current_design_data()
            self.update_stats_display(current_design_data)

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"内部スロット追加中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()

    def remove_internal_slot(self):
        """内部スロットの削除（選択可能）"""
        try:
            # 内部スロットがない場合は何もしない
            if not self.internal_slots:
                QMessageBox.information(self, "情報", "削除する内部スロットがありません。")
                return

            # 削除対象選択ダイアログを表示
            dialog = QDialog(self)
            dialog.setWindowTitle("削除するスロットを選択")
            dialog.setMinimumWidth(400)
            dialog.setMinimumHeight(300)

            layout = QVBoxLayout(dialog)
            layout.addWidget(QLabel("削除したい内部スロットを選択してください:"))

            # スロット一覧を表示
            slot_list = QListWidget()
            slot_list.setSelectionMode(QListWidget.MultiSelection)
            
            for i, slot_info in enumerate(self.internal_slots):
                slot_id = slot_info["id"]
                slot_num = i + 1
                
                # カテゴリー情報取得
                categories = []
                if hasattr(self, 'slot_category_selections') and slot_id in self.slot_category_selections:
                    categories = self.slot_category_selections[slot_id]
                
                # 装備情報取得（安全チェック付き）
                equipment_info = "なし"
                try:
                    equipment_combo = slot_info.get("equipment_combo")
                    if equipment_combo and not equipment_combo.isHidden():
                        equipment_text = equipment_combo.currentText()
                        if equipment_text != "選択する":
                            equipment_info = equipment_text
                except (RuntimeError, AttributeError):
                    # ウィジェットが削除されている場合は無視
                    equipment_info = "なし"
                
                # 表示テキスト作成
                display_text = f"内部 {slot_num} ({slot_id})"
                if categories:
                    display_text += f" - カテゴリー: {', '.join(categories[:2])}"
                    if len(categories) > 2:
                        display_text += f" (+{len(categories)-2}個)"
                
                if equipment_info != "なし":
                    # 装備名のみ表示（長すぎる場合は省略）
                    eq_name = equipment_info.split(' (')[0] if ' (' in equipment_info else equipment_info
                    if len(eq_name) > 20:
                        eq_name = eq_name[:17] + "..."
                    display_text += f" - 装備: {eq_name}"
                
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, i)  # インデックスを保存
                slot_list.addItem(item)

            layout.addWidget(slot_list)

            # ボタンレイアウト
            button_layout = QHBoxLayout()
            
            select_all_button = QPushButton("全選択")
            def select_all():
                for i in range(slot_list.count()):
                    slot_list.item(i).setSelected(True)
            select_all_button.clicked.connect(select_all)
            button_layout.addWidget(select_all_button)

            clear_selection_button = QPushButton("選択解除")
            def clear_selection():
                slot_list.clearSelection()
            clear_selection_button.clicked.connect(clear_selection)
            button_layout.addWidget(clear_selection_button)

            button_layout.addStretch()

            ok_button = QPushButton("削除")
            cancel_button = QPushButton("キャンセル")

            def on_delete():
                selected_items = slot_list.selectedItems()
                if not selected_items:
                    QMessageBox.warning(dialog, "警告", "削除するスロットを選択してください。")
                    return

                # 確認ダイアログ
                reply = QMessageBox.question(
                    dialog, 
                    "確認", 
                    f"{len(selected_items)}個のスロットを削除しますか？\n削除後は元に戻せません。",
                    QMessageBox.Yes | QMessageBox.No, 
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    # 選択されたインデックスを降順でソート（後ろから削除するため）
                    selected_indices = [item.data(Qt.UserRole) for item in selected_items]
                    selected_indices.sort(reverse=True)
                    
                    # 削除実行
                    deleted_count = 0
                    for index in selected_indices:
                        if 0 <= index < len(self.internal_slots):
                            slot_info = self.internal_slots[index]
                            
                            # UIから削除（安全チェック付き）
                            try:
                                if "label" in slot_info and slot_info["label"]:
                                    self.internal_slots_grid.removeWidget(slot_info["label"])
                                    slot_info["label"].deleteLater()
                            except (RuntimeError, AttributeError):
                                pass
                            
                            try:
                                if "category_button" in slot_info and slot_info["category_button"]:
                                    self.internal_slots_grid.removeWidget(slot_info["category_button"])
                                    slot_info["category_button"].deleteLater()
                            except (RuntimeError, AttributeError):
                                pass
                            
                            try:
                                if "equipment_combo" in slot_info and slot_info["equipment_combo"]:
                                    self.internal_slots_grid.removeWidget(slot_info["equipment_combo"])
                                    slot_info["equipment_combo"].deleteLater()
                            except (RuntimeError, AttributeError):
                                pass

                            # 辞書からも削除
                            slot_id = slot_info["id"]
                            if slot_id in self.slot_category_combos:
                                del self.slot_category_combos[slot_id]
                            if slot_id in self.slot_combos:
                                del self.slot_combos[slot_id]
                            if hasattr(self, 'slot_category_selections') and slot_id in self.slot_category_selections:
                                del self.slot_category_selections[slot_id]

                            # リストから削除
                            del self.internal_slots[index]
                            deleted_count += 1
                    
                    # スロット番号を再計算して表示を更新
                    self._refresh_internal_slots_display()
                    
                    # ステータス表示を更新
                    current_design_data = self.get_current_design_data()
                    self.update_stats_display(current_design_data)
                    
                    QMessageBox.information(dialog, "完了", f"{deleted_count}個のスロットを削除しました。")
                    dialog.accept()

            ok_button.clicked.connect(on_delete)
            cancel_button.clicked.connect(dialog.reject)

            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            
            layout.addLayout(button_layout)
            
            dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"内部スロット削除中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
    
    def _refresh_internal_slots_display(self):
        """内部スロットの表示を再描画"""
        try:
            # 既存のレイアウトをクリア
            while self.internal_slots_grid.count():
                child = self.internal_slots_grid.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            # スロットを再配置
            for i, slot_info in enumerate(self.internal_slots):
                row = i // 2  # 2列表示
                col = (i % 2) * 3  # 各スロットは3セル使用
                
                # スロット番号を更新（安全チェック付き）
                slot_num = i + 1
                try:
                    if "label" in slot_info and slot_info["label"]:
                        slot_info["label"].setText(f"内部 {slot_num}:")
                except (RuntimeError, AttributeError):
                    continue  # このスロットをスキップ
                
                # 新しいスロットIDを生成
                old_slot_id = slot_info["id"]
                new_slot_id = f"INT{slot_num}"
                slot_info["id"] = new_slot_id
                
                # 辞書のキーを更新
                if old_slot_id in self.slot_category_combos:
                    self.slot_category_combos[new_slot_id] = self.slot_category_combos.pop(old_slot_id)
                if old_slot_id in self.slot_combos:
                    self.slot_combos[new_slot_id] = self.slot_combos.pop(old_slot_id)
                if hasattr(self, 'slot_category_selections') and old_slot_id in self.slot_category_selections:
                    self.slot_category_selections[new_slot_id] = self.slot_category_selections.pop(old_slot_id)
                
                # カテゴリーボタンのクリックイベントを更新（安全チェック付き）
                try:
                    if "category_button" in slot_info and slot_info["category_button"]:
                        slot_info["category_button"].clicked.disconnect()
                        slot_info["category_button"].clicked.connect(
                            lambda _, s_id=new_slot_id: self.show_category_selection_dialog(s_id)
                        )
                except (RuntimeError, AttributeError):
                    pass
                
                # ウィジェットを再配置（安全チェック付き）
                try:
                    if "label" in slot_info and slot_info["label"]:
                        self.internal_slots_grid.addWidget(slot_info["label"], row, col)
                except (RuntimeError, AttributeError):
                    pass
                
                try:
                    if "category_button" in slot_info and slot_info["category_button"]:
                        self.internal_slots_grid.addWidget(slot_info["category_button"], row, col + 1)
                except (RuntimeError, AttributeError):
                    pass
                
                try:
                    if "equipment_combo" in slot_info and slot_info["equipment_combo"]:
                        self.internal_slots_grid.addWidget(slot_info["equipment_combo"], row, col + 2)
                except (RuntimeError, AttributeError):
                    pass
            
        except Exception as e:
            print(f"内部スロット表示更新エラー: {e}")
            import traceback
            traceback.print_exc()

    def ensure_default_internal_slots(self):
        """内部スロットが空の場合にセンサー系スロットを自動追加"""
        try:
            if self.internal_slots:
                return

            default_sets = [
                ["small_radar", "large_radar"],
                ["sonar", "large_sonar"],
                ["fire_control_system"],
            ]

            for categories in default_sets:
                self.add_internal_slot()
                if not self.internal_slots:
                    continue
                slot_info = self.internal_slots[-1]
                slot_id = slot_info["id"]
                self.slot_category_selections[slot_id] = categories

                button = slot_info["category_button"]
                names = [
                    self.app_controller.get_equipment_display_name(c)
                    if self.app_controller else c
                    for c in categories
                ]

                if len(names) == 1:
                    button.setText(names[0])
                else:
                    button.setText(f"{len(names)}種類選択")

                self.update_equipment_combo(slot_id)
        except Exception as e:
            print(f"デフォルト内部スロット追加エラー: {e}")
            import traceback
            traceback.print_exc()

    def show_category_selection_dialog(self, slot_type):
        """カテゴリー選択ダイアログを表示"""
        try:
            # カテゴリー選択ダイアログを作成
            dialog = QDialog(self)
            dialog.setWindowTitle(f"スロット {slot_type} のカテゴリー選択")
            dialog.setMinimumWidth(400)
            dialog.setMinimumHeight(500)

            # レイアウト
            layout = QVBoxLayout()

            # 年代フィルタスライダー
            year_filter_group = QGroupBox("年代フィルタ設定")
            year_layout = QVBoxLayout()

            minus_layout = QHBoxLayout()
            minus_layout.addWidget(QLabel("過去範囲"))
            minus_slider = QSlider(Qt.Horizontal)
            minus_slider.setRange(0, 50)
            minus_slider.setValue(self.year_range_minus)
            minus_value_label = QLabel(f"-{self.year_range_minus}")
            minus_slider.valueChanged.connect(lambda v: minus_value_label.setText(f"-{v}"))
            minus_layout.addWidget(minus_slider)
            minus_layout.addWidget(minus_value_label)
            year_layout.addLayout(minus_layout)

            plus_layout = QHBoxLayout()
            plus_layout.addWidget(QLabel("未来範囲"))
            plus_slider = QSlider(Qt.Horizontal)
            plus_slider.setRange(0, 50)
            plus_slider.setValue(self.year_range_plus)
            plus_value_label = QLabel(f"+{self.year_range_plus}")
            plus_slider.valueChanged.connect(lambda v: plus_value_label.setText(f"+{v}"))
            plus_layout.addWidget(plus_slider)
            plus_layout.addWidget(plus_value_label)
            year_layout.addLayout(plus_layout)

            year_filter_group.setLayout(year_layout)
            layout.addWidget(year_filter_group)

            # 説明ラベル
            description = QLabel("複数のカテゴリーを選択できます")
            layout.addWidget(description)

            # スクロールエリアを作成
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            # 入力欄のキー入力がスクロールエリアに奪われないようにする
            scroll_area.setFocusPolicy(Qt.NoFocus)
            scroll_area.viewport().setFocusPolicy(Qt.NoFocus)
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout(scroll_widget)

            # 現在選択されているカテゴリー（キー名）を取得
            current_categories = self.slot_category_selections.get(slot_type, [])

            # カテゴリーのチェックボックスを格納する辞書
            category_checkboxes = {}

            # カテゴリーを追加
            if self.app_controller:
                # キー名→表示名のマッピングを取得
                type_mapping = self.app_controller.get_equipment_type_mapping()

                for key, display_name in type_mapping.items():
                    checkbox = QCheckBox(display_name)
                    checkbox.setProperty("category_key", key)  # キー名をプロパティとして保存
                    # 現在選択されているカテゴリーをチェック状態にする
                    checkbox.setChecked(key in current_categories)
                    scroll_layout.addWidget(checkbox)
                    category_checkboxes[key] = checkbox
            else:
                # デフォルトのカテゴリー
                default_categories = [
                    "小口径砲", "中口径砲", "大口径砲", "超大口径砲", "対空砲",
                    "魚雷", "潜水艦魚雷", "対艦ミサイル", "対空ミサイル",
                    "水上機", "艦上偵察機", "回転翼機", "対潜哨戒機", "大型飛行艇",
                    "爆雷投射機", "爆雷", "対潜迫撃砲",
                    "ソナー", "大型ソナー", "小型電探", "大型電探", "測距儀",
                    "機関", "増設バルジ(中型艦)", "増設バルジ(大型艦)", "格納庫", "その他"
                ]

                for category in default_categories:
                    checkbox = QCheckBox(category)
                    checkbox.setProperty("category_key", category)
                    checkbox.setChecked(category in current_categories)
                    scroll_layout.addWidget(checkbox)
                    category_checkboxes[category] = checkbox

            # スクロールエリアにウィジェットを設定
            scroll_area.setWidget(scroll_widget)
            layout.addWidget(scroll_area)

            # 選択状態の表示
            selection_info = QLabel("選択中のカテゴリー: 0")
            layout.addWidget(selection_info)

            # 選択状態が変更されたときの処理
            def update_selection_info():
                selected_count = sum(1 for cb in category_checkboxes.values() if cb.isChecked())
                selection_info.setText(f"選択中のカテゴリー: {selected_count}")

            # 各チェックボックスの状態変更を監視
            for checkbox in category_checkboxes.values():
                checkbox.stateChanged.connect(update_selection_info)

            # 初期選択状態を反映
            update_selection_info()

            # ボタン
            button_layout = QHBoxLayout()
            ok_button = QPushButton("OK")
            cancel_button = QPushButton("キャンセル")

            def on_ok():
                # 選択されたカテゴリーのキー名を取得
                selected_categories = [
                    key for key, checkbox in category_checkboxes.items()
                    if checkbox.isChecked()
                ]

                # スライダーの値を保存
                self.year_range_minus = minus_slider.value()
                self.year_range_plus = plus_slider.value()

                # self.slot_category_selectionsにキー名を保存
                self.slot_category_selections[slot_type] = selected_categories

                # カテゴリーボタンのテキストを更新
                if slot_type in self.slot_category_combos:
                    button = self.slot_category_combos[slot_type]
                    if len(selected_categories) == 0:
                        button.setText("カテゴリー選択")
                    elif len(selected_categories) == 1:
                        # 選択されたキー名から表示名を取得
                        key = selected_categories[0]
                        if self.app_controller:
                            display_name = self.app_controller.get_equipment_display_name(key)
                            button.setText(display_name)
                        else:
                            button.setText(key)  # デフォルトの場合
                    else:
                        button.setText(f"{len(selected_categories)}種類選択")

                # 装備コンボボックスを更新
                self.update_equipment_combo(slot_type)
                dialog.accept()

            ok_button.clicked.connect(on_ok)
            cancel_button.clicked.connect(dialog.reject)

            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            dialog.setLayout(layout)
            dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"カテゴリー選択ダイアログの表示中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()

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
                "main_slots": {},
                "slot_categories": {},
                "internal_slots": [],
                "year": self.current_hull.get("year", 1936),
                "country": self.current_hull.get("country", ""),
            }

            # メインスロットのカテゴリーと装備の取得
            for slot_type in ["PA", "SA", "PSA", "SSA", "PLA", "SLA"]:
                # カテゴリーが選択されている場合は保存
                if hasattr(self, 'slot_category_selections') and slot_type in self.slot_category_selections:
                    categories = self.slot_category_selections[slot_type]
                    if categories:
                        design_data["slot_categories"][slot_type] = categories

                # 装備が選択されている場合は保存
                if slot_type in self.slot_combos:
                    combo = self.slot_combos[slot_type]
                    current_text = combo.currentText()

                    if current_text != "選択する" and "使用不可" not in current_text and "有効化可能" not in current_text:
                        # 括弧内のIDを抽出（例: "装備名 (ID) - カテゴリー"）
                        import re
                        id_match = re.search(r'\(([^)]+)\)', current_text)
                        if id_match:
                            equipment_id = id_match.group(1)
                            design_data["main_slots"][slot_type] = equipment_id

            # 内部スロットのデータを取得
            for i, slot_info in enumerate(self.internal_slots):
                slot_id = slot_info["id"]

                # カテゴリー選択
                selected_categories = []
                if hasattr(self, 'slot_category_selections') and slot_id in self.slot_category_selections:
                    selected_categories = self.slot_category_selections[slot_id]

                # 装備選択（安全チェック付き）
                selected_equipment = None
                try:
                    combo = slot_info.get("equipment_combo")
                    if combo:
                        current_text = combo.currentText()
                        
                        if current_text != "選択する" and "使用不可" not in current_text and "有効化可能" not in current_text:
                            # 括弧内のIDを抽出
                            import re
                            id_match = re.search(r'\(([^)]+)\)', current_text)
                            if id_match:
                                selected_equipment = id_match.group(1)
                except (RuntimeError, AttributeError):
                    # ウィジェットが削除されている場合は無視
                    selected_equipment = None

                # スロット情報を追加
                internal_slot_data = {
                    "slot_id": slot_id,
                    "slot_number": i + 1,
                    "categories": selected_categories,
                    "equipment_id": selected_equipment
                }

                design_data["internal_slots"].append(internal_slot_data)

            # calculated_statsはJSONファイルに含めない（デザインビューの要求により除外）

            # 設計データを保存
            if self.app_controller:
                if self.app_controller.save_design(design_data):
                    QMessageBox.information(self, "保存成功", f"艦級「{design_name}」の設計を保存しました。")
                else:
                    QMessageBox.warning(self, "警告", "設計の保存に失敗しました。")
            else:
                QMessageBox.warning(self, "警告", "アプリケーションコントローラーが設定されていません。")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設計の保存中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()

    def load_design_data(self, design_data):
        """設計データを読み込んで画面に反映"""
        try:
            # 船体データを読み込み
            hull_id = design_data.get("hull_id", "")
            if hull_id:
                if self.app_controller:
                    hull_data = self.app_controller.load_hull(hull_id)
                else:
                    # 直接モデルを使用
                    from models.hull_model import HullModel
                    hull_model = HullModel()
                    hull_data = hull_model.load_hull(hull_id)

                if hull_data:
                    # 船体を選択
                    self.current_hull = hull_data
                    self.selected_hull_label.setText(hull_data.get("name", "不明"))

                    # 船体アイコンを表示
                    hull_type = hull_data.get("type", "")
                    if hull_type:
                        hull_icon = self.ship_icon_manager.get_ship_icon(hull_type, QSize(32, 32))
                        self.hull_icon_label.setPixmap(hull_icon.pixmap(32, 32))
                    else:
                        # デフォルトアイコン
                        self.hull_icon_label.clear()
                        self.hull_icon_label.setText("?")

                    # 艦級名を設定
                    self.design_name_edit.setText(design_data.get("design_name", ""))

                    # 船体基礎情報を更新
                    self.update_hull_info(hull_data)

                    # スロット開放状況を更新
                    self.update_slot_availability()

                    # カテゴリーと装備を設定

                    # スロットカテゴリーの選択情報を初期化
                    if not hasattr(self, 'slot_category_selections'):
                        self.slot_category_selections = {}

                    # メインスロットのカテゴリーを設定
                    slot_categories = design_data.get("slot_categories", {})
                    for slot_type, categories in slot_categories.items():
                        self.slot_category_selections[slot_type] = categories

                        # ボタンテキストを更新
                        if slot_type in self.slot_category_combos:
                            button = self.slot_category_combos[slot_type]
                            if len(categories) == 1:
                                button.setText(categories[0])
                            else:
                                button.setText(f"{len(categories)}種類選択")

                    # 装備コンボボックスを更新
                    for slot_type in ["PA", "SA", "PSA", "SSA", "PLA", "SLA"]:
                        self.update_equipment_combo(slot_type)

                    # 装備選択を設定
                    main_slots = design_data.get("main_slots", {})
                    for slot_type, equipment_id in main_slots.items():
                        self.set_equipment_selection(slot_type, equipment_id)

                    # 内部スロットを復元
                    # まず既存のスロットをクリア
                    while self.internal_slots:
                        self.remove_internal_slot()

                    # 保存されていた内部スロットを追加
                    for slot_data in design_data.get("internal_slots", []):
                        # スロットを追加
                        self.add_internal_slot()

                        # 最後に追加したスロットを設定
                        if self.internal_slots:
                            last_slot = self.internal_slots[-1]
                            slot_id = last_slot["id"]

                            # カテゴリーを設定
                            categories = slot_data.get("categories", [])
                            if categories:
                                self.slot_category_selections[slot_id] = categories

                                # ボタンテキストを更新
                                button = last_slot["category_button"]
                                if len(categories) == 1:
                                    button.setText(categories[0])
                                else:
                                    button.setText(f"{len(categories)}種類選択")

                                # 装備コンボボックスを更新
                                self.update_equipment_combo(slot_id)

                                # 装備選択を設定
                                equipment_id = slot_data.get("equipment_id")
                                if equipment_id:
                                    self.set_equipment_selection(slot_id, equipment_id)

                    if not design_data.get("internal_slots"):
                        self.ensure_default_internal_slots()

                    # 性能表示を更新
                    # self.update_stats()

                    QMessageBox.information(self, "読み込み完了", f"艦級「{design_data.get('design_name', '')}」の設計を読み込みました。")
                else:
                    QMessageBox.warning(self, "警告", f"船体ID '{hull_id}' のデータが見つかりません。")
            else:
                QMessageBox.warning(self, "警告", "有効な船体IDがありません。")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設計データの読み込み中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()

    def set_equipment_selection(self, slot_id, equipment_id):
        """スロットに指定した装備IDを選択する"""
        try:
            if slot_id not in self.slot_combos:
                return

            combo = self.slot_combos[slot_id]

            # 装備データを取得
            equipment_data = None
            if self.app_controller:
                equipment_data = self.app_controller.load_equipment(equipment_id)
            else:
                # 直接モデルを使用
                from models.equipment_model import EquipmentModel
                equipment_model = EquipmentModel()
                equipment_data = equipment_model.load_equipment(equipment_id)

            if equipment_data:
                equipment_name = equipment_data.get('common', {}).get('名前', '')
                equipment_type = equipment_data.get('equipment_type', '')

                # コンボボックス内を検索
                for i in range(combo.count()):
                    item_text = combo.itemText(i)
                    if f"({equipment_id})" in item_text:
                        combo.setCurrentIndex(i)
                        return

                # 見つからない場合はアイテムを追加
                display_text = f"{equipment_name} ({equipment_id}) - {equipment_type}"
                combo.addItem(display_text)
                combo.setCurrentIndex(combo.count() - 1)

        except Exception as e:
            print(f"装備選択エラー: {e}")
            import traceback
            traceback.print_exc()

    def on_equipment_selection_changed(self, slot_id):
        """装備選択が変更されたときの処理"""
        try:
            # 現在の設計データを取得
            current_design_data = self.get_current_design_data()
            
            # ステータス表示を更新
            self.update_stats_display(current_design_data)
            
        except Exception as e:
            print(f"装備選択変更処理エラー: {e}")

