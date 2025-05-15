from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QDialog, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor

from .hull_form import HullForm

class HullListView(QWidget):
    """船体リスト表示ビュー"""

    # シグナル定義
    hull_selected = pyqtSignal(str)  # 船体選択時（船体IDを送信）

    def __init__(self, parent=None, app_controller=None):
        super(HullListView, self).__init__(parent)

        self.app_controller = app_controller

        # UI初期化
        self.init_ui()

        # データの読み込み
        self.load_hull_list()

    def init_ui(self):
        """UIの初期化"""
        # メインレイアウト
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # ヘッダー部分（タイトルとボタン）
        header_layout = QHBoxLayout()

        # タイトルラベル
        self.title_label = QLabel("船体リスト")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.title_label)

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

        self.import_button = QPushButton("CSVインポート")
        self.import_button.clicked.connect(self.on_import_clicked)
        header_layout.addWidget(self.import_button)

        main_layout.addLayout(header_layout)

        # 船体一覧テーブル
        self.hull_table = QTableWidget()
        self.hull_table.setColumnCount(7)  # ID, 艦級名, 種別, 開発年, 開発国, 排水量, 速力
        self.hull_table.setHorizontalHeaderLabels(["ID", "艦級名", "種別", "開発年", "開発国", "排水量(t)", "速力(kts)"])

        # テーブルの設定
        self.hull_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.hull_table.setSelectionMode(QTableWidget.SingleSelection)
        self.hull_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.hull_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # 艦級名列を拡大

        # ダブルクリックでの選択処理
        self.hull_table.doubleClicked.connect(self.on_table_double_clicked)

        main_layout.addWidget(self.hull_table)

    def load_hull_list(self):
        """船体リストの読み込み"""
        self.hull_table.setRowCount(0)  # テーブルをクリア

        # コントローラーから船体データを取得
        if self.app_controller:
            hull_list = self.app_controller.get_all_hulls()
        else:
            # 従来の方法（モデル直接使用）
            from models.hull_model import HullModel
            hull_model = HullModel()
            hull_list = hull_model.get_all_hulls()

        # テーブルに追加
        for row, hull in enumerate(hull_list):
            self.hull_table.insertRow(row)

            # IDセル
            id_item = QTableWidgetItem(hull.get('id', ''))
            self.hull_table.setItem(row, 0, id_item)

            # 艦級名セル
            name_item = QTableWidgetItem(hull.get('name', ''))
            self.hull_table.setItem(row, 1, name_item)

            # 種別セル
            type_item = QTableWidgetItem(hull.get('type', ''))
            self.hull_table.setItem(row, 2, type_item)

            # 開発年セル
            year_item = QTableWidgetItem(str(hull.get('year', '')))
            self.hull_table.setItem(row, 3, year_item)

            # 開発国セル
            country_item = QTableWidgetItem(hull.get('country', ''))
            self.hull_table.setItem(row, 4, country_item)

            # 排水量セル
            weight_item = QTableWidgetItem(str(hull.get('weight', '')))
            self.hull_table.setItem(row, 5, weight_item)

            # 速力セル
            speed_item = QTableWidgetItem(str(hull.get('speed', '')))
            self.hull_table.setItem(row, 6, speed_item)

            # 船体タイプによって背景色を変える（軽い視認性向上）
            hull_type = hull.get('type', '')

            # 艦種に基づいて色分け
            if 'BB' in hull_type:
                bg_color = QColor(240, 220, 220)  # 薄い赤（戦艦）
            elif 'CV' in hull_type:
                bg_color = QColor(220, 240, 220)  # 薄い緑（空母）
            elif 'CA' in hull_type or 'CL' in hull_type:
                bg_color = QColor(220, 220, 240)  # 薄い青（巡洋艦）
            elif 'DD' in hull_type:
                bg_color = QColor(240, 240, 220)  # 薄い黄（駆逐艦）
            elif 'SS' in hull_type:
                bg_color = QColor(240, 220, 240)  # 薄い紫（潜水艦）
            else:
                bg_color = QColor(255, 255, 255)  # 白（その他）

            # 背景色を設定
            for col in range(self.hull_table.columnCount()):
                self.hull_table.item(row, col).setBackground(bg_color)

    def on_add_clicked(self):
        """新規追加ボタンの処理"""
        # 親ウィンドウ（メインウィンドウ）に船体フォームビューへの切り替えリクエスト
        if self.parent() and hasattr(self.parent(), 'show_view'):
            self.parent().show_view("hull_form")
        else:
            # 従来の方法（ダイアログ表示）
            dialog = QDialog(self)
            dialog.setWindowTitle("船体データ登録")
            dialog.setMinimumWidth(600)
            dialog.setMinimumHeight(500)

            layout = QVBoxLayout()
            dialog.setLayout(layout)

            # コントローラーを渡して船体フォームを作成
            form = HullForm(dialog, self.app_controller)
            layout.addWidget(form)

            # 保存完了時の処理を接続
            form.hull_saved.connect(lambda: self.load_hull_list())
            form.hull_saved.connect(dialog.accept)

            # ダイアログを表示
            dialog.exec_()

    def on_edit_clicked(self):
        """編集ボタンの処理"""
        # 選択中の船体を取得
        selected_rows = self.hull_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "情報", "編集する船体を選択してください。")
            return

        # 選択中の船体ID
        row = selected_rows[0].row()
        hull_id = self.hull_table.item(row, 0).text()

        # 船体データを取得
        if self.app_controller:
            hull_data = self.app_controller.load_hull(hull_id)
        else:
            # 従来の方法（モデル直接使用）
            from models.hull_model import HullModel
            hull_model = HullModel()
            hull_data = hull_model.load_hull(hull_id)

        if not hull_data:
            QMessageBox.warning(self, "エラー", f"船体ID '{hull_id}' のデータが見つかりません。")
            return

        # 船体フォームダイアログを作成
        dialog = QDialog(self)
        dialog.setWindowTitle(f"船体編集: {hull_id}")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(500)

        layout = QVBoxLayout()
        dialog.setLayout(layout)

        # コントローラーを渡して船体フォームを作成
        form = HullForm(dialog, self.app_controller)
        layout.addWidget(form)

        # フォームにデータ設定
        form.set_form_data(hull_data)

        # 保存完了時の処理を接続
        form.hull_saved.connect(lambda: self.load_hull_list())
        form.hull_saved.connect(dialog.accept)

        # ダイアログを表示
        dialog.exec_()

    def on_delete_clicked(self):
        """削除ボタンの処理"""
        # 選択中の船体を取得
        selected_rows = self.hull_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "情報", "削除する船体を選択してください。")
            return

        # 選択中の船体ID
        row = selected_rows[0].row()
        hull_id = self.hull_table.item(row, 0).text()
        hull_name = self.hull_table.item(row, 1).text()

        # 確認ダイアログ
        reply = QMessageBox.question(
            self, "削除確認",
            f"船体「{hull_name}」(ID: {hull_id})を削除しますか？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # コントローラーを使用して削除
            if self.app_controller:
                if self.app_controller.delete_hull(hull_id):
                    QMessageBox.information(self, "削除完了", f"船体「{hull_name}」を削除しました。")
                    self.load_hull_list()  # リストを更新
                else:
                    QMessageBox.warning(self, "削除エラー", f"船体「{hull_name}」の削除に失敗しました。")
            else:
                # 従来の方法（モデル直接使用）
                from models.hull_model import HullModel
                hull_model = HullModel()
                if hull_model.delete_hull(hull_id):
                    QMessageBox.information(self, "削除完了", f"船体「{hull_name}」を削除しました。")
                    self.load_hull_list()  # リストを更新
                else:
                    QMessageBox.warning(self, "削除エラー", f"船体「{hull_name}」の削除に失敗しました。")

    def on_export_clicked(self):
        """エクスポートボタンの処理"""
        # 選択中の船体を取得
        selected_rows = self.hull_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "情報", "エクスポートする船体を選択してください。")
            return

        # 選択中の船体ID
        row = selected_rows[0].row()
        hull_id = self.hull_table.item(row, 0).text()

        # 船体データを取得
        if self.app_controller:
            hull_data = self.app_controller.load_hull(hull_id)
        else:
            # 従来の方法（モデル直接使用）
            from models.hull_model import HullModel
            hull_model = HullModel()
            hull_data = hull_model.load_hull(hull_id)

        if not hull_data:
            QMessageBox.warning(self, "エラー", f"船体ID '{hull_id}' のデータが見つかりません。")
            return

        # 保存先の選択
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "船体データエクスポート", f"{hull_id}.json", "JSON Files (*.json)", options=options
        )

        if not file_name:
            return

        # エクスポート実行
        try:
            import json
            with open(file_name, 'w', encoding='utf-8') as f:
                json.dump(hull_data, f, ensure_ascii=False, indent=2)

            QMessageBox.information(self, "エクスポート完了", f"船体データを '{file_name}' にエクスポートしました。")
        except Exception as e:
            QMessageBox.critical(self, "エクスポートエラー", f"エクスポートに失敗しました。\n{e}")

        def on_add_clicked(self):
            """新規追加ボタンの処理"""
        # 親ウィンドウ（メインウィンドウ）に船体フォームビューへの切り替えリクエスト
        if self.parent() and hasattr(self.parent(), 'show_view'):
            self.parent().show_view("hull_form")
        else:
            # 従来の方法（ダイアログ表示）
            dialog = QDialog(self)
            dialog.setWindowTitle("船体データ登録")
            dialog.setMinimumWidth(600)
            dialog.setMinimumHeight(500)

            layout = QVBoxLayout()
            dialog.setLayout(layout)

            # コントローラーを渡して船体フォームを作成
            form = HullForm(dialog, self.app_controller)
            layout.addWidget(form)

            # 保存完了時の処理を接続
            form.hull_saved.connect(lambda: self.load_hull_list())
            form.hull_saved.connect(dialog.accept)

            # ダイアログを表示
            dialog.exec_()

    def on_table_double_clicked(self, index):
        """テーブルダブルクリック時の処理"""
        row = index.row()
        hull_id = self.hull_table.item(row, 0).text()

        # 選択シグナルを発行
        self.hull_selected.emit(hull_id)

        # 編集ダイアログを表示
        self.on_edit_clicked()

    def on_import_clicked(self):
        """CSVインポートボタンの処理"""
        # ファイル選択
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "CSVファイルを開く", "", "CSV Files (*.csv)", options=options
        )

        if not file_name:
            return

        # インポート実行
        try:
            # AppControllerを使用してCSVをインポート
            if self.app_controller:
                imported_hulls = self.app_controller.import_from_csv(file_name)
                if imported_hulls:
                    QMessageBox.information(self, "インポート完了", f"{len(imported_hulls)}件の船体データをインポートしました。")
                    self.load_hull_list()  # リストを更新
                else:
                    QMessageBox.warning(self, "インポート警告", "CSVファイルからデータをインポートできませんでした。")
                return

            # 従来の方法（モデル直接使用）
            from models.hull_model import HullModel
            hull_model = HullModel()

            imported_hulls = hull_model.import_from_csv(file_name)
            if imported_hulls:
                QMessageBox.information(self, "インポート完了", f"{len(imported_hulls)}件の船体データをインポートしました。")
                self.load_hull_list()  # リストを更新
            else:
                QMessageBox.warning(self, "インポート警告", "CSVファイルからデータをインポートできませんでした。")

        except Exception as e:
            QMessageBox.critical(self, "インポートエラー", f"CSVのインポートに失敗しました。\n{e}")
