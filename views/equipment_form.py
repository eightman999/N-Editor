import os

from PyQt5.QtWidgets import (QWidget, QFormLayout, QLineEdit, QComboBox,
                             QSpinBox, QDoubleSpinBox, QTabWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QGroupBox,
                             QScrollArea, QMessageBox, QFileDialog, QApplication, QDialog, QListWidget)
from PyQt5.QtCore import Qt, pyqtSignal

class EquipmentForm(QWidget):
    """装備データ登録用フォーム"""
    equipment_saved = pyqtSignal(str)  # 装備保存時のシグナル（装備IDを送信）

    def __init__(self, parent=None, app_controller=None):
        super(EquipmentForm, self).__init__(parent)
        self.app_controller = app_controller
        self.init_ui()
        self.load_equipment_templates()

    def init_ui(self):
        """UIの初期化"""
        # メインレイアウト
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # 上部：装備タイプ選択
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("装備タイプ:"))
        self.equipment_type_combo = QComboBox()
        type_layout.addWidget(self.equipment_type_combo)

        # カテゴリ選択ボタン
        self.select_category_button = QPushButton("カテゴリ選択")
        self.select_category_button.clicked.connect(self.show_category_selection_dialog)
        type_layout.addWidget(self.select_category_button)

        # 装備タイプ変更時の処理を接続
        self.equipment_type_combo.currentIndexChanged.connect(self.on_equipment_type_changed)

        main_layout.addLayout(type_layout)

        # 装備データ入力用スクロールエリア
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)

        self.form_container = QWidget()
        self.form_layout = QVBoxLayout(self.form_container)

        # 共通要素グループ
        self.common_group = QGroupBox("基本情報")
        self.common_layout = QFormLayout()
        self.common_group.setLayout(self.common_layout)
        self.form_layout.addWidget(self.common_group)

        # 固有要素グループ
        self.specific_group = QGroupBox("装備固有情報")
        self.specific_layout = QFormLayout()
        self.specific_group.setLayout(self.specific_layout)
        self.form_layout.addWidget(self.specific_group)

        # ステータス表示タブ
        self.stats_tabs = QTabWidget()
        self.form_layout.addWidget(self.stats_tabs)

        # タブページの作成
        self.create_stats_tabs()

        scroll_area.setWidget(self.form_container)

        # 下部ボタン
        button_layout = QHBoxLayout()
        # ボタンの設定コードは変更なし
        main_layout.addLayout(button_layout)

        # フォーム入力フィールドの保存用辞書
        self.common_fields = {}
        self.specific_fields = {}

    def create_stats_tabs(self):
        """ステータス表示用タブの作成"""
        # 単純加算タブ
        add_tab = QWidget()
        add_layout = QFormLayout(add_tab)
        self.stats_tabs.addTab(add_tab, "単純加算")

        # %調整タブ
        multiply_tab = QWidget()
        multiply_layout = QFormLayout(multiply_tab)
        self.stats_tabs.addTab(multiply_tab, "%調整")

        # 全装備平均タブ
        average_tab = QWidget()
        average_layout = QFormLayout(average_tab)
        self.stats_tabs.addTab(average_tab, "全装備平均")

        # ステータス項目のサンプル（実際にはゲームデータから取得）
        self.stats_fields = {
            'add': {},      # 単純加算用フィールド
            'multiply': {}, # %調整用フィールド
            'average': {}   # 全装備平均用フィールド
        }

        # ステータス一覧ファイルから読み込み
        self.load_stats_definitions()

        # 各タブにフィールドを追加
        for stat_name, stat_desc in self.stats_definitions.items():
            # 単純加算タブ
            add_field = QDoubleSpinBox()
            add_field.setRange(-1000, 1000)
            add_field.setDecimals(3)
            add_field.setSingleStep(0.1)
            add_layout.addRow(f"{stat_name} ({stat_desc}):", add_field)
            self.stats_fields['add'][stat_name] = add_field

            # %調整タブ
            multiply_field = QDoubleSpinBox()
            multiply_field.setRange(-100, 100)
            multiply_field.setDecimals(3)
            multiply_field.setSingleStep(0.1)
            multiply_field.setValue(0)
            multiply_layout.addRow(f"{stat_name} ({stat_desc}):", multiply_field)
            self.stats_fields['multiply'][stat_name] = multiply_field

            # 全装備平均タブ
            average_field = QDoubleSpinBox()
            average_field.setRange(-1000, 1000)
            average_field.setDecimals(3)
            average_field.setSingleStep(0.1)
            average_field.setValue(0)
            average_layout.addRow(f"{stat_name} ({stat_desc}):", average_field)
            self.stats_fields['average'][stat_name] = average_field

    def load_stats_definitions(self):
        """ステータス定義の読み込み"""
        self.stats_definitions = {}

        try:
            # ルートディレクトリを取得してファイルパスを構築
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
                                self.stats_definitions[stat_name] = stat_desc
            else:
                print(f"ステータス定義ファイルが見つかりません: {stats_file}")
                # デフォルト値を設定
                self.stats_definitions = {
                    'build_cost_ic': 'Production Cost',
                    'reliability': 'Reliability',
                    'naval_speed': 'Max Speed',
                    'lg_attack': 'Light gun attack',
                    'hg_attack': 'Heavy gun attack'
                }
        except Exception as e:
            print(f"ステータス定義の読み込みエラー: {e}")
            # エラー時はデフォルト値を設定
            self.stats_definitions = {
                'build_cost_ic': 'Production Cost',
                'reliability': 'Reliability',
                'naval_speed': 'Max Speed',
                'lg_attack': 'Light gun attack',
                'hg_attack': 'Heavy gun attack'
            }

    def load_equipment_templates(self):
        """装備テンプレートの読み込み"""
        try:
            # AppControllerが利用可能であれば、そこから装備タイプを取得
            if self.app_controller:
                equipment_types = self.app_controller.get_equipment_types()
                self.equipment_templates = {}

                for eq_type in equipment_types:
                    self.equipment_type_combo.addItem(eq_type)
                return

            # 従来の方法（AppControllerがない場合）
            with open('paste.txt', 'r', encoding='utf-8') as f:
                content = f.read()

            # YAMLライクな形式をパースする簡易実装
            self.equipment_templates = {}
            current_type = None

            for line in content.split('\n'):
                if line.strip() and not line.startswith('#'):
                    if ':' in line and not line.startswith(' '):
                        # トップレベルの定義（装備タイプ）
                        current_type = line.split(':')[0].strip()
                        self.equipment_templates[current_type] = {'common_elements': {}, 'specific_elements': {}}
                    elif 'id_prefix:' in line and current_type:
                        prefix = line.split('id_prefix:')[1].strip()
                        self.equipment_templates[current_type]['id_prefix'] = prefix
                    elif 'common_elements:' in line or 'specific_elements:' in line:
                        # セクション定義は無視（パース簡易化のため）
                        pass

            # コンボボックスに追加
            for eq_type in self.equipment_templates.keys():
                self.equipment_type_combo.addItem(eq_type)

        except Exception as e:
            print(f"装備テンプレート読み込みエラー: {e}")
            QMessageBox.warning(self, "読み込みエラー", f"装備テンプレートの読み込みに失敗しました: {e}")



    def clear_form_fields(self):
        """フォームフィールドのクリア"""
        # 共通要素のクリア
        while self.common_layout.count():
            item = self.common_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 固有要素のクリア
        while self.specific_layout.count():
            item = self.specific_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # フィールド辞書のクリア
        self.common_fields = {}
        self.specific_fields = {}



    def clear_form(self):
        """フォームの全クリア"""
        self.on_equipment_type_changed()  # 現在のタイプのフォームを再構築

        # ステータスフィールドのクリア
        for mode in self.stats_fields:
            for field in self.stats_fields[mode].values():
                if isinstance(field, QDoubleSpinBox) or isinstance(field, QSpinBox):
                    field.setValue(0)
                elif isinstance(field, QLineEdit):
                    field.clear()
                elif isinstance(field, QComboBox):
                    field.setCurrentIndex(0)

    def get_form_data(self):
        """フォームデータの取得"""
        data = {
            'equipment_type': self.equipment_type_combo.currentText(),
            'common': {},
            'specific': {},
            'stats': {
                'add_stats': {},
                'multiply_stats': {},
                'add_average_stats': {}
            }
        }

        # 共通フィールドの取得
        for field_name, field in self.common_fields.items():
            if isinstance(field, QLineEdit):
                data['common'][field_name] = field.text()
            elif isinstance(field, QDoubleSpinBox):
                data['common'][field_name] = field.value()
            elif isinstance(field, QSpinBox):
                data['common'][field_name] = field.value()
            elif isinstance(field, QComboBox):
                data['common'][field_name] = field.currentText()

        # 固有フィールドの取得
        for field_name, field in self.specific_fields.items():
            if isinstance(field, QLineEdit):
                data['specific'][field_name] = field.text()
            elif isinstance(field, QDoubleSpinBox):
                data['specific'][field_name] = field.value()
            elif isinstance(field, QSpinBox):
                data['specific'][field_name] = field.value()
            elif isinstance(field, QComboBox):
                data['specific'][field_name] = field.currentText()

        # ステータスの取得
        for stat_name in self.stats_definitions.keys():
            if stat_name in self.stats_fields['add']:
                data['stats']['add_stats'][stat_name] = self.stats_fields['add'][stat_name].value()

            if stat_name in self.stats_fields['multiply']:
                data['stats']['multiply_stats'][stat_name] = self.stats_fields['multiply'][stat_name].value()

            if stat_name in self.stats_fields['average']:
                data['stats']['add_average_stats'][stat_name] = self.stats_fields['average'][stat_name].value()

        return data

    def save_equipment(self):
        """装備データの保存"""
        data = self.get_form_data()

        # 必須フィールドの確認
        if not data['common'].get('名前') or not data['common'].get('ID'):
            QMessageBox.warning(self, "入力エラー", "装備名称とIDは必須です。")
            return

        # AppControllerを使用して装備を保存
        if self.app_controller:
            if self.app_controller.save_equipment(data):
                equipment_id = data['common']['ID']
                QMessageBox.information(self, "保存成功", f"装備データを保存しました。\nID: {equipment_id}")
                self.equipment_saved.emit(equipment_id)
            else:
                QMessageBox.critical(self, "保存エラー", "データの保存に失敗しました。")
            return

        # 従来の方法（AppControllerがない場合）
        try:
            import os
            import json

            # 保存先ディレクトリの作成
            equipment_type = data['equipment_type']
            id_prefix = self.equipment_templates[equipment_type]['id_prefix']

            # 保存ディレクトリの処理
            base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'equipments', id_prefix)
            os.makedirs(base_dir, exist_ok=True)

            # ファイル名は装備IDを使用
            file_name = f"{data['common']['ID']}.json"
            file_path = os.path.join(base_dir, file_name)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            QMessageBox.information(self, "保存成功", f"装備データを保存しました。\n{file_path}")
            self.equipment_saved.emit(data['common']['ID'])
        except Exception as e:
            QMessageBox.critical(self, "保存エラー", f"データの保存に失敗しました。\n{e}")

    def load_equipment(self):
        """装備データの読み込み"""
        # ファイル選択ダイアログを表示
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "装備データ読み込み", "", "JSON Files (*.json)", options=options
        )

        if not file_name:
            return

        # AppControllerを使用して装備データを読み込む
        if self.app_controller:
            # ファイル名からIDを抽出
            import os
            equipment_id = os.path.splitext(os.path.basename(file_name))[0]

            # 装備データを読み込み
            equipment_data = self.app_controller.load_equipment(equipment_id)

            if equipment_data:
                self.set_form_data(equipment_data)
                QMessageBox.information(self, "読み込み成功", f"装備データを読み込みました。\nID: {equipment_id}")
            else:
                QMessageBox.critical(self, "読み込みエラー", f"装備ID '{equipment_id}' のデータの読み込みに失敗しました。")
            return

        # 従来の方法（AppControllerがない場合）
        try:
            import json
            with open(file_name, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 装備タイプの設定
            equipment_type = data.get('equipment_type')
            index = self.equipment_type_combo.findText(equipment_type)
            if index >= 0:
                self.equipment_type_combo.setCurrentIndex(index)
                self.on_equipment_type_changed()  # フォームの再構築

            # フォームにデータ設定
            self.set_form_data(data)

            QMessageBox.information(self, "読み込み成功", f"装備データを読み込みました。\n{file_name}")
        except Exception as e:
            QMessageBox.critical(self, "読み込みエラー", f"データの読み込みに失敗しました。\n{e}")

    def set_form_data(self, data):
        """フォームにデータを設定"""
        # 共通フィールドの設定
        for field_name, value in data.get('common', {}).items():
            if field_name in self.common_fields:
                field = self.common_fields[field_name]
                if isinstance(field, QLineEdit):
                    field.setText(str(value))
                elif isinstance(field, QDoubleSpinBox):
                    field.setValue(float(value))
                elif isinstance(field, QSpinBox):
                    field.setValue(int(float(value)))  # floatからintへの変換
                elif isinstance(field, QComboBox):
                    index = field.findText(str(value))
                    if index >= 0:
                        field.setCurrentIndex(index)

        # 固有フィールドの設定も同様に修正
        for field_name, value in data.get('specific', {}).items():
            if field_name in self.specific_fields:
                field = self.specific_fields[field_name]
                if isinstance(field, QLineEdit):
                    field.setText(str(value))
                elif isinstance(field, QDoubleSpinBox):
                    field.setValue(float(value))
                elif isinstance(field, QSpinBox):
                    field.setValue(int(float(value)))  # floatからintへの変換
                elif isinstance(field, QComboBox):
                    index = field.findText(str(value))
                    if index >= 0:
                        field.setCurrentIndex(index)


    def generate_specific_fields(self, equipment_type):
        """装備タイプ固有フィールドの生成"""
        try:
            # 装備タイプに基づく固有フィールドの定義
            specific_fields = {}

            # 砲系統
            if '砲' in equipment_type:
                specific_fields = {
                    '砲弾重量_kg': (QDoubleSpinBox, {'suffix': ' kg', 'range': (0, 1000)}),
                    '初速_mps': (QDoubleSpinBox, {'suffix': ' m/s', 'range': (0, 2000)}),
                    '毎分発射数': (QSpinBox, {'range': (1, 1000)}),
                    '砲口口径_cm': (QDoubleSpinBox, {'suffix': ' cm', 'range': (1, 100)}),
                    '口径': (QSpinBox, {'range': (1, 100)}),
                    '砲身数': (QSpinBox, {'range': (1, 10)}),
                    '最大仰俯角': (QLineEdit, {}),
                    '砲塔数': (QSpinBox, {'range': (1, 10)})
                }
            # 魚雷系
            elif '魚雷' in equipment_type:
                specific_fields = {
                    '炸薬重量_kg': (QDoubleSpinBox, {'suffix': ' kg', 'range': (0, 1000)}),
                    '最大射程_m': (QDoubleSpinBox, {'suffix': ' m', 'range': (0, 50000)}),
                    '雷速_kts': (QDoubleSpinBox, {'suffix': ' kts', 'range': (0, 100)}),
                    '口径_cm': (QDoubleSpinBox, {'suffix': ' cm', 'range': (1, 100)}),
                    '砲塔数': (QSpinBox, {'range': (1, 10)})
                }
            # ミサイル系
            elif 'ミサイル' in equipment_type:
                specific_fields = {
                    '炸薬重量_kg': (QDoubleSpinBox, {'suffix': ' kg', 'range': (0, 1000)}),
                    '最大射程_km': (QDoubleSpinBox, {'suffix': ' km', 'range': (0, 500)}),
                    '初速_mps': (QDoubleSpinBox, {'suffix': ' m/s', 'range': (0, 2000)}),
                    '毎分発射数': (QSpinBox, {'range': (1, 100)}),
                    '口径_cm': (QDoubleSpinBox, {'suffix': ' cm', 'range': (1, 100)}),
                    '砲塔数': (QSpinBox, {'range': (1, 100)})
                }
            # 航空機系
            elif any(x in equipment_type for x in ['水上機', '艦上偵察機', '回転翼機', '対潜哨戒機', '大型飛行艇']):
                specific_fields = {
                    '最高速度_kmh': (QDoubleSpinBox, {'suffix': ' km/h', 'range': (0, 2000)}),
                    '航続距離_km': (QDoubleSpinBox, {'suffix': ' km', 'range': (0, 10000)}),
                    'LgAttack': (QSpinBox, {'range': (0, 100)}),
                    'AAAttack': (QSpinBox, {'range': (0, 100)}),
                    'Fuel': (QDoubleSpinBox, {'range': (0, 5000)})
                }
            # 対潜系
            elif any(x in equipment_type for x in ['爆雷', '対潜迫撃砲', '爆雷投射機']):
                specific_fields = {
                    '砲弾重量_kg': (QDoubleSpinBox, {'suffix': ' kg', 'range': (0, 1000)}),
                    '炸薬量_kg': (QDoubleSpinBox, {'suffix': ' kg', 'range': (0, 500)}),
                    '射程_m': (QDoubleSpinBox, {'suffix': ' m', 'range': (0, 5000)})
                }
            # センサー系
            elif any(x in equipment_type for x in ['ソナー', '電探', '測距儀']):
                specific_fields = {
                    '探知距離_km': (QDoubleSpinBox, {'suffix': ' km', 'range': (0, 500)}),
                    '出力_dB': (QDoubleSpinBox, {'suffix': ' dB', 'range': (0, 200)})
                }
                if '測距儀' in equipment_type:
                    specific_fields['基線長_cm'] = (QDoubleSpinBox, {'suffix': ' cm', 'range': (0, 1000)})
            # 機関系
            elif '機関' in equipment_type:
                specific_fields = {
                    '機関出力_hp': (QDoubleSpinBox, {'suffix': ' hp', 'range': (0, 500000)}),
                    '燃料種別': (QComboBox, {'items': ['重油', '軽油', '石炭', '原子力']})
                }
            # バルジ系
            elif 'バルジ' in equipment_type:
                specific_fields = {
                    '装甲圧_mm': (QDoubleSpinBox, {'suffix': ' mm', 'range': (0, 500)})
                }
            # 格納庫
            elif '格納庫' in equipment_type:
                specific_fields = {
                    '格納庫サイズ': (QLineEdit, {})
                }
            # その他装備
            else:
                # その他のカテゴリーのフィールド
                specific_fields = {
                    'その他パラメータ1': (QLineEdit, {}),
                    'その他パラメータ2': (QDoubleSpinBox, {'range': (0, 1000)}),
                    'その他パラメータ3': (QSpinBox, {'range': (0, 100)})
                }

            # フィールドの生成と追加
            for field_name, (field_type, options) in specific_fields.items():
                field = field_type()

                # フィールドタイプ別の設定
                if isinstance(field, QDoubleSpinBox):
                    if 'range' in options:
                        field.setRange(*options['range'])
                    if 'suffix' in options:
                        field.setSuffix(options['suffix'])
                    field.setDecimals(2)
                    field.setSingleStep(0.1)
                elif isinstance(field, QSpinBox):
                    if 'range' in options:
                        field.setRange(*options['range'])
                elif isinstance(field, QComboBox):
                    if 'items' in options:
                        for item in options['items']:
                            field.addItem(item)

                self.specific_layout.addRow(f"{field_name}:", field)
                self.specific_fields[field_name] = field

            # 固有フィールドが生成されたことを確認するためのログ
            print(f"装備タイプ '{equipment_type}' の固有フィールドを生成しました。フィールド数: {len(specific_fields)}")

        except Exception as e:
            print(f"固有フィールド生成エラー: {e}")
            import traceback
            traceback.print_exc()

    def generate_common_fields(self, equipment_type):
        """共通フィールドの生成"""
        try:
            # 共通フィールド
            common_fields = [
                '名前', 'ID', '重量', '人員', '開発年', '開発国',
                '必要資源_鉄', '必要資源_クロム', '必要資源_アルミ',
                '必要資源_タングステン', '必要資源_ゴム'
            ]

            for field_name in common_fields:
                if field_name in ['名前', 'ID', '開発国']:
                    field = QLineEdit()
                elif field_name in ['重量']:
                    field = QDoubleSpinBox()
                    field.setRange(0, 100000)
                    field.setSingleStep(0.1)
                    field.setSuffix(' kg')
                elif field_name in ['開発年']:
                    field = QSpinBox()
                    field.setRange(1900, 2050)
                    field.setValue(1936)  # デフォルト値（HOI4初期年）
                else:
                    field = QSpinBox()
                    field.setRange(0, 10000)

                self.common_layout.addRow(f"{field_name}:", field)
                self.common_fields[field_name] = field

            # 装備タイプも追加
            equipment_type_label = QLabel(equipment_type)
            equipment_type_label.setStyleSheet("font-weight: bold;")
            self.common_layout.addRow("装備タイプ:", equipment_type_label)
            self.common_fields['equipment_type'] = equipment_type

            print(f"装備タイプ '{equipment_type}' の共通フィールドを生成しました。")

        except Exception as e:
            print(f"共通フィールド生成エラー: {e}")
            import traceback
            traceback.print_exc()


    def on_equipment_type_changed(self):
        """装備タイプ変更時の処理"""
        print("装備タイプが変更されました")
        self.clear_form_fields()

        # 現在の装備タイプ
        current_type = self.equipment_type_combo.currentText()
        print(f"選択された装備タイプ: '{current_type}'")

        if not current_type or current_type not in self.equipment_templates:
            print(f"無効な装備タイプまたはテンプレートに存在しません: {current_type}")
            return

        try:
            # テンプレートから共通フィールドと固有フィールドを生成
            print(f"共通フィールドを生成します: {current_type}")
            self.generate_common_fields(current_type)

            print(f"固有フィールドを生成します: {current_type}")
            self.generate_specific_fields(current_type)

            # UIを強制的に更新
            self.common_group.update()
            self.specific_group.update()
            QApplication.processEvents()

            # 装備IDのプレフィックスを自動設定（元のコードを維持）
            if 'ID' in self.common_fields and 'id_prefix' in self.equipment_templates[current_type]:
                # AppControllerが利用可能であれば、次のIDを取得
                if self.app_controller:
                    next_id = self.app_controller.get_next_equipment_id(current_type)
                    if next_id:
                        self.common_fields['ID'].setText(next_id)
                        return

                # 従来の方法（AppControllerがない場合）
                prefix = self.equipment_templates[current_type]['id_prefix']
                self.common_fields['ID'].setText(f"{prefix}")
        except Exception as e:
            print(f"装備タイプ変更処理でエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()

    def show_category_selection_dialog(self):
        """カテゴリ選択ダイアログを表示"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("装備カテゴリー選択")
            dialog.setMinimumWidth(400)
            dialog.setMinimumHeight(500)

            dialog_layout = QVBoxLayout()

            # ヘッダー
            header_label = QLabel("装備カテゴリーを選択してください")
            header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            dialog_layout.addWidget(header_label)

            # 検索ボックス
            search_layout = QHBoxLayout()
            search_layout.addWidget(QLabel("検索:"))
            search_edit = QLineEdit()
            search_layout.addWidget(search_edit)
            dialog_layout.addLayout(search_layout)

            # カテゴリーリスト
            category_list = QListWidget()
            dialog_layout.addWidget(category_list)

            # カテゴリー一覧を取得
            equipment_types = []
            if self.app_controller:
                equipment_types = self.app_controller.get_equipment_types()
            else:
                # テンプレートから取得
                equipment_types = list(self.equipment_templates.keys())

            # リストに追加
            for category in sorted(equipment_types):
                category_list.addItem(category)

            # 検索機能
            def filter_categories():
                search_text = search_edit.text().lower()
                for i in range(category_list.count()):
                    item = category_list.item(i)
                    item.setHidden(search_text not in item.text().lower())

            search_edit.textChanged.connect(filter_categories)

            # ボタン
            button_layout = QHBoxLayout()

            ok_button = QPushButton("選択")
            def on_ok_clicked():
                selected_item = category_list.currentItem()
                if selected_item:
                    selected_category = selected_item.text()
                    index = self.equipment_type_combo.findText(selected_category)
                    if index >= 0:
                        self.equipment_type_combo.setCurrentIndex(index)
                        self.on_equipment_type_changed()  # フォームを更新
                dialog.accept()

            ok_button.clicked.connect(on_ok_clicked)
            button_layout.addWidget(ok_button)

            cancel_button = QPushButton("キャンセル")
            cancel_button.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_button)

            dialog_layout.addLayout(button_layout)
            dialog.setLayout(dialog_layout)

            dialog.exec_()

        except Exception as e:
            print(f"カテゴリ選択ダイアログでエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()