"""HOI4エクスポートダイアログ

このモジュールは、HOI4形式でのエクスポート設定と実行を行う
ダイアログウィンドウを提供します。
"""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFileDialog, QComboBox, QCheckBox, QMessageBox,
                             QGroupBox, QFormLayout, QTextEdit, QProgressBar, QListWidget,
                             QListWidgetItem, QSplitter, QTabWidget, QWidget, QSpinBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

import os
import logging
import time
from typing import Dict, Any, List, Optional

from exporters.hoi4_exporter import HOI4Exporter
from utils.stats_calculator import StatsCalculator


class HOI4ExportWorker(QThread):
    """HOI4エクスポート処理用のワーカースレッド"""
    
    progress_updated = pyqtSignal(int, int, str)  # current, total, item_name
    export_completed = pyqtSignal(dict)  # results
    log_message = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, app_controller, export_config):
        super().__init__()
        self.app_controller = app_controller
        self.export_config = export_config
        self.cancel_requested = False
        self.logger = logging.getLogger('HOI4ExportWorker')

    def run(self):
        """エクスポート処理の実行"""
        try:
            self.log_message.emit("エクスポート処理を開始しています...")
            
            # エクスポーターを初期化
            exporter = HOI4Exporter(
                self.export_config['output_dir'], 
                self.export_config['country_tag']
            )
            
            # 設定を適用
            exporter.include_upgrades = self.export_config.get('include_upgrades', True)
            
            results = {
                'designs': {'total': 0, 'success': 0, 'failed': 0, 'errors': []},
                'hulls': {'total': 0, 'success': 0, 'failed': 0, 'errors': []},
                'output_files': []
            }
            
            total_items = 0
            current_item = 0
            
            # エクスポート対象の計算
            if self.export_config.get('export_designs', True):
                designs = self._get_designs_to_export()
                total_items += len(designs)
                results['designs']['total'] = len(designs)
            
            if self.export_config.get('export_hulls', True):
                hulls = self._get_hulls_to_export()
                total_items += len(hulls)
                results['hulls']['total'] = len(hulls)
            
            self.log_message.emit(f"エクスポート対象: 設計{results['designs']['total']}件, 船体{results['hulls']['total']}件")
            
            # 設計のエクスポート
            if self.export_config.get('export_designs', True) and designs:
                self.log_message.emit("設計データのエクスポートを開始...")
                
                for design in designs:
                    if self.cancel_requested:
                        break
                    
                    design_name = design.get('design_name', 'Unknown')
                    self.progress_updated.emit(current_item, total_items, f"設計: {design_name}")
                    
                    # 性能計算を含む設計データの準備
                    export_design = self._prepare_design_for_export(design)
                    
                    try:
                        if exporter.export_design(export_design):
                            results['designs']['success'] += 1
                            self.log_message.emit(f"✓ 設計エクスポート成功: {design_name}")
                        else:
                            results['designs']['failed'] += 1
                            results['designs']['errors'].append(f"設計エクスポート失敗: {design_name}")
                            self.log_message.emit(f"✗ 設計エクスポート失敗: {design_name}")
                    except Exception as e:
                        results['designs']['failed'] += 1
                        error_msg = f"設計エクスポートエラー: {design_name} - {str(e)}"
                        results['designs']['errors'].append(error_msg)
                        self.log_message.emit(f"✗ {error_msg}")
                    
                    current_item += 1
                    self.msleep(50)  # UI更新のための小休止
            
            # 船体のエクスポート
            if self.export_config.get('export_hulls', True) and hulls:
                self.log_message.emit("船体データのエクスポートを開始...")
                
                for hull in hulls:
                    if self.cancel_requested:
                        break
                    
                    hull_name = hull.get('name', 'Unknown')
                    self.progress_updated.emit(current_item, total_items, f"船体: {hull_name}")
                    
                    # 船体データの準備
                    export_hull = self._prepare_hull_for_export(hull)
                    
                    try:
                        if exporter.export_hull(export_hull):
                            results['hulls']['success'] += 1
                            self.log_message.emit(f"✓ 船体エクスポート成功: {hull_name}")
                        else:
                            results['hulls']['failed'] += 1
                            results['hulls']['errors'].append(f"船体エクスポート失敗: {hull_name}")
                            self.log_message.emit(f"✗ 船体エクスポート失敗: {hull_name}")
                    except Exception as e:
                        results['hulls']['failed'] += 1
                        error_msg = f"船体エクスポートエラー: {hull_name} - {str(e)}"
                        results['hulls']['errors'].append(error_msg)
                        self.log_message.emit(f"✗ {error_msg}")
                    
                    current_item += 1
                    self.msleep(50)
            
            # ファイル終了処理
            if not self.cancel_requested:
                self.log_message.emit("ファイルを完成中...")
                exporter.finalize_files()
                results['output_files'] = [exporter.designs_file, exporter.hulls_file]
                self.log_message.emit("エクスポート処理が完了しました")
            
            self.export_completed.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(f"エクスポート処理中に重大なエラー: {str(e)}")

    def _get_designs_to_export(self):
        """エクスポート対象の設計データを取得"""
        if not self.app_controller:
            return []
        
        try:
            all_designs = self.app_controller.get_all_designs()
            return all_designs or []
        except:
            return []

    def _get_hulls_to_export(self):
        """エクスポート対象の船体データを取得"""
        if not self.app_controller:
            return []
        
        try:
            all_hulls = self.app_controller.get_all_hulls()
            return all_hulls or []
        except:
            return []

    def _prepare_design_for_export(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """エクスポート用の設計データを準備"""
        export_data = {
            'design_name': design_data.get('design_name', ''),
            'hull_id': design_data.get('hull_id', ''),
            'modules': {},
            'upgrades': design_data.get('upgrades', {}),
            'name_group': design_data.get('name_group', ''),
        }
        
        # メインスロットの処理
        main_slots = design_data.get('main_slots', {})
        for slot_type, module_id in main_slots.items():
            if module_id:
                export_data['modules'][slot_type] = module_id
        
        # 内部スロットの処理
        internal_slots = design_data.get('internal_slots', [])
        for slot_data in internal_slots:
            slot_id = slot_data.get('slot_id', '')
            equipment_id = slot_data.get('equipment_id', '')
            if slot_id and equipment_id:
                export_data['modules'][slot_id] = equipment_id
        
        # 性能計算（内部表示用。結果はエクスポートデータに含めない）
        try:
            calculator = StatsCalculator(self.app_controller)
            _ = calculator.calculate_design_stats(export_data)
        except Exception as e:
            self.logger.warning(f"性能計算エラー: {e}")

        return export_data

    def _prepare_hull_for_export(self, hull_data: Dict[str, Any]) -> Dict[str, Any]:
        """エクスポート用の船体データを準備"""
        export_data = {
            'hull_id': hull_data.get('id', ''),
            'name': hull_data.get('name', ''),
            'type': hull_data.get('type', ''),
            'year': hull_data.get('year', 1940),
            'slots': {},
            'base_stats': hull_data.get('base_stats', {})
        }
        
        # スロット情報の変換
        slots = hull_data.get('slots', [])
        for slot in slots:
            slot_id = slot.get('id', '')
            export_data['slots'][slot_id] = {
                'required': slot.get('required', False),
                'categories': slot.get('categories', []),
                'default_module': slot.get('default_module', 'empty'),
                'gfx': slot.get('gfx', '')
            }
        
        return export_data

    def request_cancel(self):
        """キャンセル要求"""
        self.cancel_requested = True


class HOI4ExportDialog(QDialog):
    """HOI4エクスポートダイアログ"""
    
    def __init__(self, parent=None, app_controller=None):
        super().__init__(parent)
        self.app_controller = app_controller
        self.worker = None
        self.logger = logging.getLogger('HOI4ExportDialog')
        
        self.setWindowTitle("HOI4形式エクスポート")
        self.setModal(True)
        self.setMinimumSize(700, 600)
        
        self.initUI()
        self.load_default_settings()
    
    def initUI(self):
        """UI初期化"""
        layout = QVBoxLayout(self)
        
        # タイトル
        title_label = QLabel("Hearts of Iron IV 形式エクスポート")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # タブウィジェット
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # 基本設定タブ
        basic_tab = self._create_basic_settings_tab()
        tab_widget.addTab(basic_tab, "基本設定")
        
        # 詳細設定タブ
        advanced_tab = self._create_advanced_settings_tab()
        tab_widget.addTab(advanced_tab, "詳細設定")
        
        # プレビュータブ
        preview_tab = self._create_preview_tab()
        tab_widget.addTab(preview_tab, "プレビュー")
        
        # 進捗表示エリア
        progress_group = QGroupBox("エクスポート進捗")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("エクスポート準備完了")
        progress_layout.addWidget(self.status_label)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(120)
        self.log_text.setReadOnly(True)
        progress_layout.addWidget(self.log_text)
        
        layout.addWidget(progress_group)
        
        # ボタンエリア
        button_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("プレビュー生成")
        self.preview_btn.clicked.connect(self.generate_preview)
        
        self.export_btn = QPushButton("エクスポート実行")
        self.export_btn.clicked.connect(self.start_export)
        
        self.cancel_btn = QPushButton("キャンセル")
        self.cancel_btn.clicked.connect(self.handle_cancel)
        
        button_layout.addWidget(self.preview_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _create_basic_settings_tab(self) -> QWidget:
        """基本設定タブを作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 出力設定
        output_group = QGroupBox("出力設定")
        output_layout = QFormLayout(output_group)
        
        # 出力ディレクトリ
        dir_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("出力先ディレクトリを選択")
        dir_browse_btn = QPushButton("参照...")
        dir_browse_btn.clicked.connect(self.browse_output_dir)
        dir_layout.addWidget(self.output_dir_edit)
        dir_layout.addWidget(dir_browse_btn)
        output_layout.addRow("出力先:", dir_layout)
        
        # 国家タグ
        self.country_tag_edit = QLineEdit("GER")
        self.country_tag_edit.setMaxLength(3)
        self.country_tag_edit.setToolTip("3文字の国家タグを入力してください")
        output_layout.addRow("国家タグ:", self.country_tag_edit)
        
        layout.addWidget(output_group)
        
        # エクスポート対象
        target_group = QGroupBox("エクスポート対象")
        target_layout = QVBoxLayout(target_group)
        
        self.export_designs_cb = QCheckBox("設計データ (create_equipment_variant)")
        self.export_designs_cb.setChecked(True)
        target_layout.addWidget(self.export_designs_cb)
        
        self.export_hulls_cb = QCheckBox("船体定義 (equipments)")
        self.export_hulls_cb.setChecked(True)
        target_layout.addWidget(self.export_hulls_cb)
        
        layout.addWidget(target_group)
        
        # オプション設定
        options_group = QGroupBox("基本オプション")
        options_layout = QVBoxLayout(options_group)
        
        self.include_stats_cb = QCheckBox("性能コメントを含める")
        self.include_stats_cb.setChecked(True)
        self.include_stats_cb.setToolTip("計算された性能値をコメントとして出力に含めます")
        options_layout.addWidget(self.include_stats_cb)
        
        self.include_upgrades_cb = QCheckBox("アップグレード情報を含める")
        self.include_upgrades_cb.setChecked(True)
        self.include_upgrades_cb.setToolTip("設計のアップグレード情報を出力に含めます")
        options_layout.addWidget(self.include_upgrades_cb)
        
        self.backup_existing_cb = QCheckBox("既存ファイルをバックアップ")
        self.backup_existing_cb.setChecked(True)
        self.backup_existing_cb.setToolTip("上書き前に既存ファイルのバックアップを作成します")
        options_layout.addWidget(self.backup_existing_cb)
        
        layout.addWidget(options_group)
        
        layout.addStretch()
        return tab
    
    def _create_advanced_settings_tab(self) -> QWidget:
        """詳細設定タブを作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # ファイル設定
        file_group = QGroupBox("ファイル設定")
        file_layout = QFormLayout(file_group)
        
        # エンコーディング
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["utf-8", "utf-8-sig", "ascii"])
        file_layout.addRow("文字エンコーディング:", self.encoding_combo)
        
        # ファイル命名
        self.designs_filename_edit = QLineEdit("{country_tag}_designs.txt")
        file_layout.addRow("設計ファイル名:", self.designs_filename_edit)
        
        self.hulls_filename_edit = QLineEdit("{country_tag}_hulls.txt")
        file_layout.addRow("船体ファイル名:", self.hulls_filename_edit)
        
        layout.addWidget(file_group)
        
        # 性能計算設定
        stats_group = QGroupBox("性能計算設定")
        stats_layout = QVBoxLayout(stats_group)
        
        self.calculate_derived_cb = QCheckBox("派生統計を計算")
        self.calculate_derived_cb.setChecked(True)
        self.calculate_derived_cb.setToolTip("戦闘力、生存性などの派生統計を計算します")
        stats_layout.addWidget(self.calculate_derived_cb)
        
        self.include_cost_efficiency_cb = QCheckBox("コスト効率を計算")
        self.include_cost_efficiency_cb.setChecked(True)
        stats_layout.addWidget(self.include_cost_efficiency_cb)
        
        layout.addWidget(stats_group)
        
        # エクスポート制限
        limits_group = QGroupBox("エクスポート制限")
        limits_layout = QFormLayout(limits_group)
        
        self.max_designs_spin = QSpinBox()
        self.max_designs_spin.setRange(0, 9999)
        self.max_designs_spin.setValue(0)
        self.max_designs_spin.setSpecialValueText("制限なし")
        limits_layout.addRow("最大設計数:", self.max_designs_spin)
        
        self.max_hulls_spin = QSpinBox()
        self.max_hulls_spin.setRange(0, 9999)
        self.max_hulls_spin.setValue(0)
        self.max_hulls_spin.setSpecialValueText("制限なし")
        limits_layout.addRow("最大船体数:", self.max_hulls_spin)
        
        layout.addWidget(limits_group)
        
        layout.addStretch()
        return tab
    
    def _create_preview_tab(self) -> QWidget:
        """プレビュータブを作成"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # プレビュー生成ボタン
        preview_btn_layout = QHBoxLayout()
        generate_preview_btn = QPushButton("プレビューを生成")
        generate_preview_btn.clicked.connect(self.generate_preview)
        preview_btn_layout.addWidget(generate_preview_btn)
        preview_btn_layout.addStretch()
        layout.addLayout(preview_btn_layout)
        
        # プレビューテキスト
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(QFont("Consolas", 10))
        self.preview_text.setPlainText("プレビューを生成するには上のボタンをクリックしてください。")
        layout.addWidget(self.preview_text)
        
        return tab
    
    def browse_output_dir(self):
        """出力ディレクトリを選択"""
        dir_path = QFileDialog.getExistingDirectory(self, "出力先ディレクトリを選択")
        if dir_path:
            self.output_dir_edit.setText(dir_path)
    
    def load_default_settings(self):
        """デフォルト設定を読み込み"""
        # デフォルトの出力ディレクトリ
        default_output = os.path.join(os.path.expanduser("~"), "Desktop", "HOI4_Naval_Export")
        self.output_dir_edit.setText(default_output)
    
    def get_export_config(self) -> Dict[str, Any]:
        """現在の設定からエクスポート設定を取得"""
        return {
            'output_dir': self.output_dir_edit.text().strip(),
            'country_tag': self.country_tag_edit.text().strip().upper(),
            'export_designs': self.export_designs_cb.isChecked(),
            'export_hulls': self.export_hulls_cb.isChecked(),
            'include_upgrades': self.include_upgrades_cb.isChecked(),
            'backup_existing': self.backup_existing_cb.isChecked(),
            'encoding': self.encoding_combo.currentText(),
            'designs_filename': self.designs_filename_edit.text().strip(),
            'hulls_filename': self.hulls_filename_edit.text().strip(),
            'calculate_derived': self.calculate_derived_cb.isChecked(),
            'include_cost_efficiency': self.include_cost_efficiency_cb.isChecked(),
            'max_designs': self.max_designs_spin.value() if self.max_designs_spin.value() > 0 else None,
            'max_hulls': self.max_hulls_spin.value() if self.max_hulls_spin.value() > 0 else None
        }
    
    def validate_settings(self) -> bool:
        """設定の検証"""
        config = self.get_export_config()
        
        if not config['output_dir']:
            QMessageBox.warning(self, "エラー", "出力先ディレクトリを選択してください。")
            return False
        
        if not config['country_tag'] or len(config['country_tag']) != 3:
            QMessageBox.warning(self, "エラー", "3文字の国家タグを入力してください。")
            return False
        
        if not config['export_designs'] and not config['export_hulls']:
            QMessageBox.warning(self, "エラー", "少なくとも1つのエクスポート対象を選択してください。")
            return False
        
        return True
    
    def generate_preview(self):
        """プレビューを生成"""
        if not self.validate_settings():
            return
        
        try:
            config = self.get_export_config()
            
            # サンプル出力を生成
            preview_content = []
            preview_content.append("# HOI4エクスポートプレビュー")
            preview_content.append(f"# 国家タグ: {config['country_tag']}")
            preview_content.append(f"# 出力先: {config['output_dir']}")
            preview_content.append("")
            
            if config['export_designs']:
                preview_content.append("# 設計ファイルサンプル")
                preview_content.append(f"{config['country_tag']} = {{")
                preview_content.append("    create_equipment_variant = {")
                preview_content.append('        name = "Sample_Design"')
                preview_content.append("        type = ship_hull_carrier_1")
                preview_content.append("        upgrades = {")
                preview_content.append("            ship_mtg_naval_range_upgrade = 6")
                preview_content.append("        }")
                preview_content.append("        modules = {")
                preview_content.append("            fixed_ship_deck_slot_1 = flush_deck")
                preview_content.append("        }")
                preview_content.append("    }")
                preview_content.append("}")
                preview_content.append("")
            
            if config['export_hulls']:
                preview_content.append("# 船体ファイルサンプル")
                preview_content.append("equipments = {")
                preview_content.append("    ship_hull_sample = {")
                preview_content.append("        year = 1940")
                preview_content.append("        is_archetype = yes")
                preview_content.append("        type = carrier")
                preview_content.append("        lg_attack = 0")
                preview_content.append("        max_strength = 250")
                preview_content.append("    }")
                preview_content.append("}")
            
            self.preview_text.setPlainText("\\n".join(preview_content))
            
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"プレビュー生成エラー: {str(e)}")
    
    def start_export(self):
        """エクスポート処理を開始"""
        if not self.validate_settings():
            return
        
        config = self.get_export_config()
        
        # 出力ディレクトリの作成確認
        try:
            os.makedirs(config['output_dir'], exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"出力ディレクトリの作成に失敗: {str(e)}")
            return
        
        # UIを無効化
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("エクスポート処理を開始...")
        self.log_text.clear()
        
        # ワーカースレッドを開始
        self.worker = HOI4ExportWorker(self.app_controller, config)
        self.worker.progress_updated.connect(self.on_progress_updated)
        self.worker.export_completed.connect(self.on_export_completed)
        self.worker.log_message.connect(self.on_log_message)
        self.worker.error_occurred.connect(self.on_error_occurred)
        self.worker.start()
    
    def on_progress_updated(self, current: int, total: int, item_name: str):
        """進捗更新時の処理"""
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar.setValue(progress)
            self.status_label.setText(f"進捗: {current}/{total} - {item_name}")
    
    def on_export_completed(self, results: Dict[str, Any]):
        """エクスポート完了時の処理"""
        self.progress_bar.setVisible(False)
        self.export_btn.setEnabled(True)
        
        # 結果の表示
        designs_success = results['designs']['success']
        designs_failed = results['designs']['failed']
        hulls_success = results['hulls']['success']
        hulls_failed = results['hulls']['failed']
        
        total_success = designs_success + hulls_success
        total_failed = designs_failed + hulls_failed
        
        if total_failed == 0:
            self.status_label.setText(f"エクスポート完了: {total_success}件成功")
            QMessageBox.information(
                self, "完了", 
                f"エクスポートが完了しました。\\n"
                f"設計: {designs_success}件成功\\n"
                f"船体: {hulls_success}件成功\\n\\n"
                f"出力先: {results.get('output_files', [])}"
            )
        else:
            self.status_label.setText(f"エクスポート完了: {total_success}件成功, {total_failed}件失敗")
            error_details = "\\n".join(
                results['designs']['errors'] + results['hulls']['errors']
            )
            QMessageBox.warning(
                self, "完了（エラーあり）",
                f"エクスポートが完了しましたが、エラーがありました。\\n"
                f"成功: {total_success}件, 失敗: {total_failed}件\\n\\n"
                f"エラー詳細:\\n{error_details[:500]}..."
            )
    
    def on_log_message(self, message: str):
        """ログメッセージ追加時の処理"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
        # 自動スクロール
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def on_error_occurred(self, error_message: str):
        """エラー発生時の処理"""
        self.progress_bar.setVisible(False)
        self.export_btn.setEnabled(True)
        self.status_label.setText("エラーが発生しました")
        QMessageBox.critical(self, "エラー", error_message)
    
    def handle_cancel(self):
        """キャンセル処理"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "キャンセル確認",
                "エクスポート処理が実行中です。中断しますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.worker.request_cancel()
                self.worker.wait(3000)  # 3秒待機
                if self.worker.isRunning():
                    self.worker.terminate()
                self.reject()
            return
        
        self.reject()
    
    def closeEvent(self, event):
        """ダイアログクローズ時の処理"""
        if self.worker and self.worker.isRunning():
            self.worker.request_cancel()
            self.worker.wait(3000)
            if self.worker.isRunning():
                self.worker.terminate()
        event.accept()