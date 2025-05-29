import os
import json
import subprocess
import requests
import base64
import logging
from datetime import datetime
from typing import Optional, Dict, List
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt5.QtWidgets import QMessageBox, QProgressDialog, QInputDialog

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

    def _init_github_repository(self) -> bool:
        """GitHub APIでリポジトリを初期化（将来の実装用）"""
        # 現在は未実装
        logger.warning("GitHub API経由の初期化は未実装です")
        return False

    def _update_git_config(self) -> bool:
        """既存リポジトリのGit設定を更新"""
        try:
            # リモートリポジトリ設定の更新
            result = subprocess.run(['git', 'remote', 'get-url', 'origin'],
                                    cwd=self.data_dir, capture_output=True, text=True)

            if result.returncode == 0:
                # 既存のリモートURLと比較
                current_url = result.stdout.strip()
                if current_url != self.repo_url:
                    subprocess.run(['git', 'remote', 'set-url', 'origin', self.repo_url],
                                   cwd=self.data_dir, check=True)
            else:
                # リモートが存在しない場合は追加
                subprocess.run(['git', 'remote', 'add', 'origin', self.repo_url],
                               cwd=self.data_dir, check=True)

            # Git設定の更新
            if self.git_user_name:
                subprocess.run(['git', 'config', 'user.name', self.git_user_name],
                               cwd=self.data_dir, check=True)
            if self.git_user_email:
                subprocess.run(['git', 'config', 'user.email', self.git_user_email],
                               cwd=self.data_dir, check=True)

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Git設定更新エラー: {e}")
            return False

    def _create_gitignore(self):
        """Naval Design System用の.gitignoreファイルを作成"""
        gitignore_content = """# Naval Design System - Generated .gitignore
# このファイルはNaval Design Systemによって自動生成されました
# 必要に応じて手動で編集してください

# === Python関連 ===
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# === PyQt5関連 ===
*.ui~
*.qrc~

# === Naval Design System関連 ===
# キャッシュファイル
caches/
*.cache
*.pkl

# ログファイル
*.log
app.log
debug.log

# 一時ファイル
*.tmp
*.temp
temp/
temporary/

# バックアップファイル
*.bak
*.backup
*~
*.orig

# === HOI4 MOD開発関連 ===
# パーサー自動生成ファイル
parser/parsetab.py
parser/*_parsetab.py
parser/parser.out

# 設定ファイル（機密情報を含む可能性）
settings_local.json
config_local.json

# === 画像・メディアファイル ===
# 生成された画像ファイル
generated_images/
*.bmp
*.png
*.jpg
*.jpeg
*.gif
*.tga
*.dds

# === IDE・エディタ関連 ===
# PyCharm
.idea/

# VSCode
.vscode/
*.code-workspace

# Sublime Text
*.sublime-project
*.sublime-workspace

# Vim
*.swp
*.swo
*~

# Emacs
*~
\#*\#
/.emacs.desktop
/.emacs.desktop.lock
*.elc
auto-save-list
tramp
.\#*

# === OS関連 ===
# Windows
Thumbs.db
ehthumbs.db
Desktop.ini
$RECYCLE.BIN/

# macOS
.DS_Store
.AppleDouble
.LSOverride
Icon
._*
.DocumentRevisions-V100
.fseventsd
.Spotlight-V100
.TemporaryItems
.Trashes
.VolumeIcon.icns
.com.apple.timemachine.donotpresent

# Linux
*~
.fuse_hidden*
.directory
.Trash-*
.nfs*

# === Git関連 ===
*.orig
*.rej

# === データベース関連 ===
*.db
*.sqlite
*.sqlite3

# === 証明書・鍵ファイル ===
*.pem
*.key
*.crt
*.p12

# === 圧縮ファイル ===
*.zip
*.tar.gz
*.rar
*.7z

# === プロジェクト固有 ===
# 大容量テストデータ
test_data_large/
benchmark_results/

# ユーザー固有の設定
user_preferences.json
local_settings.json
"""
        gitignore_path = os.path.join(self.data_dir, ".gitignore")

        # 既存の.gitignoreが存在する場合はバックアップを作成
        if os.path.exists(gitignore_path):
            backup_path = gitignore_path + ".backup"
            import shutil
            shutil.copy2(gitignore_path, backup_path)
            logger.info(f".gitignoreのバックアップを作成: {backup_path}")

        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write(gitignore_content)

        logger.info(f".gitignoreファイルを作成: {gitignore_path}")

    def get_gitignore_content(self) -> str:
        """現在の.gitignoreファイルの内容を取得"""
        gitignore_path = os.path.join(self.data_dir, ".gitignore")
        if os.path.exists(gitignore_path):
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.error(f".gitignore読み込みエラー: {e}")
                return ""
        return ""

    def save_gitignore_content(self, content: str) -> bool:
        """新しい.gitignoreファイルの内容を保存"""
        gitignore_path = os.path.join(self.data_dir, ".gitignore")
        try:
            # バックアップを作成
            if os.path.exists(gitignore_path):
                backup_path = gitignore_path + ".backup"
                import shutil
                shutil.copy2(gitignore_path, backup_path)

            # 新しい内容を保存
            with open(gitignore_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(".gitignoreファイルを更新しました")
            return True

        except Exception as e:
            logger.error(f".gitignore保存エラー: {e}")
            return False

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

    def reload_settings(self):
        """設定を再読み込み"""
        self.repo_url = self.app_settings.get_setting("sync_repo_url", "")
        self.github_token = self.app_settings.get_setting("sync_github_token", "")
        self.auto_sync_enabled = self.app_settings.get_setting("auto_sync_enabled", False)
        self.sync_on_exit = self.app_settings.get_setting("sync_on_exit", True)
        self.git_user_name = self.app_settings.get_setting("git_user_name", "")
        self.git_user_email = self.app_settings.get_setting("git_user_email", "")