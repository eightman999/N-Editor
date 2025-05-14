from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QComboBox, QLineEdit, QFormLayout, QPushButton, QListWidget
)
from PySide6.QtCore import Qt
import json
import sys
from pathlib import Path

from main import load_equipment_definition


# 装備定義ファイルの読み込み


class EquipmentRegisterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("火砲登録画面")
        self.setFixedSize(800, 600)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            * {
                font-family: "MS UI Gothic";
                font-size: 14pt;
            }
            QListWidget {
                background-color: #F0F0F0;
                border: 1px solid gray;
            }
            QLabel {
                margin: 4px;
            }
        """)

        self.fire_artillery_def = load_equipment_definition("fire_artillery")

        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)

        # 左側：カテゴリ選択
        self.category_list = QListWidget()
        self.category_list.addItems(self.fire_artillery_def["major_categories"])
        self.category_list.currentRowChanged.connect(self.update_form)
        self.category_list.setFixedWidth(200)

        # 右側：装備登録フォーム
        self.form_layout = QFormLayout()
        self.form_container = QWidget()
        self.form_container.setLayout(self.form_layout)

        # 火砲登録フォーム生成
        self.form_fields = {}
        self.create_form_fields()

        # 下部の登録ボタン
        self.register_button = QPushButton("登録")
        self.register_button.clicked.connect(self.register_equipment)

        main_layout.addWidget(self.category_list)
        main_layout.addWidget(self.form_container)

        bottom_layout = QVBoxLayout()
        bottom_layout.addWidget(self.register_button)
        main_layout.addLayout(bottom_layout)

        self.setCentralWidget(main_widget)

    def create_form_fields(self):
        """JSONに基づいて火砲登録フォームを動的に生成"""
        for field in self.fire_artillery_def["fields"]:
            label = QLabel(field["label"])
            input_widget = QLineEdit()
            input_widget.setPlaceholderText(field["label"])
            self.form_fields[field["key"]] = input_widget
            self.form_layout.addRow(label, input_widget)

    def update_form(self, index):
        """カテゴリ変更時にフォームを更新"""
        selected_category = self.category_list.item(index).text()
        print(f"選択されたカテゴリ: {selected_category}")
        # 現在のフォーム内容をクリア（後で別カテゴリごとのロジック追加予定）
        for key, field in self.form_fields.items():
            field.clear()

    def register_equipment(self):
        """装備登録の処理"""
        form_data = {key: field.text() for key, field in self.form_fields.items()}
        print("登録されるデータ:", form_data)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EquipmentRegisterWindow()
    window.show()
    sys.exit(app.exec())
