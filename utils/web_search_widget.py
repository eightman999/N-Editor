# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: web_search_widgetユーティリティ
import sys
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QLabel, QSizePolicy, QWidget, QTextBrowser, QMessageBox)
from PyQt5.QtCore import QUrl, Qt, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QIcon, QKeySequence, QDesktopServices
import logging
import urllib.parse
import re

# 追加の依存関係をインポート（オプション）
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

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
        
        # ページ履歴（内部ブラウザ用）
        self.page_history = []
        self.page_history_index = -1
        
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
        
        # WebEngine利用可能性をチェック（より安全に）
        # ICUエラーを避けるため、デフォルトで簡易ブラウザを使用
        self.use_webengine = False
        
        # 環境変数でWebEngineの使用を強制的に有効化できる
        force_webengine = os.environ.get('N_EDITOR_USE_WEBENGINE', 'false').lower() == 'true'
        
        if force_webengine and WEBENGINE_AVAILABLE:
            self.use_webengine = self._check_webengine_support()
            logger.info(f"WebEngine強制使用モード: {self.use_webengine}")
        else:
            logger.debug("安定性のため簡易ブラウザモードを使用")
        
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
            # 代替: 簡易内部ブラウザ（QTextBrowser）を使用
            self.web_view = QTextBrowser(self)
            self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.web_view.setOpenExternalLinks(False)  # リンクを内部で処理
            self.web_view.anchorClicked.connect(self.on_link_clicked)  # リンククリック時の処理
            self.web_view.setTextInteractionFlags(
                self.web_view.textInteractionFlags() | Qt.TextSelectableByMouse
            )  # テキスト選択を有効化
            self.setup_simple_browser()
            logger.info("簡易内部ブラウザを使用します")
            
            # 依存関係の状況をチェック
            deps_status = f"requests: {'OK' if REQUESTS_AVAILABLE else 'NG'}, beautifulsoup4: {'OK' if BS4_AVAILABLE else 'NG'}"
            logger.info(f"依存関係の状況: {deps_status}")
        
        layout.addWidget(self.web_view)
        
        # ステータスバー
        if self.use_webengine:
            status_text = "WebEngineモード（高機能）"
        else:
            deps_available = REQUESTS_AVAILABLE and BS4_AVAILABLE
            if deps_available:
                status_text = "簡易ブラウザモード（安定動作）"
            else:
                status_text = "代替リンクモード（依存関係不足）"
        
        self.status_label = QLabel(status_text, self)
        self.status_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(self.status_label)
    
    def setup_simple_browser(self):
        """簡易内部ブラウザの設定"""
        deps_available = REQUESTS_AVAILABLE and BS4_AVAILABLE
        
        if deps_available:
            install_msg = f"""
                <div class="info">
                    <h3>ℹ️ 内部検索モード</h3>
                    <p><strong>現在の状態:</strong></p>
                    <ul>
                        <li>requests: ✅ OK</li>
                        <li>beautifulsoup4: ✅ OK</li>
                        <li>QtWebEngine: {'✅ OK (未使用)' if WEBENGINE_AVAILABLE else '❌ 未インストール'}</li>
                    </ul>
                    <p>安定性のため簡易ブラウザモードで動作しています。<br>
                       完全なWebEngineを使用したい場合は環境変数 <code>N_EDITOR_USE_WEBENGINE=true</code> を設定してください。</p>
                </div>
            """
            status_color = "#e8f4fd"
            status_title = "内部検索モード（簡易ブラウザ）"
        else:
            missing_deps = []
            if not REQUESTS_AVAILABLE:
                missing_deps.append("requests")
            if not BS4_AVAILABLE:
                missing_deps.append("beautifulsoup4")
            
            install_msg = f"""
                <div class="warning">
                    <h3>⚠️ 依存関係不足</h3>
                    <p>完全な内部検索機能を使用するには、以下のライブラリが必要です：</p>
                    <div class="install-command">pip install {' '.join(missing_deps)}</div>
                    <p><strong>現在の状態:</strong></p>
                    <ul>
                        <li>requests: {'✅ OK' if REQUESTS_AVAILABLE else '❌ 未インストール'}</li>
                        <li>beautifulsoup4: {'✅ OK' if BS4_AVAILABLE else '❌ 未インストール'}</li>
                        <li>QtWebEngine: {'✅ OK' if WEBENGINE_AVAILABLE else '❌ 未インストール'}</li>
                    </ul>
                    <p>現在は代替リンク表示モードで動作します。インストール後はアプリケーションを再起動してください。</p>
                </div>
            """
            status_color = "#fff3cd"
            status_title = "代替リンクモード"
        
        self.web_view.setHtml(f"""
            <html><head>
                <meta charset='utf-8'>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5; }}
                    h2 {{ color: #333; }}
                    .search-results {{ background-color: white; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                    .search-item {{ margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #eee; }}
                    .search-title {{ color: #1a0dab; font-size: 18px; text-decoration: none; }}
                    .search-url {{ color: #006621; font-size: 14px; }}
                    .search-snippet {{ color: #545454; font-size: 13px; line-height: 1.4; }}
                    .note {{ background-color: {status_color}; padding: 10px; border-radius: 5px; margin: 10px 0; }}
                    .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                    .warning h3 {{ color: #856404; margin-top: 0; }}
                    .info {{ background-color: #d1ecf1; border: 1px solid #bee5eb; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                    .info h3 {{ color: #0c5460; margin-top: 0; }}
                    .install-command {{ background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 10px; border-radius: 3px; font-family: monospace; margin: 10px 0; }}
                    code {{ background-color: #f8f9fa; padding: 2px 4px; border-radius: 3px; font-family: monospace; }}
                </style>
            </head><body>
                <h2>🔍 内部Web検索</h2>
                <div class="note">
                    <p><strong>{status_title}</strong> - 検索結果を内部で表示します。</p>
                    <p>上部の検索バーにキーワードを入力して検索してください。</p>
                </div>
                {install_msg}
                <div id="search-results"></div>
            </body></html>
        """)
    
    def setup_search_engines(self):
        """検索エンジンの設定"""
        self.search_engines = {
            "Google": "https://www.google.com/search?q={}",
            "DuckDuckGo": "https://duckduckgo.com/?q={}",
            "Wikipedia": "https://ja.wikipedia.org/wiki/Special:Search?search={}",
            "英Wikipedia": "https://en.wikipedia.org/wiki/Special:Search?search={}",
            "Yahoo": "https://search.yahoo.co.jp/search?p={}",
            "Bing": "https://www.bing.com/search?q={}"
        }
        self.current_engine = "DuckDuckGo"  # デフォルトをより解析しやすいDuckDuckGoに変更
    
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
            # WebEngineViewが正常にインポートできているかチェック
            if not WEBENGINE_AVAILABLE:
                return False
            
            # ICUデータファイルの存在確認（より安全な方法）
            import os
            import sys
            
            # ICUエラーを避けるため、環境変数をチェック
            icu_data_paths = [
                os.environ.get('ICU_DATA'),
                '/usr/share/qt5/resources',
                '/opt/homebrew/share/qt/resources',
                os.path.join(sys.prefix, 'share', 'qt', 'resources'),
                os.path.join(sys.prefix, 'lib', 'python*', 'site-packages', 'PyQt5', 'Qt5', 'resources')
            ]
            
            # ICUデータファイルが見つからない場合は簡易ブラウザを使用
            icu_available = False
            for path in icu_data_paths:
                if path and os.path.exists(path):
                    icu_available = True
                    break
            
            if not icu_available:
                logger.debug("ICUデータファイルが見つからないため、簡易ブラウザを使用")
                return False
            
            # WebEngineの基本機能テスト（ICUエラーを回避）
            logger.debug("WebEngine基本チェック完了")
            return True
            
        except Exception as e:
            logger.debug(f"WebEngine利用不可（簡易ブラウザを使用）: {e}")
            return False
    
    def perform_search(self, query):
        """検索実行 - 常に内部で完結"""
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
                # 内部で検索結果を取得して表示
                self.status_label.setText(f"検索中: {query}...")
                self._fetch_and_display_search_results(query, search_url)
                logger.info(f"Web検索実行(内部取得): {query} ({self.current_engine})")
            
        except Exception as e:
            logger.error(f"検索エラー: {e}")
            self.status_label.setText(f"検索エラー: {str(e)}")
    
    def _fetch_and_display_search_results(self, query, search_url):
        """検索結果を取得して内部表示"""
        # 必要な依存関係のチェック
        if not REQUESTS_AVAILABLE or not BS4_AVAILABLE:
            missing_deps = []
            if not REQUESTS_AVAILABLE:
                missing_deps.append("requests")
            if not BS4_AVAILABLE:
                missing_deps.append("beautifulsoup4")
            
            error_msg = f"必要なライブラリがインストールされていません: {', '.join(missing_deps)}"
            self._display_dependency_error(query, error_msg)
            self.status_label.setText("依存関係エラー")
            return
        
        try:
            # ユーザーエージェントを設定
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            logger.info(f"検索URL: {search_url}")
            
            # タイムアウトを設定して検索結果を取得
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            logger.info(f"レスポンス取得成功: ステータス={response.status_code}, サイズ={len(response.text)}")
            
            # 検索エンジン別の結果解析
            if self.current_engine == "Google":
                results = self._parse_google_results(response.text, query)
            elif self.current_engine == "DuckDuckGo":
                results = self._parse_duckduckgo_results(response.text, query)
            elif "Wikipedia" in self.current_engine:
                results = self._parse_wikipedia_results(response.text, query)
            else:
                results = self._parse_generic_results(response.text, query)
            
            logger.info(f"解析結果: {len(results)}件の結果を取得")
            
            # 結果が取得できない場合の代替手段
            if not results:
                logger.warning("検索結果が取得できませんでした。簡略化した結果を表示します。")
                results = self._create_fallback_results(query, search_url)
            
            # 結果を表示
            self._display_search_results(query, results)
            self.status_label.setText(f"検索完了: {len(results)}件の結果")
            
            # ナビゲーションボタンの状態を更新
            self._update_navigation_buttons()
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"検索結果取得エラー: {e}")
            # ネットワークエラーの場合も代替結果を表示
            fallback_results = self._create_fallback_results(query, search_url)
            self._display_search_results(query, fallback_results, error_mode=True)
            self.status_label.setText("ネットワークエラー: 代替リンクを表示")
        except Exception as e:
            logger.error(f"検索結果表示エラー: {e}")
            import traceback
            traceback.print_exc()
            fallback_results = self._create_fallback_results(query, search_url)
            self._display_search_results(query, fallback_results, error_mode=True)
            self.status_label.setText(f"エラー: 代替リンクを表示")
    
    def _parse_google_results(self, html_content, query):
        """Google検索結果の解析"""
        results = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            logger.info(f"HTMLパース完了、要素数: {len(soup.find_all())}")
            
            # 複数のGoogle検索結果の要素パターンを試す
            search_result_selectors = [
                'div.g',  # 通常の検索結果
                'div[data-ved]',  # data-ved属性を持つdiv
                'div.tF2Cxc',  # 新しいGoogle検索結果のクラス
                'div.yuRUbf',  # 別のGoogle検索結果のクラス
                'div.MjjYud',  # 最新のGoogle検索結果のクラス
                'div[jscontroller]',  # JSコントローラー付きdiv
                'div.kvH3mc',  # 別の検索結果コンテナ
            ]
            
            search_results = []
            for selector in search_result_selectors:
                found_results = soup.select(selector)
                if found_results:
                    search_results = found_results
                    logger.info(f"セレクタ '{selector}' で {len(found_results)} 件の結果を発見")
                    break
            
            if not search_results:
                # フォールバック: すべてのリンクを探す（改良版）
                logger.warning("標準的な検索結果が見つからないため、リンクを抽出")
                all_links = soup.find_all('a', href=True)
                found_external_links = 0
                
                for link in all_links:
                    try:
                        href = link.get('href', '')
                        title = link.get_text().strip()
                        
                        # URLの前処理
                        if href.startswith('/url?q='):
                            # Googleのリダイレクトを処理
                            import urllib.parse
                            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                            if 'q' in parsed:
                                href = parsed['q'][0]
                        
                        # 有効な外部リンクのみを抽出
                        if (href.startswith(('http://', 'https://')) and 
                            not any(domain in href for domain in ['google.com', 'gstatic.', 'googleapis.']) and
                            title and len(title) > 5 and len(title) < 200 and
                            not title.lower() in ['more', 'images', 'videos', 'news', 'maps']):
                            
                            # 親要素からスニペットを探す
                            snippet = ""
                            parent = link.parent
                            for _ in range(3):  # 最大3階層上まで探す
                                if parent:
                                    snippet_elems = parent.find_all(text=True)
                                    snippet_text = ' '.join([t.strip() for t in snippet_elems if t.strip() and len(t.strip()) > 10])
                                    if snippet_text and len(snippet_text) > 20:
                                        snippet = snippet_text[:200] + "..." if len(snippet_text) > 200 else snippet_text
                                        break
                                    parent = parent.parent
                                else:
                                    break
                            
                            results.append({
                                'title': title,
                                'url': href,
                                'snippet': snippet
                            })
                            
                            found_external_links += 1
                            if found_external_links >= 8:
                                break
                                
                    except Exception:
                        continue
                
                logger.info(f"フォールバック検索で {len(results)} 件のリンクを抽出")
                return results
            
            for result in search_results[:10]:  # 上位10件
                try:
                    # 複数のタイトル取得方法を試す
                    title = ""
                    title_selectors = ['h3', 'h2', 'h1', '[role="heading"]']
                    for selector in title_selectors:
                        title_elem = result.select_one(selector)
                        if title_elem:
                            title = title_elem.get_text().strip()
                            break
                    
                    # URL取得
                    url = ""
                    link_elem = result.find('a', href=True)
                    if link_elem:
                        url = link_elem.get('href', '')
                        # Googleのリダイレクトを処理
                        if url.startswith('/url?q='):
                            import urllib.parse
                            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                            if 'q' in parsed:
                                url = parsed['q'][0]
                    
                    # スニペット取得
                    snippet = ""
                    snippet_selectors = [
                        'span.st', 'span.aCOpRe', 'div.s', 'div.VwiC3b',
                        '[data-content-feature="1"]', '.IsZvec'
                    ]
                    for selector in snippet_selectors:
                        snippet_elem = result.select_one(selector)
                        if snippet_elem:
                            snippet = snippet_elem.get_text().strip()
                            break
                    
                    if title and url and not url.startswith('/'):
                        results.append({
                            'title': title,
                            'url': url,
                            'snippet': snippet
                        })
                        logger.debug(f"結果追加: {title[:50]}...")
                        
                except Exception as e:
                    logger.debug(f"結果解析スキップ: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"Google結果解析エラー: {e}")
            
        logger.info(f"Google解析完了: {len(results)}件の結果")
        return results
    
    def _parse_duckduckgo_results(self, html_content, query):
        """DuckDuckGo検索結果の解析"""
        results = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            logger.info(f"DuckDuckGo HTMLパース完了、要素数: {len(soup.find_all())}")
            
            # DuckDuckGoの検索結果セレクタ
            search_result_selectors = [
                'div[data-result]',  # DuckDuckGoの標準的な検索結果
                'div.result',  # 別の結果コンテナ
                'div.web-result',  # Web検索結果
                'div.results_links',  # リンク結果
                'div.result__body',  # 結果本体
            ]
            
            search_results = []
            for selector in search_result_selectors:
                found_results = soup.select(selector)
                if found_results:
                    search_results = found_results
                    logger.info(f"DuckDuckGoセレクタ '{selector}' で {len(found_results)} 件の結果を発見")
                    break
            
            if not search_results:
                # フォールバック: すべてのリンクを探す
                logger.warning("DuckDuckGo標準結果が見つからないため、リンクを抽出")
                all_links = soup.find_all('a', href=True)
                for link in all_links[:20]:
                    try:
                        href = link.get('href', '')
                        title = link.get_text().strip()
                        
                        # DuckDuckGoの外部リンクを抽出
                        if (href.startswith(('http://', 'https://')) and 
                            not any(domain in href for domain in ['duckduckgo.com', 'duck.co']) and
                            title and len(title) > 5 and len(title) < 200):
                            
                            results.append({
                                'title': title,
                                'url': href,
                                'snippet': ""
                            })
                            
                            if len(results) >= 8:
                                break
                    except Exception:
                        continue
                        
                return results
            
            for result in search_results[:10]:
                try:
                    # タイトル取得
                    title = ""
                    title_selectors = ['h2 a', 'h3 a', '.result__title a', '.result__a']
                    for selector in title_selectors:
                        title_elem = result.select_one(selector)
                        if title_elem:
                            title = title_elem.get_text().strip()
                            break
                    
                    # URL取得
                    url = ""
                    link_selectors = ['h2 a', 'h3 a', '.result__title a', '.result__a']
                    for selector in link_selectors:
                        link_elem = result.select_one(selector)
                        if link_elem:
                            url = link_elem.get('href', '')
                            break
                    
                    # スニペット取得
                    snippet = ""
                    snippet_selectors = ['.result__snippet', '.snippet', '.result__description']
                    for selector in snippet_selectors:
                        snippet_elem = result.select_one(selector)
                        if snippet_elem:
                            snippet = snippet_elem.get_text().strip()
                            break
                    
                    if title and url and url.startswith(('http://', 'https://')):
                        results.append({
                            'title': title,
                            'url': url,
                            'snippet': snippet
                        })
                        logger.debug(f"DuckDuckGo結果追加: {title[:50]}...")
                        
                except Exception as e:
                    logger.debug(f"DuckDuckGo結果解析スキップ: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"DuckDuckGo結果解析エラー: {e}")
            
        logger.info(f"DuckDuckGo解析完了: {len(results)}件の結果")
        return results
    
    def _parse_wikipedia_results(self, html_content, query):
        """Wikipedia検索結果の解析"""
        results = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Wikipedia検索結果の要素を取得
            search_results = soup.find_all('div', {'class': 'mw-search-result'})
            
            for result in search_results[:10]:
                try:
                    title_elem = result.find('div', {'class': 'mw-search-result-heading'})
                    if title_elem:
                        link_elem = title_elem.find('a')
                        if link_elem:
                            title = link_elem.get_text().strip()
                            url = 'https://ja.wikipedia.org' + link_elem.get('href', '')
                            
                            snippet_elem = result.find('div', {'class': 'searchresult'})
                            snippet = snippet_elem.get_text().strip() if snippet_elem else ""
                            
                            results.append({
                                'title': title,
                                'url': url,
                                'snippet': snippet
                            })
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning(f"Wikipedia結果解析エラー: {e}")
            
        return results
    
    def _parse_generic_results(self, html_content, query):
        """汎用検索結果の解析"""
        results = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 汎用的なリンク要素を取得
            links = soup.find_all('a', href=True)
            
            for link in links[:15]:  # 上位15件から有効なものを抽出
                try:
                    href = link.get('href', '')
                    title = link.get_text().strip()
                    
                    # 有効なリンクかチェック
                    if (href.startswith('http') and title and 
                        len(title) > 5 and len(title) < 200):
                        
                        results.append({
                            'title': title,
                            'url': href,
                            'snippet': ""
                        })
                        
                        if len(results) >= 10:
                            break
                            
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning(f"汎用結果解析エラー: {e}")
            
        return results
    
    def _create_fallback_results(self, query, search_url):
        """検索結果が取得できない場合の代替結果を作成"""
        results = []
        
        # 検索エンジンのリンクを直接提供
        results.append({
            'title': f"{self.current_engine}で「{query}」を検索",
            'url': search_url,
            'snippet': f"{self.current_engine}の検索結果ページを直接開きます。"
        })
        
        # よく使われるリソースへのリンクを追加
        if any(keyword in query.lower() for keyword in ['warship', '戦艦', '艦船', 'ship', 'hull']):
            results.extend([
                {
                    'title': 'Wikipedia - List of battleships',
                    'url': 'https://en.wikipedia.org/wiki/List_of_battleships',
                    'snippet': 'List of battleships by country and class'
                },
                {
                    'title': 'Naval History - Warship Database',
                    'url': 'https://www.naval-history.net/',
                    'snippet': 'Comprehensive database of naval vessels and history'
                },
                {
                    'title': 'World War Photos - Naval Vessels',
                    'url': 'https://www.worldwarphotos.info/category/navy/',
                    'snippet': 'Historical photos and information about naval vessels'
                }
            ])
        
        if any(keyword in query.lower() for keyword in ['equipment', '装備', 'gun', '砲', 'weapon']):
            results.extend([
                {
                    'title': 'Naval Weapons - NavWeaps',
                    'url': 'http://www.navweaps.com/',
                    'snippet': 'Comprehensive database of naval weapons and equipment'
                },
                {
                    'title': 'Wikipedia - Naval artillery',
                    'url': 'https://en.wikipedia.org/wiki/Naval_artillery',
                    'snippet': 'Information about naval guns and artillery systems'
                }
            ])
        
        # 日本の軍艦関連キーワードの場合
        if any(keyword in query for keyword in ['赤城', '大和', '長門', '金剛', '扶桑']):
            results.extend([
                {
                    'title': 'Wikipedia - 日本海軍艦艇一覧',
                    'url': 'https://ja.wikipedia.org/wiki/日本海軍艦艇一覧',
                    'snippet': '大日本帝国海軍の艦艇一覧'
                },
                {
                    'title': 'Wikipedia - Imperial Japanese Navy',
                    'url': 'https://en.wikipedia.org/wiki/Imperial_Japanese_Navy',
                    'snippet': 'History and ships of the Imperial Japanese Navy'
                }
            ])
        
        return results[:8]  # 最大8件まで
    
    def _display_search_results(self, query, results, error_mode=False):
        """検索結果を表示"""
        status_text = "⚠️ 代替リンク表示" if error_mode else "検索結果"
        info_color = "#fff3cd" if error_mode else "#e8f4fd"
        
        html = f"""
        <html><head>
            <meta charset='utf-8'>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    padding: 20px; 
                    background-color: #f5f5f5; 
                    user-select: text;
                    -webkit-user-select: text;
                    -moz-user-select: text;
                    -ms-user-select: text;
                }}
                h2 {{ color: #333; }}
                .search-info {{ 
                    background-color: {info_color}; 
                    padding: 10px; 
                    border-radius: 5px; 
                    margin: 10px 0; 
                }}
                .search-results {{ 
                    background-color: white; 
                    padding: 15px; 
                    border-radius: 5px; 
                    margin: 10px 0; 
                }}
                .search-item {{ 
                    margin-bottom: 15px; 
                    padding-bottom: 10px; 
                    border-bottom: 1px solid #eee; 
                }}
                .search-title {{ 
                    color: #1a0dab; 
                    font-size: 18px; 
                    text-decoration: none; 
                    font-weight: bold; 
                }}
                .search-title:hover {{ text-decoration: underline; }}
                .search-url {{ 
                    color: #006621; 
                    font-size: 14px; 
                    margin: 5px 0; 
                    word-break: break-all;
                    user-select: text;
                    -webkit-user-select: text;
                    cursor: text;
                }}
                .search-snippet {{ 
                    color: #545454; 
                    font-size: 13px; 
                    line-height: 1.4; 
                    user-select: text;
                    -webkit-user-select: text;
                }}
                .no-results {{ color: #666; font-style: italic; }}
                p, div, span {{ 
                    user-select: text; 
                    -webkit-user-select: text; 
                }}
                .copyable {{ 
                    user-select: text; 
                    -webkit-user-select: text; 
                    -moz-user-select: text; 
                    -ms-user-select: text; 
                    cursor: text;
                    padding: 2px 4px;
                    background-color: #f8f9fa;
                    border-radius: 3px;
                    font-family: monospace;
                }}
            </style>
        </head><body>
            <h2>🔍 {status_text}: "<span class="copyable">{query}</span>"</h2>
            <div class="search-info">
                <p><strong>検索エンジン:</strong> {self.current_engine} | <strong>結果件数:</strong> {len(results)}件</p>
                {f'<p><strong>注意:</strong> 通常の検索結果が取得できませんでした。関連リンクを表示しています。</p>' if error_mode else ''}
            </div>
            <div class="search-results">
        """
        
        if results:
            for i, result in enumerate(results, 1):
                title = self._escape_html(result.get('title', ''))
                url = self._escape_html(result.get('url', ''))
                snippet = self._escape_html(result.get('snippet', ''))
                
                html += f"""
                <div class="search-item">
                    <div class="search-title">
                        <a href="{url}">{i}. {title}</a>
                    </div>
                    <div class="search-url copyable">{url}</div>
                    <div class="search-snippet">{snippet}</div>
                </div>
                """
        else:
            html += '<div class="no-results">検索結果が見つかりませんでした。</div>'
        
        html += """
            </div>
        </body></html>
        """
        
        self.web_view.setHtml(html)
    
    def _display_error_message(self, query, error_message):
        """エラーメッセージを表示"""
        html = f"""
        <html><head>
            <meta charset='utf-8'>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5; }}
                .error {{ background-color: #ffe6e6; border: 1px solid #ff9999; padding: 15px; border-radius: 5px; }}
                .error h3 {{ color: #cc0000; margin-top: 0; }}
            </style>
        </head><body>
            <div class="error">
                <h3>🚫 検索エラー</h3>
                <p><strong>検索クエリ:</strong> "{query}"</p>
                <p><strong>エラー:</strong> {error_message}</p>
                <p>ネットワーク接続を確認するか、しばらく後に再試行してください。</p>
            </div>
        </body></html>
        """
        self.web_view.setHtml(html)
    
    def _display_dependency_error(self, query, error_message):
        """依存関係エラーメッセージを表示"""
        html = f"""
        <html><head>
            <meta charset='utf-8'>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5; }}
                .error {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; }}
                .error h3 {{ color: #856404; margin-top: 0; }}
                .install-command {{ background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 10px; border-radius: 3px; font-family: monospace; margin: 10px 0; }}
            </style>
        </head><body>
            <div class="error">
                <h3>⚠️ 依存関係エラー</h3>
                <p><strong>検索クエリ:</strong> "{query}"</p>
                <p><strong>エラー:</strong> {error_message}</p>
                <p>内部検索機能を使用するには、以下のコマンドで必要なライブラリをインストールしてください：</p>
                <div class="install-command">
                    pip install requests beautifulsoup4
                </div>
                <p>インストール後、アプリケーションを再起動してください。</p>
            </div>
        </body></html>
        """
        self.web_view.setHtml(html)
    
    def on_link_clicked(self, url):
        """リンクがクリックされた時の処理"""
        try:
            url_str = url.toString()
            logger.info(f"リンククリック: {url_str}")
            
            # 相対URLや無効なURLの処理
            if not url_str.startswith(('http://', 'https://')):
                if url_str.startswith('/'):
                    # 相対URLの場合、ベースURLを追加
                    base_url = "https://www.google.com"
                    url_str = base_url + url_str
                    logger.info(f"相対URL修正: {url_str}")
                elif url_str.startswith('#'):
                    # アンカーリンクは無視
                    logger.info("アンカーリンクのため処理をスキップ")
                    return
                else:
                    # その他の無効なURLは外部ブラウザで開く
                    logger.warning(f"無効なURL形式のため外部ブラウザで開く: {url_str}")
                    QDesktopServices.openUrl(QUrl(url_str))
                    self.status_label.setText("外部ブラウザで開きました")
                    return
            
            # 現在のページを履歴に追加
            self._add_to_page_history()
            
            if self.use_webengine:
                # WebEngineの場合は直接ロード
                self.web_view.load(QUrl(url_str))
            else:
                # 内部ブラウザでページを取得・表示
                self._load_page_internally(url_str)
                
        except Exception as e:
            logger.error(f"リンククリック処理エラー: {e}")
            self.status_label.setText(f"リンクエラー: {str(e)}")
    
    def _add_to_page_history(self):
        """現在のページを履歴に追加"""
        try:
            # 現在の表示内容を履歴に保存
            current_html = self.web_view.toHtml() if hasattr(self.web_view, 'toHtml') else ""
            current_title = "検索結果" # 簡略化
            
            # 履歴に追加
            if self.page_history_index < len(self.page_history) - 1:
                # 現在位置より後の履歴を削除
                self.page_history = self.page_history[:self.page_history_index + 1]
            
            self.page_history.append({
                'html': current_html,
                'title': current_title
            })
            
            self.page_history_index = len(self.page_history) - 1
            
            # 履歴サイズ制限
            if len(self.page_history) > 20:
                self.page_history.pop(0)
                self.page_history_index -= 1
                
        except Exception as e:
            logger.warning(f"履歴追加エラー: {e}")
    
    def _load_page_internally(self, url):
        """内部ブラウザでページを読み込み"""
        try:
            self.status_label.setText(f"読み込み中: {url}")
            
            if not REQUESTS_AVAILABLE or not BS4_AVAILABLE:
                # 依存関係不足の場合は外部ブラウザで開く
                QDesktopServices.openUrl(QUrl(url))
                self.status_label.setText("外部ブラウザで開きました")
                return
            
            # ユーザーエージェントを設定
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # ページを取得
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # HTMLを解析して表示用に整形
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 不要な要素を削除
            for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()
            
            # ページタイトルを取得
            title_elem = soup.find('title')
            page_title = title_elem.get_text().strip() if title_elem else "ページ"
            
            # メインコンテンツを抽出
            main_content = ""
            content_selectors = ['article', 'main', '[role="main"]', '.content', '#content', '.main']
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    main_content = str(content_elem)
                    break
            
            if not main_content:
                # フォールバック: body全体
                body_elem = soup.find('body')
                if body_elem:
                    main_content = str(body_elem)
                else:
                    main_content = str(soup)
            
            # 表示用HTMLを構築
            display_html = f"""
            <html><head>
                <meta charset='utf-8'>
                <style>
                    body {{ 
                        font-family: Arial, sans-serif; 
                        padding: 20px; 
                        background-color: #f5f5f5; 
                        line-height: 1.6;
                    }}
                    .page-header {{ 
                        background-color: #e8f4fd; 
                        padding: 15px; 
                        border-radius: 5px; 
                        margin-bottom: 20px; 
                    }}
                    .page-content {{ 
                        background-color: white; 
                        padding: 20px; 
                        border-radius: 5px; 
                        max-width: 800px;
                    }}
                    img {{ max-width: 100%; height: auto; }}
                    a {{ color: #1a0dab; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    pre, code {{ 
                        background-color: #f8f9fa; 
                        padding: 10px; 
                        border-radius: 3px; 
                        font-family: monospace;
                        white-space: pre-wrap;
                        word-wrap: break-word;
                        user-select: text;
                        -webkit-user-select: text;
                        -moz-user-select: text;
                        -ms-user-select: text;
                    }}
                    .copyable {{ 
                        user-select: text; 
                        -webkit-user-select: text; 
                        -moz-user-select: text; 
                        -ms-user-select: text; 
                        cursor: text;
                    }}
                    p, div, span {{ 
                        user-select: text; 
                        -webkit-user-select: text; 
                    }}
                </style>
            </head><body>
                <div class="page-header">
                    <h2>📄 {self._escape_html(page_title)}</h2>
                    <p><strong>URL:</strong> <span class="copyable">{self._escape_html(url)}</span></p>
                </div>
                <div class="page-content copyable">
                    {main_content}
                </div>
            </body></html>
            """
            
            self.web_view.setHtml(display_html)
            self.status_label.setText(f"ページ読み込み完了: {page_title}")
            
            # ナビゲーションボタンの状態を更新
            self._update_navigation_buttons()
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"ページ読み込みエラー: {e}")
            # 外部ブラウザで開く
            QDesktopServices.openUrl(QUrl(url))
            self.status_label.setText("外部ブラウザで開きました")
        except Exception as e:
            logger.error(f"ページ処理エラー: {e}")
            self.status_label.setText(f"ページエラー: {str(e)}")
    
    def _update_navigation_buttons(self):
        """ナビゲーションボタンの状態を更新"""
        if self.use_webengine:
            # WebEngineの場合
            if hasattr(self.web_view, 'history'):
                self.back_button.setEnabled(self.web_view.history().canGoBack())
                self.forward_button.setEnabled(self.web_view.history().canGoForward())
        else:
            # 内部ブラウザの場合
            self.back_button.setEnabled(self.page_history_index > 0)
            self.forward_button.setEnabled(self.page_history_index < len(self.page_history) - 1)
    
    def _escape_html(self, text):
        """HTMLエスケープ"""
        if not text:
            return ""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#39;'))
    
    def go_back(self):
        """戻る"""
        if self.use_webengine and hasattr(self.web_view, 'history'):
            if self.web_view.history().canGoBack():
                self.web_view.back()
        else:
            # 内部ブラウザのページ履歴を使用
            if self.page_history_index > 0:
                self.page_history_index -= 1
                page_data = self.page_history[self.page_history_index]
                self.web_view.setHtml(page_data['html'])
                self.status_label.setText(f"前のページに戻りました: {page_data['title']}")
                self._update_navigation_buttons()
            else:
                # ページ履歴がない場合は検索履歴を使用
                if len(self.search_history) > 1:
                    current_query = self.search_input.text().strip()
                    try:
                        current_index = self.search_history.index(current_query)
                        if current_index > 0:
                            prev_query = self.search_history[current_index - 1]
                            self.search_input.setText(prev_query)
                            self.perform_search(prev_query)
                            self.status_label.setText(f"前の検索に戻りました: {prev_query}")
                        else:
                            self.status_label.setText("これ以上戻れません")
                    except ValueError:
                        if len(self.search_history) > 0:
                            prev_query = self.search_history[-1]
                            self.search_input.setText(prev_query)
                            self.perform_search(prev_query)
                            self.status_label.setText(f"最近の検索に戻りました: {prev_query}")
                else:
                    self.status_label.setText("戻る履歴がありません")
    
    def go_forward(self):
        """進む"""
        if self.use_webengine and hasattr(self.web_view, 'history'):
            if self.web_view.history().canGoForward():
                self.web_view.forward()
        else:
            # 内部ブラウザのページ履歴を使用
            if self.page_history_index < len(self.page_history) - 1:
                self.page_history_index += 1
                page_data = self.page_history[self.page_history_index]
                self.web_view.setHtml(page_data['html'])
                self.status_label.setText(f"次のページに進みました: {page_data['title']}")
                self._update_navigation_buttons()
            else:
                self.status_label.setText("これ以上進めません")
    
    def refresh_page(self):
        """ページ更新"""
        if self.use_webengine and hasattr(self.web_view, 'reload'):
            self.web_view.reload()
        else:
            # 現在の検索を再実行
            current_query = self.search_input.text().strip()
            if current_query:
                self.perform_search(current_query)
                self.status_label.setText(f"検索を更新しました: {current_query}")
            else:
                self.setup_simple_browser()
                self.status_label.setText("ページを更新しました")
    
    def on_load_started(self):
        """読み込み開始（WebEngineのみ）"""
        if self.use_webengine:
            self.status_label.setText("読み込み中...")
            self.refresh_button.setText("✕")
            self.refresh_button.clicked.disconnect()
            self.refresh_button.clicked.connect(self.web_view.stop)
    
    def on_load_finished(self, success):
        """読み込み完了（WebEngineのみ）"""
        if self.use_webengine:
            if success:
                self.status_label.setText("読み込み完了")
            else:
                self.status_label.setText("読み込み失敗")
            
            self.refresh_button.setText("⟳")
            self.refresh_button.clicked.disconnect()
            self.refresh_button.clicked.connect(self.refresh_page)
            
            # ナビゲーションボタンの状態更新
            if hasattr(self.web_view, 'history'):
                self.back_button.setEnabled(self.web_view.history().canGoBack())
                self.forward_button.setEnabled(self.web_view.history().canGoForward())
        else:
            # 内部ブラウザモードの場合、検索履歴に基づいてボタン状態を更新
            self.back_button.setEnabled(len(self.search_history) > 1)
            self.forward_button.setEnabled(False)  # 進む機能は無効
    
    def on_url_changed(self, url):
        """URL変更時（WebEngineのみ）"""
        if self.use_webengine:
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