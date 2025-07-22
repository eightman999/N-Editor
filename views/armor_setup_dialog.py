# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: armor_setup_dialogビュー
# -*- coding: utf-8 -*-
"""Dialog for creating armor equipment."""

from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QVBoxLayout,
    QComboBox, QDoubleSpinBox, QLabel, QPushButton
)

# Armor categories derived from historical materials
ARMOR_TYPES = [
    # Face-hardened / Cemented types
    "KC", "CA", "VH", "TC", "KC n/A", "Class A",
    # Homogeneous / Rolled types
    "KNC", "Wh", "Ww", "Wsh", "NCA", "STS/Class B",
    "MNC", "NVNC", "CNC", "NCV", "AOD",
    # Structural steels and others
    "HT", "HHT", "st52", "DS", "DW", "BK", "FBK",
]

class ArmorSetupDialog(QDialog):
    """Dialog to define armor equipment parameters."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("装甲設定")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.armor_type = QComboBox()
        self.armor_type.addItems(ARMOR_TYPES)
        self.armor_thickness = QDoubleSpinBox()
        self.armor_thickness.setRange(0, 1000)
        self.armor_thickness.setSuffix(" mm")
        self.armor_weight = QDoubleSpinBox()
        self.armor_weight.setRange(0, 20000)
        self.armor_weight.setSuffix(" t")

        form.addRow("装甲種別", self.armor_type)
        form.addRow("装甲厚", self.armor_thickness)
        form.addRow("重量", self.armor_weight)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def get_result(self):
        return {
            "armor_type": self.armor_type.currentText(),
            "available_armor": self.armor_thickness.value(),
            "weight": self.armor_weight.value(),
        }
