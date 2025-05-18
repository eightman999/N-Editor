from PyQt5.QtWidgets import QWidget, QProgressDialog, QLabel, QVBoxLayout, QTextEdit
from PyQt5.QtGui import QPainter, QColor, QPen, QPixmap, QImage
from PyQt5.QtCore import Qt, QPoint, QRect, QTimer, pyqtSignal
from .map_data import MapData
import os
import logging
import numpy as np
from PIL import Image
import psutil
import gc
import time
import threading
from pathlib import Path
import sys

class MapWidget(QWidget):
    # シグナルの定義
    loading_progress = pyqtSignal(int, str)  # 進捗率とメッセージ
    loading_complete = pyqtSignal()
    loading_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.map_data = MapData()
        self.zoom_level = 1.0
        self.offset = QPoint(0, 0)
        self.dragging = False
        self.last_pos = None
        self.province_image = None
        self.cached_pixmap = None
        self.setMouseTracking(True)
        self.loading_worker = None
        self.progress_dialog = None
        self.status_label = None
        self.detail_text = None
        
        # ロガーの設定
        self.logger = logging.getLogger('MapWidget')
        self.logger.setLevel(logging.DEBUG)
        
        # 既存のハンドラをクリア
        self.logger.handlers.clear()
        
        # ログディレクトリの作成
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # ファイルハンドラの設定（日付ごとにログファイルを分割）
        current_time = time.strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f"map_widget_{current_time}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # コンソールハンドラの設定
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # フォーマッタの設定
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # ハンドラの追加
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # プロセスの情報を取得
        self.process = psutil.Process()
        
        # システム情報のログ出力
        self.logger.info(f"Pythonバージョン: {sys.version}")
        self.logger.info(f"NumPyバージョン: {np.__version__}")
        self.logger.info(f"PILバージョン: {Image.__version__}")
        self.logger.info(f"CPUコア数: {os.cpu_count()}")
        self.logger.info(f"メモリ情報: {psutil.virtual_memory()}")
        
        # シグナルの接続
        self.loading_progress.connect(self.update_progress)
        self.loading_complete.connect(self.on_loading_complete)
        self.loading_error.connect(self.on_loading_error)
        self.map_data.detailed_progress.connect(self.update_detailed_progress)
        
        # メモリ使用量の初期値を記録
        self._log_memory_usage("初期化完了")
        self.logger.info("MapWidgetの初期化が完了しました")

    def _log_memory_usage(self, context=""):
        """メモリ使用量をログに記録"""
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        cpu_percent = self.process.cpu_percent()
        
        extra = {
            'memory_usage': f"{memory_mb:.1f}",
            'cpu_percent': f"{cpu_percent:.1f}",
            'thread_name': threading.current_thread().name
        }
        
        self.logger.info(f"メモリ使用量: {context}", extra=extra)

    def create_progress_dialog(self):
        """プログレスダイアログを作成"""
        self.logger.info("プログレスダイアログを作成")
        self._log_memory_usage("ダイアログ作成前")
        
        self.progress_dialog = QProgressDialog(self)
        self.progress_dialog.setWindowTitle("マップデータ読み込み")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setCancelButtonText("キャンセル")
        self.progress_dialog.canceled.connect(self.cancel_loading)
        
        # メインレイアウト
        main_layout = QVBoxLayout()
        
        # プログレスバーをレイアウトに追加
        main_layout.addWidget(self.progress_dialog)
        
        # ステータスラベルの追加
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        main_layout.addWidget(self.status_label)
        
        # 詳細な進捗状況を表示するテキストエリア
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMaximumHeight(150)
        main_layout.addWidget(self.detail_text)
        
        # レイアウトをダイアログに設定
        self.progress_dialog.setLayout(main_layout)
        
        self.progress_dialog.show()
        self._log_memory_usage("ダイアログ作成後")

    def cancel_loading(self):
        """読み込みをキャンセル"""
        if self.map_data:
            self.map_data.cancel_loading()
            self.status_label.setText("読み込みをキャンセルしています...")
            self.logger.info("マップデータの読み込みをキャンセルしました")

    def update_detailed_progress(self, message):
        """詳細な進捗状況を更新"""
        if self.detail_text:
            self.detail_text.append(message)
            # 最新のメッセージが見えるようにスクロール
            self.detail_text.verticalScrollBar().setValue(
                self.detail_text.verticalScrollBar().maximum()
            )

    def load_map_data(self, mod_path):
        """マップデータを非同期で読み込む"""
        self.logger.info(f"マップデータの読み込みを開始: {mod_path}")
        self.logger.debug(f"現在のズームレベル: {self.zoom_level}")
        self.logger.debug(f"現在のオフセット: {self.offset}")
        self._log_memory_usage("読み込み開始")
        
        # プログレスダイアログの作成
        self.create_progress_dialog()
        self.update_progress(0, "プロヴィンス画像を読み込み中...")
        
        # プロヴィンス画像の読み込みと最適化
        self.logger.info("プロヴィンス画像を読み込み中...")
        try:
            self._log_memory_usage("画像読み込み前")
            
            # PILを使用して画像を読み込み
            image_path = os.path.join(mod_path, 'map', 'provinces.bmp')
            self.logger.info(f"画像ファイルパス: {image_path}")
            
            with Image.open(image_path) as img:
                self.logger.info(f"元画像サイズ: {img.size}")
                # 画像をNumPy配列に変換
                img_array = np.array(img)
                
                # 画像を最適化（サイズを調整）
                max_size = 2048  # 最大サイズを制限
                if img_array.shape[0] > max_size or img_array.shape[1] > max_size:
                    scale = max_size / max(img_array.shape[0], img_array.shape[1])
                    new_size = (int(img_array.shape[1] * scale), int(img_array.shape[0] * scale))
                    self.logger.info(f"画像をリサイズ: {img.size} -> {new_size}")
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    img_array = np.array(img)
                
                self._log_memory_usage("画像読み込み後")
                
                # NumPy配列をQImageに変換
                height, width = img_array.shape[:2]
                bytes_per_line = 3 * width
                q_image = QImage(img_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
                
                # QPixmapに変換
                self.province_image = QPixmap.fromImage(q_image)
                self.logger.info(f"QPixmapサイズ: {self.province_image.size()}")
                
                # キャッシュ用のQPixmapを作成
                self.cached_pixmap = QPixmap(self.province_image.size())
                self.cached_pixmap.fill(Qt.transparent)
                
                # キャッシュの描画
                self.update_cache()
                
                self._log_memory_usage("キャッシュ作成後")
                
        except Exception as e:
            self.logger.error(f"プロヴィンス画像の読み込みに失敗: {e}", exc_info=True)
            self.progress_dialog.close()
            self.loading_error.emit(f"プロヴィンス画像の読み込みに失敗しました: {e}")
            return
            
        self.logger.info(f"プロヴィンス画像の読み込み完了: {self.province_image.width()}x{self.province_image.height()}")
        self.update_progress(20, "プロヴィンス定義を読み込み中...")
        
        # 非同期読み込みの開始
        self.logger.info("MapDataの非同期読み込みを開始")
        self.loading_worker = self.map_data.start_loading(mod_path)
        
        # タイマーで読み込み状態を監視
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_loading_status)
        self.check_timer.start(100)  # 100ミリ秒ごとにチェック
        self.logger.info("読み込み状態の監視を開始")

    def update_cache(self):
        """マップのキャッシュを更新"""
        if not self.province_image or not self.cached_pixmap:
            return
            
        self.logger.info("キャッシュの更新を開始")
        self._log_memory_usage("キャッシュ更新前")
        
        try:
            # キャッシュ用のQPixmapを作成（必要に応じて）
            if self.cached_pixmap.size() != self.province_image.size():
                self.cached_pixmap = QPixmap(self.province_image.size())
                self.cached_pixmap.fill(Qt.transparent)
            
            painter = QPainter(self.cached_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            
            # プロヴィンス画像の描画
            painter.drawPixmap(0, 0, self.province_image)
            
            # ステートの境界線と海軍基地の描画を最適化
            if self.map_data.states:
                # 境界線の描画をバッチ処理
                for state_id, (name, provinces, owner) in self.map_data.states.items():
                    if owner:
                        color = self.map_data.get_country_color(owner)
                        pen = QPen(QColor(*color), 2)
                        painter.setPen(pen)
                        
                        # プロヴィンスの境界を描画
                        for i, prov_id in enumerate(provinces):
                            if i < len(provinces) - 1:
                                next_prov_id = provinces[i + 1]
                                coords1 = self.map_data.get_province_coordinates(prov_id)
                                coords2 = self.map_data.get_province_coordinates(next_prov_id)
                                
                                if coords1 and coords2:
                                    # 最も近い座標ペアを見つける
                                    coords1_array = np.array(coords1)
                                    coords2_array = np.array(coords2)
                                    
                                    # 距離行列を計算（メモリ効率を考慮）
                                    chunk_size = 1000
                                    min_dist = float('inf')
                                    best_pair = None
                                    
                                    for i in range(0, len(coords1_array), chunk_size):
                                        chunk1 = coords1_array[i:i + chunk_size]
                                        for j in range(0, len(coords2_array), chunk_size):
                                            chunk2 = coords2_array[j:j + chunk_size]
                                            dist_matrix = np.sum((chunk1[:, np.newaxis] - chunk2) ** 2, axis=2)
                                            min_idx = np.unravel_index(np.argmin(dist_matrix), dist_matrix.shape)
                                            min_chunk_dist = dist_matrix[min_idx]
                                            
                                            if min_chunk_dist < min_dist:
                                                min_dist = min_chunk_dist
                                                best_pair = (
                                                    coords1[i + min_idx[0]],
                                                    coords2[j + min_idx[1]]
                                                )
                                    
                                    if best_pair:
                                        painter.drawLine(
                                            best_pair[0][0], best_pair[0][1],
                                            best_pair[1][0], best_pair[1][1]
                                        )
            
            # 海軍基地の描画を最適化
            if self.map_data.naval_bases:
                painter.setPen(QPen(Qt.red, 2))
                for prov_id, level in self.map_data.naval_bases.items():
                    if level > 0:
                        coords = self.map_data.get_province_coordinates(prov_id)
                        if coords:
                            coords_array = np.array(coords)
                            min_x, min_y = np.min(coords_array, axis=0)
                            max_x, max_y = np.max(coords_array, axis=0)
                            painter.drawRect(min_x, min_y, max_x - min_x, max_y - min_y)
            
            painter.end()
            
            self._log_memory_usage("キャッシュ更新後")
            self.logger.info("キャッシュの更新が完了")
            
        except Exception as e:
            self.logger.error(f"キャッシュの更新中にエラーが発生: {e}")
            self.loading_error.emit(str(e))
        finally:
            # メモリ解放
            gc.collect()

    def update_progress(self, value, message=""):
        """プログレスバーとステータスメッセージを更新"""
        if self.progress_dialog:
            self.progress_dialog.setValue(value)
            if self.status_label and message:
                self.status_label.setText(message)
                self.logger.info(message)
                self._log_memory_usage(f"進捗更新: {message}")

    def check_loading_status(self):
        """非同期読み込みの状態を確認"""
        if self.map_data.is_loading_complete():
            self.check_timer.stop()
            
            if self.map_data.get_loading_error():
                error_msg = str(self.map_data.get_loading_error())
                self.logger.error(f"マップデータの読み込み中にエラーが発生しました: {error_msg}")
                self.loading_error.emit(error_msg)
                return
                
            self.logger.info("マップデータの読み込みが完了しました")
            self._log_memory_usage("読み込み完了")
            self.loading_complete.emit()
            self.update()

    def on_loading_complete(self):
        """読み込み完了時の処理"""
        if self.progress_dialog:
            self.progress_dialog.close()
        self.statusBar().showMessage("マップデータの読み込みが完了しました")
        self._log_memory_usage("完了処理後")

    def on_loading_error(self, error_msg):
        """エラー発生時の処理"""
        if self.progress_dialog:
            self.progress_dialog.close()
        self.statusBar().showMessage(f"エラー: {error_msg}")
        self._log_memory_usage("エラー処理後")

    def paintEvent(self, event):
        if not self.cached_pixmap:
            return

        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)

            # ズームとオフセットを適用
            painter.translate(self.offset)
            painter.scale(self.zoom_level, self.zoom_level)

            # キャッシュされたピクスマップを描画
            painter.drawPixmap(0, 0, self.cached_pixmap)
            painter.end()
            
        except Exception as e:
            self.logger.error(f"描画中にエラーが発生: {e}")

    def wheelEvent(self, event):
        """マウスホイールでズーム"""
        factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        old_zoom = self.zoom_level
        self.zoom_level *= factor
        self.zoom_level = max(0.1, min(5.0, self.zoom_level))
        if old_zoom != self.zoom_level:
            self.logger.debug(f"ズームレベル変更: {old_zoom:.2f} -> {self.zoom_level:.2f}")
        self.update()

    def mousePressEvent(self, event):
        """マウスドラッグ開始"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.last_pos = event.pos()
            self.logger.debug("マウスドラッグ開始")

    def mouseReleaseEvent(self, event):
        """マウスドラッグ終了"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.logger.debug("マウスドラッグ終了")

    def mouseMoveEvent(self, event):
        """マウスドラッグ中"""
        if self.dragging and self.last_pos:
            delta = event.pos() - self.last_pos
            self.offset += delta
            self.last_pos = event.pos()
            self.logger.debug(f"マップ移動: {delta.x()}, {delta.y()}")
            self.update() 