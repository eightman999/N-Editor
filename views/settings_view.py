# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: settings_viewビュー
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QCheckBox, QPushButton, QGroupBox, QFormLayout,
                             QComboBox, QSpinBox, QTabWidget, QMessageBox,
                             QTextEdit, QScrollArea)
from PyQt5.QtCore import Qt
import subprocess
import requests
import logging
import miyabi

logger = logging.getLogger(__name__)

class SettingsView(QWidget):
    """設定画面（Git同期設定を統合）"""

    def __init__(self, parent=None, app_settings=None):
        super().__init__(parent)
        self.app_settings = app_settings
        self.main_window = parent
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """UIの初期化"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # タブウィジェットで設定を分類
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # 各タブを作成
        self.create_general_tab()
        self.create_sync_tab()
        self.create_advanced_tab()

        # ボタン
        button_layout = QHBoxLayout()

        self.test_connection_button = QPushButton("Git接続テスト")
        self.test_connection_button.clicked.connect(self.test_git_connection)
        button_layout.addWidget(self.test_connection_button)

        button_layout.addStretch()

        self.apply_button = QPushButton("適用")
        self.apply_button.clicked.connect(self.apply_settings)
        button_layout.addWidget(self.apply_button)

        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_button)

        main_layout.addLayout(button_layout)

    def create_general_tab(self):
        """一般設定タブ"""
        general_tab = QWidget()
        layout = QVBoxLayout(general_tab)

        # スクロールエリア
        scroll_area = QScrollArea()
        # 入力欄のキー入力がスクロールエリアに奪われないようにする
        scroll_area.setFocusPolicy(Qt.NoFocus)
        scroll_area.viewport().setFocusPolicy(Qt.NoFocus)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # アプリケーション設定
        app_group = QGroupBox("アプリケーション設定")
        app_layout = QFormLayout()

        self.language_combo = QComboBox()
        self.language_combo.addItems(["日本語", "English"])
        app_layout.addRow("言語:", self.language_combo)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Windows95", "Modern", "Dark"])
        app_layout.addRow("テーマ:", self.theme_combo)

        self.auto_save_check = QCheckBox("自動保存を有効にする")
        app_layout.addRow(self.auto_save_check)

        app_group.setLayout(app_layout)
        scroll_layout.addWidget(app_group)

        # ウィンドウ設定
        window_group = QGroupBox("ウィンドウ設定")
        window_layout = QFormLayout()

        self.width_spin = QSpinBox()
        self.width_spin.setRange(800, 2560)
        self.width_spin.setValue(1080)
        window_layout.addRow("幅:", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(600, 1440)
        self.height_spin.setValue(720)
        window_layout.addRow("高さ:", self.height_spin)

        self.fullscreen_check = QCheckBox("全画面表示で起動")
        window_layout.addRow(self.fullscreen_check)

        window_group.setLayout(window_layout)
        scroll_layout.addWidget(window_group)

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        self.tab_widget.addTab(general_tab, "一般")

    def create_sync_tab(self):
        """同期設定タブ"""
        sync_tab = QWidget()
        layout = QVBoxLayout(sync_tab)

        # スクロールエリア
        scroll_area = QScrollArea()
        # フォーカスが奪われないように設定
        scroll_area.setFocusPolicy(Qt.NoFocus)
        # viewport にも同様のポリシーを適用
        scroll_area.viewport().setFocusPolicy(Qt.NoFocus)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Git リポジトリ設定
        repo_group = QGroupBox("リポジトリ設定")
        repo_layout = QFormLayout()

        self.repo_url_edit = QLineEdit()
        self.repo_url_edit.setPlaceholderText("https://github.com/username/repository.git")
        repo_layout.addRow("GitHubリポジトリURL:", self.repo_url_edit)

        self.github_token_edit = QLineEdit()
        self.github_token_edit.setEchoMode(QLineEdit.Password)
        self.github_token_edit.setPlaceholderText("ghp_xxxxxxxxxxxxxxxxxxxx")
        repo_layout.addRow("GitHubアクセストークン:", self.github_token_edit)

        repo_group.setLayout(repo_layout)
        scroll_layout.addWidget(repo_group)

        # Git ユーザー設定
        git_group = QGroupBox("Git設定")
        git_layout = QFormLayout()

        self.git_name_edit = QLineEdit()
        git_layout.addRow("ユーザー名:", self.git_name_edit)

        self.git_email_edit = QLineEdit()
        self.git_email_edit.setPlaceholderText("user@example.com")
        git_layout.addRow("メールアドレス:", self.git_email_edit)

        git_group.setLayout(git_layout)
        scroll_layout.addWidget(git_group)

        # 同期オプション
        sync_options_group = QGroupBox("同期オプション")
        sync_options_layout = QVBoxLayout()

        self.auto_sync_check = QCheckBox("保存時に自動コミット")
        sync_options_layout.addWidget(self.auto_sync_check)

        self.sync_on_exit_check = QCheckBox("終了時に自動同期")
        self.sync_on_exit_check.setChecked(True)
        sync_options_layout.addWidget(self.sync_on_exit_check)

        self.auto_pull_check = QCheckBox("起動時にリモートから自動プル")
        sync_options_layout.addWidget(self.auto_pull_check)

        sync_options_group.setLayout(sync_options_layout)
        scroll_layout.addWidget(sync_options_group)

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        self.tab_widget.addTab(sync_tab, "同期設定")

    def create_advanced_tab(self):
        """高度な設定タブ"""
        advanced_tab = QWidget()
        layout = QVBoxLayout(advanced_tab)

        # スクロールエリア
        scroll_area = QScrollArea()
        # スクロールエリアがフォーカスを保持しないようにする
        # scroll_area.setFocusPolicy(Qt.NoFocus)
        # scroll_area.viewport().setFocusPolicy(Qt.NoFocus)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # キャッシュ設定
        cache_group = QGroupBox("キャッシュ設定")
        cache_layout = QVBoxLayout()

        self.enable_cache_check = QCheckBox("パースキャッシュを有効にする")
        self.enable_cache_check.setChecked(True)
        cache_layout.addWidget(self.enable_cache_check)

        cache_button_layout = QHBoxLayout()
        self.clear_cache_button = QPushButton("キャッシュクリア")
        self.clear_cache_button.clicked.connect(self.clear_cache)
        cache_button_layout.addWidget(self.clear_cache_button)

        self.cache_info_button = QPushButton("キャッシュ情報")
        self.cache_info_button.clicked.connect(self.show_cache_info)
        cache_button_layout.addWidget(self.cache_info_button)

        cache_button_layout.addStretch()
        cache_layout.addLayout(cache_button_layout)

        cache_group.setLayout(cache_layout)
        scroll_layout.addWidget(cache_group)

        # デバッグ設定
        debug_group = QGroupBox("デバッグ設定")
        debug_layout = QVBoxLayout()

        self.debug_mode_check = QCheckBox("デバッグモードを有効にする")
        debug_layout.addWidget(self.debug_mode_check)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["INFO", "DEBUG", "WARNING", "ERROR"])
        debug_layout.addWidget(QLabel("ログレベル:"))
        debug_layout.addWidget(self.log_level_combo)

        debug_group.setLayout(debug_layout)
        scroll_layout.addWidget(debug_group)

        # パフォーマンス設定
        performance_group = QGroupBox("パフォーマンス設定")
        performance_layout = QFormLayout()

        self.max_threads_spin = QSpinBox()
        self.max_threads_spin.setRange(1, 16)
        self.max_threads_spin.setValue(4)
        performance_layout.addRow("最大スレッド数:", self.max_threads_spin)

        self.memory_limit_spin = QSpinBox()
        self.memory_limit_spin.setRange(512, 8192)
        self.memory_limit_spin.setValue(2048)
        self.memory_limit_spin.setSuffix(" MB")
        performance_layout.addRow("メモリ使用制限:", self.memory_limit_spin)

        performance_group.setLayout(performance_layout)
        scroll_layout.addWidget(performance_group)

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        self.tab_widget.addTab(advanced_tab, "高度な設定")

    def load_settings(self):
        """設定をUIに読み込み"""
        if not self.app_settings:
            return

        try:
            # 一般設定
            language = self.app_settings.get_setting("language", "ja")
            self.language_combo.setCurrentText("日本語" if language == "ja" else "English")

            theme = self.app_settings.get_setting("theme", "light")
            if theme in ["Windows95", "Modern", "Dark"]:
                self.theme_combo.setCurrentText(theme)

            # ウィンドウ設定
            window_size = self.app_settings.get_setting("window_size", [1080, 720])
            self.width_spin.setValue(window_size[0])
            self.height_spin.setValue(window_size[1])

            fullscreen = self.app_settings.get_setting("fullscreen", False)
            self.fullscreen_check.setChecked(fullscreen)

            # 同期設定
            self.repo_url_edit.setText(self.app_settings.get_setting("sync_repo_url", ""))
            
            # 暗号化された設定を復号化
            encoded_token = self.app_settings.get_setting("sync_github_token", "")
            encoded_name = self.app_settings.get_setting("git_user_name", "")
            encoded_email = self.app_settings.get_setting("git_user_email", "")
            
            try:
                self.github_token_edit.setText(miyabi.decode_text(encoded_token) if encoded_token else "")
                self.git_name_edit.setText(miyabi.decode_text(encoded_name) if encoded_name else "")
                self.git_email_edit.setText(miyabi.decode_text(encoded_email) if encoded_email else "")
            except Exception as e:
                logger.error(f"設定の復号化エラー: {e}")
                self.github_token_edit.setText("")
                self.git_name_edit.setText("")
                self.git_email_edit.setText("")

            self.auto_sync_check.setChecked(self.app_settings.get_setting("auto_sync_enabled", False))
            self.sync_on_exit_check.setChecked(self.app_settings.get_setting("sync_on_exit", True))
            self.auto_pull_check.setChecked(self.app_settings.get_setting("auto_pull_enabled", False))

            # 高度な設定
            self.enable_cache_check.setChecked(self.app_settings.get_setting("enable_cache", True))
            self.debug_mode_check.setChecked(self.app_settings.get_setting("debug_mode", False))

            log_level = self.app_settings.get_setting("log_level", "INFO")
            if log_level in ["INFO", "DEBUG", "WARNING", "ERROR"]:
                self.log_level_combo.setCurrentText(log_level)

            self.max_threads_spin.setValue(self.app_settings.get_setting("max_threads", 4))
            self.memory_limit_spin.setValue(self.app_settings.get_setting("memory_limit", 2048))

        except Exception as e:
            logger.error(f"設定読み込みエラー: {e}")

    def apply_settings(self):
        """設定を適用（保存はしない）"""
        if not self.app_settings:
            return

        try:
            # 同期マネージャーへの設定適用
            if hasattr(self.main_window, 'app_controller') and self.main_window.app_controller:
                sync_manager = self.main_window.app_controller.sync_manager

                # Git設定の更新
                sync_manager.repo_url = self.repo_url_edit.text().strip()
                sync_manager.github_token = self.github_token_edit.text().strip()
                sync_manager.git_user_name = self.git_name_edit.text().strip()
                sync_manager.git_user_email = self.git_email_edit.text().strip()
                sync_manager.auto_sync_enabled = self.auto_sync_check.isChecked()
                sync_manager.sync_on_exit = self.sync_on_exit_check.isChecked()

            QMessageBox.information(self, "適用完了", "設定を適用しました。")

        except Exception as e:
            logger.error(f"設定適用エラー: {e}")
            QMessageBox.critical(self, "エラー", f"設定の適用に失敗しました: {e}")

    def save_settings(self):
        """設定を保存"""
        if not self.app_settings:
            return

        try:
            # 一般設定
            language = "ja" if self.language_combo.currentText() == "日本語" else "en"
            self.app_settings.set_setting("language", language)
            self.app_settings.set_setting("theme", self.theme_combo.currentText())

            # ウィンドウ設定
            window_size = [self.width_spin.value(), self.height_spin.value()]
            self.app_settings.set_setting("window_size", window_size)
            self.app_settings.set_setting("fullscreen", self.fullscreen_check.isChecked())

            # 同期設定
            self.app_settings.set_setting("sync_repo_url", self.repo_url_edit.text().strip())
            
            # 機密情報を暗号化して保存
            github_token = self.github_token_edit.text().strip()
            git_name = self.git_name_edit.text().strip()
            git_email = self.git_email_edit.text().strip()
            
            self.app_settings.set_setting("sync_github_token", miyabi.encode_text(github_token) if github_token else "")
            self.app_settings.set_setting("git_user_name", miyabi.encode_text(git_name) if git_name else "")
            self.app_settings.set_setting("git_user_email", miyabi.encode_text(git_email) if git_email else "")
            
            self.app_settings.set_setting("auto_sync_enabled", self.auto_sync_check.isChecked())
            self.app_settings.set_setting("sync_on_exit", self.sync_on_exit_check.isChecked())
            self.app_settings.set_setting("auto_pull_enabled", self.auto_pull_check.isChecked())

            # 高度な設定
            self.app_settings.set_setting("enable_cache", self.enable_cache_check.isChecked())
            self.app_settings.set_setting("debug_mode", self.debug_mode_check.isChecked())
            self.app_settings.set_setting("log_level", self.log_level_combo.currentText())
            self.app_settings.set_setting("max_threads", self.max_threads_spin.value())
            self.app_settings.set_setting("memory_limit", self.memory_limit_spin.value())

            # 同期マネージャーにも適用
            self.apply_settings()

            # リポジトリセットアップ
            if (hasattr(self.main_window, 'app_controller') and
                    self.main_window.app_controller and
                    self.repo_url_edit.text().strip()):

                sync_manager = self.main_window.app_controller.sync_manager
                success = sync_manager.setup_repository(
                    self.repo_url_edit.text().strip(),
                    self.github_token_edit.text().strip()
                )

                if success:
                    QMessageBox.information(self, "保存完了", "設定を保存し、リポジトリをセットアップしました。")
                else:
                    QMessageBox.warning(self, "警告", "設定は保存されましたが、リポジトリのセットアップに失敗しました。")
            else:
                QMessageBox.information(self, "保存完了", "設定を保存しました。")

        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
            QMessageBox.critical(self, "エラー", f"設定の保存に失敗しました: {e}")

    def test_git_connection(self):
        """Git接続テスト"""
        repo_url = self.repo_url_edit.text().strip()
        github_token = self.github_token_edit.text().strip()

        if not repo_url:
            QMessageBox.warning(self, "警告", "リポジトリURLを入力してください。")
            return

        try:
            # GitHub APIで接続テスト
            if github_token and 'github.com' in repo_url:
                repo_path = repo_url.replace('https://github.com/', '').replace('.git', '')
                api_url = f"https://api.github.com/repos/{repo_path}"

                headers = {'Authorization': f'token {github_token}'}
                response = requests.get(api_url, headers=headers, timeout=10)

                if response.status_code == 200:
                    QMessageBox.information(self, "成功", "GitHub APIでの接続に成功しました。")
                else:
                    QMessageBox.warning(self, "警告", f"GitHub API接続エラー: {response.status_code}")
            else:
                # Git コマンドでテスト
                result = subprocess.run(['git', 'ls-remote', repo_url],
                                        capture_output=True, text=True, timeout=10)

                if result.returncode == 0:
                    QMessageBox.information(self, "成功", "リポジトリへの接続に成功しました。")
                else:
                    QMessageBox.warning(self, "警告", f"接続エラー: {result.stderr}")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"接続テストエラー: {e}")

    def clear_cache(self):
        """キャッシュクリア"""
        if hasattr(self.main_window, 'app_controller') and self.main_window.app_controller:
            try:
                self.main_window.app_controller.clear_cache()
                QMessageBox.information(self, "完了", "キャッシュをクリアしました。")
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"キャッシュクリアに失敗しました: {e}")
        else:
            QMessageBox.warning(self, "警告", "アプリケーションコントローラーが利用できません。")

    def show_cache_info(self):
        """キャッシュ情報表示"""
        if hasattr(self.main_window, 'app_controller') and self.main_window.app_controller:
            try:
                cache_info = self.main_window.app_controller.get_cache_info()

                # 情報表示ダイアログ
                dialog = QMessageBox(self)
                dialog.setWindowTitle("キャッシュ情報")
                dialog.setIcon(QMessageBox.Information)

                info_text = f"MOD名: {cache_info.get('mod_name', 'N/A')}\n"
                info_text += f"キャッシュディレクトリ: {cache_info.get('base_cache_dir', 'N/A')}\n"
                info_text += f"キャッシュ存在: {cache_info.get('cache_exists', False)}\n\n"

                file_types = cache_info.get('file_types', [])
                if file_types:
                    info_text += "ファイル種別別キャッシュ数:\n"
                    for file_type_info in file_types:
                        info_text += f"  - {file_type_info['type']}: {file_type_info['cache_count']}件\n"
                else:
                    info_text += "キャッシュファイルなし\n"

                dialog.setText(info_text)
                dialog.exec_()

            except Exception as e:
                QMessageBox.critical(self, "エラー", f"キャッシュ情報の取得に失敗しました: {e}")
        else:
            QMessageBox.warning(self, "警告", "アプリケーションコントローラーが利用できません。")