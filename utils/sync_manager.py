import os
import json
import subprocess
import requests
import base64
import logging
from datetime import datetime
from typing import Optional, Dict, List
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt5.QtWidgets import QMessageBox, QProgressDialog, QInputDialog, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QCheckBox

logger = logging.getLogger(__name__)

class SyncWorker(QThread):
    """同期処理用のワーカースレッド"""
    progress = pyqtSignal(str)  # 進捗メッセージ
    finished = pyqtSignal(bool, str)  # 成功/失敗, メッセージ
    error = pyqtSignal(str)  # エラーメッセージ

    def __init__(self, sync_manager, operation):
        super().__init__()
        self.sync_manager = sync_manager
        self.operation = operation  # 'push', 'pull', 'full_sync'

    def run(self):
        try:
            if self.operation == 'push':
                result = self.sync_manager._push_data()
            elif self.operation == 'pull':
                result = self.sync_manager._pull_data()
            elif self.operation == 'full_sync':
                result = self.sync_manager._full_sync()
            else:
                result = (False, f"不明な操作: {self.operation}")

            self.finished.emit(result[0], result[1])
        except Exception as e:
            logger.error(f"同期エラー: {e}")
            self.error.emit(str(e))

class SyncManager(QObject):
    """データ同期管理クラス"""

    # シグナル定義
    sync_started = pyqtSignal(str)  # 同期開始
    sync_progress = pyqtSignal(str)  # 進捗更新
    sync_completed = pyqtSignal(bool, str)  # 完了（成功/失敗, メッセージ）

    def __init__(self, app_settings):
        super().__init__()
        self.app_settings = app_settings
        self.data_dir = app_settings.data_dir

        # 設定の初期化
        self.repo_url = self.app_settings.get_setting("sync_repo_url", "")
        self.github_token = self.app_settings.get_setting("sync_github_token", "")
        self.auto_sync_enabled = self.app_settings.get_setting("auto_sync_enabled", False)
        self.sync_on_exit = self.app_settings.get_setting("sync_on_exit", True)

        # Git設定
        self.git_user_name = self.app_settings.get_setting("git_user_name", "")
        self.git_user_email = self.app_settings.get_setting("git_user_email", "")

        # 自動同期タイマー
        self.auto_sync_timer = QTimer()
        self.auto_sync_timer.timeout.connect(self._auto_sync_check)

        # ワーカースレッド
        self.worker = None

    def is_configured(self) -> bool:
        """同期設定が完了しているかチェック"""
        return bool(self.repo_url and (self.github_token or self._has_git_credentials()))

    def _has_git_credentials(self) -> bool:
        """Git認証情報があるかチェック"""
        try:
            # SSH鍵またはHTTPS認証の確認
            result = subprocess.run(['git', 'config', '--get', 'user.name'],
                                    capture_output=True, text=True, cwd=self.data_dir)
            return result.returncode == 0
        except Exception:
            return False

    def setup_repository(self, repo_url: str, github_token: str = "", use_git_cmd: bool = True) -> bool:
        """リポジトリのセットアップ"""
        try:
            self.repo_url = repo_url
            self.github_token = github_token

            # 設定を保存
            self.app_settings.set_setting("sync_repo_url", repo_url)
            if github_token:
                self.app_settings.set_setting("sync_github_token", github_token)

            # .gitディレクトリが存在するかチェック
            git_dir = os.path.join(self.data_dir, ".git")

            if not os.path.exists(git_dir):
                # 新規リポジトリの初期化
                if use_git_cmd:
                    return self._init_git_repository()
                else:
                    return self._init_github_repository()
            else:
                # 既存リポジトリの設定更新
                return self._update_git_config()

        except Exception as e:
            logger.error(f"リポジトリセットアップエラー: {e}")
            return False

    def _init_git_repository(self) -> bool:
        """Gitコマンドでリポジトリを初期化"""
        try:
            # Gitリポジトリ初期化
            subprocess.run(['git', 'init'], cwd=self.data_dir, check=True)

            # リモートリポジトリ設定
            subprocess.run(['git', 'remote', 'add', 'origin', self.repo_url],
                           cwd=self.data_dir, check=True)

            # Git設定
            if self.git_user_name:
                subprocess.run(['git', 'config', 'user.name', self.git_user_name],
                               cwd=self.data_dir, check=True)
            if self.git_user_email:
                subprocess.run(['git', 'config', 'user.email', self.git_user_email],
                               cwd=self.data_dir, check=True)

            # .gitignoreファイルの作成
            self._create_gitignore()

            # 初回コミット
            subprocess.run(['git', 'add', '.'], cwd=self.data_dir, check=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit: Naval Design System data'],
                           cwd=self.data_dir, check=True)

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Gitコマンドエラー: {e}")
            return False

    def _create_gitignore(self):
        """適切な.gitignoreファイルを作成"""
        gitignore_content = """# Naval Design System
*.tmp
*.log
*.cache
__pycache__/
.DS_Store
Thumbs.db

# 一時ファイル
temp/
cache/
*.bmp
*.png
# バックアップファイル
*.bak
*.pkl
"""
        gitignore_path = os.path.join(self.data_dir, ".gitignore")
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write(gitignore_content)

    def sync_data_async(self, operation: str = 'full_sync'):
        """非同期でデータ同期を実行"""
        if not self.is_configured():
            self.sync_completed.emit(False, "同期設定が完了していません")
            return

        if self.worker and self.worker.isRunning():
            self.sync_completed.emit(False, "既に同期処理が実行中です")
            return

        self.sync_started.emit(f"データ同期を開始: {operation}")

        # ワーカースレッドで同期実行
        self.worker = SyncWorker(self, operation)
        self.worker.progress.connect(self.sync_progress.emit)
        self.worker.finished.connect(self.sync_completed.emit)
        self.worker.error.connect(lambda msg: self.sync_completed.emit(False, msg))
        self.worker.start()

    def _full_sync(self) -> tuple:
        """完全同期（プル→プッシュ）"""
        try:
            # まずリモートの変更を取得
            pull_result = self._pull_data()
            if not pull_result[0]:
                return pull_result

            # ローカルの変更をプッシュ
            push_result = self._push_data()
            return push_result

        except Exception as e:
            return (False, f"完全同期エラー: {e}")

    def _pull_data(self) -> tuple:
        """リモートからデータを取得"""
        try:
            self.sync_progress.emit("リモートデータを取得中...")

            # Git pullを実行
            result = subprocess.run(['git', 'pull', 'origin', 'main'],
                                    cwd=self.data_dir, capture_output=True, text=True)

            if result.returncode != 0:
                # mainブランチが存在しない場合はmasterを試行
                result = subprocess.run(['git', 'pull', 'origin', 'master'],
                                        cwd=self.data_dir, capture_output=True, text=True)

            if result.returncode == 0:
                return (True, "リモートデータの取得が完了しました")
            else:
                return (False, f"データ取得エラー: {result.stderr}")

        except Exception as e:
            return (False, f"プルエラー: {e}")

    def _push_data(self) -> tuple:
        """ローカルデータをリモートにプッシュ"""
        try:
            self.sync_progress.emit("変更をコミット中...")

            # 変更をステージング
            subprocess.run(['git', 'add', '.'], cwd=self.data_dir, check=True)

            # 変更があるかチェック
            result = subprocess.run(['git', 'diff', '--cached', '--quiet'],
                                    cwd=self.data_dir)

            if result.returncode == 0:
                return (True, "変更がありません")

            # コミット
            commit_msg = f"Naval Design System data update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            subprocess.run(['git', 'commit', '-m', commit_msg],
                           cwd=self.data_dir, check=True)

            self.sync_progress.emit("リモートにプッシュ中...")

            # プッシュ
            result = subprocess.run(['git', 'push', 'origin', 'main'],
                                    cwd=self.data_dir, capture_output=True, text=True)

            if result.returncode != 0:
                # mainブランチが存在しない場合はmasterを試行
                result = subprocess.run(['git', 'push', 'origin', 'master'],
                                        cwd=self.data_dir, capture_output=True, text=True)

            if result.returncode == 0:
                return (True, "データのプッシュが完了しました")
            else:
                return (False, f"プッシュエラー: {result.stderr}")

        except subprocess.CalledProcessError as e:
            return (False, f"コミットエラー: {e}")

    def auto_sync_on_save(self):
        """保存時の自動同期"""
        if self.auto_sync_enabled and self.is_configured():
            # ローカルコミットのみ（プッシュは手動）
            self._local_commit()

    def _local_commit(self):
        """ローカルコミットのみ実行"""
        try:
            subprocess.run(['git', 'add', '.'], cwd=self.data_dir, check=True)

            # 変更があるかチェック
            result = subprocess.run(['git', 'diff', '--cached', '--quiet'],
                                    cwd=self.data_dir)

            if result.returncode != 0:
                commit_msg = f"Auto save: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                subprocess.run(['git', 'commit', '-m', commit_msg],
                               cwd=self.data_dir, check=True)
                logger.info("自動コミット完了")

        except Exception as e:
            logger.error(f"自動コミットエラー: {e}")

    def sync_on_exit(self):
        """終了時の同期"""
        if self.sync_on_exit and self.is_configured():
            try:
                # 同期実行（同期処理）
                result = self._push_data()
                if result[0]:
                    logger.info("終了時同期完了")
                else:
                    logger.error(f"終了時同期エラー: {result[1]}")
            except Exception as e:
                logger.error(f"終了時同期エラー: {e}")

    def _auto_sync_check(self):
        """自動同期チェック（定期実行）"""
        # 実装は必要に応じて追加
        pass

    def show_sync_settings_dialog(self, parent=None):
        """同期設定ダイアログを表示"""
        dialog = SyncSettingsDialog(self, parent)
        return dialog.exec_()

