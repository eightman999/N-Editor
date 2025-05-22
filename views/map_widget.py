from PyQt5.QtWidgets import QWidget, QProgressDialog, QLabel, QVBoxLayout, QTextEdit, QScrollArea, QPushButton, \
    QHBoxLayout, QMessageBox
from PyQt5.QtGui import QPainter, QColor, QPen, QPixmap, QImage, QBrush, QPainterPath
from PyQt5.QtCore import Qt, QPoint, QRect, QSize, QTimer, pyqtSignal, QThread
import os
import logging
import numpy as np
from PIL import Image
import re
import csv
import time
import gc
import traceback
from scipy.spatial import ConvexHull

from views.map_data import MapData


class MapLoadingThread(QThread):
    """マップデータを非同期で読み込むためのスレッド"""
    
    progress_updated = pyqtSignal(int, str)
    loading_complete = pyqtSignal()
    loading_error = pyqtSignal(str)
    
    def __init__(self, map_data, mod_path):
        super().__init__()
        self.map_data = map_data
        self.mod_path = mod_path
    
    def run(self):
        try:
            # プロヴィンス定義の読み込み
            self.progress_updated.emit(10, "プロヴィンス定義を読み込み中...")
            self.map_data.load_province_definitions(os.path.join(self.mod_path, 'map', 'definition.csv'))
            
            # プロヴィンス画像の読み込みと座標抽出
            self.progress_updated.emit(30, "プロヴィンス画像を読み込み中...")
            self.map_data.load_province_coordinates(os.path.join(self.mod_path, 'map', 'provinces.bmp'))
            
            # ステート情報の読み込み
            self.progress_updated.emit(70, "ステート情報を読み込み中...")
            self.map_data.load_states(os.path.join(self.mod_path, 'history', 'states'))
            
            # 国家の色定義を読み込み
            self.progress_updated.emit(90, "国家の色定義を読み込み中...")
            self.map_data.load_country_colors(os.path.join(self.mod_path, 'common', 'countries', 'colors.txt'))
            
            self.progress_updated.emit(100, "読み込みが完了しました")
            self.loading_complete.emit()
            
        except Exception as e:
            self.loading_error.emit(str(e))


