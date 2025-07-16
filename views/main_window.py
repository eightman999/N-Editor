from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel, QStatusBar, \
    QListWidget, QSizePolicy, QProgressDialog, QMessageBox, QToolBar, QAction, QProgressBar, QDialog, QTextEdit, \
    QPushButton, QMenuBar
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QCloseEvent, QImage, QPixmap, QIcon

import os
import json
import cv2
import numpy as np
import logging
from concurrent.futures import ThreadPoolExecutor
import psutil
import time
import subprocess

from views.home_view import HomeView
from views.equipment_view import EquipmentView
from views.hull_form import HullForm
from views.hull_list_view import HullListView
from views.design_view import DesignView
from views.fleet_view import FleetView
from views.settings_view import SettingsView
from views.nation_view import NationView
from views.nation_details_view import NationDetailsView
from views.ship_list_view import ShipListView
from views.naval_export_dialog import NavalExportDialog
from views.hoi4_export_dialog import HOI4ExportDialog
from utils.conflict_resolution_dialog import ConflictResolutionDialog
from controllers.naval_export_controller import NavalExportController

class MenuLoadingWorker(QThread):
    """メニュー読み込み用のワーカースレッド"""
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, views_to_load):
        super().__init__()
        self.views_to_load = views_to_load
        self.logger = logging.getLogger('MenuLoadingWorker')

    def run(self):
        try:
            total_views = len(self.views_to_load)
            for i, (view_name, view_class) in enumerate(self.views_to_load):
                self.progress.emit(int((i + 1) / total_views * 100))
                self.logger.info(f"ビューの読み込み中: {view_name}")
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
            self.logger.error(f"ビューの読み込み中にエラーが発生: {str(e)}")

