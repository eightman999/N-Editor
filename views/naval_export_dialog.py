# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: naval_export_dialogビュー
"""海軍編成データ書き出し用ダイアログ"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QFileDialog, QMessageBox, QProgressBar, QGroupBox,
                             QTextEdit, QLineEdit, QFormLayout, QCheckBox, QSpinBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

import os
import logging

from controllers.naval_export_controller import NavalExportController
from models.data_models import Fleet


class ExportWorker(QThread):
    """エクスポート処理用のワーカースレッド"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    error = pyqtSignal(str)

    def __init__(self, fleet_data, output_path):
        super().__init__()
        self.fleet_data = fleet_data
        self.output_path = output_path
        self.logger = logging.getLogger('ExportWorker')

    def run(self):
        try:
            self.progress.emit(10)
            controller = NavalExportController()
            
            self.progress.emit(30)
            validation_errors = controller.validate_fleet_data(self.fleet_data)
            if validation_errors:
                self.error.emit(f"データ検証エラー:\n{chr(10).join(validation_errors)}")
                return
            
            self.progress.emit(60)
            success = controller.export_to_hoi4_format(self.fleet_data, self.output_path)
            
            self.progress.emit(100)
            if success:
                self.finished.emit(True, "書き出しが完了しました")
            else:
                self.finished.emit(False, "書き出しに失敗しました")
                
        except Exception as e:
            self.logger.error(f"エクスポート処理中にエラー: {str(e)}")
            self.error.emit(f"エクスポート処理中にエラーが発生しました:\n{str(e)}")


