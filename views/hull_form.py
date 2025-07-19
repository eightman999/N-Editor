# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: hull_formビュー
import pdx_tools.pdx_ssw
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
                             QPushButton, QGroupBox, QFileDialog, QMessageBox, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal
from utils.web_search_widget import WebSearchButton
from utils.ship_role_constraints import get_allowed_roles, get_ship_type_from_role_display, get_ship_types_for_role
import os
import json
import csv
from utils.path_utils import get_data_dir


class HullForm(QWidget):
    """船体登録フォーム"""

    # 船体保存時のシグナル（船体IDを送信）
    hull_saved = pyqtSignal(str)

    def __init__(self, parent=None, app_controller=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.initUI()
        
        # 機関装備一覧を読み込み
        self.load_available_engines()

    def initUI(self):
        """UIの初期化"""
        # メインレイアウト
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # 上部レイアウト（Web検索ボタン用）
        top_layout = QHBoxLayout()
        top_layout.addStretch()
        
        # Web検索ボタン
        self.web_search_button = WebSearchButton(self, "warship hull design")
        top_layout.addWidget(self.web_search_button)
        
        main_layout.addLayout(top_layout)

        # スクロールエリア
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        # 入力欄のキー入力がスクロールエリアに奪われないようにする
        scroll_area.setFocusPolicy(Qt.NoFocus)
        scroll_area.viewport().setFocusPolicy(Qt.NoFocus)
        main_layout.addWidget(scroll_area)

        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)

        # 基本情報グループ
        basic_group = QGroupBox("基本情報")
        basic_layout = QFormLayout()
        basic_group.setLayout(basic_layout)
        form_layout.addWidget(basic_group)

        # 艦級名
        self.name_edit = QLineEdit()
        basic_layout.addRow("艦級名:", self.name_edit)

        # ID
        self.id_edit = QLineEdit()
        basic_layout.addRow("ID:", self.id_edit)

        # description
        self.description_edit = QLineEdit()
        basic_layout.addRow("description:", self.description_edit)

        # 種別（TYPE）
        self.type_combo = QComboBox()
        # TYPEリストの追加（HOI4の艦艇種別）
        ship_types =  [
            "AM - 掃海艇",
            "CMC - 沿岸敷設艇",
            "MCM - 掃海艦",
            "MCS - 掃海母艦",
            "AV - 水上機母艦",
            "CV - 航空母艦",
            "CVE - 護衛空母",
            "CVL - 軽空母",
            "CVS - 対潜空母",
            "SV - 飛行艇母艦",
            "LCSL - 上陸支援艇",
            "PC - 哨戒艇、駆潜艇",
            "PT - 高速魚雷艇",
            "FF - フリゲート",
            "K - コルベット",
            "MB - ミサイル艇",
            "PF - 哨戒フリゲート",
            "PG - 砲艦",
            "TB - 魚雷艇",
            "D - 水雷駆逐艦",
            "DB - 通報艦",
            "DD - 駆逐艦",
            "DDE - 対潜護衛駆逐艦",
            "DDG - ミサイル駆逐艦",
            "DDR - レーダーピケット駆逐艦",
            "DE - 護衛駆逐艦",
            "DL - 嚮導駆逐艦",
            "DM - 敷設駆逐艦",
            "DMS - 掃海駆逐艦",
            "CSS - 沿岸潜水艦",
            "MSM - 特殊潜航艇",
            "SC - 巡洋潜水艦",
            "SCV - 潜水空母",
            "SF - 艦隊型潜水艦",
            "SM - 敷設型潜水艦",
            "SS - 航洋型潜水艦",
            "ACR - 装甲巡洋艦",
            "IC - 装甲艦",
            "B - 前弩級戦艦",
            "BB - 戦艦",
            "BBG - ミサイル戦艦",
            "BC - 巡洋戦艦",
            "BF - 航空戦艦",
            "BM - モニター艦",
            "CA - 重巡・一等巡洋艦",
            "CB - 大型巡洋艦",
            "CDB - 海防戦艦",
            "CF - 航空巡洋艦",
            "CG - ミサイル巡洋艦",
            "FBB - 高速戦艦",
            "PB - ポケット戦艦",
            "SB - 超戦艦",
            "C - 防護巡洋艦",
            "CL - 軽巡洋艦/二等巡洋艦",
            "CM - 敷設巡洋艦",
            "CS - 偵察巡洋艦",
            "HTC - 重雷装巡洋艦",
            "TC - 水雷巡洋艦",
            "TCL - 練習巡洋艦",
            "AAA - 特設防空艦",
            "AAG - 特設防空警備艦",
            "AAM - 特設掃海艇",
            "AAS - 特設駆潜艇",
            "AAV - 特設水上機母艦",
            "AC - 特設巡洋艦",
            "AG - 特設砲艦",
            "AMS - 特設敷設艦",
            "APC - 特設監視艇",
            "APS - 特設哨戒艦",
            "CAM - CAMシップ",
            "MAC - 特設空母",
            "APB - 航行可能な宿泊艦",
            "PL - 大型巡視船",
            "PLH - ヘリ搭載型",
            "PM - 中型巡視船",
            "WHEC - 長距離カッター"
        ]

        self.type_combo.addItems(ship_types)
        basic_layout.addRow("種別(TYPE):", self.type_combo)

        # 艦種クラス
        self.class_edit = QLineEdit()
        basic_layout.addRow("艦種クラス:", self.class_edit)

        # 開発年
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1900, 2050)
        self.year_spin.setValue(1936)  # HOI4の初期年
        basic_layout.addRow("開発年:", self.year_spin)

        # 開発国
        self.country_edit = QLineEdit()
        basic_layout.addRow("開発国:", self.country_edit)

        # archetype（制約適用）
        self.archetype_combo = QComboBox()
        self.archetype_combo.addItems(pdx_tools.pdx_ssw.ship_types)
        basic_layout.addRow("archetype:", self.archetype_combo)
        
        # 無限再帰を防ぐためのフラグ
        self._updating_constraints = False
        
        # 種別変更時にarchetypeを制約する
        self.type_combo.currentTextChanged.connect(self.update_archetype_constraints)
        
        # archetype変更時にship_typeを制約する
        self.archetype_combo.currentTextChanged.connect(self.update_ship_type_constraints)

        # 物理的特性グループ
        physical_group = QGroupBox("物理的特性")
        physical_layout = QFormLayout()
        physical_group.setLayout(physical_layout)
        form_layout.addWidget(physical_group)

        # 重量
        self.weight_spin = QDoubleSpinBox()
        self.weight_spin.setRange(0, 100000)
        self.weight_spin.setDecimals(2)
        self.weight_spin.setSuffix(" t")
        physical_layout.addRow("重量:", self.weight_spin)

        # 全長
        self.length_spin = QDoubleSpinBox()
        self.length_spin.setRange(0, 500)
        self.length_spin.setDecimals(2)
        self.length_spin.setSuffix(" m")
        physical_layout.addRow("全長:", self.length_spin)

        # 全幅
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0, 100)
        self.width_spin.setDecimals(2)
        self.width_spin.setSuffix(" m")
        physical_layout.addRow("全幅:", self.width_spin)

        # 人員
        self.crew_spin = QSpinBox()
        self.crew_spin.setRange(0, 10000)
        self.crew_spin.setSuffix(" 人")
        physical_layout.addRow("人員:", self.crew_spin)

        # 船体性能グループ
        performance_group = QGroupBox("船体性能")
        performance_layout = QFormLayout()
        performance_group.setLayout(performance_layout)
        form_layout.addWidget(performance_group)

        # 最大速度
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0, 100)
        self.speed_spin.setDecimals(2)
        self.speed_spin.setSuffix(" kts")
        performance_layout.addRow("最大速度:", self.speed_spin)

        # 巡航速度
        self.cruise_speed_spin = QDoubleSpinBox()
        self.cruise_speed_spin.setRange(0, 100)
        self.cruise_speed_spin.setDecimals(2)
        self.cruise_speed_spin.setSuffix(" kts")
        performance_layout.addRow("巡航速度:", self.cruise_speed_spin)

        # 航続距離
        self.range_spin = QDoubleSpinBox()
        self.range_spin.setRange(0, 20000)
        self.range_spin.setDecimals(2)
        self.range_spin.setSuffix(" nm")
        performance_layout.addRow("航続距離:", self.range_spin)

        # 機関装備グループ
        engine_group = QGroupBox("機関装備")
        engine_layout = QVBoxLayout()
        engine_group.setLayout(engine_layout)
        form_layout.addWidget(engine_group)

        # 主機選択
        main_engine_layout = QHBoxLayout()
        self.main_engine_combo = QComboBox()
        self.main_engine_combo.addItem("機関を選択してください", "")
        main_engine_layout.addWidget(QLabel("主機:"))
        main_engine_layout.addWidget(self.main_engine_combo)
        
        self.main_engine_count_spin = QSpinBox()
        self.main_engine_count_spin.setRange(1, 10)
        self.main_engine_count_spin.setValue(1)
        self.main_engine_count_spin.setSuffix(" 基")
        main_engine_layout.addWidget(QLabel("数量:"))
        main_engine_layout.addWidget(self.main_engine_count_spin)
        
        engine_layout.addLayout(main_engine_layout)

        # 補機選択エリア
        aux_engine_label = QLabel("補機:")
        engine_layout.addWidget(aux_engine_label)
        
        self.aux_engine_layout = QVBoxLayout()
        engine_layout.addLayout(self.aux_engine_layout)
        
        # 補機追加ボタン
        add_aux_button = QPushButton("補機を追加")
        add_aux_button.clicked.connect(self.add_auxiliary_engine)
        engine_layout.addWidget(add_aux_button)

        # 機関装備作成ボタン
        create_engine_button = QPushButton("新しい機関装備を作成")
        create_engine_button.clicked.connect(self.create_new_engine)
        engine_layout.addWidget(create_engine_button)

        # 補機装備のリスト（動的に追加されるウィジェット管理用）
        self.auxiliary_engines = []

        # 防御特性グループ
        defense_group = QGroupBox("防御特性")
        defense_layout = QFormLayout()
        defense_group.setLayout(defense_layout)
        form_layout.addWidget(defense_group)

        # 舷側装甲最大
        self.armor_max_spin = QDoubleSpinBox()
        self.armor_max_spin.setRange(0, 500)
        self.armor_max_spin.setDecimals(2)
        self.armor_max_spin.setSuffix(" mm")
        defense_layout.addRow("舷側装甲最大:", self.armor_max_spin)

        # 舷側装甲最小
        self.armor_min_spin = QDoubleSpinBox()
        self.armor_min_spin.setRange(0, 500)
        self.armor_min_spin.setDecimals(2)
        self.armor_min_spin.setSuffix(" mm")
        defense_layout.addRow("舷側装甲最小:", self.armor_min_spin)

        # 船殻構造
        self.hull_structure_combo = QComboBox()
        hull_structures = ["なし", "中世型", "近代型", "WWI型", "戦間期型", "WWII型", "戦後前期型", "現代型"]
        self.hull_structure_combo.addItems(hull_structures)
        self.hull_structure_combo.setCurrentIndex(2)  # デフォルトは近代型
        defense_layout.addRow("船殻構造:", self.hull_structure_combo)

        # 装甲種別
        self.armor_type_combo = QComboBox()
        armor_types = ["なし", "装甲なし", "軽装甲", "標準装甲", "重装甲", "特殊装甲", "複合装甲"]
        self.armor_type_combo.addItems(armor_types)
        self.armor_type_combo.setCurrentIndex(3)  # デフォルトは標準装甲
        defense_layout.addRow("装甲種別:", self.armor_type_combo)

        # プレイヤースロットグループ
        slot_group = QGroupBox("プレイヤースロット")
        slot_layout = QFormLayout()
        slot_group.setLayout(slot_layout)
        form_layout.addWidget(slot_group)

        # プレイヤースロットのオプション
        slot_options = ["有効", "無効", "有効化可能"]

        # PA (主武装)
        self.pa_combo = QComboBox()
        self.pa_combo.addItems(slot_options)
        slot_layout.addRow("PA:", self.pa_combo)

        # SA (副武装)
        self.sa_combo = QComboBox()
        self.sa_combo.addItems(slot_options)
        slot_layout.addRow("SA:", self.sa_combo)

        # PSA (主舷武装)
        self.psa_combo = QComboBox()
        self.psa_combo.addItems(slot_options)
        slot_layout.addRow("PSA:", self.psa_combo)

        # SSA (サブ舷武装)
        self.ssa_combo = QComboBox()
        self.ssa_combo.addItems(slot_options)
        slot_layout.addRow("SSA:", self.ssa_combo)

        # PLA (主軽武装)
        self.pla_combo = QComboBox()
        self.pla_combo.addItems(slot_options)
        slot_layout.addRow("PLA:", self.pla_combo)

        # SLA (サブ軽武装)
        self.sla_combo = QComboBox()
        self.sla_combo.addItems(slot_options)
        slot_layout.addRow("SLA:", self.sla_combo)

        scroll_area.setWidget(form_container)

        # ボタン部分
        button_layout = QHBoxLayout()

        self.import_button = QPushButton("CSVインポート")
        self.import_button.clicked.connect(self.import_from_csv)

        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_hull)

        self.clear_button = QPushButton("クリア")
        self.clear_button.clicked.connect(self.clear_form)

        self.load_button = QPushButton("読み込み")
        self.load_button.clicked.connect(self.load_hull)

        button_layout.addWidget(self.import_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.clear_button)

        main_layout.addLayout(button_layout)

    def save_hull(self):
        """船体データの保存"""
        hull_data = self.get_form_data()

        # 必須フィールドの確認
        if not hull_data["name"] or not hull_data["id"]:
            QMessageBox.warning(self, "入力エラー", "艦級名とIDは必須です。")
            return

        # AppControllerを使用して船体を保存
        if self.app_controller:
            if self.app_controller.save_hull(hull_data):
                hull_id = hull_data["id"]
                QMessageBox.information(self, "保存成功", f"船体データを保存しました。\nID: {hull_id}")
                self.hull_saved.emit(hull_id)
            else:
                QMessageBox.critical(self, "保存エラー", "データの保存に失敗しました。")
            return

        # 従来の方法（AppControllerがない場合）
        try:
            import os
            import json

            # 保存先ディレクトリの作成
            base_dir = get_data_dir('hulls')

            # ファイル名は船体IDを使用
            file_name = f"{hull_data['id']}.json"
            file_path = os.path.join(base_dir, file_name)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(hull_data, f, ensure_ascii=False, indent=2)

            QMessageBox.information(self, "保存成功", f"船体データを保存しました。\n{file_path}")
            self.hull_saved.emit(hull_data["id"])
        except Exception as e:
            QMessageBox.critical(self, "保存エラー", f"データの保存に失敗しました。\n{e}")

    def get_form_data(self):
        """フォームデータの取得"""
        # スロット状態のマッピング
        slot_mapping = {
            0: " ",  # 有効
            1: "-",  # 無効
            2: "="   # 有効化可能
        }

        # 船殻構造のマッピング
        hull_structure_mapping = {
            0: 0,    # なし
            1: 1,    # 中世型
            2: 2,    # 近代型
            3: 3,    # WWI型
            4: 4,    # 戦間期型
            5: 5,    # WWII型
            6: 6,    # 戦後前期型
            7: 7     # 現代型
        }

        # 装甲種別のマッピング
        armor_type_mapping = {
            0: 0.0,    # なし
            1: 1.0,    # 装甲なし
            2: 1.35,   # 軽装甲
            3: 1.4,    # 標準装甲
            4: 1.5,    # 重装甲
            5: 1.8,    # 特殊装甲
            6: 2.0     # 複合装甲
        }

        # 機関装備データを取得
        engine_data = self.get_engine_data()
        
        hull_data = {
            "name": self.name_edit.text(),
            "id": self.id_edit.text(),
            "description": self.description_edit.text(),
            "type": self.type_combo.currentText(),
            "class": self.class_edit.text(),
            "year": self.year_spin.value(),
            "country": self.country_edit.text(),
            "archetype": self.archetype_combo.currentText(),
            "weight": self.weight_spin.value(),
            "length": self.length_spin.value(),
            "width": self.width_spin.value(),
            "crew": self.crew_spin.value(),
            "speed": self.speed_spin.value(),
            "max_speed": self.speed_spin.value(),
            "cruise_speed": self.cruise_speed_spin.value(),
            "range": self.range_spin.value(),
            "naval_range": self.range_spin.value(),
            "armor_max": self.armor_max_spin.value(),
            "armor_min": self.armor_min_spin.value(),
            "hull_structure": self.hull_structure_combo.currentText(),
            "hull_structure_id": hull_structure_mapping[self.hull_structure_combo.currentIndex()],
            "armor_type": self.armor_type_combo.currentText(),
            "armor_type_id": armor_type_mapping[self.armor_type_combo.currentIndex()],
            "slots": {
                "PA": slot_mapping[self.pa_combo.currentIndex()],
                "SA": slot_mapping[self.sa_combo.currentIndex()],
                "PSA": slot_mapping[self.psa_combo.currentIndex()],
                "SSA": slot_mapping[self.ssa_combo.currentIndex()],
                "PLA": slot_mapping[self.pla_combo.currentIndex()],
                "SLA": slot_mapping[self.sla_combo.currentIndex()]
            },
            # 機関装備データの統合
            "main_engine_id": engine_data['main_engine_id'],
            "auxiliary_engine_ids": engine_data['auxiliary_engine_ids'],
            "engine_count": {
                'main': engine_data['main_engine_count'],
                'auxiliary': sum(engine_data['auxiliary_engine_counts'])
            }
        }
        
        return hull_data

    def set_form_data(self, data):
        """フォームにデータを設定"""
        # 基本情報
        self.name_edit.setText(data.get("name", ""))
        self.id_edit.setText(data.get("id", ""))
        self.description_edit.setText(data.get("description", ""))

        # 種別(TYPE)
        type_index = self.type_combo.findText(data.get("type", ""))
        if type_index >= 0:
            self.type_combo.setCurrentIndex(type_index)

        # 艦種クラス
        self.class_edit.setText(data.get("class", ""))

        # 開発年
        self.year_spin.setValue(int(data.get("year", 1936)))

        # 開発国
        self.country_edit.setText(data.get("country", ""))

        # archetype
        archetype_index = self.archetype_combo.findText(data.get("archetype", ""))
        if archetype_index >= 0:
            self.archetype_combo.setCurrentIndex(archetype_index)

        # 物理的特性
        self.weight_spin.setValue(float(data.get("weight", 0)))
        self.length_spin.setValue(float(data.get("length", 0)))
        self.width_spin.setValue(float(data.get("width", 0)))
        self.crew_spin.setValue(int(data.get("crew", 0)))

        # 船体性能
        self.speed_spin.setValue(float(data.get("speed", data.get("max_speed", 0))))
        self.cruise_speed_spin.setValue(float(data.get("cruise_speed", 0)))
        self.range_spin.setValue(float(data.get("range", data.get("naval_range", 0))))

        # 機関装備データを設定
        engine_data = {
            'main_engine_id': data.get('main_engine_id', ''),
            'main_engine_count': data.get('engine_count', {}).get('main', 1),
            'auxiliary_engine_ids': data.get('auxiliary_engine_ids', []),
            'auxiliary_engine_counts': []  # 既存データから推定
        }
        
        # 補機数量を推定（総数から均等配分）
        aux_total = data.get('engine_count', {}).get('auxiliary', 0)
        aux_ids = engine_data['auxiliary_engine_ids']
        if aux_ids and aux_total > 0:
            per_engine = max(1, aux_total // len(aux_ids))
            engine_data['auxiliary_engine_counts'] = [per_engine] * len(aux_ids)
        
        self.set_engine_data(engine_data)

        # 防御特性
        self.armor_max_spin.setValue(float(data.get("armor_max", 0)))
        self.armor_min_spin.setValue(float(data.get("armor_min", 0)))

        # 船殻構造
        hull_structure = data.get("hull_structure", "近代型")
        hull_structure_index = self.hull_structure_combo.findText(hull_structure)
        if hull_structure_index >= 0:
            self.hull_structure_combo.setCurrentIndex(hull_structure_index)
        else:
            # 数値から対応するインデックスを探す
            hull_id = float(data.get("hull_structure_id", 2.0))
            hull_mapping_reverse = {
                0: 0,  # なし
                1: 1,  # 中世型
                2: 2,  # 近代型
                3: 3,  # WWI型
                4: 4,  # 戦間期型
                5: 5,  # WWII型
                6: 6,  # 戦後前期型
                7: 7   # 現代型
            }
            self.hull_structure_combo.setCurrentIndex(hull_mapping_reverse.get(hull_id, 2))

        # 装甲種別
        armor_type = data.get("armor_type", "標準装甲")
        armor_type_index = self.armor_type_combo.findText(armor_type)
        if armor_type_index >= 0:
            self.armor_type_combo.setCurrentIndex(armor_type_index)
        else:
            # 数値から対応するインデックスを探す
            armor_id = float(data.get("armor_type_id", 1.4))
            armor_mapping_reverse = {
                0.0: 0,  # なし
                1.0: 1,  # 装甲なし
                1.35: 2, # 軽装甲
                1.4: 3,  # 標準装甲
                1.5: 4,  # 重装甲
                1.8: 5,  # 特殊装甲
                2.0: 6   # 複合装甲
            }
            self.armor_type_combo.setCurrentIndex(armor_mapping_reverse.get(armor_id, 3))

        # スロット情報
        slots = data.get("slots", {})
        slot_mapping_reverse = {" ": 0, "-": 1, "=": 2}

        self.pa_combo.setCurrentIndex(slot_mapping_reverse.get(slots.get("PA", " "), 0))
        self.sa_combo.setCurrentIndex(slot_mapping_reverse.get(slots.get("SA", " "), 0))
        self.psa_combo.setCurrentIndex(slot_mapping_reverse.get(slots.get("PSA", " "), 0))
        self.ssa_combo.setCurrentIndex(slot_mapping_reverse.get(slots.get("SSA", " "), 0))
        self.pla_combo.setCurrentIndex(slot_mapping_reverse.get(slots.get("PLA", " "), 0))
        self.sla_combo.setCurrentIndex(slot_mapping_reverse.get(slots.get("SLA", " "), 0))

    def clear_form(self):
        """フォームのクリア"""
        self.name_edit.clear()
        self.id_edit.clear()
        self.description_edit.clear()
        self.type_combo.setCurrentIndex(0)
        self.class_edit.clear()
        self.year_spin.setValue(1936)
        self.country_edit.clear()
        self.archetype_combo.setCurrentIndex(0)

        self.weight_spin.setValue(0)
        self.length_spin.setValue(0)
        self.width_spin.setValue(0)
        self.crew_spin.setValue(0)

        self.speed_spin.setValue(0)
        self.range_spin.setValue(0)
        self.cruise_speed_spin.setValue(0)
        
        # 機関装備をクリア
        self.main_engine_combo.setCurrentIndex(0)
        self.main_engine_count_spin.setValue(1)
        for aux in self.auxiliary_engines[:]:
            self.remove_auxiliary_engine(aux['widget'])

        self.armor_max_spin.setValue(0)
        self.armor_min_spin.setValue(0)
        self.hull_structure_combo.setCurrentIndex(2)  # 近代型
        self.armor_type_combo.setCurrentIndex(3)      # 標準装甲

        self.pa_combo.setCurrentIndex(0)
        self.sa_combo.setCurrentIndex(0)
        self.psa_combo.setCurrentIndex(0)
        self.ssa_combo.setCurrentIndex(0)
        self.pla_combo.setCurrentIndex(0)
        self.sla_combo.setCurrentIndex(0)

    def load_hull(self):
        """船体データの読み込み"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "船体データ読み込み", "", "JSON Files (*.json)", options=options
        )

        if not file_name:
            return

        try:
            with open(file_name, 'r', encoding='utf-8') as f:
                hull_data = json.load(f)

            self.set_form_data(hull_data)

            QMessageBox.information(self, "読み込み成功", f"船体データを読み込みました。\n{file_name}")
        except Exception as e:
            QMessageBox.critical(self, "読み込みエラー", f"データの読み込みに失敗しました。\n{e}")

    def import_from_csv(self):
        """CSVからのインポート"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "CSVファイルを開く", "", "CSV Files (*.csv)", options=options
        )

        if not file_name:
            return

        try:
            # AppControllerを使用してCSVをインポート
            if self.app_controller:
                # 最初の行のみ表示用に取得
                hull_data = self.app_controller.import_first_hull_from_csv(file_name)
                if hull_data:
                    self.set_form_data(hull_data)
                    QMessageBox.information(self, "インポート成功", "CSVファイルから最初の行のデータをインポートしました。")
                else:
                    QMessageBox.warning(self, "インポート警告", "CSVファイルからデータをインポートできませんでした。")
                return

            # 従来の方法（AppControllerがない場合）
            with open(file_name, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                # 最初の行のみ取得
                try:
                    row = next(reader)
                except StopIteration:
                    QMessageBox.warning(self, "インポート警告", "CSVファイルにデータがありません。")
                    return

            # データマッピングとフォーム設定
            hull_data = self._convert_csv_row_to_hull_data(row)
            if hull_data:
                self.set_form_data(hull_data)
                QMessageBox.information(self, "インポート成功", "CSVファイルから最初の行のデータをインポートしました。")
            else:
                QMessageBox.warning(self, "インポート警告", "CSVデータの変換に失敗しました。")

        except Exception as e:
            QMessageBox.critical(self, "インポートエラー", f"CSVの解析に失敗しました。\n{e}")

    def _convert_csv_row_to_hull_data(self, row):
        """CSVの行データを船体データ形式に変換"""
        hull_data = {}

        # CSVから読み込めるデータのマッピング
        field_mapping = {
            '艦級名': 'name',
            'システム名称': 'id',
            'weight': 'weight',
            'length': 'length',
            'width': 'width',
            'power': 'power',
            'speed': 'speed',
            'range': 'range',
            'cruise_speed': 'cruise_speed',
            'fuel_capacity': 'fuel_capacity',
            'armor_max': 'armor_max',
            'armor_min': 'armor_min',
            '船殻構造': 'hull_structure_id',
            '装甲種別': 'armor_type_id',
            'crew': 'crew',
            'country': 'country',
            '種別': 'class',
            'year': 'year',
            'archetype': 'archetype',
            'TYPE': 'type'
        }

        # 基本情報の変換
        for csv_field, data_field in field_mapping.items():
            if csv_field in row:
                hull_data[data_field] = row[csv_field]

        # IDが未設定の場合は新しいIDを生成
        if not hull_data.get('id') or hull_data.get('id') == '-':
            base_dir = get_data_dir('hulls')
            try:
                next_id = len(os.listdir(base_dir)) + 1
            except:
                next_id = 1
            hull_data['id'] = f"HULL{next_id:03d}"

        # 数値型フィールドの変換
        numeric_fields = ['weight', 'length', 'width', 'power', 'speed', 'range',
                          'cruise_speed', 'fuel_capacity', 'armor_max', 'armor_min',
                          'crew', 'year', 'hull_structure_id', 'armor_type_id']

        for field in numeric_fields:
            if field in hull_data:
                try:
                    # '#REF!'などの特殊値を処理
                    if hull_data[field] in ['', '#REF!', 'NULL']:
                        hull_data[field] = 0
                    else:
                        hull_data[field] = float(hull_data[field])
                except (ValueError, TypeError):
                    hull_data[field] = 0

        # 船殻構造と装甲種別の変換
        # 数値IDから文字列表現へマッピング
        hull_structure_id = float(hull_data.get('hull_structure_id', 2.0))
        hull_structure_mapping = {
            0: 'なし',
            1: '中世型',
            2: '近代型',
            3: 'WWI型',
            4: '戦間期型',
            5: 'WWII型',
            6: '戦後前期型',
            7: '現代型'
        }
        hull_data['hull_structure'] = hull_structure_mapping.get(hull_structure_id, '近代型')

        armor_type_id = float(hull_data.get('armor_type_id', 1.4))
        armor_type_mapping = {
            0.0: 'なし',
            1.0: '装甲なし',
            1.35: '軽装甲',
            1.4: '標準装甲',
            1.5: '重装甲',
            1.8: '特殊装甲',
            2.0: '複合装甲'
        }
        hull_data['armor_type'] = armor_type_mapping.get(armor_type_id, '標準装甲')

        # スロット情報の処理
        slots = {}
        slot_fields = ['PA', 'SA', 'PSA', 'SSA', 'PLA', 'SLA']

        for slot in slot_fields:
            if slot in row:
                value = row[slot]
                if value == '':
                    slots[slot] = ' '  # 有効
                elif value == '-':
                    slots[slot] = '-'  # 無効
                elif value == '=':
                    slots[slot] = '='  # 有効化可能
                else:
                    slots[slot] = ' '  # デフォルトは有効
            else:
                slots[slot] = ' '  # デフォルトは有効

        hull_data['slots'] = slots

        return hull_data
    
    def update_archetype_constraints(self, text=None):
        """種別選択に基づいてarchetypeの選択肢を制約"""
        if self._updating_constraints:
            return
            
        try:
            self._updating_constraints = True
            
            # 現在選択されている種別を取得
            current_type_text = self.type_combo.currentText()
            
            # 種別から略称を抽出（例: "BB - 戦艦" → "BB"）
            ship_type = get_ship_type_from_role_display(current_type_text)
            
            # 利用可能なロール種別を取得
            allowed_roles = get_allowed_roles(ship_type)
            
            # 現在選択されているarchetype を保存
            current_archetype = self.archetype_combo.currentText()
            
            # archetypeコンボボックスをクリア
            self.archetype_combo.clear()
            
            if allowed_roles:
                # 制約に基づいて選択肢を追加
                for role in allowed_roles:
                    self.archetype_combo.addItem(role)
                
                # 以前の選択が有効な場合は復元
                if current_archetype in allowed_roles:
                    index = self.archetype_combo.findText(current_archetype)
                    if index >= 0:
                        self.archetype_combo.setCurrentIndex(index)
                        
                print(f"船体種別 '{ship_type}' に対して {len(allowed_roles)} 個のロール種別を設定しました")
            else:
                # 制約が定義されていない場合は全てのship_typesを追加
                self.archetype_combo.addItems(pdx_tools.pdx_ssw.ship_types)
                
                # 以前の選択を復元
                index = self.archetype_combo.findText(current_archetype)
                if index >= 0:
                    self.archetype_combo.setCurrentIndex(index)
                    
                print(f"船体種別 '{ship_type}' の制約が未定義のため、全ロール種別を表示しています")
                
        except Exception as e:
            print(f"archetype制約更新エラー: {e}")
            # エラー時は全てのship_typesを表示
            self.archetype_combo.clear()
            self.archetype_combo.addItems(pdx_tools.pdx_ssw.ship_types)
        finally:
            self._updating_constraints = False
    
    def update_ship_type_constraints(self, text=None):
        """archetype選択に基づいてship_typeの選択肢を制約"""
        if self._updating_constraints:
            return
            
        try:
            self._updating_constraints = True
            
            # 現在選択されているarchetypeを取得
            current_archetype = self.archetype_combo.currentText()
            
            if not current_archetype:
                return
            
            # そのarchetypeを利用可能なship_typeを取得
            compatible_ship_types = get_ship_types_for_role(current_archetype)
            
            # 現在選択されているship_typeを保存
            current_ship_type_text = self.type_combo.currentText()
            current_ship_type = get_ship_type_from_role_display(current_ship_type_text)
            
            # ship_typeコンボボックスをクリア
            self.type_combo.clear()
            
            if compatible_ship_types:
                # 制約に基づいて選択肢を追加
                # 全ての船種リストから対象のもののみを抽出
                ship_types = [
                    "AM - 掃海艇", "CMC - 沿岸敷設艇", "MCM - 掃海艦", "MCS - 掃海母艦",
                    "AV - 水上機母艦", "CV - 航空母艦", "CVE - 護衛空母", "CVL - 軽空母", "CVS - 対潜空母", "SV - 飛行艇母艦",
                    "LCSL - 上陸支援艇", "PC - 哨戒艇、駆潜艇", "PT - 高速魚雷艇", "FF - フリゲート", "K - コルベット",
                    "MB - ミサイル艇", "PF - 哨戒フリゲート", "PG - 砲艦", "TB - 魚雷艇",
                    "D - 水雷駆逐艦", "DB - 通報艦", "DD - 駆逐艦", "DDE - 対潜護衛駆逐艦", "DDG - ミサイル駆逐艦",
                    "DDR - レーダーピケット駆逐艦", "DE - 護衛駆逐艦", "DL - 嚮導駆逐艦", "DM - 敷設駆逐艦", "DMS - 掃海駆逐艦",
                    "CSS - 沿岸潜水艦", "MSM - 特殊潜航艇", "SC - 巡洋潜水艦", "SCV - 潜水空母", "SF - 艦隊型潜水艦", "SM - 敷設型潜水艦", "SS - 航洋型潜水艦",
                    "ACR - 装甲巡洋艦", "IC - 装甲艦", "B - 前弩級戦艦", "BB - 戦艦", "BBG - ミサイル戦艦", "BC - 巡洋戦艦", "BF - 航空戦艦",
                    "BM - モニター艦", "CA - 重巡・一等巡洋艦", "CB - 大型巡洋艦", "CDB - 海防戦艦", "CF - 航空巡洋艦", "CG - ミサイル巡洋艦",
                    "FBB - 高速戦艦", "PB - ポケット戦艦", "SB - 超戦艦", "C - 防護巡洋艦", "CL - 軽巡洋艦/二等巡洋艦",
                    "CM - 敷設巡洋艦", "CS - 偵察巡洋艦", "HTC - 重雷装巡洋艦", "TC - 水雷巡洋艦", "TCL - 練習巡洋艦",
                    "AAA - 特設防空艦", "AAG - 特設防空警備艦", "AAM - 特設掃海艇", "AAS - 特設駆潜艇", "AAV - 特設水上機母艦",
                    "AC - 特設巡洋艦", "AG - 特設砲艦", "AMS - 特設敷設艦", "APC - 特設監視艇", "APS - 特設哨戒艦",
                    "CAM - CAMシップ", "MAC - 特設空母", "APB - 航行可能な宿泊艦", "PL - 大型巡視船", "PLH - ヘリ搭載型",
                    "PM - 中型巡視船", "WHEC - 長距離カッター"
                ]
                
                # 制約に合致する船種のみを追加
                for ship_type_display in ship_types:
                    ship_type_abbrev = get_ship_type_from_role_display(ship_type_display)
                    if ship_type_abbrev in compatible_ship_types:
                        self.type_combo.addItem(ship_type_display)
                
                # 以前の選択が有効な場合は復元
                if current_ship_type in compatible_ship_types:
                    for i in range(self.type_combo.count()):
                        item_text = self.type_combo.itemText(i)
                        item_abbrev = get_ship_type_from_role_display(item_text)
                        if item_abbrev == current_ship_type:
                            self.type_combo.setCurrentIndex(i)
                            break
                            
                print(f"archetype '{current_archetype}' に対して {len(compatible_ship_types)} 個の船体種別を設定しました: {compatible_ship_types}")
            else:
                # 制約が見つからない場合は全ての種別を表示
                ship_types =  [
                    "AM - 掃海艇", "CMC - 沿岸敷設艇", "MCM - 掃海艦", "MCS - 掃海母艦",
                    "AV - 水上機母艦", "CV - 航空母艦", "CVE - 護衛空母", "CVL - 軽空母", "CVS - 対潜空母", "SV - 飛行艇母艦",
                    "LCSL - 上陸支援艇", "PC - 哨戒艇、駆潜艇", "PT - 高速魚雷艇", "FF - フリゲート", "K - コルベット",
                    "MB - ミサイル艇", "PF - 哨戒フリゲート", "PG - 砲艦", "TB - 魚雷艇",
                    "D - 水雷駆逐艦", "DB - 通報艦", "DD - 駆逐艦", "DDE - 対潜護衛駆逐艦", "DDG - ミサイル駆逐艦",
                    "DDR - レーダーピケット駆逐艦", "DE - 護衛駆逐艦", "DL - 嚮導駆逐艦", "DM - 敷設駆逐艦", "DMS - 掃海駆逐艦",
                    "CSS - 沿岸潜水艦", "MSM - 特殊潜航艇", "SC - 巡洋潜水艦", "SCV - 潜水空母", "SF - 艦隊型潜水艦", "SM - 敷設型潜水艦", "SS - 航洋型潜水艦",
                    "ACR - 装甲巡洋艦", "IC - 装甲艦", "B - 前弩級戦艦", "BB - 戦艦", "BBG - ミサイル戦艦", "BC - 巡洋戦艦", "BF - 航空戦艦",
                    "BM - モニター艦", "CA - 重巡・一等巡洋艦", "CB - 大型巡洋艦", "CDB - 海防戦艦", "CF - 航空巡洋艦", "CG - ミサイル巡洋艦",
                    "FBB - 高速戦艦", "PB - ポケット戦艦", "SB - 超戦艦", "C - 防護巡洋艦", "CL - 軽巡洋艦/二等巡洋艦",
                    "CM - 敷設巡洋艦", "CS - 偵察巡洋艦", "HTC - 重雷装巡洋艦", "TC - 水雷巡洋艦", "TCL - 練習巡洋艦",
                    "AAA - 特設防空艦", "AAG - 特設防空警備艦", "AAM - 特設掃海艇", "AAS - 特設駆潜艇", "AAV - 特設水上機母艦",
                    "AC - 特設巡洋艦", "AG - 特設砲艦", "AMS - 特設敷設艦", "APC - 特設監視艇", "APS - 特設哨戒艦",
                    "CAM - CAMシップ", "MAC - 特設空母", "APB - 航行可能な宿泊艦", "PL - 大型巡視船", "PLH - ヘリ搭載型",
                    "PM - 中型巡視船", "WHEC - 長距離カッター"
                ]
                self.type_combo.addItems(ship_types)
                
                # 以前の選択を復元
                for i in range(self.type_combo.count()):
                    if self.type_combo.itemText(i) == current_ship_type_text:
                        self.type_combo.setCurrentIndex(i)
                        break
                        
                print(f"archetype '{current_archetype}' の制約が未定義のため、全船体種別を表示しています")
                
        except Exception as e:
            print(f"ship_type制約更新エラー: {e}")
            # エラー時は全ての種別を表示
            ship_types =  [
                "AM - 掃海艇", "CMC - 沿岸敷設艇", "MCM - 掃海艦", "MCS - 掃海母艦",
                "AV - 水上機母艦", "CV - 航空母艦", "CVE - 護衛空母", "CVL - 軽空母", "CVS - 対潜空母", "SV - 飛行艇母艦",
                "LCSL - 上陸支援艇", "PC - 哨戒艇、駆潜艇", "PT - 高速魚雷艇", "FF - フリゲート", "K - コルベット",
                "MB - ミサイル艇", "PF - 哨戒フリゲート", "PG - 砲艦", "TB - 魚雷艇",
                "D - 水雷駆逐艦", "DB - 通報艦", "DD - 駆逐艦", "DDE - 対潜護衛駆逐艦", "DDG - ミサイル駆逐艦",
                "DDR - レーダーピケット駆逐艦", "DE - 護衛駆逐艦", "DL - 嚮導駆逐艦", "DM - 敷設駆逐艦", "DMS - 掃海駆逐艦",
                "CSS - 沿岸潜水艦", "MSM - 特殊潜航艇", "SC - 巡洋潜水艦", "SCV - 潜水空母", "SF - 艦隊型潜水艦", "SM - 敷設型潜水艦", "SS - 航洋型潜水艦",
                "ACR - 装甲巡洋艦", "IC - 装甲艦", "B - 前弩級戦艦", "BB - 戦艦", "BBG - ミサイル戦艦", "BC - 巡洋戦艦", "BF - 航空戦艦",
                "BM - モニター艦", "CA - 重巡・一等巡洋艦", "CB - 大型巡洋艦", "CDB - 海防戦艦", "CF - 航空巡洋艦", "CG - ミサイル巡洋艦",
                "FBB - 高速戦艦", "PB - ポケット戦艦", "SB - 超戦艦", "C - 防護巡洋艦", "CL - 軽巡洋艦/二等巡洋艦",
                "CM - 敷設巡洋艦", "CS - 偵察巡洋艦", "HTC - 重雷装巡洋艦", "TC - 水雷巡洋艦", "TCL - 練習巡洋艦",
                "AAA - 特設防空艦", "AAG - 特設防空警備艦", "AAM - 特設掃海艇", "AAS - 特設駆潜艇", "AAV - 特設水上機母艦",
                "AC - 特設巡洋艦", "AG - 特設砲艦", "AMS - 特設敷設艦", "APC - 特設監視艇", "APS - 特設哨戒艦",
                "CAM - CAMシップ", "MAC - 特設空母", "APB - 航行可能な宿泊艦", "PL - 大型巡視船", "PLH - ヘリ搭載型",
                "PM - 中型巡視船", "WHEC - 長距離カッター"
            ]
            self.type_combo.clear()
            self.type_combo.addItems(ship_types)
        finally:
            self._updating_constraints = False

    def load_available_engines(self):
        """利用可能な機関装備の一覧を読み込み"""
        if not self.app_controller:
            return

        try:
            # 機関装備（SMEN_プレフィックス）を取得
            all_equipment = self.app_controller.equipment_model.get_all_equipment()
            engines = [eq for eq in all_equipment 
                      if eq.get('common', {}).get('ID', '').startswith('SMEN_')]
            
            # 主機コンボボックスの更新
            self.main_engine_combo.clear()
            self.main_engine_combo.addItem("機関を選択してください", "")
            
            for engine in engines:
                engine_id = engine.get('common', {}).get('ID', '')
                engine_name = engine.get('common', {}).get('名前', engine_id)
                self.main_engine_combo.addItem(f"{engine_name} ({engine_id})", engine_id)

        except Exception as e:
            print(f"機関装備読み込みエラー: {e}")

    def add_auxiliary_engine(self):
        """補機装備を追加"""
        aux_widget = QWidget()
        aux_layout = QHBoxLayout(aux_widget)
        
        # 補機選択コンボボックス
        aux_combo = QComboBox()
        aux_combo.addItem("補機を選択してください", "")
        
        # 機関装備データを読み込み
        if self.app_controller:
            try:
                all_equipment = self.app_controller.equipment_model.get_all_equipment()
                engines = [eq for eq in all_equipment 
                          if eq.get('common', {}).get('ID', '').startswith('SMEN_')]
                
                for engine in engines:
                    engine_id = engine.get('common', {}).get('ID', '')
                    engine_name = engine.get('common', {}).get('名前', engine_id)
                    aux_combo.addItem(f"{engine_name} ({engine_id})", engine_id)
            except Exception as e:
                print(f"補機装備読み込みエラー: {e}")
        
        # 数量選択
        aux_count = QSpinBox()
        aux_count.setRange(1, 5)
        aux_count.setValue(1)
        aux_count.setSuffix(" 基")
        
        # 削除ボタン
        remove_button = QPushButton("削除")
        remove_button.clicked.connect(lambda: self.remove_auxiliary_engine(aux_widget))
        
        aux_layout.addWidget(QLabel("補機:"))
        aux_layout.addWidget(aux_combo)
        aux_layout.addWidget(QLabel("数量:"))
        aux_layout.addWidget(aux_count)
        aux_layout.addWidget(remove_button)
        
        # ウィジェットをリストに追加
        self.auxiliary_engines.append({
            'widget': aux_widget,
            'combo': aux_combo,
            'count': aux_count
        })
        
        # レイアウトに追加
        self.aux_engine_layout.addWidget(aux_widget)

    def remove_auxiliary_engine(self, widget):
        """補機装備を削除"""
        # リストから削除
        self.auxiliary_engines = [aux for aux in self.auxiliary_engines 
                                 if aux['widget'] != widget]
        
        # レイアウトから削除
        self.aux_engine_layout.removeWidget(widget)
        widget.deleteLater()

    def create_new_engine(self):
        """新しい機関装備を作成（装備フォームを開く）"""
        if self.app_controller:
            # 装備フォームを開いて機関装備を作成
            from views.equipment_form import EquipmentForm
            engine_form = EquipmentForm(self, self.app_controller)
            
            # 機関装備タイプを事前選択
            index = engine_form.equipment_type_combo.findText("主機")
            if index >= 0:
                engine_form.equipment_type_combo.setCurrentIndex(index)
            else:
                # "主機"がない場合は最初の機関関連タイプを探す
                for i in range(engine_form.equipment_type_combo.count()):
                    text = engine_form.equipment_type_combo.itemText(i)
                    if "機関" in text or "エンジン" in text or "主機" in text:
                        engine_form.equipment_type_combo.setCurrentIndex(i)
                        break
            
            engine_form.show()
            
            # 作成完了後に機関一覧を更新
            engine_form.equipment_saved.connect(self.load_available_engines)

    def get_engine_data(self):
        """機関装備データを取得"""
        engine_data = {
            'main_engine_id': self.main_engine_combo.currentData() or '',
            'main_engine_count': self.main_engine_count_spin.value(),
            'auxiliary_engine_ids': [],
            'auxiliary_engine_counts': []
        }
        
        # 補機データを収集
        for aux in self.auxiliary_engines:
            engine_id = aux['combo'].currentData()
            if engine_id:
                engine_data['auxiliary_engine_ids'].append(engine_id)
                engine_data['auxiliary_engine_counts'].append(aux['count'].value())
        
        return engine_data

    def set_engine_data(self, data):
        """機関装備データを設定"""
        # 主機設定
        main_engine_id = data.get('main_engine_id', '')
        if main_engine_id:
            index = self.main_engine_combo.findData(main_engine_id)
            if index >= 0:
                self.main_engine_combo.setCurrentIndex(index)
        
        self.main_engine_count_spin.setValue(data.get('main_engine_count', 1))
        
        # 既存の補機をクリア
        for aux in self.auxiliary_engines[:]:
            self.remove_auxiliary_engine(aux['widget'])
        
        # 補機設定
        aux_ids = data.get('auxiliary_engine_ids', [])
        aux_counts = data.get('auxiliary_engine_counts', [])
        
        for i, engine_id in enumerate(aux_ids):
            self.add_auxiliary_engine()
            if self.auxiliary_engines:
                last_aux = self.auxiliary_engines[-1]
                
                # 機関ID設定
                index = last_aux['combo'].findData(engine_id)
                if index >= 0:
                    last_aux['combo'].setCurrentIndex(index)
                
                # 数量設定
                if i < len(aux_counts):
                    last_aux['count'].setValue(aux_counts[i])