class MapWidget(QWidget):
    """マップを表示するウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 状態変数の初期化
        self.map_data = MapData()
        self.map_data.detailed_progress.connect(self.update_progress)
        self.zoom_level = 1.0
        self.offset = QPoint(0, 0)
        self.dragging = False
        self.last_pos = None
        self.province_image = None
        self.cached_pixmap = None
        
        # マウス追跡を有効化
        self.setMouseTracking(True)
        
        # ウィジェットの最小サイズを設定
        self.setMinimumSize(800, 600)
        
        # ロガーの設定
        self.logger = logging.getLogger('MapWidget')
        self.logger.setLevel(logging.DEBUG)
        
        # ファイルハンドラの設定
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(log_dir, f"map_widget_{time.strftime('%Y%m%d_%H%M%S')}.log"))
        file_handler.setLevel(logging.DEBUG)
        
        # コンソールハンドラの設定
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # フォーマッタの設定
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # ハンドラの追加
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info("MapWidgetの初期化が完了しました")
    
    def load_map_data(self, mod_path):
        """マップデータを非同期で読み込む"""
        self.logger.info(f"マップデータの読み込みを開始: {mod_path}")
        
        # プログレスダイアログの作成
        self.progress_dialog = QProgressDialog("マップデータ読み込み中...", "キャンセル", 0, 100, self)
        self.progress_dialog.setWindowTitle("マップデータ読み込み")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.canceled.connect(self.cancel_loading)
        self.progress_dialog.show()
        
        # 詳細なログを表示するためのテキストエリア
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        
        # スクロールエリアにテキストエリアを追加
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.log_text)
        
        # プログレスダイアログのレイアウトを作成
        layout = QVBoxLayout(self.progress_dialog)
        layout.addWidget(scroll_area)
        
        # マップデータの読み込みを開始
        self.map_data.start_loading(mod_path)
        
        # 進捗状況を監視するタイマーを設定
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.check_loading_progress)
        self.progress_timer.start(100)  # 100ミリ秒ごとにチェック
    
    def check_loading_progress(self):
        """読み込みの進捗状況をチェック"""
        if self.map_data.is_loading_complete():
            self.progress_timer.stop()
            self.on_loading_complete()
        elif self.map_data.get_loading_error():
            self.progress_timer.stop()
            self.on_loading_error(self.map_data.get_loading_error())
    
    def update_progress(self, message):
        """プログレスバーとステータスメッセージを更新"""
        if self.progress_dialog:
            # メッセージから進捗率を推定
            if "プロヴィンス定義" in message:
                value = 10
            elif "プロヴィンス画像" in message:
                value = 30
            elif "ステート情報" in message:
                value = 70
            elif "国家の色定義" in message:
                value = 90
            elif "完了" in message:
                value = 100
            else:
                value = self.progress_dialog.value()  # 現在の値を維持
            
            self.progress_dialog.setValue(value)
            self.progress_dialog.setLabelText(message)
            self.log_text.append(message)
            
            # 最新のメッセージが見えるようにスクロール
            self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def cancel_loading(self):
        """読み込みをキャンセル"""
        if self.map_data:
            self.map_data.cancel_loading()
            self.log_text.append("読み込みをキャンセルしています...")
            self.logger.info("マップデータの読み込みをキャンセルしました")
    
    def on_loading_complete(self):
        """読み込み完了時の処理"""
        if self.progress_dialog:
            self.progress_dialog.close()
        
        self.logger.info("マップデータの読み込みが完了しました")
        
        # プロヴィンス画像を作成
        self.create_province_image()
        
        # 画面を更新
        self.update()
        
        # ステータスバーがあれば更新
        if hasattr(self, 'statusBar') and callable(getattr(self, 'statusBar', None)):
            self.statusBar().showMessage("マップデータの読み込みが完了しました")
        elif self.parent() and hasattr(self.parent(), 'statusBar') and callable(getattr(self.parent(), 'statusBar', None)):
            self.parent().statusBar().showMessage("マップデータの読み込みが完了しました")
    
    def on_loading_error(self, error_msg):
        """エラー発生時の処理"""
        if self.progress_dialog:
            self.progress_dialog.close()
        
        self.logger.error(f"マップデータの読み込み中にエラーが発生しました: {error_msg}")
        
        # エラーメッセージを表示
        QMessageBox.critical(self, "エラー", f"マップデータの読み込み中にエラーが発生しました:\n{error_msg}")
        
        # ステータスバーがあれば更新
        if hasattr(self, 'statusBar') and callable(getattr(self, 'statusBar', None)):
            self.statusBar().showMessage(f"エラー: {error_msg}")
        elif self.parent() and hasattr(self.parent(), 'statusBar') and callable(getattr(self.parent(), 'statusBar', None)):
            self.parent().statusBar().showMessage(f"エラー: {error_msg}")
    
    def create_province_image(self):
        """プロヴィンス画像を作成"""
        try:
            # 座標情報がなければ何もしない
            if not self.map_data.original_map_image_data is None:
                return
            
            # マップのサイズを取得
            width = self.map_data.original_width
            height = self.map_data.original_height
            
            self.logger.info(f"マップ画像のサイズ: {width}x{height}")
            
            # QPixmapを作成
            self.province_image = QPixmap(width, height)
            self.province_image.fill(Qt.white)
            
            # 描画用のペインタを作成
            painter = QPainter(self.province_image)
            painter.setRenderHint(QPainter.Antialiasing, False)  # アンチエイリアスを無効化
            
            # プロヴィンスを描画
            for province_id, (r, g, b, _, _) in self.map_data.provinces.items():
                color = QColor(r, g, b)
                painter.setPen(color)
                painter.setBrush(color)
                
                # プロヴィンスの重心を取得
                centroid = self.map_data.get_province_coordinates(province_id)
                if centroid:
                    x, y = centroid
                    # プロヴィンスの中心に点を描画
                    painter.drawPoint(int(x), int(y))
            
            # 海軍基地を描画
            for province_id, level in self.map_data.naval_bases.items():
                centroid = self.map_data.get_province_coordinates(province_id)
                if centroid:
                    x, y = centroid
                    # 海軍基地のマーカーを描画
                    painter.setPen(QPen(QColor(0, 0, 255), 2))
                    painter.setBrush(QColor(0, 0, 255, 100))
                    painter.drawEllipse(QPointF(x, y), 8, 8)
            
            painter.end()
            
            self.logger.info("プロヴィンス画像の作成が完了しました")
            
            # 画面を更新
            self.update()
            
        except Exception as e:
            self.logger.error(f"プロヴィンス画像の作成中にエラーが発生しました: {e}")
            self.logger.error(traceback.format_exc())
    
    def paintEvent(self, event):
        """描画イベント"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 背景を描画
        painter.fillRect(event.rect(), QColor(200, 200, 200))
        
        # プロヴィンス画像がなければ何もしない
        if not self.province_image:
            painter.drawText(event.rect(), Qt.AlignCenter, "マップデータを読み込んでください")
            painter.end()
            return
        
        # ズームとオフセットを適用
        painter.translate(self.offset)
        painter.scale(self.zoom_level, self.zoom_level)
        
        # プロヴィンス画像を描画
        painter.drawPixmap(0, 0, self.province_image)
        
        painter.end()
    
    def wheelEvent(self, event):
        """マウスホイールイベント（ズーム）"""
        # ズーム前の状態を保存
        old_pos = event.pos()
        old_scene_pos = (old_pos - self.offset) / self.zoom_level
        
        # ズームレベルを更新
        zoom_factor = 1.1
        if event.angleDelta().y() > 0:
            self.zoom_level *= zoom_factor  # ズームイン
        else:
            self.zoom_level /= zoom_factor  # ズームアウト
        
        # ズームレベルの範囲を制限
        self.zoom_level = max(0.1, min(5.0, self.zoom_level))
        
        # 新しいシーン座標を計算
        new_scene_pos = (old_pos - self.offset) / self.zoom_level
        
        # オフセットを調整して、マウス位置が同じ場所を指すようにする
        delta = (new_scene_pos - old_scene_pos) * self.zoom_level
        self.offset -= delta
        
        # 画面を更新
        self.update()
    
    def mousePressEvent(self, event):
        """マウスボタン押下イベント（ドラッグ開始）"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.last_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
    
    def mouseReleaseEvent(self, event):
        """マウスボタン解放イベント（ドラッグ終了）"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.setCursor(Qt.ArrowCursor)
    
    def mouseMoveEvent(self, event):
        """マウス移動イベント（ドラッグ中）"""
        if self.dragging and self.last_pos:
            # マウス移動量を計算
            delta = event.pos() - self.last_pos
            self.last_pos = event.pos()
            
            # オフセットを更新
            self.offset += delta
            
            # 画面を更新
            self.update()
    
    def resizeEvent(self, event):
        """ウィジェットサイズ変更イベント"""
        super().resizeEvent(event)
        self.update()


