from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QTabWidget, QWidget,
                             QTreeWidget, QTreeWidgetItem, QSplitter,
                             QScrollArea, QFrame)

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette

class ConflictResolutionDialog(QDialog):
    """同期コンフリクト解決ダイアログ"""
    
    def __init__(self, conflict_info, parent=None):
        super().__init__(parent)
        self.conflict_info = conflict_info
        self.resolution_choice = None
        self.init_ui()
        
        # ダイアログを中央に配置
        if parent:
            self.move(
                parent.x() + (parent.width() - self.width()) // 2,
                parent.y() + (parent.height() - self.height()) // 2
            )
    
    def init_ui(self):
        self.setWindowTitle("同期コンフリクトの解決 - Naval Design System")
        self.setMinimumSize(900, 700)
        self.setModal(True)
        
        # Windows95風のスタイル適用
        self.setStyleSheet("""
            QDialog {
                background-color: #e6e6e6;
                border: 2px outset #d4d0c8;
            }
            QTabWidget::pane {
                border: 2px inset #808080;
                background-color: #e6e6e6;
            }
            QTabBar::tab {
                background-color: #e6e6e6;
                border: 2px outset #d4d0c8;
                border-bottom: none;
                padding: 4px 8px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #e6e6e6;
                border-bottom: 2px solid #e6e6e6;
            }
            QPushButton {
                background-color: #e6e6e6;
                border: 2px outset #d4d0c8;
                padding: 6px 12px;
                min-width: 80px;
                min-height: 24px;
            }
            QPushButton:pressed {
                border: 2px inset #808080;
            }
            QTextEdit {
                background-color: white;
                border: 2px inset #808080;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 9pt;
            }
            QTreeWidget {
                background-color: white;
                border: 2px inset #808080;
            }
        """)
        
        layout = QVBoxLayout()
        
        # ヘッダー部分
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        header_layout = QVBoxLayout()
        
        # アイコンと状況説明
        warning_layout = QHBoxLayout()
        
        # 警告アイコン（テキストベース）
        icon_label = QLabel("⚠️")
        icon_label.setStyleSheet("font-size: 24px;")
        warning_layout.addWidget(icon_label)
        
        situation_label = QLabel("ローカルとリモートで異なる変更が検出されました。")
        situation_label.setStyleSheet("font-weight: bold; color: #d9534f; font-size: 14px;")
        warning_layout.addWidget(situation_label)
        warning_layout.addStretch()
        
        header_layout.addLayout(warning_layout)
        
        # 概要情報
        summary_text = self._create_summary_text()
        summary_label = QLabel(summary_text)
        summary_label.setWordWrap(True)
        summary_label.setStyleSheet("margin: 10px; padding: 8px; background-color: #f5f5f5; border: 1px solid #ddd;")
        header_layout.addWidget(summary_label)
        
        header_frame.setLayout(header_layout)
        layout.addWidget(header_frame)
        
        # タブウィジェット
        tab_widget = QTabWidget()
        
        # 1. コミット履歴タブ
        commits_tab = self._create_commits_tab()
        tab_widget.addTab(commits_tab, "📝 コミット履歴")
        
        # 2. 差分表示タブ
        diff_tab = self._create_diff_tab()
        tab_widget.addTab(diff_tab, "🔍 変更差分")
        
        # 3. ファイル一覧タブ
        files_tab = self._create_files_tab()
        tab_widget.addTab(files_tab, "📁 影響ファイル")
        
        layout.addWidget(tab_widget)
        
        # 解決方法選択部分
        resolution_frame = QFrame()
        resolution_frame.setFrameStyle(QFrame.Box | QFrame.Raised)
        resolution_layout = QVBoxLayout()
        
        resolution_label = QLabel("解決方法を選択してください：")
        resolution_label.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 8px;")
        resolution_layout.addWidget(resolution_label)
        
        # ボタンレイアウト（2行に分割）
        button_layout1 = QHBoxLayout()
        button_layout2 = QHBoxLayout()
        
        # 推奨オプション（上段）
        merge_button = QPushButton("🔗 マージ (推奨)")
        merge_button.setStyleSheet("QPushButton { background-color: #5bc0de; color: white; font-weight: bold; }")
        merge_button.setToolTip("両方の変更を統合します。最も安全な選択肢です。")
        merge_button.clicked.connect(lambda: self.set_resolution('merge'))
        button_layout1.addWidget(merge_button)
        
        rebase_button = QPushButton("📐 リベース")
        rebase_button.setToolTip("ローカル変更をリモート変更の上に再適用します。")
        rebase_button.clicked.connect(lambda: self.set_resolution('rebase'))
        button_layout1.addWidget(rebase_button)
        
        button_layout1.addStretch()
        
        # 強制オプション（下段）
        local_button = QPushButton("⬆️ ローカルを強制適用")
        local_button.setStyleSheet("QPushButton { background-color: #f0ad4e; color: white; }")
        local_button.setToolTip("リモートの変更を破棄してローカルを優先します。")
        local_button.clicked.connect(lambda: self.set_resolution('force_local'))
        button_layout2.addWidget(local_button)
        
        remote_button = QPushButton("⬇️ リモートを強制適用")
        remote_button.setStyleSheet("QPushButton { background-color: #d9534f; color: white; }")
        remote_button.setToolTip("ローカルの変更を破棄してリモートに合わせます。")
        remote_button.clicked.connect(lambda: self.set_resolution('force_remote'))
        button_layout2.addWidget(remote_button)
        
        # キャンセルボタン
        cancel_button = QPushButton("❌ キャンセル")
        cancel_button.clicked.connect(self.reject)
        button_layout2.addWidget(cancel_button)
        
        button_layout2.addStretch()
        
        resolution_layout.addLayout(button_layout1)
        resolution_layout.addLayout(button_layout2)
        
        # 説明文
        help_text = QLabel(
            "💡 <b>選択肢の説明:</b><br>"
            "• <b>マージ</b>: 両方の変更を統合します（推奨）<br>"
            "• <b>リベース</b>: ローカル変更をリモート変更の上に再適用<br>"
            "• <b>ローカル強制</b>: リモートの変更を無視してローカルを維持<br>"
            "• <b>リモート強制</b>: ローカルの変更を破棄してリモートに合わせる"
        )
        help_text.setStyleSheet(
            "color: #666; font-size: 10px; padding: 8px; "
            "background-color: #f9f9f9; border: 1px solid #ddd; "
            "border-radius: 4px; margin-top: 8px;"
        )
        help_text.setWordWrap(True)
        resolution_layout.addWidget(help_text)
        
        resolution_frame.setLayout(resolution_layout)
        layout.addWidget(resolution_frame)
        
        self.setLayout(layout)

    def _create_summary_text(self) -> str:
        """概要テキストを作成"""
        local_commits = len(self.conflict_info.get('local_commits', []))
        remote_commits = len(self.conflict_info.get('remote_commits', []))
        changed_files = len(self.conflict_info.get('changed_files', []))
        
        current_branch = self.conflict_info.get('current_branch', 'master')
        
        summary = f"現在のブランチ: <b>{current_branch}</b><br>"
        summary += f"ローカル固有のコミット: <b>{local_commits}件</b> | "
        summary += f"リモート固有のコミット: <b>{remote_commits}件</b> | "
        summary += f"影響を受けるファイル: <b>{changed_files}件</b>"
        
        return summary

    def _create_commits_tab(self) -> QWidget:
        """コミット履歴タブの作成"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # スプリッターで左右に分割
        splitter = QSplitter(Qt.Horizontal)
        
        # ローカルコミット（左側）
        local_frame = QFrame()
        local_frame.setFrameStyle(QFrame.StyledPanel)
        local_layout = QVBoxLayout()
        
        local_label = QLabel("🏠 ローカルコミット")
        local_label.setStyleSheet("font-weight: bold; color: #5bc0de; font-size: 12px;")
        local_layout.addWidget(local_label)
        
        local_commits = QTextEdit()
        local_commits.setReadOnly(True)
        local_commits.setMaximumHeight(200)
        
        local_text = ""
        for commit in self.conflict_info.get('local_commits', []):
            local_text += f"• {commit['hash'][:8]} - {commit['message']}\n"
        
        if not local_text:
            local_text = "ローカル固有のコミットはありません"
        
        local_commits.setPlainText(local_text)
        local_layout.addWidget(local_commits)
        local_frame.setLayout(local_layout)
        
        # リモートコミット（右側）
        remote_frame = QFrame()
        remote_frame.setFrameStyle(QFrame.StyledPanel)
        remote_layout = QVBoxLayout()
        
        remote_label = QLabel("🌐 リモートコミット")
        remote_label.setStyleSheet("font-weight: bold; color: #d9534f; font-size: 12px;")
        remote_layout.addWidget(remote_label)
        
        remote_commits = QTextEdit()
        remote_commits.setReadOnly(True)
        remote_commits.setMaximumHeight(200)
        
        remote_text = ""
        for commit in self.conflict_info.get('remote_commits', []):
            remote_text += f"• {commit['hash'][:8]} - {commit['message']}\n"
        
        if not remote_text:
            remote_text = "リモート固有のコミットはありません"
        
        remote_commits.setPlainText(remote_text)
        remote_layout.addWidget(remote_commits)
        remote_frame.setLayout(remote_layout)
        
        splitter.addWidget(local_frame)
        splitter.addWidget(remote_frame)
        splitter.setSizes([400, 400])
        
        layout.addWidget(splitter)
        widget.setLayout(layout)
        return widget

    def _create_diff_tab(self) -> QWidget:
        """差分表示タブの作成"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 差分表示のヘッダー
        diff_header = QLabel("🔍 変更内容の詳細差分:")
        diff_header.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 8px;")
        layout.addWidget(diff_header)
        
        # 差分表示テキストエリア
        diff_text = QTextEdit()
        diff_text.setReadOnly(True)
        diff_text.setFont(QFont("Consolas", 9))
        
        # 差分データを表示
        diff_content = self.conflict_info.get('diff_content', '')
        
        if diff_content:
            # 差分を色分けして表示（簡易実装）
            formatted_diff = self._format_diff_content(diff_content)
            diff_text.setHtml(formatted_diff)
        else:
            diff_text.setPlainText("差分情報を取得できませんでした。")
        
        layout.addWidget(diff_text)
        
        # 差分統計
        stats_label = QLabel(self._create_diff_stats())
        stats_label.setStyleSheet(
            "background-color: #f5f5f5; padding: 8px; border: 1px solid #ddd; "
            "font-family: monospace; font-size: 10px;"
        )
        layout.addWidget(stats_label)
        
        widget.setLayout(layout)
        return widget

    def _format_diff_content(self, diff_content: str) -> str:
        """差分内容をHTMLフォーマットで色分け"""
        lines = diff_content.split('\n')
        formatted_lines = []
        
        for line in lines:
            if line.startswith('+++') or line.startswith('---'):
                formatted_lines.append(f'<span style="color: #666; font-weight: bold;">{line}</span>')
            elif line.startswith('+'):
                formatted_lines.append(f'<span style="color: #22863a; background-color: #f0fff4;">{line}</span>')
            elif line.startswith('-'):
                formatted_lines.append(f'<span style="color: #cb2431; background-color: #ffeef0;">{line}</span>')
            elif line.startswith('@@'):
                formatted_lines.append(f'<span style="color: #005cc5; font-weight: bold;">{line}</span>')
            else:
                formatted_lines.append(line)
        
        return '<pre style="font-family: Consolas, monospace; font-size: 9pt;">' + '\n'.join(formatted_lines) + '</pre>'

    def _create_diff_stats(self) -> str:
        """差分統計情報を作成"""
        changed_files = self.conflict_info.get('changed_files', [])
        
        if not changed_files:
            return "ファイル変更統計: データなし"
        
        stats = {}
        for file_info in changed_files:
            status = file_info.get('status', '不明')
            stats[status] = stats.get(status, 0) + 1
        
        stats_text = "ファイル変更統計: "
        stats_parts = []
        for status, count in stats.items():
            stats_parts.append(f"{status}: {count}件")
        
        return stats_text + " | ".join(stats_parts)

    def _create_files_tab(self) -> QWidget:
        """ファイル一覧タブの作成"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # ファイル一覧ヘッダー
        files_header = QLabel("📁 変更されたファイル一覧:")
        files_header.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 8px;")
        layout.addWidget(files_header)
        
        # ファイルツリー
        files_tree = QTreeWidget()
        files_tree.setHeaderLabels(["ファイルパス", "変更種別", "詳細"])
        files_tree.setAlternatingRowColors(True)
        
        # ルートアイテムを作成
        root_dirs = {}
        
        for file_info in self.conflict_info.get('changed_files', []):
            file_path = file_info.get('path', '')
            status = file_info.get('status', '不明')
            
            # ディレクトリごとにグループ化
            if '/' in file_path:
                dir_name = file_path.split('/')[0]
                file_name = '/'.join(file_path.split('/')[1:])
            else:
                dir_name = "ルート"
                file_name = file_path
            
            # ディレクトリアイテムを作成または取得
            if dir_name not in root_dirs:
                dir_item = QTreeWidgetItem()
                dir_item.setText(0, f"📂 {dir_name}")
                dir_item.setText(1, "ディレクトリ")
                files_tree.addTopLevelItem(dir_item)
                root_dirs[dir_name] = dir_item
            
            # ファイルアイテムを追加
            file_item = QTreeWidgetItem()
            
            # ファイル種別に応じたアイコン
            if file_name.endswith(('.txt', '.md')):
                icon = "📄"
            elif file_name.endswith(('.json', '.yml', '.yaml')):
                icon = "⚙️"
            elif file_name.endswith('.py'):
                icon = "🐍"
            else:
                icon = "📄"
            
            file_item.setText(0, f"{icon} {file_name}")
            file_item.setText(1, status)
            
            # 状態に応じた詳細情報
            if status == "追加":
                file_item.setText(2, "新規ファイル")
            elif status == "削除":
                file_item.setText(2, "削除予定")
            elif status == "変更":
                file_item.setText(2, "内容変更")
            else:
                file_item.setText(2, status)
            
            root_dirs[dir_name].addChild(file_item)
        
        # 列幅を調整
        files_tree.resizeColumnToContents(0)
        files_tree.resizeColumnToContents(1)
        files_tree.expandAll()
        
        layout.addWidget(files_tree)
        
        # ファイル数サマリー
        file_count = len(self.conflict_info.get('changed_files', []))
        summary_label = QLabel(f"合計 {file_count} 個のファイルが変更されています")
        summary_label.setStyleSheet("font-style: italic; color: #666; margin-top: 8px;")
        layout.addWidget(summary_label)
        
        widget.setLayout(layout)
        return widget

    def set_resolution(self, choice: str):
        """解決方法を設定して閉じる"""
        self.resolution_choice = choice
        self.accept()

    def closeEvent(self, event):
        """ダイアログが閉じられる時の処理"""
        if self.resolution_choice is None:
            # 何も選択せずに閉じた場合はキャンセル扱い
            self.reject()
        event.accept() 