from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel, QStatusBar, \
    QListWidget, QSizePolicy, QProgressDialog, QMessageBox
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QCloseEvent, QImage, QPixmap

import os
import json
import cv2
import numpy as np
import logging
from concurrent.futures import ThreadPoolExecutor
import psutil
import time

from views.home_view import HomeView
from views.equipment_view import EquipmentView
from views.hull_form import HullForm
from views.hull_list_view import HullListView
from views.design_view import DesignView
from views.fleet_view import FleetView
from views.settings_view import SettingsView
from views.nation_view import NationView
from views.nation_details_view import NationDetailsView

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
    """Naval Design Systemのメインウィンドウ"""

    def __init__(self, app_controller=None, app_settings=None):
        super().__init__()

        # コントローラーとアプリケーション設定
        self.app_controller = app_controller
        self.app_settings = app_settings

        # アプリケーションコントローラーの状態を確認
        print(f"NavalDesignSystem.__init__: app_controller = {self.app_controller}")

        # ビューマッピング
        self.views = {}

        # アプリケーション設定の読み込み
        self.load_config()

        # スレッドプールの初期化（ワーカー数を制限）
        self.thread_pool = ThreadPoolExecutor(max_workers=2)
        
        # メモリ管理用の変数
        self._memory_warning_threshold = 500  # MB
        self._memory_critical_threshold = 800  # MB
        self._last_cleanup_time = 0
        self._cleanup_interval = 60  # 秒
        
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

    def load_config(self):
        """設定ファイルを読み込む"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'config.json')

        # デフォルト設定
        self.config = {
            "app_name": "Naval Design System",
            "version": "β0.0.1",
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
        """UIの初期化"""
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

        # サイドバーメニュー
        self.create_sidebar(main_layout)

        # メインビュー
        self.create_main_view(main_layout)

        # ステータスバー
        self.statusBar().showMessage("準備完了")

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
        """緊急時のリソース解放"""
        try:
            self.logger.warning("緊急リソース解放を実行します")
            
            # スレッドプールのシャットダウン
            if hasattr(self, 'thread_pool'):
                self.thread_pool.shutdown(wait=False)
                self.thread_pool = ThreadPoolExecutor(max_workers=1)
            
            # すべてのビューのキャッシュをクリア
            if hasattr(self, 'views'):
                for view in self.views.values():
                    if hasattr(view, 'clear_cache'):
                        view.clear_cache()
                    if hasattr(view, 'clear_resources'):
                        view.clear_resources()
            
            # 画像キャッシュのクリア
            if hasattr(self, 'image_cache'):
                self.image_cache.clear()
            
            # ガベージコレクションの強制実行
            import gc
            gc.collect()
            
            # メモリ使用量の再確認
            import psutil
            import os
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_usage = memory_info.rss / 1024 / 1024
            self.logger.info(f"緊急クリーンアップ後のメモリ使用量: {memory_usage:.2f} MB")
            
        except Exception as e:
            self.logger.error(f"緊急リソース解放中にエラーが発生: {e}")

    def cleanup_resources(self):
        """不要なリソースの解放"""
        try:
            # キャッシュのクリア
            if hasattr(self, 'views'):
                for view in self.views.values():
                    if hasattr(view, 'clear_cache'):
                        view.clear_cache()
            
            # 画像キャッシュのクリア
            if hasattr(self, 'image_cache'):
                self.image_cache.clear()
            
            # 未使用のビューの解放
            current_view = self.stacked_widget.currentWidget()
            for view_name, view in list(self.views.items()):
                if view != current_view and hasattr(view, 'clear_resources'):
                    view.clear_resources()
            
            # ガベージコレクションの強制実行
            import gc
            gc.collect()
            
            self.logger.info("リソースの解放を実行しました")
        except Exception as e:
            self.logger.error(f"リソース解放中にエラーが発生: {e}")

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
        self.logger.info(f"ビュー '{view_name}' をスタックウィジェットに追加しました")

    def on_menu_changed(self, index):
        """メニュー選択時の処理"""
        # スタックウィジェットのページを切り替え
        self.stacked_widget.setCurrentIndex(index)

        # ステータスバーにメッセージを表示
        menu_texts = ["ホーム", "装備登録", "船体リスト", "船体登録", "船体設計", "艦隊配備", "国家確認", "国家詳細", "設定"]
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
            "settings": 8
        }

        if view_name in view_mapping:
            index = view_mapping[view_name]
            self.menu_list.setCurrentRow(index)
            self.stacked_widget.setCurrentIndex(index)

            # ステータスバーにメッセージを表示
            menu_texts = ["ホーム", "装備登録", "船体リスト", "船体登録", "船体設計", "艦隊配備", "国家確認", "国家詳細", "設定"]
            if 0 <= index < len(menu_texts):
                self.statusBar().showMessage(f"{menu_texts[index]}ページを表示しています")

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
        """デバッグ用メニューを追加"""
        from PyQt5.QtWidgets import QMenuBar, QMenu, QAction

        # メニューバーの作成
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        # デバッグメニュー
        debug_menu = QMenu("デバッグ", self)
        menubar.addMenu(debug_menu)

        # デバッグアクション
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