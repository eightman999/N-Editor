from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QFormLayout, QComboBox, QSpinBox, QPushButton

class EquipmentForm(QWidget):
    def __init__(self, parent=None):
        """
        Initialize the Equipment Form widget.

        Args:
            parent: Parent widget, typically the main window
        """
        super(EquipmentForm, self).__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Setup the equipment form UI elements"""
        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Form layout for equipment properties
        form_layout = QFormLayout()
        main_layout.addLayout(form_layout)

        # Equipment name
        self.name_input = QLineEdit()
        form_layout.addRow("装備名:", self.name_input)

        # Equipment type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["主砲", "副砲", "対空砲", "魚雷", "機関", "レーダー", "装甲", "その他"])
        form_layout.addRow("装備種別:", self.type_combo)

        # Equipment specifications - these will vary based on type
        # Weight
        self.weight_input = QSpinBox()
        self.weight_input.setRange(0, 10000)
        self.weight_input.setSuffix(" t")
        form_layout.addRow("重量:", self.weight_input)

        # Power
        self.power_input = QSpinBox()
        self.power_input.setRange(0, 100000)
        self.power_input.setSuffix(" hp")
        form_layout.addRow("出力:", self.power_input)

        # Space required
        self.space_input = QSpinBox()
        self.space_input.setRange(0, 1000)
        self.space_input.setSuffix(" ㎡")
        form_layout.addRow("必要スペース:", self.space_input)

        # Production cost
        self.cost_input = QSpinBox()
        self.cost_input.setRange(0, 10000)
        form_layout.addRow("生産コスト:", self.cost_input)

        # Year of introduction
        self.year_input = QSpinBox()
        self.year_input.setRange(1900, 1945)
        form_layout.addRow("開発年:", self.year_input)

        # Nation of origin
        self.nation_combo = QComboBox()
        self.nation_combo.addItems(["日本", "アメリカ", "イギリス", "ドイツ", "イタリア", "ソ連", "フランス", "その他"])
        form_layout.addRow("開発国:", self.nation_combo)

        # Save & Cancel buttons
        button_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)

        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_equipment)
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("キャンセル")
        self.cancel_button.clicked.connect(self.cancel)
        button_layout.addWidget(self.cancel_button)

    def save_equipment(self):
        """Save the equipment data to the database"""
        # This will be implemented later to save data to SQLite database
        print("Equipment saved:", self.name_input.text())

    def cancel(self):
        """Clear the form or return to previous view"""
        self.name_input.clear()
        # Additional cleanup or navigation would go here