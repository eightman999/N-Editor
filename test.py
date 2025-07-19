# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: ユーティリティのインポートテスト
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit

app = QApplication(sys.argv)

win = QWidget()
win.setWindowTitle("キーボード入力テスト")
layout = QVBoxLayout()

line_edit = QLineEdit()
layout.addWidget(line_edit)

win.setLayout(layout)
win.show()
line_edit.setFocus()

sys.exit(app.exec_())