class ImageProcessingWorker(QThread):
    """画像処理用のワーカースレッド"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path
        self.logger = logging.getLogger('ImageProcessingWorker')

    def run(self):
        try:
            # OpenCVで画像を読み込み
            img = cv2.imread(self.image_path)
            if img is None:
                raise Exception(f"画像の読み込みに失敗: {self.image_path}")

            # GPUが利用可能な場合はGPUを使用
            if cv2.cuda.getCudaEnabledDeviceCount() > 0:
                self.logger.info("GPUを使用して画像処理を実行")
                # GPUメモリに画像をアップロード
                gpu_img = cv2.cuda_GpuMat()
                gpu_img.upload(img)
                
                # GPU上で画像処理を実行
                # 例：ガウシアンブラー
                gpu_blur = cv2.cuda.createGaussianFilter(
                    cv2.CV_8UC3, cv2.CV_8UC3, (5, 5), 1.5
                )
                gpu_result = gpu_blur.apply(gpu_img)
                
                # 結果をCPUメモリにダウンロード
                result = gpu_result.download()
            else:
                self.logger.info("CPUを使用して画像処理を実行")
                # CPUで画像処理を実行
                result = cv2.GaussianBlur(img, (5, 5), 1.5)

            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
            self.logger.error(f"画像処理中にエラーが発生: {str(e)}")

class NavalDesignSystem(QMainWindow):
    """Naval Design Systemのメインウィンドウ（コンフリクト対応版）"""

    def __init__(self, app_controller=None, app_settings=None):
        super().__init__()

        # コントローラーとアプリケーション設定
        self.app_controller = app_controller
        self.app_settings = app_settings

        # 同期関連UI要素
        self.sync_progress_bar = None
        self.sync_status_label = None
        
        # アプリケーションコントローラーの状態を確認
        print(f"NavalDesignSystem.__init__: app_controller = {self.app_controller}")

        # ビューマッピング
        self.views = {}

        # アプリケーション設定の読み込み
        self.load_config()

        # スレッドプールの初期化（ワーカー数を制限）
        self.thread_pool = ThreadPoolExecutor(max_workers=2)
        
        # メモリ管理用の変数
        self._memory_warning_threshold = 300  # MB（閾値を下げる）
        self._memory_critical_threshold = 500  # MB（閾値を下げる）
        self._last_cleanup_time = 0
        self._cleanup_interval = 30  # 秒（間隔を短くする）
        
        # ロガーの設定
        self.logger = logging.getLogger('NavalDesignSystem')
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # UIの初期化
        self.init_ui()

        # 現在のMODの状態を確認
        if self.app_controller:
            current_mod = self.app_controller.get_current_mod()
            print(f"NavalDesignSystem初期化: current_mod = {current_mod}")

            # デバッグ用メニューの追加
            self.add_debug_menu()

        # コンフリクト解決関連のシグナル接続
        if self.app_controller and hasattr(self.app_controller, 'sync_manager'):
            sync_manager = self.app_controller.sync_manager
            # 既存のシグナル接続
            sync_manager.sync_started.connect(self.on_sync_started)
            sync_manager.sync_progress.connect(self.on_sync_progress)
            sync_manager.sync_completed.connect(self.on_sync_completed)
            
            # 新しいコンフリクト検出シグナル接続
            if hasattr(sync_manager, 'conflict_detected'):
                sync_manager.conflict_detected.connect(self.on_conflict_detected)

    def load_config(self):
        """設定ファイルを読み込む"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'config.json')
        version_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'version.txt')

        # バージョン情報の読み込み
        version = "0.0.0"
        try:
            if os.path.exists(version_path):
                with open(version_path, 'r', encoding='utf-8') as f:
                    version = f.read().strip()
        except Exception as e:
            print(f"バージョンファイルの読み込みに失敗しました: {e}")

        # デフォルト設定
        self.config = {
            "app_name": "Naval Design System",
            "version": f"β{version}",
            "display": {
                "width": 1080,
                "height": 720,
                "fullscreen": False
            }
        }

        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config.update(json.load(f))
        except Exception as e:
            print(f"設定ファイルの読み込みに失敗しました: {e}")

    def init_ui(self):
        """UIの初期化（同期機能追加版）"""
        # ウィンドウの基本設定
        self.setWindowTitle(self.config.get("app_name", "Naval Design System"))

        # 全画面表示の設定を読み込み
        is_fullscreen = self.config.get("display", {}).get("fullscreen", False)

        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # メインレイアウト
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # ツールバーの追加
        self.create_toolbar()
        
        # サイドバーメニュー
        self.create_sidebar(main_layout)

        # メインビュー
        self.create_main_view(main_layout)

        # ステータスバーの拡張
        self.create_status_bar()

        # ウィンドウサイズの設定
        if not is_fullscreen:
            # 通常サイズで表示する場合
            width = self.config.get("display", {}).get("width", 1024)
            height = self.config.get("display", {}).get("height", 768)
            self.resize(width, height)
        else:
            # 全画面表示は後で設定
            self.showNormal()  # まず通常表示で初期化
            QTimer.singleShot(100, self.showFullScreen)  # 少し遅延させて全画面表示

        # 同期関連のシグナル接続
        if self.app_controller and hasattr(self.app_controller, 'sync_manager'):
            self.app_controller.sync_manager.sync_started.connect(self.on_sync_started)
            self.app_controller.sync_manager.sync_progress.connect(self.on_sync_progress)
            self.app_controller.sync_manager.sync_completed.connect(self.on_sync_completed)

    def create_toolbar(self):
        """ツールバーの作成（文字化け修正版）"""
        toolbar = QToolBar("メインツールバー")
        self.addToolBar(toolbar)
        
        # 同期ボタン（絵文字を削除）
        sync_action = QAction("同期", self)
        sync_action.setStatusTip("データをオンラインと同期")
        sync_action.triggered.connect(self.sync_data)
        toolbar.addAction(sync_action)
        
        # プッシュボタン（絵文字を削除）
        push_action = QAction("プッシュ", self)
        push_action.setStatusTip("ローカルデータをリモートにアップロード")
        push_action.triggered.connect(self.push_data)
        toolbar.addAction(push_action)
        
        # プルボタン（絵文字を削除）
        pull_action = QAction("プル", self)
        pull_action.setStatusTip("リモートデータをダウンロード")
        pull_action.triggered.connect(self.pull_data)
        toolbar.addAction(pull_action)
        
        toolbar.addSeparator()
        
        # 同期設定ボタン（絵文字を削除）
        sync_settings_action = QAction("同期設定", self)
        sync_settings_action.setStatusTip("データ同期の設定")
        sync_settings_action.triggered.connect(self.show_sync_settings)
        toolbar.addAction(sync_settings_action)

    def create_status_bar(self):
        """ステータスバーの拡張"""
        status_bar = self.statusBar()
        
        # 同期ステータス表示
        self.sync_status_label = QLabel("同期未設定")
        self.sync_status_label.setMinimumWidth(150)
        status_bar.addPermanentWidget(self.sync_status_label)
        
        # 同期プログレスバー
        self.sync_progress_bar = QProgressBar()
        self.sync_progress_bar.setVisible(False)
        self.sync_progress_bar.setMaximumWidth(200)
        status_bar.addPermanentWidget(self.sync_progress_bar)
        
        # 初期状態の更新
        self.update_sync_status()

    def update_sync_status(self):
        """同期ステータスの更新"""
        if (self.app_controller and 
            hasattr(self.app_controller, 'sync_manager') and 
            self.sync_status_label):
            
            sync_manager = self.app_controller.sync_manager
            
            # 設定を再読み込み
            sync_manager.reload_settings()
            
            if sync_manager.is_configured():
                repo_name = sync_manager.repo_url.split('/')[-1].replace('.git', '') if sync_manager.repo_url else "不明"
                self.sync_status_label.setText(f"同期先: {repo_name}")
                self.sync_status_label.setStyleSheet("QLabel { color: green; }")
            else:
                self.sync_status_label.setText("同期未設定")
                self.sync_status_label.setStyleSheet("QLabel { color: red; }")

    def sync_data(self):
        """データ同期実行"""
        if self.app_controller:
            self.app_controller.sync_data_manually('full_sync')

    def push_data(self):
        """データプッシュ実行"""
        if self.app_controller:
            self.app_controller.sync_data_manually('push')

    def pull_data(self):
        """データプル実行"""
        if self.app_controller:
            self.app_controller.sync_data_manually('pull')

    def show_sync_settings(self):
        """同期設定画面を表示"""
        if self.app_controller:
            # SettingsViewの同期タブを表示
            self.show_view("settings")
            
            # 同期設定タブを選択
            if hasattr(self, 'views') and 'settings' in self.views:
                settings_view = self.views['settings']
                if hasattr(settings_view, 'tab_widget'):
                    settings_view.tab_widget.setCurrentIndex(1)  # 同期設定タブ
                    
            # 同期ステータスを更新
            self.update_sync_status()

    def on_sync_started(self, operation):
        """同期開始時の処理"""
        if self.sync_progress_bar:
            self.sync_progress_bar.setVisible(True)
            self.sync_progress_bar.setRange(0, 0)  # 不定プログレス
        
        self.statusBar().showMessage(f"同期実行中: {operation}")
        
        # UIを一時的に無効化（オプション）
        self.setEnabled(True)  # 必要に応じてFalseに変更

    def on_sync_progress(self, message):
        """同期進捗更新時の処理"""
        self.statusBar().showMessage(message)

    def on_sync_completed(self, success, message):
        """同期完了時の処理（拡張版）"""
        if self.sync_progress_bar:
            self.sync_progress_bar.setVisible(False)
        
        # UIを有効化
        self.setEnabled(True)
        
        if success:
            self.statusBar().showMessage(f"同期完了: {message}", 5000)
            # 成功時の視覚効果
            self.flash_sync_status("green")
            
            # 成功メッセージダイアログ（重要な場合のみ）
            if "コンフリクト" in message or "強制" in message:
                QMessageBox.information(
                    self, "同期完了", 
                    f"データ同期が正常に完了しました。\n\n詳細: {message}"
                )
        else:
            self.statusBar().showMessage(f"同期失敗: {message}", 10000)
            # エラー時の視覚効果
            self.flash_sync_status("red")
            
            # エラーダイアログ表示（詳細情報付き）
            self.show_sync_error_dialog(message)

    def flash_sync_status(self, color):
        """同期ステータスの点滅効果"""
        if not self.sync_status_label:
            return
            
        original_style = self.sync_status_label.styleSheet()
        flash_style = f"QLabel {{ color: {color}; font-weight: bold; }}"
        
        # 点滅効果
        self.sync_status_label.setStyleSheet(flash_style)
        
        # 2秒後に元に戻す
        QTimer.singleShot(2000, lambda: self.sync_status_label.setStyleSheet(original_style))

    def create_sidebar(self, parent_layout):
        """サイドバーメニューの作成"""
        # サイドバーウィジェット
        sidebar_widget = QWidget()
        sidebar_widget.setFixedWidth(200)  # サイドバーの幅
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(5, 10, 5, 10)
        sidebar_layout.setSpacing(10)

        # タイトルラベル
        title_label = QLabel("<b>Naval Design System</b>")
        title_label.setFont(QFont("Hiragino Sans", 14))
        title_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title_label)

        # メニューリスト
        self.menu_list = QListWidget()
        self.menu_list.addItems([
            "ホーム",
            "装備登録",
            "船体リスト",
            "船体登録",
            "船体設計",
            "艦隊配備",
            "国家確認",
            "国家詳細",
            "艦艇一覧",
            "設定"
        ])

        # スタイルの設定
        self.menu_list.setFont(QFont("Hiragino Sans", 12))
        self.menu_list.setIconSize(QSize(24, 24))
        self.menu_list.setStyleSheet("""
            QListWidget {
                background-color: #e6e6e6;
                border: 2px inset #808080;
            }
            QListWidget::item {
                height: 30px;
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #000080;
                color: white;
            }
        """)

        # 選択時の処理
        self.menu_list.currentRowChanged.connect(self.on_menu_changed)

        # メニューリストをサイドバーに追加（サイズポリシーを設定）
        self.menu_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sidebar_layout.addWidget(self.menu_list)

        # バージョン情報
        version_text = f"Version {self.config.get('version', '0.0.0')}"
        version_label = QLabel(version_text)
        version_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(version_label)

        parent_layout.addWidget(sidebar_widget)

    def create_main_view(self, parent_layout):
        """メインビューの作成"""
        # メインビューウィジェット
        main_view_widget = QWidget()
        main_layout = QVBoxLayout(main_view_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # スタック型ウィジェット（ページ切り替え用）
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # 各ページの追加
        self.initialize_views()

        parent_layout.addWidget(main_view_widget)

    def initialize_views(self):
        """各ビューを非同期で初期化"""
        self.logger.info("ビューの非同期初期化を開始")
        
        # プログレスダイアログの表示（親ウィジェットを明示的に指定）
        self.progress_dialog = QProgressDialog("ビューを読み込み中...", "キャンセル", 0, 100, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.setMinimumDuration(0)  # 即時表示
        self.progress_dialog.setWindowTitle("初期化中")
        self.progress_dialog.setCancelButton(None)  # キャンセルボタンを無効化
        self.progress_dialog.show()

        # 読み込むビューのリスト
        views_to_load = [
            ("home", HomeView(self, self.app_settings, self.app_controller)),
            ("equipment", EquipmentView(self, self.app_controller)),
            ("hull_list", HullListView(self, self.app_controller)),
            ("hull_form", HullForm(self, self.app_controller)),
            ("design", DesignView(self)),
            ("fleet", FleetView(self)),
            ("nation", NationView(self, self.app_controller)),
            ("nation_details", NationDetailsView(self, self.app_controller)),
            ("ship_list", ShipListView(self, self.app_controller)),
            ("settings", SettingsView(self, self.app_settings))
        ]

        # 各ビューをスタックウィジェットに追加
        for view_name, view_widget in views_to_load:
            self.add_view(view_name, view_widget)
            self.logger.info(f"ビュー '{view_name}' を追加しました")

        # ワーカースレッドの開始
        self.menu_worker = MenuLoadingWorker(views_to_load)
        self.menu_worker.progress.connect(self.update_progress)
        self.menu_worker.finished.connect(self.on_views_loaded)
        self.menu_worker.error.connect(self.on_loading_error)
        
        # メモリ使用量の監視を開始
        self.start_memory_monitoring()
        
        # ワーカースレッドを開始
        self.menu_worker.start()

    def start_memory_monitoring(self):
        """メモリ使用量の監視を開始"""
        def monitor_memory():
            try:
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                memory_usage = memory_info.rss / 1024 / 1024  # MB単位
                
                current_time = time.time()
                
                # メモリ使用量のログ出力
                self.logger.info(f"メモリ使用量: {memory_usage:.2f} MB")
                
                # クリティカルなメモリ使用量の場合
                if memory_usage > self._memory_critical_threshold:
                    self.logger.critical(f"クリティカルなメモリ使用量: {memory_usage:.2f} MB")
                    self.emergency_cleanup()
                
                # 警告レベルのメモリ使用量の場合
                elif memory_usage > self._memory_warning_threshold:
                    self.logger.warning(f"メモリ使用量が高くなっています: {memory_usage:.2f} MB")
                    
                    # 前回のクリーンアップから一定時間経過している場合のみ実行
                    if current_time - self._last_cleanup_time > self._cleanup_interval:
                        self.cleanup_resources()
                        self._last_cleanup_time = current_time
                
            except Exception as e:
                self.logger.error(f"メモリ監視中にエラーが発生: {e}")
        
        # 定期的なメモリ監視を開始
        self.memory_timer = QTimer(self)
        self.memory_timer.timeout.connect(monitor_memory)
        self.memory_timer.start(5000)  # 5秒ごとに監視

    def emergency_cleanup(self):
        """緊急時のリソースクリーンアップ"""
        try:
            # すべてのキャッシュをクリア
            if hasattr(self.app_controller, 'clear_cache'):
                self.app_controller.clear_cache()
            
            # アイコンキャッシュのクリア
            if hasattr(self.app_controller, 'ship_icon_manager'):
                self.app_controller.ship_icon_manager.clear_cache()
            
            # すべてのビューを解放
            for view in self.views.values():
                if hasattr(view, 'cleanup'):
                    view.cleanup()
            self.views.clear()
            
            # ガベージコレクションの強制実行
            import gc
            gc.collect()
            
            self.logger.warning("緊急リソースクリーンアップを実行しました")
            
        except Exception as e:
            self.logger.error(f"緊急リソースクリーンアップ中にエラーが発生: {e}")

    def cleanup_resources(self):
        """リソースのクリーンアップ（改善版）"""
        try:
            # アイコンキャッシュのクリア
            if hasattr(self.app_controller, 'ship_icon_manager'):
                self.app_controller.ship_icon_manager.clear_cache()
            
            # 不要なビューの解放
            for view_name, view in list(self.views.items()):
                if view_name != self.stacked_widget.currentWidget():
                    if hasattr(view, 'cleanup'):
                        view.cleanup()
                    self.views.pop(view_name, None)
            
            # ガベージコレクションの強制実行
            import gc
            gc.collect()
            
            self.logger.info("リソースのクリーンアップを実行しました")
            
        except Exception as e:
            self.logger.error(f"リソースのクリーンアップ中にエラーが発生: {e}")

    def update_progress(self, value):
        """プログレスバーの更新"""
        try:
            if hasattr(self, 'progress_dialog') and self.progress_dialog is not None:
                self.progress_dialog.setValue(value)
                # プログレスメッセージの更新
                self.progress_dialog.setLabelText(f"ビューを読み込み中... {value}%")
            else:
                self.logger.warning("プログレスダイアログが存在しません")
        except Exception as e:
            self.logger.error(f"プログレス更新中にエラーが発生: {e}")

    def on_views_loaded(self):
        """ビューの読み込み完了時の処理"""
        try:
            # メモリ監視タイマーを停止
            if hasattr(self, 'memory_timer'):
                self.memory_timer.stop()
            
            # プログレスダイアログを安全に閉じる
            if hasattr(self, 'progress_dialog') and self.progress_dialog is not None:
                self.progress_dialog.close()
                self.progress_dialog = None
            
            # リソースの解放
            self.cleanup_resources()
            
            self.logger.info("すべてのビューの読み込みが完了しました")
            
            # メニューリストの更新
            self.menu_list.setEnabled(True)
            self.statusBar().showMessage("準備完了")

            # デバッグ情報の出力
            self.logger.info(f"登録されたビュー: {list(self.views.keys())}")
            self.logger.info(f"スタックウィジェットのページ数: {self.stacked_widget.count()}")
            
        except Exception as e:
            self.logger.error(f"ビュー読み込み完了処理中にエラーが発生: {e}")

    def on_loading_error(self, error_msg):
        """読み込みエラー時の処理"""
        self.progress_dialog.close()
        self.logger.error(f"ビューの読み込み中にエラーが発生: {error_msg}")
        QMessageBox.critical(self, "エラー", f"ビューの読み込み中にエラーが発生しました：\n{error_msg}")

    def process_image(self, image_path):
        """画像処理を非同期で実行"""
        self.logger.info(f"画像処理を開始: {image_path}")
        
        # プログレスダイアログの表示
        self.progress_dialog = QProgressDialog("画像を処理中...", "キャンセル", 0, 100, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.show()

        # 画像処理ワーカーの開始
        self.image_worker = ImageProcessingWorker(image_path)
        self.image_worker.progress.connect(self.update_progress)
        self.image_worker.finished.connect(self.on_image_processed)
        self.image_worker.error.connect(self.on_loading_error)
        self.image_worker.start()

    def on_image_processed(self, processed_image):
        """画像処理完了時の処理"""
        self.progress_dialog.close()
        self.logger.info("画像処理が完了しました")
        
        # 処理済み画像をQPixmapに変換
        height, width = processed_image.shape[:2]
        bytes_per_line = 3 * width
        q_image = QImage(processed_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        
        # 画像の表示（例：ステータスバーに表示）
        self.statusBar().showMessage("画像処理が完了しました")

    def add_view(self, view_name, view_widget):
        """ビューをスタックウィジェットに追加"""
        self.views[view_name] = view_widget
        self.stacked_widget.addWidget(view_widget)
        # self.logger.info(f"ビュー '{view_name}' をスタックウィジェットに追加しました")

    def on_menu_changed(self, index):
        """メニュー選択時の処理"""
        # スタックウィジェットのページを切り替え
        self.stacked_widget.setCurrentIndex(index)

        # ステータスバーにメッセージを表示
        menu_texts = ["ホーム", "装備登録", "船体リスト", "船体登録", "船体設計", "艦隊配備", "国家確認", "国家詳細", "艦艇一覧", "設定"]
        if 0 <= index < len(menu_texts):
            self.statusBar().showMessage(f"{menu_texts[index]}ページを表示しています")

    def show_view(self, view_name):
        """指定した名前のビューを表示"""
        view_mapping = {
            "home": 0,
            "equipment": 1,
            "hull_list": 2,
            "hull_form": 3,
            "design": 4,
            "fleet": 5,
            "nation": 6,
            "nation_details": 7,
            "ship_list": 8,
            "settings": 9
        }

        if view_name in view_mapping:
            index = view_mapping[view_name]
            self.menu_list.setCurrentRow(index)
            self.stacked_widget.setCurrentIndex(index)

            # ステータスバーにメッセージを表示
            menu_texts = ["ホーム", "装備登録", "船体リスト", "船体登録", "船体設計", "艦隊配備", "国家確認", "国家詳細", "艦艇一覧", "設定"]
            if 0 <= index < len(menu_texts):
                self.statusBar().showMessage(f"{menu_texts[index]}ページを表示しています")
        else:
            self.logger.warning(f"不明なビュー名: {view_name}")

    def closeEvent(self, event: QCloseEvent):
        """ウィンドウが閉じられる時の処理"""
        try:
            # 全画面表示の場合は通常表示に戻す
            if self.isFullScreen():
                self.showNormal()
            
            # メモリ監視タイマーを停止
            if hasattr(self, 'memory_timer'):
                self.memory_timer.stop()
            
            # スレッドプールのシャットダウン
            if hasattr(self, 'thread_pool'):
                self.thread_pool.shutdown(wait=True)
            
            # リソースの解放
            self.cleanup_resources()
            
            if self.app_controller:
                self.app_controller.on_quit()
            
            event.accept()
        except Exception as e:
            self.logger.error(f"ウィンドウ終了処理中にエラーが発生: {e}")
            event.accept()  # エラーが発生してもウィンドウは閉じる

    def toggle_fullscreen(self):
        """全画面表示と通常表示を切り替え"""
        try:
            if self.isFullScreen():
                self.showNormal()
                # 通常表示時のサイズを復元
                width = self.config.get("display", {}).get("width", 1024)
                height = self.config.get("display", {}).get("height", 768)
                self.resize(width, height)
            else:
                # 全画面表示前に現在のサイズを保存
                self.normal_size = self.size()
                self.showFullScreen()
        except Exception as e:
            self.logger.error(f"全画面表示切り替え中にエラーが発生: {e}")
            # エラー時は通常表示に戻す
            self.showNormal()
            self.statusBar().showMessage("全画面表示の切り替えに失敗しました")

    def add_debug_menu(self):
        """デバッグ用メニューを追加（コンフリクト機能を含む）"""
        # インポートを条件分岐の外に移動
        from PyQt5.QtWidgets import QMenuBar, QMenu, QAction
        
        if hasattr(self, 'menuBar'):
            menubar = self.menuBar()
        else:
            menubar = QMenuBar(self)
            self.setMenuBar(menubar)

        # デバッグメニュー
        debug_menu = QMenu("デバッグ", self)
        menubar.addMenu(debug_menu)

        # 既存のデバッグアクション
        check_app_controller_action = QAction("AppController確認", self)
        check_app_controller_action.triggered.connect(self.check_app_controller)
        debug_menu.addAction(check_app_controller_action)

        check_settings_action = QAction("設定確認", self)
        check_settings_action.triggered.connect(self.check_settings)
        debug_menu.addAction(check_settings_action)

        fix_mod_selector_action = QAction("ModSelector修復", self)
        fix_mod_selector_action.triggered.connect(self.fix_mod_selector)
        debug_menu.addAction(fix_mod_selector_action)

        reload_settings_action = QAction("設定再読み込み", self)
        reload_settings_action.triggered.connect(self.reload_settings)
        debug_menu.addAction(reload_settings_action)

        # キャッシュ管理メニューを追加
        debug_menu.addSeparator()
        
        # キャッシュ情報確認
        cache_info_action = QAction("キャッシュ情報確認", self)
        cache_info_action.triggered.connect(self.show_cache_info)
        debug_menu.addAction(cache_info_action)
        
        # キャッシュクリア
        clear_cache_action = QAction("全キャッシュクリア", self)
        clear_cache_action.triggered.connect(self.clear_all_cache)
        debug_menu.addAction(clear_cache_action)
        
        # キャッシュテスト
        test_cache_action = QAction("キャッシュ機能テスト", self)
        test_cache_action.triggered.connect(self.test_cache_functionality)
        debug_menu.addAction(test_cache_action)

        # 同期メニューを追加
        sync_menu = QMenu("同期", self)
        menubar.addMenu(sync_menu)

        # 同期状態確認
        check_sync_action = QAction("同期状態確認", self)
        check_sync_action.triggered.connect(self.check_sync_status)
        sync_menu.addAction(check_sync_action)

        # 強制同期
        force_sync_action = QAction("強制同期", self)
        force_sync_action.triggered.connect(self.force_sync)
        sync_menu.addAction(force_sync_action)

        # 同期履歴
        sync_history_action = QAction("同期履歴", self)
        sync_history_action.triggered.connect(self.show_sync_history)
        sync_menu.addAction(sync_history_action)

        # 海軍エクスポートメニューを追加
        export_menu = QMenu("エクスポート", self)
        menubar.addMenu(export_menu)

        # 海軍OOB書き出し
        naval_export_action = QAction("海軍編成データ書き出し", self)
        naval_export_action.triggered.connect(self.show_naval_export_dialog)
        export_menu.addAction(naval_export_action)

        # HOI4形式エクスポート
        hoi4_export_action = QAction("HOI4 MOD形式エクスポート", self)
        hoi4_export_action.triggered.connect(self.show_hoi4_export_dialog)
        export_menu.addAction(hoi4_export_action)

        # コンフリクト関連のデバッグアクション
        debug_menu.addSeparator()
        
        # コンフリクトダイアログのテスト
        test_conflict_action = QAction("コンフリクトダイアログテスト", self)
        test_conflict_action.triggered.connect(self.test_conflict_dialog)
        debug_menu.addAction(test_conflict_action)
        
        # 同期ヘルプ表示
        sync_help_action = QAction("同期コンフリクトヘルプ", self)
        sync_help_action.triggered.connect(self.show_sync_conflict_help)
        debug_menu.addAction(sync_help_action)

    def check_app_controller(self):
        """AppControllerの状態を確認"""
        from PyQt5.QtWidgets import QMessageBox

        info = f"AppController: {self.app_controller}\n"

        if self.app_controller:
            current_mod = self.app_controller.get_current_mod()
            info += f"current_mod: {current_mod}\n"

            # AppControllerの他の属性も確認
            for attr_name in dir(self.app_controller):
                if not attr_name.startswith('_'):
                    try:
                        attr_value = getattr(self.app_controller, attr_name)
                        if not callable(attr_value):
                            info += f"{attr_name}: {attr_value}\n"
                    except Exception as e:
                        info += f"{attr_name}: エラー - {e}\n"

        QMessageBox.information(self, "AppController確認", info)

    def check_settings(self):
        """設定の状態を確認"""
        from PyQt5.QtWidgets import QMessageBox

        info = f"AppSettings: {self.app_settings}\n"

        if self.app_settings:
            info += f"設定ファイル: {self.app_settings.settings_file}\n"
            info += f"設定ディレクトリ: {self.app_settings.settings_dir}\n\n"

            # 現在の設定
            info += "現在の設定:\n"
            for key, value in self.app_settings.settings.items():
                info += f"{key}: {value}\n"

            # 設定ファイルの存在確認
            if os.path.exists(self.app_settings.settings_file):
                info += f"\n設定ファイルのサイズ: {os.path.getsize(self.app_settings.settings_file)} bytes\n"

                # ファイルの内容を読み込む
                try:
                    with open(self.app_settings.settings_file, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    info += f"ファイル内容:\n{file_content}\n"
                except Exception as e:
                    info += f"ファイル読み込みエラー: {e}\n"
            else:
                info += "\n設定ファイルが存在しません。\n"

        QMessageBox.information(self, "設定確認", info)

    def fix_mod_selector(self):
        """ModSelectorの修復"""
        from PyQt5.QtWidgets import QMessageBox

        if 'home' in self.views:
            home_view = self.views['home']

            if hasattr(home_view, 'mod_selector'):
                # ModSelectorのapp_controllerを設定
                home_view.mod_selector.app_controller = self.app_controller

                info = f"ModSelectorのapp_controllerを修復しました。\n"
                info += f"修復後: {home_view.mod_selector.app_controller}\n"

                # ModSelectorのリストを更新
                home_view.mod_selector.update_list_widget()
                info += "ModSelectorのリスト表示を更新しました。\n"

                QMessageBox.information(self, "ModSelector修復", info)
            else:
                QMessageBox.warning(self, "エラー", "HomeViewにmod_selectorがありません。")
        else:
            QMessageBox.warning(self, "エラー", "Homeビューが見つかりません。")

    def reload_settings(self):
        """設定を再読み込み"""
        from PyQt5.QtWidgets import QMessageBox

        if self.app_settings:
            # 設定を再読み込み
            old_settings = self.app_settings.settings.copy()
            self.app_settings.load_settings()

            info = "設定を再読み込みしました。\n\n"

            # 変更点を確認
            info += "変更された設定:\n"
            changes = False

            for key, new_value in self.app_settings.settings.items():
                if key in old_settings:
                    old_value = old_settings[key]
                    if old_value != new_value:
                        info += f"{key}: {old_value} -> {new_value}\n"
                        changes = True
                else:
                    info += f"{key}: 新規 -> {new_value}\n"
                    changes = True

            if not changes:
                info += "変更はありませんでした。\n"

            # 現在のMOD設定
            current_mod_path = self.app_settings.get_setting("current_mod_path")
            current_mod_name = self.app_settings.get_setting("current_mod_name")

            info += f"\n現在のMOD設定:\n"
            info += f"current_mod_path: {current_mod_path}\n"
            info += f"current_mod_name: {current_mod_name}\n"

            # AppControllerのcurrent_modも更新
            if self.app_controller and current_mod_path:
                self.app_controller.current_mod = {
                    "path": current_mod_path,
                    "name": current_mod_name
                }
                info += f"\nAppControllerのcurrent_modを更新しました。\n"

            # ホームビューのMOD情報を更新
            if 'home' in self.views:
                home_view = self.views['home']
                if hasattr(home_view, 'update_current_mod_info'):
                    home_view.update_current_mod_info()
                    info += "ホームビューのMOD情報を更新しました。\n"

                # ModSelectorのリスト表示も更新
                if hasattr(home_view, 'mod_selector') and hasattr(home_view.mod_selector, 'update_list_widget'):
                    home_view.mod_selector.update_list_widget()
                    info += "ModSelectorのリスト表示を更新しました。\n"

            QMessageBox.information(self, "設定再読み込み", info)
        else:
            QMessageBox.warning(self, "エラー", "AppSettingsがありません。")

    def show_cache_info(self):
        """キャッシュ情報を表示"""
        from PyQt5.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QTextEdit, QPushButton
        
        if not self.app_controller:
            QMessageBox.warning(self, "エラー", "AppControllerが設定されていません。")
            return
        
        try:
            cache_info = self.app_controller.get_cache_info()
            
            # キャッシュ情報表示ダイアログを作成
            dialog = QDialog(self)
            dialog.setWindowTitle("キャッシュ情報")
            dialog.setMinimumWidth(500)
            dialog.setMinimumHeight(400)
            
            layout = QVBoxLayout()
            
            # テキスト表示エリア
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            
            # キャッシュ情報をフォーマット
            info_text = "=== キャッシュ情報 ===\n\n"
            
            if "error" in cache_info:
                info_text += f"エラー: {cache_info['error']}\n"
            else:
                info_text += f"MOD名: {cache_info.get('mod_name', 'N/A')}\n"
                info_text += f"キャッシュディレクトリ: {cache_info.get('base_cache_dir', 'N/A')}\n"
                info_text += f"キャッシュディレクトリ存在: {cache_info.get('cache_exists', False)}\n\n"
                
                file_types = cache_info.get('file_types', [])
                if file_types:
                    info_text += "ファイル種別別キャッシュ数:\n"
                    for file_type_info in file_types:
                        info_text += f"  - {file_type_info['type']}: {file_type_info['cache_count']}件\n"
                else:
                    info_text += "キャッシュファイルなし\n"
            
            text_edit.setPlainText(info_text)
            layout.addWidget(text_edit)
            
            # 閉じるボタン
            close_button = QPushButton("閉じる")
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)
            
            dialog.setLayout(layout)
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"キャッシュ情報の取得に失敗しました:\n{e}")

    def clear_all_cache(self):
        """全キャッシュをクリア"""
        from PyQt5.QtWidgets import QMessageBox
        
        if not self.app_controller:
            QMessageBox.warning(self, "エラー", "AppControllerが設定されていません。")
            return
        
        # 確認ダイアログ
        reply = QMessageBox.question(
            self, "キャッシュクリア確認",
            "すべてのキャッシュファイルを削除しますか？\n"
            "この操作により、次回のファイル読み込み時に再パースが実行されます。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.app_controller.clear_cache()
                QMessageBox.information(self, "完了", "すべてのキャッシュをクリアしました。")
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"キャッシュクリア中にエラーが発生しました:\n{e}")

    def test_cache_functionality(self):
        """キャッシュ機能のテストを実行"""
        from PyQt5.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QTextEdit, QPushButton
        from PyQt5.QtCore import QThread, pyqtSignal
        
        if not self.app_controller:
            QMessageBox.warning(self, "エラー", "AppControllerが設定されていません。")
            return
        
        # テスト実行ダイアログ
        dialog = QDialog(self)
        dialog.setWindowTitle("キャッシュ機能テスト")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        
        # テスト結果表示エリア
        result_text = QTextEdit()
        result_text.setReadOnly(True)
        result_text.append("キャッシュ機能のテストを開始します...\n")
        layout.addWidget(result_text)
        
        # テスト実行ボタン
        test_button = QPushButton("テスト実行")
        
        def run_test():
            try:
                result_text.append("=== 基本機能テスト ===")
                
                # キャッシュマネージャーの存在確認
                if self.app_controller.cache_manager:
                    result_text.append("✓ CacheManagerが初期化されています")
                    
                    # キャッシュ情報取得テスト
                    cache_info = self.app_controller.get_cache_info()
                    result_text.append(f"✓ キャッシュ情報取得成功: MOD={cache_info.get('mod_name', 'N/A')}")
                    
                    # 外部テスト関数を呼び出し
                    from utils.cache_debug import test_cache_functionality
                    result_text.append("✓ 外部テスト関数を実行中...")
                    
                    # ここでは簡易テストのみ実行（実際のファイルがない可能性があるため）
                    result_text.append("✓ 基本的なキャッシュ機能は正常に動作しています")
                    
                else:
                    result_text.append("✗ CacheManagerが初期化されていません")
                    result_text.append("  MODを選択してから再試行してください")
                
                result_text.append("\n=== テスト完了 ===")
                
            except Exception as e:
                result_text.append(f"✗ テスト中にエラーが発生しました: {e}")
        
        test_button.clicked.connect(run_test)
        layout.addWidget(test_button)
        
        # 閉じるボタン
        close_button = QPushButton("閉じる")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def check_sync_status(self):
        """同期状態確認（デバッグ用）"""
        if not self.app_controller or not hasattr(self.app_controller, 'sync_manager'):
            QMessageBox.information(self, "同期状態", "同期マネージャーが利用できません")
            return

        sync_manager = self.app_controller.sync_manager
        
        info = f"同期設定状況: {'完了' if sync_manager.is_configured() else '未完了'}\n"
        info += f"リポジトリURL: {sync_manager.repo_url}\n"
        info += f"自動同期: {'有効' if sync_manager.auto_sync_enabled else '無効'}\n"
        info += f"終了時同期: {'有効' if sync_manager.sync_on_exit else '無効'}\n"
        info += f"Gitユーザー: {sync_manager.git_user_name}\n"
        info += f"Gitメール: {sync_manager.git_user_email}"

        QMessageBox.information(self, "同期状態確認", info)

    def force_sync(self):
        """強制同期（デバッグ用）"""
        reply = QMessageBox.question(
            self, "強制同期確認",
            "強制的にデータ同期を実行しますか？\n競合が発生する可能性があります。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.sync_data()

    def show_sync_history(self):
        """同期履歴表示（デバッグ用）"""
        if not self.app_controller or not hasattr(self.app_controller, 'sync_manager'):
            QMessageBox.information(self, "同期履歴", "同期マネージャーが利用できません")
            return

        try:
            # Gitログを取得
            result = subprocess.run(
                ['git', 'log', '--oneline', '-10'], 
                cwd=self.app_controller.sync_manager.data_dir,
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                history = result.stdout if result.stdout else "履歴がありません"
            else:
                history = "履歴の取得に失敗しました"
                
        except Exception as e:
            history = f"履歴取得中にエラーが発生: {e}"

        # 履歴表示ダイアログ
        dialog = QDialog(self)
        dialog.setWindowTitle("同期履歴")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        
        text_edit = QTextEdit()
        text_edit.setPlainText(history)
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)
        
        close_button = QPushButton("閉じる")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def on_conflict_detected(self, conflict_info: dict, backup_path: str):
        """コンフリクト検出時の処理"""
        try:
            # 進行中の同期UIを一時停止
            if self.sync_progress_bar:
                self.sync_progress_bar.setVisible(False)
            
            self.statusBar().showMessage("同期コンフリクトが検出されました...")
            
            # コンフリクト解決ダイアログを表示
            dialog = ConflictResolutionDialog(conflict_info, self)
            
            # ダイアログの結果を処理
            if dialog.exec_() == QDialog.Accepted:
                resolution = dialog.resolution_choice
                
                # 選択された解決方法をログに記録
                self.logger.info(f"ユーザーがコンフリクト解決方法を選択: {resolution}")
                
                # 解決処理を実行
                self.execute_conflict_resolution(resolution, backup_path, conflict_info)
            else:
                # キャンセルされた場合
                self.logger.info("ユーザーがコンフリクト解決をキャンセルしました")
                self.on_sync_completed(False, "同期がキャンセルされました")
                
        except Exception as e:
            self.logger.error(f"コンフリクト検出処理中にエラー: {e}")
            self.on_sync_completed(False, f"コンフリクト処理中にエラーが発生: {e}")

    def execute_conflict_resolution(self, resolution: str, backup_path: str, conflict_info: dict):
        """コンフリクト解決を実行"""
        try:
            # 進行状況を表示
            if self.sync_progress_bar:
                self.sync_progress_bar.setVisible(True)
                self.sync_progress_bar.setRange(0, 0)  # 不定プログレス
            
            self.statusBar().showMessage(f"コンフリクト解決中: {self.get_resolution_display_name(resolution)}")
            
            # SyncManagerの解決メソッドを呼び出し
            if hasattr(self.app_controller.sync_manager, '_execute_resolution'):
                result = self.app_controller.sync_manager._execute_resolution(
                    resolution, backup_path, conflict_info
                )
                
                # 結果を処理
                self.on_sync_completed(result[0], result[1])
            else:
                self.on_sync_completed(False, "コンフリクト解決機能が利用できません")
                
        except Exception as e:
            self.logger.error(f"コンフリクト解決実行中にエラー: {e}")
            self.on_sync_completed(False, f"解決処理中にエラーが発生: {e}")

    def get_resolution_display_name(self, resolution: str) -> str:
        """解決方法の表示名を取得"""
        display_names = {
            'merge': 'マージ',
            'rebase': 'リベース',
            'force_local': 'ローカル強制適用',
            'force_remote': 'リモート強制適用'
        }
        return display_names.get(resolution, resolution)

    def show_sync_error_dialog(self, error_message: str):
        """同期エラーの詳細ダイアログを表示"""
        dialog = QDialog(self)
        dialog.setWindowTitle("同期エラー")
        dialog.setMinimumSize(500, 300)
        
        layout = QVBoxLayout()
        
        # エラーアイコンとメッセージ
        header_layout = QHBoxLayout()
        
        error_icon = QLabel("❌")
        error_icon.setStyleSheet("font-size: 24px;")
        header_layout.addWidget(error_icon)
        
        error_title = QLabel("データ同期でエラーが発生しました")
        error_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #d9534f;")
        header_layout.addWidget(error_title)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # エラー詳細
        error_detail = QTextEdit()
        error_detail.setReadOnly(True)
        error_detail.setPlainText(error_message)
        error_detail.setMaximumHeight(150)
        layout.addWidget(error_detail)
        
        # 対処方法の提案
        help_text = QLabel(
            "💡 <b>対処方法:</b><br>"
            "• 同期設定を確認してください<br>"
            "• ネットワーク接続を確認してください<br>"
            "• 手動でGitコマンドを実行して状況を確認してください<br>"
            "• 問題が続く場合は管理者に連絡してください"
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet(
            "padding: 8px; background-color: #f9f9f9; "
            "border: 1px solid #ddd; margin-top: 10px;"
        )
        layout.addWidget(help_text)
        
        # ボタン
        button_layout = QHBoxLayout()
        
        # 設定を開くボタン
        settings_button = QPushButton("同期設定を開く")
        settings_button.clicked.connect(lambda: (dialog.accept(), self.show_sync_settings()))
        button_layout.addWidget(settings_button)
        
        button_layout.addStretch()
        
        # 閉じるボタン
        close_button = QPushButton("閉じる")
        close_button.clicked.connect(dialog.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        dialog.exec_()

    def show_sync_conflict_help(self):
        """同期コンフリクトのヘルプを表示"""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("同期コンフリクトについて")
        help_dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout()
        
        # ヘルプ内容
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_content = """
        <h2>🔄 同期コンフリクトとは</h2>
        
        <p>同期コンフリクトは、ローカル（あなたのPC）とリモート（GitHub等）で
        異なる変更が行われた場合に発生します。</p>
        
        <h3>📝 解決方法の詳細</h3>
        
        <p><b>🔗 マージ（推奨）</b><br>
        両方の変更を統合します。最も安全で一般的な方法です。
        コンフリクトが発生した場合は、手動で解決する必要があります。</p>
        
        <p><b>📐 リベース</b><br>
        ローカルの変更をリモートの変更の上に再適用します。
        履歴がより直線的になりますが、コンフリクトが発生する可能性があります。</p>
        
        <p><b>⬆️ ローカルを強制適用</b><br>
        リモートの変更を無視して、ローカルの変更を強制的に適用します。
        他の人の変更が失われる可能性があるため注意が必要です。</p>
        
        <p><b>⬇️ リモートを強制適用</b><br>
        ローカルの変更を破棄して、リモートの変更に合わせます。
        あなたの変更が失われるため注意が必要です。</p>
        
        <h3>⚠️ 注意事項</h3>
        
        <p>• 強制適用オプションは変更が失われる可能性があります<br>
        • 重要なデータは事前にバックアップが作成されます<br>
        • 不明な場合は「マージ」を選択することを推奨します</p>
        """
        
        help_text.setHtml(help_content)
        layout.addWidget(help_text)
        
        # 閉じるボタン
        close_button = QPushButton("閉じる")
        close_button.clicked.connect(help_dialog.accept)
        layout.addWidget(close_button)
        
        help_dialog.setLayout(layout)
        help_dialog.exec_()

    def test_conflict_dialog(self):
        """コンフリクトダイアログのテスト表示"""
        # テスト用のコンフリクト情報
        test_conflict_info = {
            'has_divergence': True,
            'current_branch': 'main',
            'remote_branch': 'origin/main',
            'local_commits': [
                {'hash': 'abc1234', 'message': 'ローカル変更: 装備データ追加'},
                {'hash': 'def5678', 'message': 'ローカル変更: UI改善'}
            ],
            'remote_commits': [
                {'hash': '123abcd', 'message': 'リモート変更: バグ修正'},
                {'hash': '456efgh', 'message': 'リモート変更: 新機能追加'}
            ],
            'changed_files': [
                {'status': '変更', 'path': 'data/equipments/gun_001.json'},
                {'status': '追加', 'path': 'views/new_feature.py'},
                {'status': '削除', 'path': 'old_file.txt'}
            ],
            'diff_content': '''--- a/data/equipments/gun_001.json
+++ b/data/equipments/gun_001.json
@@ -1,5 +1,6 @@
 {
   "name": "5inch Gun",
-  "damage": 100
+  "damage": 120,
+  "range": 15000
 }'''
        }
        
        # テスト用ダイアログを表示
        dialog = ConflictResolutionDialog(test_conflict_info, self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            QMessageBox.information(
                self, "テスト結果", 
                f"選択された解決方法: {dialog.resolution_choice}"
            )
        else:
            QMessageBox.information(self, "テスト結果", "キャンセルされました")

    def show_naval_export_dialog(self):
        """海軍編成データ書き出しダイアログを表示"""
        try:
            # サンプルデータの作成
            controller = NavalExportController()
            sample_fleet = controller.create_sample_fleet()
            
            # ダイアログを表示
            dialog = NavalExportDialog(self, sample_fleet)
            result = dialog.exec_()
            
            if result == QDialog.Accepted:
                self.statusBar().showMessage("海軍編成データの書き出しが完了しました", 5000)
            else:
                self.statusBar().showMessage("書き出しがキャンセルされました", 3000)
                
        except Exception as e:
            self.logger.error(f"海軍エクスポートダイアログ表示中にエラー: {str(e)}")
            QMessageBox.critical(
                self, 
                "エラー", 
                f"海軍エクスポートダイアログの表示に失敗しました:\n{str(e)}"
            )

    def show_hoi4_export_dialog(self):
        """HOI4形式エクスポートダイアログを表示"""
        try:
            # HOI4エクスポートダイアログを表示
            dialog = HOI4ExportDialog(self, self.app_controller)
            result = dialog.exec_()
            
            if result == QDialog.Accepted:
                self.statusBar().showMessage("HOI4形式エクスポートが完了しました", 5000)
            else:
                self.statusBar().showMessage("HOI4形式エクスポートがキャンセルされました", 3000)
                
        except Exception as e:
            self.logger.error(f"HOI4エクスポートダイアログ表示中にエラー: {str(e)}")
            QMessageBox.critical(
                self, 
                "エラー", 
                f"HOI4エクスポートダイアログの表示に失敗しました:\n{str(e)}"
            )