class MapViewWidget(QWidget):
    """マップビューを表示するためのウィジェット"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # レイアウトの設定
        layout = QVBoxLayout(self)
        
        # マップウィジェットを追加
        self.map_widget = MapWidget()
        layout.addWidget(self.map_widget)
        
        # コントロールパネルの追加
        control_layout = QHBoxLayout()
        
        # ズームインボタン
        zoom_in_button = QPushButton("+")
        zoom_in_button.clicked.connect(self.zoom_in)
        control_layout.addWidget(zoom_in_button)
        
        # ズームアウトボタン
        zoom_out_button = QPushButton("-")
        zoom_out_button.clicked.connect(self.zoom_out)
        control_layout.addWidget(zoom_out_button)
        
        # リセットボタン
        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self.reset_view)
        control_layout.addWidget(reset_button)
        
        # スペーサーを追加
        control_layout.addStretch(1)
        
        # コントロールパネルをレイアウトに追加
        layout.addLayout(control_layout)
    
    def load_map_data(self, mod_path):
        """マップデータを読み込む"""
        self.map_widget.load_map_data(mod_path)
    
    def zoom_in(self):
        """ズームイン"""
        self.map_widget.zoom_level *= 1.2
        self.map_widget.zoom_level = min(5.0, self.map_widget.zoom_level)
        self.map_widget.update()
    
    def zoom_out(self):
        """ズームアウト"""
        self.map_widget.zoom_level /= 1.2
        self.map_widget.zoom_level = max(0.1, self.map_widget.zoom_level)
        self.map_widget.update()
    
    def reset_view(self):
        """ビューをリセット"""
        self.map_widget.zoom_level = 1.0
        self.map_widget.offset = QPoint(0, 0)
        self.map_widget.update()