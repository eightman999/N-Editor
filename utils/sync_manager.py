import os
import json
import subprocess
import requests
import base64
import logging
import shutil
from datetime import datetime
from typing import Optional, Dict, List
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer
from PyQt5.QtWidgets import QMessageBox, QProgressDialog, QInputDialog, QApplication
import miyabi

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
    """データ同期管理クラス（コンフリクト対応版）"""

    # シグナル定義
    sync_started = pyqtSignal(str)  # 同期開始
    sync_progress = pyqtSignal(str)  # 進捗更新
    sync_completed = pyqtSignal(bool, str)  # 完了（成功/失敗, メッセージ）
    conflict_detected = pyqtSignal(dict, str)  # conflict_info, backup_path

    def __init__(self, app_settings):
        super().__init__()
        self.app_settings = app_settings
        self.data_dir = app_settings.data_dir
        
        # バックアップディレクトリの設定
        self.backup_dir = os.path.join(self.data_dir, '.sync_backups')
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 設定の初期化
        self.repo_url = self.app_settings.get_setting("sync_repo_url", "")
        self.github_token = self.app_settings.get_setting("sync_github_token", "")
        self.auto_sync_enabled = self.app_settings.get_setting("auto_sync_enabled", False)
        self.sync_on_exit = self.app_settings.get_setting("sync_on_exit", True)
        self.git_user_name = self.app_settings.get_setting("git_user_name", "")
        self.git_user_email = self.app_settings.get_setting("git_user_email", "")

        # 自動同期タイマー
        self.auto_sync_timer = QTimer()
        self.auto_sync_timer.timeout.connect(self._auto_sync_check)

        # ワーカースレッド
        self.worker = None
        
        # コンフリクト解決用のシグナル接続
        self.conflict_detected.connect(self._show_conflict_dialog)

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
                # トークンを暗号化して保存
                self.app_settings.set_setting("sync_github_token", miyabi.encode_text(github_token))

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
config.json
setting.json
settings.json
mods.json

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
\\#*\\#
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
        """リモートからデータを取得（改善版）"""
        try:
            self.sync_progress.emit("リモートデータを取得中...")
            
            # バックアップを作成
            backup_path = self._create_backup()
            logger.info(f"バックアップを作成しました: {backup_path}")
            
            # フェッチを実行
            fetch_result = subprocess.run(
                ['git', 'fetch', 'origin'], 
                cwd=self.data_dir, capture_output=True, text=True
            )
            
            if fetch_result.returncode != 0:
                return (False, f"リモートデータの取得に失敗: {fetch_result.stderr}")
            
            # ブランチの状態を分析
            conflict_info = self._analyze_branch_status()
            
            if conflict_info.get('has_divergence', False):
                logger.warning("ブランチの分散を検出しました")
                
                # UIスレッドでコンフリクト解決ダイアログを表示
                self.conflict_detected.emit(conflict_info, backup_path)
                
                # ダイアログの結果を待つ（同期処理として扱う）
                return (False, "コンフリクト解決が必要です。ダイアログで選択してください。")
            else:
                # 通常のpullを実行
                return self._execute_simple_pull()
                
        except Exception as e:
            logger.error(f"プル処理中にエラー: {e}")
            return (False, f"データ取得エラー: {e}")

    def _push_data(self) -> tuple:
        """ローカルデータをリモートにプッシュ（競合対応版）"""
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

            # まずプッシュを試行
            result = subprocess.run(['git', 'push', 'origin', 'master'],
                                    cwd=self.data_dir, capture_output=True, text=True)

            if result.returncode == 0:
                return (True, "データのプッシュが完了しました")
            
            # プッシュが失敗した場合（競合の可能性）
            if "rejected" in result.stderr or "non-fast-forward" in result.stderr:
                self.sync_progress.emit("競合を解決中...")
                
                # リモートの変更を取得してリベース
                pull_result = subprocess.run(['git', 'pull', '--rebase', 'origin', 'master'],
                                             cwd=self.data_dir, capture_output=True, text=True)
                
                if pull_result.returncode != 0:
                    # masterブランチも試行
                    pull_result = subprocess.run(['git', 'pull', '--rebase', 'origin', 'master'],
                                                 cwd=self.data_dir, capture_output=True, text=True)
                
                if pull_result.returncode == 0:
                    # リベース成功後、再度プッシュ
                    retry_result = subprocess.run(['git', 'push', 'origin', 'master'],
                                                  cwd=self.data_dir, capture_output=True, text=True)
                    
                    if retry_result.returncode != 0:
                        # mainブランチも試行
                        retry_result = subprocess.run(['git', 'push', 'origin', 'main'],
                                                      cwd=self.data_dir, capture_output=True, text=True)
                    
                    if retry_result.returncode == 0:
                        return (True, "競合解決後、データのプッシュが完了しました")
                    else:
                        return (False, f"競合解決後のプッシュエラー: {retry_result.stderr}")
                else:
                    return (False, f"リベースエラー: {pull_result.stderr}")
            
            # その他のエラー
            return (False, f"プッシュエラー: {result.stderr}")

        except subprocess.CalledProcessError as e:
            return (False, f"コマンド実行エラー: {e}")
        except Exception as e:
            return (False, f"予期しないエラー: {e}")

    def handle_git_conflict(self) -> tuple:
        """Git競合の自動解決を試行"""
        try:
            # リベース中の競合チェック
            rebase_status = subprocess.run(['git', 'status', '--porcelain'],
                                           cwd=self.data_dir, capture_output=True, text=True)
            
            if 'UU' in rebase_status.stdout:  # マージ競合
                # 自動解決を試行（Naval Design Systemの場合、通常は自分の変更を優先）
                subprocess.run(['git', 'checkout', '--ours', '.'],
                               cwd=self.data_dir, check=True)
                
                subprocess.run(['git', 'add', '.'],
                               cwd=self.data_dir, check=True)
                
                subprocess.run(['git', 'rebase', '--continue'],
                               cwd=self.data_dir, check=True)
                
                return (True, "競合を自動解決しました")
            
            return (True, "競合はありませんでした")
            
        except subprocess.CalledProcessError as e:
            return (False, f"競合解決エラー: {e}")

    def sync_data_with_conflict_resolution(self) -> tuple:
        """競合対応付きの完全同期"""
        try:
            # まずリモートの変更を取得
            pull_result = self._pull_data()
            if not pull_result[0]:
                return pull_result

            # ローカルの変更をプッシュ
            push_result = self._push_data()
            return push_result

        except Exception as e:
            return (False, f"同期エラー: {e}")

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
        
        # 暗号化されたトークンを復号化
        encoded_token = self.app_settings.get_setting("sync_github_token", "")
        try:
            self.github_token = miyabi.decode_text(encoded_token) if encoded_token else ""
        except Exception as e:
            logger.error(f"トークンの復号化エラー: {e}")
            self.github_token = ""
            
        self.auto_sync_enabled = self.app_settings.get_setting("auto_sync_enabled", False)
        self.sync_on_exit = self.app_settings.get_setting("sync_on_exit", True)
        
        # Gitユーザー情報も復号化
        encoded_name = self.app_settings.get_setting("git_user_name", "")
        encoded_email = self.app_settings.get_setting("git_user_email", "")
        
        try:
            self.git_user_name = miyabi.decode_text(encoded_name) if encoded_name else ""
            self.git_user_email = miyabi.decode_text(encoded_email) if encoded_email else ""
        except Exception as e:
            logger.error(f"Gitユーザー情報の復号化エラー: {e}")
            self.git_user_name = ""
            self.git_user_email = ""

    def _analyze_branch_status(self) -> dict:
        """ブランチの状態を分析"""
        try:
            conflict_info = {
                'has_divergence': False,
                'current_branch': '',
                'remote_branch': '',
                'local_commits': [],
                'remote_commits': [],
                'changed_files': [],
                'diff_content': ''
            }
            
            # 現在のブランチを取得
            branch_result = subprocess.run(
                ['git', 'branch', '--show-current'], 
                cwd=self.data_dir, capture_output=True, text=True
            )
            
            if branch_result.returncode == 0:
                conflict_info['current_branch'] = branch_result.stdout.strip() or 'master'
            else:
                conflict_info['current_branch'] = 'master'
            
            # リモートブランチ名を設定
            remote_branch = f"origin/{conflict_info['current_branch']}"
            conflict_info['remote_branch'] = remote_branch
            
            # 分散の確認
            try:
                divergence_result = subprocess.run(
                    ['git', 'rev-list', '--left-right', '--count', f'HEAD...{remote_branch}'], 
                    cwd=self.data_dir, capture_output=True, text=True
                )
                
                if divergence_result.returncode == 0:
                    counts = divergence_result.stdout.strip().split('\t')
                    if len(counts) >= 2:
                        local_ahead = int(counts[0])
                        remote_ahead = int(counts[1])
                        
                        conflict_info['has_divergence'] = local_ahead > 0 and remote_ahead > 0
                        
                        # 詳細情報を取得（分散がある場合のみ）
                        if conflict_info['has_divergence']:
                            self._get_commit_details(conflict_info, remote_branch)
                            
            except (subprocess.SubprocessError, ValueError, IndexError) as e:
                logger.warning(f"分散状態の確認に失敗: {e}")
                # 安全のため、分散ありとして扱う
                conflict_info['has_divergence'] = True
            
            return conflict_info
            
        except Exception as e:
            logger.error(f"ブランチ状態分析エラー: {e}")
            return {
                'has_divergence': True,  # エラー時は安全のため分散ありとする
                'error': str(e)
            }

    def _create_backup(self) -> str:
        """現在の状態をバックアップ"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # データディレクトリをコピー（.gitディレクトリも含む）
            shutil.copytree(self.data_dir, backup_path, 
                          ignore=shutil.ignore_patterns('.sync_backups'))
            
            logger.info(f"バックアップを作成: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"バックアップ作成エラー: {e}")
            raise Exception(f"バックアップ作成に失敗: {e}")

    def _restore_backup(self, backup_path: str) -> bool:
        """バックアップから復元"""
        try:
            if not os.path.exists(backup_path):
                logger.error(f"バックアップが存在しません: {backup_path}")
                return False
            
            # 現在のデータディレクトリを一時移動
            temp_dir = f"{self.data_dir}_temp_{int(datetime.now().timestamp())}"
            shutil.move(self.data_dir, temp_dir)
            
            try:
                # バックアップから復元
                shutil.copytree(backup_path, self.data_dir)
                
                # 一時ディレクトリを削除
                shutil.rmtree(temp_dir)
                
                logger.info(f"バックアップから復元完了: {backup_path}")
                return True
                
            except Exception as e:
                # 復元に失敗した場合は元に戻す
                if os.path.exists(self.data_dir):
                    shutil.rmtree(self.data_dir)
                shutil.move(temp_dir, self.data_dir)
                raise e
                
        except Exception as e:
            logger.error(f"バックアップ復元エラー: {e}")
            return False

    def _cleanup_old_backups(self, keep_count: int = 5):
        """古いバックアップを削除"""
        try:
            if not os.path.exists(self.backup_dir):
                return
            
            backups = []
            for item in os.listdir(self.backup_dir):
                item_path = os.path.join(self.backup_dir, item)
                if os.path.isdir(item_path) and item.startswith('backup_'):
                    backups.append((item_path, os.path.getmtime(item_path)))
            
            # 作成日時でソート（新しい順）
            backups.sort(key=lambda x: x[1], reverse=True)
            
            # 指定数を超えるバックアップを削除
            for backup_path, _ in backups[keep_count:]:
                shutil.rmtree(backup_path)
                logger.info(f"古いバックアップを削除: {backup_path}")
                
        except Exception as e:
            logger.warning(f"バックアップクリーンアップエラー: {e}")

    def _show_conflict_dialog(self, conflict_info: dict, backup_path: str):
        """コンフリクト解決ダイアログを表示（UIスレッド）"""
        from .conflict_resolution_dialog import ConflictResolutionDialog
        
        try:
            # メインウィンドウを取得
            app = QApplication.instance()
            main_window = None
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'app_controller'):
                    main_window = widget
                    break
            
            # ダイアログを表示
            dialog = ConflictResolutionDialog(conflict_info, main_window)
            if dialog.exec_() == dialog.Accepted:
                resolution = dialog.resolution_choice
                
                # 選択された解決方法を実行
                result = self._execute_resolution(resolution, backup_path, conflict_info)
                
                # 結果をメインウィンドウに通知
                if main_window and hasattr(main_window, 'on_sync_completed'):
                    main_window.on_sync_completed(result[0], result[1])
            else:
                # キャンセルされた場合
                if main_window and hasattr(main_window, 'on_sync_completed'):
                    main_window.on_sync_completed(False, "同期がキャンセルされました")
                    
        except Exception as e:
            logger.error(f"コンフリクトダイアログ表示エラー: {e}")

    def _get_commit_details(self, conflict_info: dict, remote_branch: str):
        """コミットの詳細情報を取得"""
        try:
            # ローカルコミットを取得
            local_commits_result = subprocess.run(
                ['git', 'log', '--oneline', f'{remote_branch}..HEAD'], 
                cwd=self.data_dir, capture_output=True, text=True
            )
            
            if local_commits_result.returncode == 0:
                for line in local_commits_result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split(' ', 1)
                        conflict_info['local_commits'].append({
                            'hash': parts[0],
                            'message': parts[1] if len(parts) > 1 else ''
                        })
            
            # リモートコミットを取得
            remote_commits_result = subprocess.run(
                ['git', 'log', '--oneline', f'HEAD..{remote_branch}'], 
                cwd=self.data_dir, capture_output=True, text=True
            )
            
            if remote_commits_result.returncode == 0:
                for line in remote_commits_result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split(' ', 1)
                        conflict_info['remote_commits'].append({
                            'hash': parts[0],
                            'message': parts[1] if len(parts) > 1 else ''
                        })
            
            # 差分を取得
            diff_result = subprocess.run(
                ['git', 'diff', f'HEAD...{remote_branch}'], 
                cwd=self.data_dir, capture_output=True, text=True
            )
            
            if diff_result.returncode == 0:
                conflict_info['diff_content'] = diff_result.stdout
            
            # 変更ファイル一覧を取得
            files_result = subprocess.run(
                ['git', 'diff', '--name-status', f'HEAD...{remote_branch}'], 
                cwd=self.data_dir, capture_output=True, text=True
            )
            
            if files_result.returncode == 0:
                for line in files_result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            conflict_info['changed_files'].append({
                                'status': self._translate_git_status(parts[0]),
                                'path': parts[1],
                                'additions': 0,
                                'deletions': 0
                            })
                            
        except Exception as e:
            logger.warning(f"コミット詳細取得エラー: {e}")

    def _translate_git_status(self, status: str) -> str:
        """Gitステータスを日本語に変換"""
        status_map = {
            'A': '追加',
            'M': '変更',
            'D': '削除',
            'R': '名前変更',
            'C': 'コピー',
            'U': '未マージ'
        }
        return status_map.get(status, status)

    def _execute_resolution(self, resolution: str, backup_path: str, conflict_info: dict) -> tuple:
        """コンフリクト解決を実行"""
        try:
            current_branch = conflict_info.get('current_branch', 'main')
            remote_branch = f"origin/{current_branch}"
            
            if resolution == 'merge':
                return self._execute_merge(remote_branch)
            elif resolution == 'rebase':
                return self._execute_rebase(remote_branch)
            elif resolution == 'force_local':
                return self._execute_force_push(current_branch)
            elif resolution == 'force_remote':
                return self._execute_reset_to_remote(remote_branch)
            else:
                return (False, "不明な解決方法が選択されました")
                
        except Exception as e:
            # エラー時はバックアップから復元
            if self._restore_backup(backup_path):
                return (False, f"解決処理中にエラーが発生しました。バックアップから復元しました: {e}")
            else:
                return (False, f"解決処理中にエラーが発生し、復元にも失敗しました: {e}")

    def _execute_merge(self, remote_branch: str) -> tuple:
        """マージ実行"""
        try:
            result = subprocess.run(
                ['git', 'merge', '--no-ff', remote_branch], 
                cwd=self.data_dir, capture_output=True, text=True
            )
            
            if result.returncode == 0:
                self._cleanup_old_backups()
                return (True, "マージによる同期が完了しました")
            else:
                if "CONFLICT" in result.stdout:
                    return (False, f"マージコンフリクトが発生しました。\n"
                                 f"手動で解決後、以下のコマンドを実行してください:\n"
                                 f"git add .\n"
                                 f"git commit\n\n"
                                 f"詳細: {result.stdout}")
                else:
                    return (False, f"マージに失敗しました: {result.stderr}")
                    
        except Exception as e:
            return (False, f"マージ実行エラー: {e}")

    def _execute_rebase(self, remote_branch: str) -> tuple:
        """リベース実行"""
        try:
            result = subprocess.run(
                ['git', 'rebase', remote_branch], 
                cwd=self.data_dir, capture_output=True, text=True
            )
            
            if result.returncode == 0:
                self._cleanup_old_backups()
                return (True, "リベースによる同期が完了しました")
            else:
                return (False, f"リベースに失敗しました: {result.stderr}")
                
        except Exception as e:
            return (False, f"リベース実行エラー: {e}")

    def _execute_force_push(self, current_branch: str) -> tuple:
        """強制プッシュ実行"""
        try:
            result = subprocess.run(
                ['git', 'push', '--force', 'origin', current_branch], 
                cwd=self.data_dir, capture_output=True, text=True
            )
            
            if result.returncode == 0:
                self._cleanup_old_backups()
                return (True, "ローカル変更を強制的にリモートに反映しました")
            else:
                return (False, f"強制プッシュに失敗しました: {result.stderr}")
                
        except Exception as e:
            return (False, f"強制プッシュ実行エラー: {e}")

    def _execute_reset_to_remote(self, remote_branch: str) -> tuple:
        """リモートに合わせてリセット"""
        try:
            result = subprocess.run(
                ['git', 'reset', '--hard', remote_branch], 
                cwd=self.data_dir, capture_output=True, text=True
            )
            
            if result.returncode == 0:
                self._cleanup_old_backups()
                return (True, "リモート変更でローカルを上書きしました")
            else:
                return (False, f"リセットに失敗しました: {result.stderr}")
                
        except Exception as e:
            return (False, f"リセット実行エラー: {e}")

    def _execute_simple_pull(self) -> tuple:
        """通常のpullを実行"""
        try:
            # 通常のpullを実行
            result = subprocess.run(['git', 'pull', 'origin', ''],
                                    cwd=self.data_dir, capture_output=True, text=True)

            if result.returncode == 0:
                return (True, "リモートデータの取得が完了しました")
            else:
                return (False, f"データ取得エラー: {result.stderr}")

        except Exception as e:
            return (False, f"プルエラー: {e}")