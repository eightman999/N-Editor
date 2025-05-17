from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QListWidget, QListWidgetItem,
                             QSizePolicy, QMessageBox, QTabWidget, QComboBox)
from PyQt5.QtCore import Qt

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
        self.formation_list = QListWidget()
        self.formation_list.setStyleSheet(self.equipment_list.styleSheet())
        self.formation_list.itemDoubleClicked.connect(self.on_formation_double_clicked)
        self.tab_widget.addTab(self.formation_list, "編成")

        # mod内の編成タブ
        self.mod_formation_list = QListWidget()
        self.mod_formation_list.setStyleSheet(self.equipment_list.styleSheet())
        self.mod_formation_list.itemDoubleClicked.connect(self.on_mod_formation_double_clicked)
        self.tab_widget.addTab(self.mod_formation_list, "mod内の編成")

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
            for nation in nations:
                self.nation_combo.addItem(f"{nation['tag']}: {nation['name']}", nation['tag'])

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
            if self.app_controller:
                # TODO: app_controllerに実装が必要
                mod_design_data = self.app_controller.get_nation_mod_designs(nation_tag)
                for item in mod_design_data:
                    list_item = QListWidgetItem()
                    list_item.setText(f"{item['name']} (船体: {item['hull']})")
                    list_item.setData(Qt.UserRole, item)
                    self.mod_design_list.addItem(list_item)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"mod内の設計データの読み込み中にエラーが発生しました：\n{str(e)}")

    def load_formations(self, nation_tag):
        """編成データを読み込む"""
        try:
            self.formation_list.clear()
            if self.app_controller:
                # TODO: app_controllerに実装が必要
                formation_data = self.app_controller.get_nation_formations(nation_tag)
                for item in formation_data:
                    list_item = QListWidgetItem()
                    list_item.setText(f"{item['name']}")
                    list_item.setData(Qt.UserRole, item)
                    self.formation_list.addItem(list_item)
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

            mod_design_data = item.data(Qt.UserRole)
            if mod_design_data:
                # TODO: app_controllerに実装が必要
                self.app_controller.show_mod_design_view(mod_design_data)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"mod内の設計ビューの表示中にエラーが発生しました：\n{str(e)}")

    def on_formation_double_clicked(self, item):
        """編成アイテムがダブルクリックされた時の処理"""
        try:
            if not self.app_controller:
                return

            formation_data = item.data(Qt.UserRole)
            if formation_data:
                # TODO: app_controllerに実装が必要
                self.app_controller.show_formation_view(formation_data)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"編成ビューの表示中にエラーが発生しました：\n{str(e)}")

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