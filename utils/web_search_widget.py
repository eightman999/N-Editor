import sys
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QLabel, QSizePolicy, QWidget, QTextBrowser, QMessageBox)
from PyQt5.QtCore import QUrl, Qt, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QIcon, QKeySequence, QDesktopServices
import logging
import urllib.parse

# WebEngineの代替実装用
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False

logger = logging.getLogger(__name__)

class WebSearchWidget(QDialog):
    """
    設計・登録画面用の小さなWeb検索ウィンドウ
    
    特徴:
    - コンパクトなサイズで調べ物に特化
    - 複数の検索エンジン対応
    - 履歴機能付き
    - 親ウィンドウとの連携
    """
    
    # シグナル定義
    search_completed = pyqtSignal(str)  # 検索完了時
    closed = pyqtSignal()  # ウィンドウ閉じられた時
    
    def __init__(self, parent=None, default_search=""):
        super().__init__(parent)
        self.parent_window = parent
        self.search_history = []
        self.current_history_index = -1
        
        self.setup_ui()
        self.setup_search_engines()
        
        if default_search:
            self.search_input.setText(default_search)
            self.perform_search(default_search)
    
    def setup_ui(self):
        """UI構築"""
        self.setWindowTitle("Web検索 - Naval Design System")
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        
        # コンパクトサイズで設定
        self.resize(800, 600)
        
        # WebEngine利用可能性をチェック
        self.use_webengine = WEBENGINE_AVAILABLE and self._check_webengine_support()
        
        # メインレイアウト
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 検索バー
        search_layout = QHBoxLayout()
        
        # 戻る・進むボタン
        self.back_button = QPushButton("◀", self)
        self.back_button.setFixedSize(30, 25)
        self.back_button.setEnabled(False)
        self.back_button.clicked.connect(self.go_back)
        search_layout.addWidget(self.back_button)
        
        self.forward_button = QPushButton("▶", self)
        self.forward_button.setFixedSize(30, 25)
        self.forward_button.setEnabled(False)
        self.forward_button.clicked.connect(self.go_forward)
        search_layout.addWidget(self.forward_button)
        
        # 更新ボタン
        self.refresh_button = QPushButton("⟳", self)
        self.refresh_button.setFixedSize(30, 25)
        self.refresh_button.clicked.connect(self.refresh_page)
        search_layout.addWidget(self.refresh_button)
        
        # 検索エンジン選択
        self.search_engine_combo = QPushButton("Google", self)
        self.search_engine_combo.setFixedWidth(80)
        self.search_engine_combo.clicked.connect(self.toggle_search_engine)
        search_layout.addWidget(self.search_engine_combo)
        
        # 検索入力
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("検索キーワードを入力...")
        self.search_input.returnPressed.connect(self.on_search_pressed)
        search_layout.addWidget(self.search_input)
        
        # 検索ボタン
        self.search_button = QPushButton("検索", self)
        self.search_button.setFixedWidth(60)
        self.search_button.clicked.connect(self.on_search_pressed)
        search_layout.addWidget(self.search_button)
        
        # 閉じるボタン
        self.close_button = QPushButton("✕", self)
        self.close_button.setFixedSize(25, 25)
        self.close_button.clicked.connect(self.close)
        search_layout.addWidget(self.close_button)
        
        layout.addLayout(search_layout)
        
        # クイック検索ボタン
        quick_layout = QHBoxLayout()
        quick_searches = [
            ("Wikipedia", "site:wikipedia.org"),
            ("艦船", "warship OR battleship OR destroyer"),
            ("兵器", "weapon OR armament OR gun"),
            ("歴史", "history OR historical"),
            ("技術", "technology OR engineering")
        ]
        
        for label, query in quick_searches:
            btn = QPushButton(label, self)
            btn.setFixedHeight(20)
            btn.clicked.connect(lambda checked, q=query: self.quick_search(q))
            quick_layout.addWidget(btn)
        
        quick_layout.addStretch()
        layout.addLayout(quick_layout)
        
        # Webビュー（WebEngine利用可能性に応じて選択）
        if self.use_webengine:
            try:
                self.web_view = QWebEngineView(self)
                self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                # WebEngineのシグナル接続
                self.web_view.loadStarted.connect(self.on_load_started)
                self.web_view.loadFinished.connect(self.on_load_finished)
                self.web_view.urlChanged.connect(self.on_url_changed)
                logger.info("WebEngineViewを使用します")
            except Exception as e:
                logger.warning(f"WebEngineView初期化失敗、代替方式を使用: {e}")
                self.use_webengine = False
        
        if not self.use_webengine:
            # 代替: デスクトップブラウザで開く方式
            self.web_view = QTextBrowser(self)
            self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.web_view.setHtml("""
                <html><body style="font-family: Arial; padding: 20px;">
                <h2>🔍 Web検索</h2>
                <p>検索ボタンをクリックすると、デフォルトブラウザで検索結果が開きます。</p>
                <p><strong>利用可能な検索エンジン:</strong></p>
                <ul>
                    <li>Google</li>
                    <li>Wikipedia（日本語・英語）</li>
                    <li>Yahoo</li>
                    <li>Bing</li>
                </ul>
                <p><em>クイック検索ボタンで関連キーワードを素早く検索できます。</em></p>
                </body></html>
            """)
            logger.info("代替検索方式を使用します（デスクトップブラウザ連携）")
        
        layout.addWidget(self.web_view)
        
        # ステータスバー
        status_text = "WebEngine利用可能" if self.use_webengine else "デスクトップブラウザ連携モード"
        self.status_label = QLabel(status_text, self)
        self.status_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.status_label)
    
    def setup_search_engines(self):
        """検索エンジンの設定"""
        self.search_engines = {
            "Google": "https://www.google.com/search?q={}",
            "Wikipedia": "https://ja.wikipedia.org/wiki/Special:Search?search={}",
            "英Wikipedia": "https://en.wikipedia.org/wiki/Special:Search?search={}",
            "Yahoo": "https://search.yahoo.co.jp/search?p={}",
            "Bing": "https://www.bing.com/search?q={}"
        }
        self.current_engine = "Google"
    
    def toggle_search_engine(self):
        """検索エンジンを切り替え"""
        engines = list(self.search_engines.keys())
        current_index = engines.index(self.current_engine)
        next_index = (current_index + 1) % len(engines)
        self.current_engine = engines[next_index]
        self.search_engine_combo.setText(self.current_engine)
    
    def on_search_pressed(self):
        """検索ボタンが押された時の処理"""
        query = self.search_input.text().strip()
        if query:
            self.perform_search(query)
    
    def quick_search(self, query_addon):
        """クイック検索"""
        current_text = self.search_input.text().strip()
        if current_text:
            full_query = f"{current_text} {query_addon}"
        else:
            full_query = query_addon
        
        self.search_input.setText(full_query)
        self.perform_search(full_query)
    
    def _check_webengine_support(self):
        """WebEngineサポートをチェック"""
        try:
            # ICUデータファイルの存在確認
            from PyQt5.QtWebEngineCore import QWebEngineSettings
            return True
        except Exception as e:
            logger.warning(f"WebEngine利用不可: {e}")
            return False
    
    def perform_search(self, query):
        """検索実行"""
        try:
            # 履歴に追加
            if query not in self.search_history:
                self.search_history.append(query)
                if len(self.search_history) > 50:  # 履歴上限
                    self.search_history.pop(0)
            
            # 検索URL生成
            encoded_query = urllib.parse.quote_plus(query)
            search_url = self.search_engines[self.current_engine].format(encoded_query)
            
            if self.use_webengine:
                # WebEngineで内部表示
                self.web_view.load(QUrl(search_url))
                logger.info(f"Web検索実行(WebEngine): {query} ({self.current_engine})")
            else:
                # デスクトップブラウザで開く
                QDesktopServices.openUrl(QUrl(search_url))
                logger.info(f"Web検索実行(外部ブラウザ): {query} ({self.current_engine})")
                self.status_label.setText(f"デスクトップブラウザで検索: {query}")
            
        except Exception as e:
            logger.error(f"検索エラー: {e}")
            self.status_label.setText(f"検索エラー: {str(e)}")
    
    def go_back(self):
        """戻る"""
        if self.use_webengine and hasattr(self.web_view, 'history'):
            if self.web_view.history().canGoBack():
                self.web_view.back()
        else:
            self.status_label.setText("ナビゲーション機能は外部ブラウザで利用してください")
    
    def go_forward(self):
        """進む"""
        if self.use_webengine and hasattr(self.web_view, 'history'):
            if self.web_view.history().canGoForward():
                self.web_view.forward()
        else:
            self.status_label.setText("ナビゲーション機能は外部ブラウザで利用してください")
    
    def refresh_page(self):
        """ページ更新"""
        if self.use_webengine and hasattr(self.web_view, 'reload'):
            self.web_view.reload()
        else:
            self.status_label.setText("更新機能は外部ブラウザで利用してください")
    
    def on_load_started(self):
        """読み込み開始"""
        self.status_label.setText("読み込み中...")
        self.refresh_button.setText("✕")
        self.refresh_button.clicked.disconnect()
        self.refresh_button.clicked.connect(self.web_view.stop)
    
    def on_load_finished(self, success):
        """読み込み完了"""
        if success:
            self.status_label.setText("読み込み完了")
        else:
            self.status_label.setText("読み込み失敗")
        
        self.refresh_button.setText("⟳")
        self.refresh_button.clicked.disconnect()
        self.refresh_button.clicked.connect(self.refresh_page)
        
        # ナビゲーションボタンの状態更新（WebEngineの場合のみ）
        if self.use_webengine and hasattr(self.web_view, 'history'):
            self.back_button.setEnabled(self.web_view.history().canGoBack())
            self.forward_button.setEnabled(self.web_view.history().canGoForward())
        else:
            self.back_button.setEnabled(False)
            self.forward_button.setEnabled(False)
    
    def on_url_changed(self, url):
        """URL変更時"""
        self.status_label.setText(f"URL: {url.toString()}")
    
    def set_search_query(self, query):
        """外部から検索クエリを設定"""
        self.search_input.setText(query)
        if query.strip():
            self.perform_search(query.strip())
    
    def closeEvent(self, event):
        """ウィンドウクローズ時"""
        self.closed.emit()
        event.accept()