class NavalExportDialog(QDialog):
    """海軍編成データ書き出し用ダイアログ"""
    
    def __init__(self, parent=None, fleet_data=None):
        super().__init__(parent)
        self.fleet_data = fleet_data
        self.controller = NavalExportController()
        self.worker = None
        self.setupUI()
        self.load_fleet_data()
    
    def setupUI(self):
        """UI初期化"""
        self.setWindowTitle("海軍編成データ書き出し")
        self.setModal(True)
        self.resize(600, 500)
        
        layout = QVBoxLayout()
        
        # タイトル
        title_label = QLabel("HOI4海軍編成データ書き出し")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 艦隊情報表示エリア
        fleet_group = QGroupBox("艦隊情報")
        fleet_layout = QFormLayout()
        
        self.fleet_name_label = QLabel("未設定")
        self.naval_base_label = QLabel("未設定")
        self.task_force_count_label = QLabel("0")
        self.ship_count_label = QLabel("0")
        
        fleet_layout.addRow("艦隊名:", self.fleet_name_label)
        fleet_layout.addRow("海軍基地:", self.naval_base_label)
        fleet_layout.addRow("任務部隊数:", self.task_force_count_label)
        fleet_layout.addRow("総艦船数:", self.ship_count_label)
        
        fleet_group.setLayout(fleet_layout)
        layout.addWidget(fleet_group)
        
        # エクスポート設定エリア
        export_group = QGroupBox("書き出し設定")
        export_layout = QFormLayout()
        
        # ファイルパス選択
        file_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("書き出し先ファイルを選択してください")
        browse_btn = QPushButton("参照")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(browse_btn)
        
        export_layout.addRow("書き出し先:", file_layout)
        
        # オプション設定
        self.validate_checkbox = QCheckBox("書き出し前にデータを検証")
        self.validate_checkbox.setChecked(True)
        export_layout.addRow("", self.validate_checkbox)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        # プレビューエリア
        preview_group = QGroupBox("データ検証結果")
        preview_layout = QVBoxLayout()
        
        self.validation_text = QTextEdit()
        self.validation_text.setMaximumHeight(120)
        self.validation_text.setReadOnly(True)
        preview_layout.addWidget(self.validation_text)
        
        validate_btn = QPushButton("データを検証")
        validate_btn.clicked.connect(self.validate_data)
        preview_layout.addWidget(validate_btn)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # ボタンエリア
        button_layout = QHBoxLayout()
        
        # サンプル生成ボタン
        sample_btn = QPushButton("サンプルデータを生成")
        sample_btn.clicked.connect(self.create_sample_data)
        button_layout.addWidget(sample_btn)
        
        button_layout.addStretch()
        
        # 実行・キャンセルボタン
        self.export_btn = QPushButton("書き出し実行")
        self.export_btn.clicked.connect(self.export_data)
        self.cancel_btn = QPushButton("キャンセル")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # 初期状態の設定
        self.update_export_button_state()
    
    def load_fleet_data(self):
        """艦隊データを読み込んで表示を更新"""
        if self.fleet_data and isinstance(self.fleet_data, Fleet):
            self.fleet_name_label.setText(self.fleet_data.name or "未設定")
            self.naval_base_label.setText(str(self.fleet_data.naval_base) or "未設定")
            self.task_force_count_label.setText(str(len(self.fleet_data.task_forces)))
            self.ship_count_label.setText(str(self.fleet_data.get_total_ships()))
        else:
            self.fleet_name_label.setText("データなし")
            self.naval_base_label.setText("データなし")
            self.task_force_count_label.setText("0")
            self.ship_count_label.setText("0")
        
        self.update_export_button_state()
    
    def browse_file(self):
        """書き出し先ファイル選択"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "書き出し先を選択",
            "naval_oob.txt",
            "Text files (*.txt);;All files (*.*)"
        )
        if file_path:
            self.file_path_edit.setText(file_path)
            self.update_export_button_state()
    
    def validate_data(self):
        """データ検証実行"""
        if not self.fleet_data:
            self.validation_text.setText("検証対象のデータがありません")
            return
        
        try:
            errors = self.controller.validate_fleet_data(self.fleet_data)
            if errors:
                self.validation_text.setText(f"検証エラー ({len(errors)}件):\n" + "\n".join(f"• {error}" for error in errors))
            else:
                self.validation_text.setText("✓ データ検証に成功しました。問題は見つかりませんでした。")
        except Exception as e:
            self.validation_text.setText(f"検証中にエラーが発生しました:\n{str(e)}")
    
    def create_sample_data(self):
        """サンプルデータ生成"""
        self.fleet_data = self.controller.create_sample_fleet()
        self.load_fleet_data()
        self.validation_text.setText("サンプル艦隊データを生成しました")
        
        QMessageBox.information(
            self,
            "サンプルデータ生成",
            "サンプル艦隊データを生成しました。\n書き出し先を選択して実行してください。"
        )
    
    def update_export_button_state(self):
        """書き出しボタンの有効/無効状態を更新"""
        has_data = self.fleet_data is not None
        has_path = bool(self.file_path_edit.text().strip())
        self.export_btn.setEnabled(has_data and has_path)
    
    def export_data(self):
        """データ書き出し実行"""
        if not self.fleet_data:
            QMessageBox.warning(self, "エラー", "書き出し対象のデータがありません")
            return
        
        output_path = self.file_path_edit.text().strip()
        if not output_path:
            QMessageBox.warning(self, "エラー", "書き出し先ファイルを選択してください")
            return
        
        # 事前検証（オプション）
        if self.validate_checkbox.isChecked():
            errors = self.controller.validate_fleet_data(self.fleet_data)
            if errors:
                reply = QMessageBox.question(
                    self,
                    "データ検証エラー",
                    f"データに {len(errors)} 件のエラーがあります:\n\n" +
                    "\n".join(f"• {error}" for error in errors[:5]) +
                    ("\n..." if len(errors) > 5 else "") +
                    "\n\n書き出しを続行しますか？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
        
        # 既存ファイルの確認
        if os.path.exists(output_path):
            reply = QMessageBox.question(
                self,
                "ファイル上書き確認",
                f"ファイル '{os.path.basename(output_path)}' は既に存在します。\n上書きしますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        # エクスポート処理開始
        self.start_export(output_path)
    
    def start_export(self, output_path):
        """エクスポート処理開始"""
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # ワーカースレッド開始
        self.worker = ExportWorker(self.fleet_data, output_path)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_export_finished)
        self.worker.error.connect(self.on_export_error)
        self.worker.start()
    
    def on_export_finished(self, success, message):
        """エクスポート完了処理"""
        self.progress_bar.setVisible(False)
        self.export_btn.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "完了", message)
            self.accept()
        else:
            QMessageBox.warning(self, "エラー", message)
    
    def on_export_error(self, error_message):
        """エクスポートエラー処理"""
        self.progress_bar.setVisible(False)
        self.export_btn.setEnabled(True)
        QMessageBox.critical(self, "エラー", error_message)
    
    def closeEvent(self, event):
        """ダイアログクローズ時の処理"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "処理中断確認",
                "エクスポート処理が実行中です。\n中断しますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.worker.terminate()
                self.worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()