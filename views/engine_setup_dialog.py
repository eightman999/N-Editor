# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: engine_setup_dialogビュー
# -*- coding: utf-8 -*-
"""Dialog for creating main and auxiliary engines."""

from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QVBoxLayout,
    QComboBox, QDoubleSpinBox, QLabel, QPushButton
)
from PyQt5.QtCore import Qt

ENGINE_TYPES = [
    "Coal", "HeavyOil", "Diesel", "GasTurbine",
    "CoalHeavyOil", "DieselGas", "Battery", "Nuclear"
]

class EngineSetupDialog(QDialog):
    """Dialog to define main and auxiliary engine configuration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("機関設定")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.main_type = QComboBox()
        self.main_type.addItems(ENGINE_TYPES)
        self.main_power = QDoubleSpinBox()
        self.main_power.setRange(0, 100000)
        self.main_power.setSuffix(" hp")
        form.addRow("主機種別", self.main_type)
        form.addRow("主機馬力", self.main_power)

        self.aux_type = QComboBox()
        self.aux_type.addItems(ENGINE_TYPES)
        self.aux_power = QDoubleSpinBox()
        self.aux_power.setRange(0, 100000)
        self.aux_power.setSuffix(" hp")
        form.addRow("補機種別", self.aux_type)
        form.addRow("補機馬力", self.aux_power)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        btn_layout.addWidget(self.ok_button)
        cancel = QPushButton("キャンセル")
        cancel.clicked.connect(self.reject)
        btn_layout.addWidget(cancel)
        layout.addLayout(btn_layout)

    def get_result(self):
        total_power = self.main_power.value() + self.aux_power.value()
        main_ratio = 0.0
        aux_ratio = 0.0
        if total_power > 0:
            main_ratio = self.main_power.value() / total_power
            aux_ratio = self.aux_power.value() / total_power
        return {
            "main": {
                "engine_type": self.main_type.currentText(),
                "power": self.main_power.value(),
                "ratio": main_ratio,
            },
            "auxiliary": {
                "engine_type": self.aux_type.currentText(),
                "power": self.aux_power.value(),
                "ratio": aux_ratio,
            },
        }