class WebSearchButton(QPushButton):
    """
    Web検索ボタンウィジェット
    
    設計・登録画面に埋め込み用の小さなボタン
    """
    
    def __init__(self, parent=None, default_search=""):
        super().__init__("🔍 Web検索", parent)
        self.parent_window = parent
        self.default_search = default_search
        self.web_search_dialog = None
        
        self.setFixedSize(80, 25)
        self.setToolTip("Web検索ウィンドウを開く")
        self.clicked.connect(self.open_web_search)
        
        # Windows 98風スタイル
        self.setStyleSheet("""
            QPushButton {
                background-color: #e6e6e6;
                border: 2px outset #d4d0c8;
                border-top-color: white;
                border-left-color: white;
                padding: 2px;
                font-size: 10px;
            }
            QPushButton:pressed {
                border: 2px inset #808080;
                border-bottom-color: white;
                border-right-color: white;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
    
    def open_web_search(self):
        """Web検索ダイアログを開く"""
        try:
            if self.web_search_dialog is None or not self.web_search_dialog.isVisible():
                self.web_search_dialog = WebSearchWidget(self.parent_window, self.default_search)
                self.web_search_dialog.show()
            else:
                # 既に開いている場合は前面に持ってくる
                self.web_search_dialog.raise_()
                self.web_search_dialog.activateWindow()
            
            logger.info("Web検索ダイアログを開きました")
            
        except Exception as e:
            logger.error(f"Web検索ダイアログ開くエラー: {e}")
    
    def set_default_search(self, search_query):
        """デフォルト検索クエリを設定"""
        self.default_search = search_query
        if self.web_search_dialog and self.web_search_dialog.isVisible():
            self.web_search_dialog.set_search_query(search_query)