class SyncSettingsDialog(QDialog):
    """同期設定ダイアログ"""

    def __init__(self, sync_manager, parent=None):
        super().__init__(parent)
        self.sync_manager = sync_manager
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        self.setWindowTitle("データ同期設定")
        self.setMinimumWidth(500)

        layout = QVBoxLayout()

        # リポジトリURL
        layout.addWidget(QLabel("GitHubリポジトリURL:"))
        self.repo_url_edit = QLineEdit()
        self.repo_url_edit.setPlaceholderText("https://github.com/username/repository.git")
        layout.addWidget(self.repo_url_edit)

        # GitHubトークン
        layout.addWidget(QLabel("GitHubパーソナルアクセストークン（オプション）:"))
        self.github_token_edit = QLineEdit()
        self.github_token_edit.setEchoMode(QLineEdit.Password)
        self.github_token_edit.setPlaceholderText("ghp_xxxxxxxxxxxxxxxxxxxx")
        layout.addWidget(self.github_token_edit)

        # Git設定
        layout.addWidget(QLabel("Git設定:"))

        git_layout = QHBoxLayout()
        git_layout.addWidget(QLabel("ユーザー名:"))
        self.git_name_edit = QLineEdit()
        git_layout.addWidget(self.git_name_edit)

        git_layout.addWidget(QLabel("メール:"))
        self.git_email_edit = QLineEdit()
        git_layout.addWidget(self.git_email_edit)
        layout.addLayout(git_layout)

        # オプション
        self.auto_sync_check = QCheckBox("保存時に自動コミット")
        layout.addWidget(self.auto_sync_check)

        self.sync_on_exit_check = QCheckBox("終了時に自動同期")
        self.sync_on_exit_check.setChecked(True)
        layout.addWidget(self.sync_on_exit_check)

        # ボタン
        button_layout = QHBoxLayout()

        test_button = QPushButton("接続テスト")
        test_button.clicked.connect(self.test_connection)
        button_layout.addWidget(test_button)

        button_layout.addStretch()

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)

        cancel_button = QPushButton("キャンセル")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def load_settings(self):
        """設定を読み込み"""
        self.repo_url_edit.setText(self.sync_manager.repo_url)
        self.github_token_edit.setText(self.sync_manager.github_token)
        self.git_name_edit.setText(self.sync_manager.git_user_name)
        self.git_email_edit.setText(self.sync_manager.git_user_email)
        self.auto_sync_check.setChecked(self.sync_manager.auto_sync_enabled)
        self.sync_on_exit_check.setChecked(self.sync_manager.sync_on_exit)

    def accept(self):
        """設定を保存"""
        self.sync_manager.repo_url = self.repo_url_edit.text().strip()
        self.sync_manager.github_token = self.github_token_edit.text().strip()
        self.sync_manager.git_user_name = self.git_name_edit.text().strip()
        self.sync_manager.git_user_email = self.git_email_edit.text().strip()
        self.sync_manager.auto_sync_enabled = self.auto_sync_check.isChecked()
        self.sync_manager.sync_on_exit = self.sync_on_exit_check.isChecked()

        # app_settingsに保存
        self.sync_manager.app_settings.set_setting("sync_repo_url", self.sync_manager.repo_url)
        self.sync_manager.app_settings.set_setting("sync_github_token", self.sync_manager.github_token)
        self.sync_manager.app_settings.set_setting("git_user_name", self.sync_manager.git_user_name)
        self.sync_manager.app_settings.set_setting("git_user_email", self.sync_manager.git_user_email)
        self.sync_manager.app_settings.set_setting("auto_sync_enabled", self.sync_manager.auto_sync_enabled)
        self.sync_manager.app_settings.set_setting("sync_on_exit", self.sync_manager.sync_on_exit)

        # リポジトリセットアップ
        if self.sync_manager.repo_url:
            success = self.sync_manager.setup_repository(
                self.sync_manager.repo_url,
                self.sync_manager.github_token
            )

            if success:
                QMessageBox.information(self, "成功", "同期設定が完了しました")
            else:
                QMessageBox.warning(self, "警告", "リポジトリのセットアップに失敗しました")

        super().accept()

    def test_connection(self):
        """接続テスト"""
        repo_url = self.repo_url_edit.text().strip()
        github_token = self.github_token_edit.text().strip()

        if not repo_url:
            QMessageBox.warning(self, "警告", "リポジトリURLを入力してください")
            return

        try:
            # GitHub APIで接続テスト
            if github_token and 'github.com' in repo_url:
                # リポジトリ情報を取得してテスト
                repo_path = repo_url.replace('https://github.com/', '').replace('.git', '')
                api_url = f"https://api.github.com/repos/{repo_path}"

                headers = {'Authorization': f'token {github_token}'}
                response = requests.get(api_url, headers=headers, timeout=10)

                if response.status_code == 200:
                    QMessageBox.information(self, "成功", "GitHub APIでの接続に成功しました")
                else:
                    QMessageBox.warning(self, "警告", f"GitHub API接続エラー: {response.status_code}")
            else:
                # Git コマンドでテスト
                result = subprocess.run(['git', 'ls-remote', repo_url],
                                        capture_output=True, text=True, timeout=10)

                if result.returncode == 0:
                    QMessageBox.information(self, "成功", "リポジトリへの接続に成功しました")
                else:
                    QMessageBox.warning(self, "警告", f"接続エラー: {result.stderr}")

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"接続テストエラー: {e}")