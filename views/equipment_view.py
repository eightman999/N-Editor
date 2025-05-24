from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QDialog, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor

from .equipment_form import EquipmentForm

class EquipmentView(QWidget):
    """装備管理ビュー"""

    # シグナル定義
    equipment_selected = pyqtSignal(str)  # 装備選択時（装備IDを送信）

    def __init__(self, parent=None, app_controller=None):
        super(EquipmentView, self).__init__(parent)

        # コントローラーの設定
        self.app_controller = app_controller

        # 選択中の装備タイプ
        self.current_type = None

        # UI初期化
        self.init_ui()

        # データの読み込み
        self.load_equipment_types()

    def init_ui(self):
        """UIの初期化"""
        # メインレイアウト
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # ヘッダー部分（タイプ選択とボタン）
        header_layout = QHBoxLayout()

        # 装備タイプ選択
        self.type_label = QLabel("装備タイプ:")
        header_layout.addWidget(self.type_label)

        self.type_combo = QComboBox()
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        header_layout.addWidget(self.type_combo)

        # スペーサー
        header_layout.addStretch(1)

        # 各種ボタン
        self.add_button = QPushButton("新規追加")
        self.add_button.clicked.connect(self.on_add_clicked)
        header_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("編集")
        self.edit_button.clicked.connect(self.on_edit_clicked)
        header_layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("削除")
        self.delete_button.clicked.connect(self.on_delete_clicked)
        header_layout.addWidget(self.delete_button)

        self.export_button = QPushButton("エクスポート")
        self.export_button.clicked.connect(self.on_export_clicked)
        header_layout.addWidget(self.export_button)

        self.import_button = QPushButton("インポート")
        self.import_button.clicked.connect(self.on_import_clicked)
        header_layout.addWidget(self.import_button)

        main_layout.addLayout(header_layout)

        # 装備一覧テーブル
        self.equipment_table = QTableWidget()
        self.equipment_table.setColumnCount(5)  # ID, 名前, 開発年, 開発国, 重量
        self.equipment_table.setHorizontalHeaderLabels(["ID", "名称", "開発年", "開発国", "重量(kg)"])

        # テーブルの設定
        self.equipment_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.equipment_table.setSelectionMode(QTableWidget.SingleSelection)
        self.equipment_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.equipment_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # 名前列を拡大

        # ダブルクリックでの選択処理
        self.equipment_table.doubleClicked.connect(self.on_table_double_clicked)

        main_layout.addWidget(self.equipment_table)

    def load_equipment_types(self):
        """装備タイプの読み込み"""
        self.type_combo.clear()

        # 全タイプ表示用の項目
        self.type_combo.addItem("全タイプ", None)

        # コントローラーから装備タイプを取得
        if self.app_controller:
            # キー名→表示名のマッピングを取得
            type_mapping = self.app_controller.get_equipment_type_mapping()
            
            # 表示名でソートして追加
            for key, display_name in sorted(type_mapping.items(), key=lambda x: x[1]):
                self.type_combo.addItem(display_name, key)
        else:
            # 従来の方法（モデル直接使用）
            from models.equipment_model import EquipmentModel
            equipment_model = EquipmentModel()
            equipment_types = equipment_model.get_equipment_types()

            # 装備タイプをコンボボックスに追加（従来方式では表示名とキー名が同じ）
            for eq_type in sorted(equipment_types):
                self.type_combo.addItem(eq_type, eq_type)

    def load_equipment_list(self):
        """装備リストの読み込み"""
        self.equipment_table.setRowCount(0)  # テーブルをクリア

        # コントローラーから装備データを取得
        if self.app_controller:
            equipment_list = self.app_controller.get_all_equipment(
                None if self.type_combo.currentIndex() == 0 else self.current_type
            )
        else:
            # 従来の方法（モデル直接使用）
            from models.equipment_model import EquipmentModel
            equipment_model = EquipmentModel()
            equipment_list = equipment_model.get_all_equipment(
                None if self.type_combo.currentIndex() == 0 else self.current_type
            )

        # テーブルに追加
        for row, equipment in enumerate(equipment_list):
            common = equipment.get('common', {})

            self.equipment_table.insertRow(row)

            # IDセル
            id_item = QTableWidgetItem(common.get('ID', ''))
            self.equipment_table.setItem(row, 0, id_item)

            # 名前セル
            name_item = QTableWidgetItem(common.get('名前', ''))
            self.equipment_table.setItem(row, 1, name_item)

            # 開発年セル
            year_item = QTableWidgetItem(str(common.get('開発年', '')))
            self.equipment_table.setItem(row, 2, year_item)

            # 開発国セル
            country_item = QTableWidgetItem(common.get('開発国', ''))
            self.equipment_table.setItem(row, 3, country_item)

            # 重量セル
            weight_item = QTableWidgetItem(str(common.get('重量', '')))
            self.equipment_table.setItem(row, 4, weight_item)

            # 装備タイプによって背景色を変える（軽い視認性向上）
            eq_type = equipment.get('equipment_type', '')

            # 装備タイプに基づいて色分け（例）
            if '砲' in eq_type:
                bg_color = QColor(240, 240, 255)  # 薄い青
            elif '魚雷' in eq_type:
                bg_color = QColor(240, 255, 240)  # 薄い緑
            elif 'ミサイル' in eq_type:
                bg_color = QColor(255, 240, 240)  # 薄い赤
            elif any(x in eq_type for x in ['水上機', '艦上偵察機', '回転翼機']):
                bg_color = QColor(255, 255, 240)  # 薄い黄
            else:
                bg_color = QColor(255, 255, 255)  # 白

            # 背景色を設定
            for col in range(self.equipment_table.columnCount()):
                self.equipment_table.item(row, col).setBackground(bg_color)

    def on_type_changed(self, index):
        """装備タイプ変更時の処理"""
        if index == 0:
            # 全タイプ
            self.current_type = None
        else:
            # キー名を取得
            self.current_type = self.type_combo.currentData()

        # 装備リストを再読み込み
        self.load_equipment_list()

    def on_add_clicked(self):
        """新規追加ボタンの処理"""
        # 装備フォームダイアログを作成
        dialog = QDialog(self)
        dialog.setWindowTitle("装備データ登録")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(500)

        layout = QVBoxLayout()
        dialog.setLayout(layout)

        # コントローラーを渡して装備フォームを作成
        form = EquipmentForm(dialog, self.app_controller)
        layout.addWidget(form)

        # 保存完了時の処理を接続
        form.equipment_saved.connect(lambda: self.load_equipment_list())
        form.equipment_saved.connect(dialog.accept)

        # ダイアログを表示
        dialog.exec_()

    def on_edit_clicked(self):
        """編集ボタンの処理"""
        # 選択中の装備を取得
        selected_rows = self.equipment_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "情報", "編集する装備を選択してください。")
            return

        # 選択中の装備ID
        row = selected_rows[0].row()
        equipment_id = self.equipment_table.item(row, 0).text()

        # 装備データを取得
        if self.app_controller:
            equipment_data = self.app_controller.load_equipment(equipment_id)
        else:
            # 従来の方法（モデル直接使用）
            from models.equipment_model import EquipmentModel
            equipment_model = EquipmentModel()
            equipment_data = equipment_model.load_equipment(equipment_id)

        if not equipment_data:
            QMessageBox.warning(self, "エラー", f"装備ID '{equipment_id}' のデータが見つかりません。")
            return

        # 装備フォームダイアログを作成
        dialog = QDialog(self)
        dialog.setWindowTitle(f"装備編集: {equipment_id}")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(500)

        layout = QVBoxLayout()
        dialog.setLayout(layout)

        # コントローラーを渡して装備フォームを作成
        form = EquipmentForm(dialog, self.app_controller)
        layout.addWidget(form)

        # データを設定
        equipment_type = equipment_data.get('equipment_type', '')
        type_index = form.equipment_type_combo.findText(equipment_type)
        if type_index >= 0:
            form.equipment_type_combo.setCurrentIndex(type_index)
            form.on_equipment_type_changed()  # フォームを再構築

        # フォームにデータ設定
        form.set_form_data(equipment_data)

        # 保存完了時の処理を接続
        form.equipment_saved.connect(lambda: self.load_equipment_list())
        form.equipment_saved.connect(dialog.accept)

        # ダイアログを表示
        dialog.exec_()

    def on_delete_clicked(self):
        """削除ボタンの処理"""
        # 選択中の装備を取得
        selected_rows = self.equipment_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "情報", "削除する装備を選択してください。")
            return

        # 選択中の装備ID
        row = selected_rows[0].row()
        equipment_id = self.equipment_table.item(row, 0).text()
        equipment_name = self.equipment_table.item(row, 1).text()

        # 確認ダイアログ
        reply = QMessageBox.question(
            self, "削除確認",
            f"装備「{equipment_name}」(ID: {equipment_id})を削除しますか？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # コントローラーを使用して削除
            if self.app_controller:
                if self.app_controller.delete_equipment(equipment_id):
                    QMessageBox.information(self, "削除完了", f"装備「{equipment_name}」を削除しました。")
                    self.load_equipment_list()  # リストを更新
                else:
                    QMessageBox.warning(self, "削除エラー", f"装備「{equipment_name}」の削除に失敗しました。")
            else:
                # 従来の方法（モデル直接使用）
                from models.equipment_model import EquipmentModel
                equipment_model = EquipmentModel()
                if equipment_model.delete_equipment(equipment_id):
                    QMessageBox.information(self, "削除完了", f"装備「{equipment_name}」を削除しました。")
                    self.load_equipment_list()  # リストを更新
                else:
                    QMessageBox.warning(self, "削除エラー", f"装備「{equipment_name}」の削除に失敗しました。")

    def on_export_clicked(self):
        """エクスポートボタンの処理"""
        # 選択中の装備を取得
        selected_rows = self.equipment_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "情報", "エクスポートする装備を選択してください。")
            return

        # 選択中の装備ID
        row = selected_rows[0].row()
        equipment_id = self.equipment_table.item(row, 0).text()

        # 装備データを取得
        if self.app_controller:
            equipment_data = self.app_controller.load_equipment(equipment_id)
        else:
            # 従来の方法（モデル直接使用）
            from models.equipment_model import EquipmentModel
            equipment_model = EquipmentModel()
            equipment_data = equipment_model.load_equipment(equipment_id)

        if not equipment_data:
            QMessageBox.warning(self, "エラー", f"装備ID '{equipment_id}' のデータが見つかりません。")
            return

        # 保存先の選択
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "装備データエクスポート", f"{equipment_id}.json", "JSON Files (*.json)", options=options
        )

        if not file_name:
            return

        # エクスポート実行
        try:
            import json
            with open(file_name, 'w', encoding='utf-8') as f:
                json.dump(equipment_data, f, ensure_ascii=False, indent=2)

            QMessageBox.information(self, "エクスポート完了", f"装備データを '{file_name}' にエクスポートしました。")
        except Exception as e:
            QMessageBox.critical(self, "エクスポートエラー", f"エクスポートに失敗しました。\n{e}")

    def on_import_clicked(self):
        """インポートボタンの処理"""
        # ファイル選択
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "装備データインポート", "", "JSON Files (*.json)", options=options
        )

        if not file_name:
            return

        # インポート実行
        try:
            import json
            import os

            with open(file_name, 'r', encoding='utf-8') as f:
                equipment_data = json.load(f)

            # 基本的な検証
            if not isinstance(equipment_data, dict) or 'equipment_type' not in equipment_data or 'common' not in equipment_data:
                raise ValueError("無効な装備データ形式です。")

            # コントローラーを使用して装備を保存
            if self.app_controller:
                if self.app_controller.save_equipment(equipment_data):
                    equipment_id = equipment_data.get('common', {}).get('ID', '')
                    QMessageBox.information(self, "インポート完了", f"装備データ '{equipment_id}' をインポートしました。")
                    self.load_equipment_list()  # リストを更新
                else:
                    QMessageBox.warning(self, "インポートエラー", "装備データの保存に失敗しました。")
            else:
                # 従来の方法（モデル直接使用）
                from models.equipment_model import EquipmentModel
                equipment_model = EquipmentModel()

                # 装備タイプの確認
                equipment_type = equipment_data.get('equipment_type', '')
                if equipment_type not in equipment_model.get_equipment_types():
                    raise ValueError(f"未知の装備タイプ '{equipment_type}' です。")

                # 装備IDの確認
                equipment_id = equipment_data.get('common', {}).get('ID', '')
                if not equipment_id:
                    raise ValueError("装備IDが指定されていません。")

                # 既存データの確認
                existing_data = equipment_model.load_equipment(equipment_id)
                if existing_data:
                    reply = QMessageBox.question(
                        self, "上書き確認",
                        f"装備ID '{equipment_id}' は既に存在します。上書きしますか？",
                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                    )
                    if reply != QMessageBox.Yes:
                        return

                # データ保存
                if equipment_model.save_equipment(equipment_data):
                    QMessageBox.information(self, "インポート完了", f"装備データ '{equipment_id}' をインポートしました。")
                    self.load_equipment_list()  # リストを更新
                else:
                    QMessageBox.warning(self, "インポートエラー", f"装備データ '{equipment_id}' の保存に失敗しました。")

        except Exception as e:
            QMessageBox.critical(self, "インポートエラー", f"インポートに失敗しました。\n{e}")

    def on_table_double_clicked(self, index):
        """テーブルダブルクリック時の処理"""
        row = index.row()
        equipment_id = self.equipment_table.item(row, 0).text()

        # 選択シグナルを発行
        self.equipment_selected.emit(equipment_id)

        # 編集ダイアログを表示
        self.on_edit_clicked()