import logging
import sys
import os
import csv
import re
import math
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QFileDialog, QVBoxLayout, QWidget, QMessageBox, QLabel,
    QPushButton, QHBoxLayout, QComboBox, QLineEdit, QScrollBar
)
from PyQt5.QtGui import QPixmap, QImage, QColor, QPainter, QFont, QPen, QBrush
from PyQt5.QtCore import Qt, QRectF, QPointF, QPoint, QPropertyAnimation, QEasingCurve, pyqtProperty, QTimer, QSize

# PIL (Pillow) は画像を扱うために必要です
from PIL import Image
import numpy as np
import random  # 色をランダムに割り当てるため
import time  # パフォーマンス計測用

# 既存のパーサーモジュールをインポート
from parser.StateParser import StateParser
from parser.StateParser import ParserError
from parser.StrategicRegionParser import StrategicRegionParser
from parser.CountryColorParser import CountryColorParser
from parser.NavalOOBParser import NavalOOBParser
from utils.ship_icon_manager import ShipIconManager


def get_file_content(file_path):
    """ファイルの内容を読み込む関数"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            # print(f"ファイルの読み込みに失敗しました: {file_path} - {str(e)}")
            return None
    except Exception as e:
        # print(f"ファイルの読み込みに失敗しました: {file_path} - {str(e)}")
        return None


# プロビンスデータを保持するクラス
class Province:
    def __init__(self, id, r, g, b, name, type):
        self.id = id
        self.color_rgb = (r, g, b)
        self.name = name
        self.type = type
        self.state_id = None
        self.strategic_region_id = None
        self.display_color = QColor(r, g, b)


class MapViewer(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)

        # ロガーの設定
        self.logger = logging.getLogger('MapViewer')
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # アイコンマネージャーを初期化
        self.ship_icon_manager = ShipIconManager()
        self.ship_icon_manager.ensure_default_icons()  # デフォルトアイコンを確保

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing, False)

        # スクロールモードを無効にし、手動でスクロールを制御
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        self.map_image_item = None
        self.original_map_image_data = None
        self.provinces_data_by_rgb = {}
        self.provinces_data_by_id = {}

        self.states_data = {}
        self.strategic_regions_data = {}
        self.country_colors = {}

        self.original_width = 0
        self.original_height = 0

        self.current_filter = "provinces"
        self.base_qimage_cache = {}

        self._rgb_to_id_map_array = np.full(256 * 256 * 256, -1, dtype=np.int32)

        self.province_centroids = {}
        self.naval_base_locations = {}
        self.state_boundaries = {}

        # 艦隊情報を保持する変数を追加
        self.fleet_data = {}  # プロビンスIDをキーとして艦隊情報を保持
        self.show_fleet_info = False  # 艦隊情報の表示フラグ
        self.current_country = None  # 現在選択されている国家
        self.show_mod_fleets = False  # MOD内の艦隊を表示するフラグ

        # app_controllerを追加
        self.app_controller = parent.app_controller if parent else None

        # デバウンス処理用のタイマー追加
        self._move_timer = QTimer(self)
        self._move_timer.setSingleShot(True)
        self._move_timer.timeout.connect(self._execute_pending_move)
        self._pending_move_data = None
        
        # ズーム制限の設定
        self._min_zoom = 0.5
        self._max_zoom = 10.0
        self._default_zoom = 3.0

        # マウスオーバー時のツールチップ用
        self.setMouseTracking(True)
        self.hovered_province = None
        self.tooltip_label = QLabel(self)
        self.tooltip_label.setStyleSheet("""
            QLabel {
                background-color: #c0c0c0;
                color: black;
                padding: 5px;
                border: 2px solid #808080;
                font-family: "MS Sans Serif";
                font-size: 12pt;
            }
        """)
        self.tooltip_label.hide()

        # 検索機能用のウィジェット
        search_widget = QWidget(self)
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(0, 0, 0, 0)

        self.search_label = QLabel("ID検索:", self)
        self.search_input = QLineEdit(self)
        self.search_button = QPushButton("検索", self)
        self.search_result_label = QLabel("", self)

        search_layout.addWidget(self.search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.search_result_label)
        search_layout.addStretch()

        # Windows 98風のスタイル設定
        search_style = """
            QLabel, QLineEdit, QPushButton {
                background-color: #c0c0c0;
                border: 1px solid #808080;
                border-radius: 0px;
                padding: 2px;
                font-family: "MS Sans Serif";
                font-size: 10pt;
            }
            QLineEdit {
                min-width: 100px;
            }
            QPushButton {
                min-width: 60px;
            }
            QPushButton:hover {
                border: 1px solid #000000;
            }
        """
        search_widget.setStyleSheet(search_style)
        search_widget.setLayout(search_layout)
        search_widget.move(10, 40)

        # 検索ボタンのクリックイベントを接続
        self.search_button.clicked.connect(self.search_province)
        self.search_input.returnPressed.connect(self.search_province)

        # フィルター切り替え用のプルダウンを追加
        self.filter_combo = QComboBox(self)
        self.filter_combo.addItem("プロビンス", "provinces")
        self.filter_combo.addItem("ステート", "states")
        self.filter_combo.addItem("戦略地域", "strategic_regions")
        self.filter_combo.addItem("国家", "countries")
        self.filter_combo.currentIndexChanged.connect(self.on_filter_changed)

        # Windows 98風のクラシックなスタイル設定
        self.filter_combo.setStyleSheet("""
            QComboBox {
                background-color: #c0c0c0;
                border: 1px solid #808080;
                border-radius: 0px;
                padding: 2px;
                min-width: 100px;
                font-family: "MS Sans Serif";
                font-size: 10pt;
            }
            QComboBox:hover {
                border: 1px solid #000000;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                width: 0px;
                height: 0px;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid black;
                margin-right: 4px;
            }
            QComboBox QAbstractItemView {
                background-color: #c0c0c0;
                border: 1px solid #808080;
                selection-background-color: #000080;
                selection-color: white;
                font-family: "MS Sans Serif";
                font-size: 10pt;
            }
        """)

        # プルダウンの位置を設定
        self.filter_combo.move(10, 10)

        # マップの左右ループスクロールと滑らかなスクロールのための変数
        self._scroll_offset_x = 0.0  # 現在のX方向のスクロールオフセット
        self._last_drag_pos = QPoint()  # マウスドラッグの開始位置
        self._last_move_delta = QPoint(0, 0)  # 慣性スクロールのための最後の移動量

        self._animation = QPropertyAnimation(self, b"scrollOffsetX")  # スクロールアニメーション
        self._animation.setDuration(200)  # アニメーション時間 (ミリ秒) - より速く
        self._animation.setEasingCurve(QEasingCurve.OutCubic)  # イージングカーブ
        self._animation.finished.connect(self._animation_finished)  # アニメーション終了時の処理

    @pyqtProperty(float)
    def scrollOffsetX(self):
        """X方向のスクロールオフセットプロパティ"""
        return self._scroll_offset_x

    @scrollOffsetX.setter
    def scrollOffsetX(self, value):
        """X方向のスクロールオフセットを設定し、マップを更新"""
        if self.original_width > 0:
            # マップの幅で剰余演算を行い、ループを実現
            self._scroll_offset_x = value % self.original_width
        else:
            self._scroll_offset_x = value
        self.update_map_item_position()  # マップアイテムの位置を更新

    def _animation_finished(self):
        """アニメーション終了時にログを出力"""
        self.logger.debug("Scroll animation finished.")

    def update_map_item_position(self):
        """マップアイテムの表示位置を更新し、ループ描画を考慮する"""
        if self.map_image_item is None or self.original_width == 0:
            return

        # メインのマップアイテムのピックスマップ
        current_pixmap = self.map_image_item.pixmap()

        # シーンから既存のループ用アイテムを削除
        # QGraphicsScene.items() は変更中に呼ばれると問題がある可能性があるので、コピーしてから削除
        items_to_remove = [item for item in self.scene.items() if item.data(0) == "loop_map_item"]
        for item in items_to_remove:
            self.scene.removeItem(item)

        # メインのマップアイテムの位置を設定
        # _scroll_offset_x はマップの左端がビューポートのどこに位置するかを示す
        # シーンの左端を基準にするため、負の値で設定
        main_item_x_pos = -self._scroll_offset_x
        self.map_image_item.setPos(main_item_x_pos, 0)

        # 現在のビューポートのシーン座標での矩形
        view_rect_scene = self.mapToScene(self.viewport().rect()).boundingRect()

        # 描画が必要なマップコピーの範囲を決定
        # 例えば、-2 から +2 までの範囲でコピーをチェックする
        # これにより、ズームアウト時でも十分な範囲がカバーされる
        num_copies_each_side = 2  # 左右にそれぞれ2枚のコピーを常に考慮

        for i in range(-num_copies_each_side, num_copies_each_side + 1):
            # メインアイテム自身は既に設定されているのでスキップ
            if i == 0:
                continue

            copy_x_pos = main_item_x_pos + i * self.original_width

            # コピーアイテムのシーン座標での矩形
            copy_rect_scene = QRectF(copy_x_pos, 0, self.original_width, self.original_height)

            # コピーアイテムがビューポートと重なる場合のみ描画
            if copy_rect_scene.intersects(view_rect_scene):
                loop_item = self.scene.addPixmap(current_pixmap)
                loop_item.setPos(copy_x_pos, 0)
                loop_item.setData(0, "loop_map_item")  # カスタムデータで識別

        # シーンの更新を強制
        self.scene.update()

    def load_map_data(self, mod_path):
        start_time = time.time()
        self.scene.clear()
        self.map_image_item = None
        self.original_map_image_data = None
        self.provinces_data_by_rgb = {}
        self.provinces_data_by_id = {}

        self.states_data = {}
        self.strategic_regions_data = {}
        self.country_colors = {}

        self.original_width = 0
        self.original_height = 0

        self.current_filter = "provinces"
        self.base_qimage_cache = {}
        self.state_owners = {}  # ステートの所有者情報を保持

        self._rgb_to_id_map_array.fill(-1)
        self.province_centroids = {}
        self.naval_base_locations = {}
        self.state_boundaries = {}

        base_mod_dir = mod_path

        # 国家の色情報を読み込む
        colors_txt_path = os.path.join(base_mod_dir, 'common', 'countries', 'colors.txt')
        if os.path.exists(colors_txt_path):
            # print(f"Loading country colors from: {colors_txt_path}")
            content = get_file_content(colors_txt_path)
            if content:
                parser = CountryColorParser(content)
                self.country_colors = parser.parse()
                # print(f"Loaded {len(self.country_colors)} country colors")

        provinces_img_path = os.path.join(base_mod_dir, 'map', 'provinces.bmp')
        if not os.path.exists(provinces_img_path):
            QMessageBox.critical(self, "エラー",
                                 f"provinces.bmp が指定されたModパスのmap/ ディレクトリ以下に見つかりません。\n({provinces_img_path})")
            return False

        definition_csv_path = os.path.join(base_mod_dir, 'map', 'definition.csv')
        if not os.path.exists(definition_csv_path):
            QMessageBox.critical(self, "エラー",
                                 f"definition.csv が指定されたModパスのmap/ ディレクトリ以下に見つかりません。\n({definition_csv_path})")
            return False

        try:
            img_pil = Image.open(provinces_img_path).convert("RGB")
            self.original_width, self.original_height = img_pil.size
            self.original_map_image_data = np.array(img_pil)

            with open(definition_csv_path, 'r', encoding='latin-1') as f:
                reader = csv.reader(f, delimiter=';')
                next(reader)
                for row in reader:
                    if len(row) >= 5:
                        try:
                            id = int(row[0])
                            r, g, b = int(row[1]), int(row[2]), int(row[3])
                            name = row[4].strip()
                            province_type = row[5].strip() if len(row) > 5 else "unknown"
                            province = Province(id, r, g, b, name, province_type)
                            self.provinces_data_by_rgb[(r, g, b)] = province
                            self.provinces_data_by_id[id] = province

                            rgb_hash = r * 65536 + g * 256 + b
                            if rgb_hash < len(self._rgb_to_id_map_array):
                                self._rgb_to_id_map_array[rgb_hash] = id
                        except ValueError as e:
                            pass

            # ステートデータの読み込み
            states_dir = os.path.join(base_mod_dir, 'history', 'states')

            if os.path.exists(states_dir):
                for filename in os.listdir(states_dir):
                    if filename.endswith('.txt'):
                        file_path = os.path.join(states_dir, filename)
                        content = get_file_content(file_path)
                        if content:
                            try:
                                parser_ply = StateParser(content)
                                state_data = parser_ply.parse()

                                state_id = state_data.get('id')
                                if state_id is not None and 'provinces' in state_data and state_data['provinces']:
                                    state_name = state_data.get('name', f"State {state_id}").strip('"')
                                    state_color = QColor(random.randint(0, 255), random.randint(0, 255),
                                                         random.randint(0, 255))
                                    self.states_data[state_id] = {
                                        'name': state_name,
                                        'provinces': state_data['provinces'],
                                        'color': (state_color.red(), state_color.green(), state_color.blue()),
                                        'raw_data': state_data
                                    }
                                    owner = state_data.get('owner')
                                    if owner:
                                        self.state_owners[state_id] = owner
                                    for prov_id in state_data['provinces']:
                                        if prov_id in self.provinces_data_by_id:
                                            self.provinces_data_by_id[prov_id].state_id = state_id

                                    # 海軍基地情報の取得
                                    if 'province_buildings' in state_data:
                                        for prov_id, buildings in state_data['province_buildings'].items():
                                            if isinstance(buildings, dict) and 'naval_base' in buildings:
                                                self.naval_base_locations[prov_id] = buildings['naval_base']
                            except ParserError as e:
                                pass
                            except Exception as e:
                                pass
                        else:
                            pass
            else:
                pass

            # 戦略地域の読み込み (map/strategicregions)
            self.strategic_regions_data = {}
            strategic_regions_dir = os.path.join(base_mod_dir, 'map', 'strategicregions')

            if os.path.exists(strategic_regions_dir):
                for filename in os.listdir(strategic_regions_dir):
                    if filename.endswith('.txt'):
                        file_path = os.path.join(strategic_regions_dir, filename)
                        content = get_file_content(file_path)
                        if content:
                            try:
                                parser = StrategicRegionParser(content)
                                region_data = parser.parse()

                                region_id = region_data.get('id')
                                if region_id is not None and 'provinces' in region_data and region_data['provinces']:
                                    region_name = region_data.get('name', f"Strategic Region {region_id}").strip('"')
                                    region_color = QColor(random.randint(0, 255), random.randint(0, 255),
                                                          random.randint(0, 255))
                                    self.strategic_regions_data[region_id] = {
                                        'name': region_name,
                                        'provinces': region_data['provinces'],
                                        'color': (region_color.red(), region_color.green(), region_color.blue()),
                                        'raw_data': region_data
                                    }
                                    for prov_id in region_data['provinces']:
                                        if prov_id in self.provinces_data_by_id:
                                            self.provinces_data_by_id[prov_id].strategic_region_id = region_id
                            except ParserError as e:
                                pass
                            except Exception as e:
                                pass
                        else:
                            pass
            else:
                pass

            # プロビンス重心の計算
            self._load_or_calculate_province_centroids(provinces_img_path, definition_csv_path)

            # ステートの境界線を計算
            self.calculate_state_boundaries()

            # 高速化用の色マップを構築 (NumPy配列として)
            max_prov_id = max(self.provinces_data_by_id.keys()) if self.provinces_data_by_id else 0

            default_unknown_color = (50, 50, 50)

            self._palette_province = np.full((max_prov_id + 1, 3), (0, 0, 0), dtype=np.uint8)
            self._palette_state = np.full((max_prov_id + 1, 3), default_unknown_color, dtype=np.uint8)
            self._palette_region = np.full((max_prov_id + 1, 3), default_unknown_color, dtype=np.uint8)

            for prov_id, prov_obj in self.provinces_data_by_id.items():
                if prov_id <= max_prov_id:
                    self._palette_province[prov_id] = prov_obj.color_rgb

                    if prov_obj.state_id is not None and prov_obj.state_id in self.states_data:
                        self._palette_state[prov_id] = self.states_data[prov_obj.state_id]['color']

                    # strategic_regions_dataが空の場合もあるためチェック
                    if prov_obj.strategic_region_id is not None and self.strategic_regions_data and prov_obj.strategic_region_id in self.strategic_regions_data:
                        self._palette_region[prov_id] = self.strategic_regions_data[prov_obj.strategic_region_id][
                            'color']

            self.render_map()
            end_time = time.time()
            return True

        except Exception as e:
            QMessageBox.critical(self, "ロードエラー", f"地図データの読み込み中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _load_or_calculate_province_centroids(self, provinces_bmp_path, definition_csv_path):
        """
        プロヴィンス中心座標をキャッシュから読み込み、または計算して保存
        
        Args:
            provinces_bmp_path: provinces.bmpファイルのパス
            definition_csv_path: definition.csvファイルのパス
        """
        start_time = time.time()
        
        # キャッシュマネージャーが利用可能かチェック
        if not self.app_controller or not self.app_controller.cache_manager:
            self.logger.warning("キャッシュマネージャーが利用できません。直接計算を実行します。")
            self.calculate_province_centroids()
            return
        
        cache_manager = self.app_controller.cache_manager
        
        # 現在のファイルの更新時刻を取得
        current_bmp_mtime = os.path.getmtime(provinces_bmp_path) if os.path.exists(provinces_bmp_path) else 0
        current_csv_mtime = os.path.getmtime(definition_csv_path) if os.path.exists(definition_csv_path) else 0
        
        # キャッシュから読み込み試行
        try:
            cached_data = cache_manager.load("province_centroids", provinces_bmp_path)
            
            if cached_data is not None and isinstance(cached_data, dict):
                cached_bmp_mtime = cached_data.get('bmp_mtime', 0)
                cached_csv_mtime = cached_data.get('csv_mtime', 0)
                cached_centroids = cached_data.get('centroids')
                
                # キャッシュの有効性チェック
                if (cached_bmp_mtime >= current_bmp_mtime and 
                    cached_csv_mtime >= current_csv_mtime and 
                    cached_centroids is not None):
                    
                    # キャッシュが有効
                    self.province_centroids = cached_centroids
                    cache_load_time = time.time() - start_time
                    self.logger.info(f"プロヴィンス中心座標をキャッシュから読み込み完了: {len(self.province_centroids)}個のプロヴィンス, 所要時間: {cache_load_time:.3f}秒")
                    return
                else:
                    self.logger.info("キャッシュが古いため、再計算を実行します")
            else:
                self.logger.info("キャッシュが見つからないため、計算を実行します")
                
        except Exception as e:
            self.logger.warning(f"キャッシュ読み込み中にエラーが発生: {e}")
        
        # キャッシュが無効または存在しない場合は計算を実行
        calculation_start = time.time()
        self.calculate_province_centroids()
        calculation_time = time.time() - calculation_start
        
        # 計算結果をキャッシュに保存
        cache_data = {
            'centroids': self.province_centroids,
            'bmp_mtime': current_bmp_mtime,
            'csv_mtime': current_csv_mtime,
            'calculation_time': calculation_time,
            'timestamp': time.time()
        }
        
        try:
            cache_manager.save("province_centroids", provinces_bmp_path, cache_data)
            total_time = time.time() - start_time
            self.logger.info(f"プロヴィンス中心座標の計算とキャッシュ保存完了: {len(self.province_centroids)}個のプロヴィンス, 計算時間: {calculation_time:.3f}秒, 総時間: {total_time:.3f}秒")
        except Exception as e:
            self.logger.warning(f"プロヴィンス中心座標のキャッシュ保存に失敗: {e}")

    def calculate_province_centroids(self):
        """
        プロヴィンス中心座標を計算（既存メソッドの改良版）
        """
        start_time = time.time()
        if self.original_map_image_data is None:
            self.logger.warning("マップ画像データが読み込まれていません")
            return

        height, width, _ = self.original_map_image_data.shape
        self.logger.info(f"プロヴィンス中心座標の計算を開始: マップサイズ {width}x{height}")

        # 全ピクセルのRGBハッシュを計算
        pixels_flat = self.original_map_image_data.reshape(-1, 3)
        pixel_hashes = (pixels_flat[:, 0].astype(np.int32) * 65536 +
                        pixels_flat[:, 1].astype(np.int32) * 256 +
                        pixels_flat[:, 2].astype(np.int32))

        # RGBハッシュからプロビンスIDへのマッピングを一括で適用
        prov_ids_flat = np.full_like(pixel_hashes, -1)
        valid_hash_indices = (pixel_hashes >= 0) & (pixel_hashes < len(self._rgb_to_id_map_array))
        prov_ids_flat[valid_hash_indices] = self._rgb_to_id_map_array[pixel_hashes[valid_hash_indices]]

        # 有効なプロビンスIDを持つピクセルのみを抽出
        valid_prov_pixel_indices = prov_ids_flat != -1
        valid_prov_ids = prov_ids_flat[valid_prov_pixel_indices]

        # 各ピクセルの座標配列を生成 (0からwidth-1, 0からheight-1の繰り返し)
        x_indices, y_indices = np.meshgrid(np.arange(width), np.arange(height))
        x_coords_flat = x_indices.flatten()
        y_coords_flat = y_indices.flatten()

        # 有効なプロビンスピクセルに属するX, Y座標を抽出
        valid_x_coords = x_coords_flat[valid_prov_pixel_indices]
        valid_y_coords = y_coords_flat[valid_prov_pixel_indices]

        # NumPyのbincountを使って、プロビンスIDごとのX座標の合計、Y座標の合計、ピクセル数を高速に計算
        # bincountの出力はインデックスがプロビンスIDに対応
        max_prov_id = valid_prov_ids.max() if len(valid_prov_ids) > 0 else 0

        # 指定された範囲を超える可能性があるため、minlengthで配列サイズを保証
        sum_x_per_prov = np.bincount(valid_prov_ids, weights=valid_x_coords, minlength=max_prov_id + 1)
        sum_y_per_prov = np.bincount(valid_prov_ids, weights=valid_y_coords, minlength=max_prov_id + 1)
        count_per_prov = np.bincount(valid_prov_ids, minlength=max_prov_id + 1)

        self.province_centroids = {}
        calculated_count = 0
        missing_count = 0
        
        for prov_id in self.provinces_data_by_id.keys():
            if prov_id <= max_prov_id and count_per_prov[prov_id] > 0:
                center_x = sum_x_per_prov[prov_id] / count_per_prov[prov_id]
                center_y = sum_y_per_prov[prov_id] / count_per_prov[prov_id]
                self.province_centroids[prov_id] = (center_x, center_y)
                calculated_count += 1
            else:
                self.province_centroids[prov_id] = None  # プロビンスが存在しない、または画像中に見つからない場合
                missing_count += 1

        end_time = time.time()
        calculation_time = end_time - start_time
        
        self.logger.info(f"プロヴィンス中心座標の計算完了: {calculated_count}個成功, {missing_count}個見つからず, 所要時間: {calculation_time:.3f}秒")
        
        if missing_count > 0:
            self.logger.warning(f"{missing_count}個のプロヴィンスの中心座標を計算できませんでした（definition.csvにあるがprovinces.bmpに色が見つからない）")

    def get_province_center_coords(self, province_id):
        """
        指定されたプロヴィンスIDの中心座標を取得
        
        Args:
            province_id: プロヴィンスID
            
        Returns:
            tuple: (x, y) 座標のタプル、見つからない場合はNone
        """
        return self.province_centroids.get(province_id)

    def get_all_province_centroids(self):
        """
        すべてのプロヴィンス中心座標を取得
        
        Returns:
            dict: プロヴィンスID -> (x, y) 座標の辞書
        """
        return self.province_centroids.copy()

    def clear_province_centroids_cache(self):
        """
        プロヴィンス中心座標のキャッシュをクリア
        """
        if self.app_controller and self.app_controller.cache_manager:
            try:
                self.app_controller.cache_manager.clear_cache("province_centroids")
                self.logger.info("プロヴィンス中心座標のキャッシュをクリアしました")
            except Exception as e:
                self.logger.error(f"キャッシュクリア中にエラーが発生: {e}")

    def draw_province_centroids_debug(self, target_pixmap: QPixmap):
        """
        デバッグ用: プロヴィンス中心座標をマップ上に描画
        
        Args:
            target_pixmap: 描画対象のピクスマップ
        """
        if not self.province_centroids:
            return
            
        painter = QPainter(target_pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # 中心点を赤い小さな円で描画
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        painter.setBrush(QBrush(QColor(255, 0, 0, 128)))
        
        drawn_count = 0
        for prov_id, coords in self.province_centroids.items():
            if coords is not None:
                x, y = coords
                painter.drawEllipse(QPointF(x, y), 3, 3)
                drawn_count += 1
        
        painter.end()
        self.logger.info(f"デバッグ: {drawn_count}個のプロヴィンス中心点を描画しました")

    def benchmark_province_centroids_calculation(self, iterations=3):
        """
        プロヴィンス中心座標計算のベンチマーク
        
        Args:
            iterations: ベンチマーク実行回数
            
        Returns:
            dict: ベンチマーク結果
        """
        if self.original_map_image_data is None:
            self.logger.error("マップデータが読み込まれていません")
            return None
            
        self.logger.info(f"プロヴィンス中心座標計算のベンチマークを開始: {iterations}回実行")
        
        times = []
        for i in range(iterations):
            # キャッシュを一時的にクリア
            original_centroids = self.province_centroids.copy()
            
            start_time = time.time()
            self.calculate_province_centroids()
            end_time = time.time()
            
            calculation_time = end_time - start_time
            times.append(calculation_time)
            self.logger.info(f"ベンチマーク {i+1}/{iterations}: {calculation_time:.3f}秒")
            
            # 元の中心座標を復元
            self.province_centroids = original_centroids
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        benchmark_result = {
            'iterations': iterations,
            'times': times,
            'average_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'total_provinces': len(self.provinces_data_by_id),
            'calculated_provinces': len([c for c in self.province_centroids.values() if c is not None])
        }
        
        self.logger.info(f"ベンチマーク結果: 平均 {avg_time:.3f}秒, 最短 {min_time:.3f}秒, 最長 {max_time:.3f}秒")
        
        return benchmark_result

    def calculate_state_boundaries(self):
        start_time = time.time()

        if self.original_map_image_data is None:
            return

        height, width, _ = self.original_map_image_data.shape
        self.state_boundaries = {}

        # 各ステートのプロビンスを取得
        for state_id, state_data in self.states_data.items():
            provinces = state_data['provinces']
            if not provinces:
                continue

            # ステートの境界線を計算
            boundaries = set()
            for prov_id in provinces:
                if prov_id not in self.province_centroids:
                    continue

                # プロビンスの中心座標を取得
                center_x, center_y = self.province_centroids[prov_id]
                center_x, center_y = int(center_x), int(center_y)

                # 8方向の隣接ピクセルをチェック
                for dx, dy in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
                    nx, ny = center_x + dx, center_y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        pixel_rgb = tuple(self.original_map_image_data[ny, nx])
                        neighbor_prov = self.provinces_data_by_rgb.get(pixel_rgb)
                        if neighbor_prov and neighbor_prov.id not in provinces:
                            # 境界線を追加（両端の座標を追加）
                            boundaries.add((center_x, center_y, nx, ny))

            self.state_boundaries[state_id] = list(boundaries)

        end_time = time.time()

    def render_map(self):
        start_time = time.time()
        if self.original_map_image_data is None:
            print("マップデータが読み込まれていません")
            return

        # 現在の表示位置を保存
        current_center = self.map_image_item.pos() if self.map_image_item else None
        current_scale = self.map_image_item.scale() if self.map_image_item else 1.0
        current_rotation = self.map_image_item.rotation() if self.map_image_item else 0.0

        self.logger.debug(
            f"render_map called: current_filter={self.current_filter}, show_fleet_info={self.show_fleet_info}")
        self.logger.debug(f"艦隊データの状態: {self.fleet_data}")

        if self.current_filter not in self.base_qimage_cache:
            self.logger.debug("キャッシュからマップを生成")
            original_pixels_flat = self.original_map_image_data.reshape(-1, 3)

            pixel_hashes = (original_pixels_flat[:, 0].astype(np.int32) * 65536 +
                            original_pixels_flat[:, 1].astype(np.int32) * 256 +
                            original_pixels_flat[:, 2].astype(np.int32))

            prov_ids_flat = np.full_like(pixel_hashes, -1)
            valid_hash_indices = (pixel_hashes >= 0) & (pixel_hashes < len(self._rgb_to_id_map_array))
            prov_ids_flat[valid_hash_indices] = self._rgb_to_id_map_array[pixel_hashes[valid_hash_indices]]

            if self.current_filter == "provinces":
                selected_palette = self._palette_province
            elif self.current_filter == "states":
                selected_palette = self._palette_state
            elif self.current_filter == "strategic_regions":
                selected_palette = self._palette_region
            elif self.current_filter == "countries":
                # 国家モードの場合、ステートの所有者の色を使用
                selected_palette = np.full(
                    (max(self.provinces_data_by_id.keys()) + 1 if self.provinces_data_by_id else 1, 3), (50, 50, 50),
                    dtype=np.uint8)
                for state_id, state_data in self.states_data.items():
                    owner = state_data['raw_data'].get('owner', None)
                    if owner and owner in self.country_colors:
                        color = self.country_colors[owner]['color']
                        for prov_id in state_data['provinces']:
                            if prov_id <= max(self.provinces_data_by_id.keys()):
                                selected_palette[prov_id] = color
            else:
                selected_palette = np.full(
                    (max(self.provinces_data_by_id.keys()) + 1 if self.provinces_data_by_id else 1, 3), (0, 0, 0),
                    dtype=np.uint8)

            default_unknown_color = (50, 50, 50)
            filtered_colors_flat = np.full_like(original_pixels_flat, default_unknown_color, dtype=np.uint8)

            max_id_in_palette = selected_palette.shape[0] - 1
            valid_indices_for_palette_lookup = (prov_ids_flat >= 0) & (prov_ids_flat <= max_id_in_palette)

            filtered_colors_flat[valid_indices_for_palette_lookup] = selected_palette[
                prov_ids_flat[valid_indices_for_palette_lookup]]

            display_array = filtered_colors_flat.reshape(self.original_height, self.original_width, 3)

            height, width, channel = display_array.shape
            bytes_per_line = channel * width
            q_image = QImage(display_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
            self.base_qimage_cache[self.current_filter] = q_image.copy()
        else:
            self.logger.debug("キャッシュからマップを読み込み")
            pass

        current_pixmap = QPixmap.fromImage(self.base_qimage_cache[self.current_filter])

        # 国家モードの場合、ステートの境界線を描画
        if self.current_filter == "countries":
            self.logger.debug("ステートの境界線を描画")
            self.draw_state_boundaries(current_pixmap)

        self.draw_naval_bases(current_pixmap)

        # 艦隊情報を描画
        self.logger.debug(
            f"艦隊情報の描画条件チェック: show_fleet_info={self.show_fleet_info}, fleet_data={bool(self.fleet_data)}")
        if self.show_fleet_info and self.fleet_data:
            self.logger.debug("艦隊情報を描画")
            self.draw_fleet_info(current_pixmap)
        else:
            self.logger.debug(
                f"艦隊情報の描画をスキップ: show_fleet_info={self.show_fleet_info}, fleet_data={bool(self.fleet_data)}")

        # シーンをクリアし、新しいマップアイテムを追加
        self.scene.clear()
        self.map_image_item = self.scene.addPixmap(current_pixmap)
        
        # 保存した表示位置を復元
        if current_center is not None:
            self.map_image_item.setPos(current_center)
            self.map_image_item.setScale(current_scale)
            self.map_image_item.setRotation(current_rotation)
        else:
            # 初回表示時は通常の初期化処理
            self.setSceneRect(QRectF(0, 0, self.original_width, self.original_height))
            self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
            self.scale(4.0, 4.0)

        # マップアイテムの位置を更新してループ描画を適用
        self.update_map_item_position()

        end_time = time.time()
        self.logger.debug(f"マップの描画が完了: 所要時間 {end_time - start_time:.2f}秒")

    def draw_state_boundaries(self, target_pixmap: QPixmap):
        painter = QPainter(target_pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(QColor(0, 0, 0, 200), 2))  # 線の太さを2に増やし、より見やすく

        for state_id, boundaries in self.state_boundaries.items():
            for x1, y1, x2, y2 in boundaries:
                painter.drawLine(x1, y1, x2, y2)

        painter.end()

    def draw_naval_bases(self, target_pixmap: QPixmap):
        painter = QPainter(target_pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # 固定の円のサイズを使用
        circle_radius = 8

        for prov_id, level in self.naval_base_locations.items():
            if prov_id in self.province_centroids and self.province_centroids[prov_id] is not None:
                center_x, center_y = self.province_centroids[prov_id]

                # 港湾の色を設定（レベルに応じて）
                if level >= 10:
                    base_color = QColor(0, 0, 255)  # 青
                elif level >= 5:
                    base_color = QColor(0, 128, 255)  # 水色
                else:
                    base_color = QColor(0, 255, 255)  # 薄い水色

                # 外側の円（港湾の色の輪郭）
                painter.setPen(QPen(base_color, 2))
                painter.setBrush(QColor(base_color.red(), base_color.green(), base_color.blue(), 100))
                painter.drawEllipse(QPointF(center_x, center_y), circle_radius, circle_radius)

                # 内側の円（白い輪郭）
                inner_radius = circle_radius * 0.7
                painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
                painter.setBrush(QColor(255, 255, 255, 150))
                painter.drawEllipse(QPointF(center_x, center_y), inner_radius, inner_radius)

        painter.end()

    def draw_selected_country_naval_bases(self, target_pixmap: QPixmap, country_tag):
        """選択された国家の港湾のみを表示する"""
        if not country_tag:
            return

        painter = QPainter(target_pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # 固定の円のサイズを使用
        circle_radius = 8

        # 港湾名を表示するためのフォント設定
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        # 選択された国家の港湾のみを表示
        for prov_id, level in self.naval_base_locations.items():
            if prov_id in self.province_centroids and self.province_centroids[prov_id] is not None:
                # プロビンスが属するステートを取得
                province = self.provinces_data_by_id.get(prov_id)
                if province and province.state_id:
                    state_data = self.states_data.get(province.state_id)
                    if state_data and state_data['raw_data'].get('owner') == country_tag:
                        center_x, center_y = self.province_centroids[prov_id]

                        # 港湾の色を設定（レベルに応じて）
                        if level >= 10:
                            base_color = QColor(255, 0, 0)  # 赤
                        elif level >= 5:
                            base_color = QColor(255, 128, 0)  # オレンジ
                        else:
                            base_color = QColor(255, 255, 0)  # 黄

                        # 外側の円（港湾の色の輪郭）
                        painter.setPen(QPen(base_color, 2))
                        painter.setBrush(QColor(base_color.red(), base_color.green(), base_color.blue(), 100))
                        painter.drawEllipse(QPointF(center_x, center_y), circle_radius, circle_radius)

                        # 内側の円（白い輪郭）
                        inner_radius = circle_radius * 0.7
                        painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
                        painter.setBrush(QColor(255, 255, 255, 150))
                        painter.drawEllipse(QPointF(center_x, center_y), inner_radius, inner_radius)

                        # 港湾名を表示
                        if prov_id in self.provinces_data_by_id:
                            prov_obj = self.provinces_data_by_id[prov_id]
                            if prov_obj.name:
                                # 港湾名の背景を描画
                                text = f"{prov_obj.name} (Lv{level})"
                                text_rect = painter.fontMetrics().boundingRect(text)
                                text_rect.moveCenter(QPoint(int(center_x), int(center_y + circle_radius + 5)))
                                text_rect.adjust(-2, -2, 2, 2)  # パディングを追加

                                # 背景を描画
                                painter.setPen(Qt.NoPen)
                                painter.setBrush(QColor(0, 0, 0, 180))
                                painter.drawRect(text_rect)

                                # テキストを描画
                                painter.setPen(QColor(255, 255, 255))
                                painter.drawText(text_rect, Qt.AlignCenter, text)

        painter.end()

    def draw_fleet_info(self, pixmap):
        """艦隊情報を描画（改善版）"""
        if not self.fleet_data or not self.show_fleet_info:
            return

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # プロビンスごとの艦隊情報を描画
        for prov_id, fleets in self.fleet_data.items():
            if prov_id in self.province_centroids:
                center_x, center_y = self.province_centroids[prov_id]
                
                # 艦隊ボタンを描画
                button_radius = 10
                button_color = QColor(0, 128, 255)  # 青色
                
                # ボタンの背景を描画
                painter.setPen(QPen(QColor(0, 0, 0, 180), 1))
                painter.setBrush(button_color)
                painter.drawEllipse(QPointF(center_x, center_y), button_radius, button_radius)
                
                # ボタンのテキストを描画
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(QFont("Arial", 8))
                painter.drawText(
                    QRectF(center_x - button_radius, center_y - button_radius,
                          button_radius * 2, button_radius * 2),
                    Qt.AlignCenter,
                    "艦"
                )

        painter.end()

    def _aggregate_fleet_info(self, province_group, province_fleets):
        """艦隊情報を集約"""
        aggregated_info = {
            'fleets': [],
            'total_ships': 0,
            'ship_types': {}
        }

        for prov_id in province_group:
            if prov_id in province_fleets:
                for fleet in province_fleets[prov_id]:
                    fleet_info = {
                        'name': fleet['name'],
                        'task_forces': []
                    }

                    for tf in fleet.get('task_forces', []):
                        tf_info = {
                            'name': tf['name'],
                            'ships': []
                        }

                        for ship in tf.get('ships', []):
                            ship_type = self._get_ship_type_from_design(ship)
                            if ship_type:
                                if ship_type not in aggregated_info['ship_types']:
                                    aggregated_info['ship_types'][ship_type] = 0
                                aggregated_info['ship_types'][ship_type] += 1
                                aggregated_info['total_ships'] += 1

                            tf_info['ships'].append({
                                'name': ship['name'],
                                'type': ship_type,
                                'is_pride': ship.get('is_pride', False)
                            })

                        fleet_info['task_forces'].append(tf_info)

                    aggregated_info['fleets'].append(fleet_info)

        return aggregated_info

    def _calculate_fleet_composition(self, fleets: list) -> dict:
        """
        艦隊データから艦種別隻数を計算
        
        Args:
            fleets: 艦隊データのリスト
            
        Returns:
            dict: 艦種別隻数 {"DD": 3, "CA": 2, ...}
        """
        composition = {}
        
        try:
            for fleet in fleets:
                if not isinstance(fleet, dict):
                    self.logger.warning(f"無効な艦隊データ: {fleet}")
                    continue

                for task_force in fleet.get('task_forces', []):
                    if not isinstance(task_force, dict):
                        self.logger.warning(f"無効な任務部隊データ: {task_force}")
                        continue

                    ships = task_force.get('ships', [])
                    if not isinstance(ships, list):
                        self.logger.warning(f"無効な艦艇リスト: {ships}")
                        continue

                    for ship in ships:
                        if not isinstance(ship, dict):
                            continue

                        # 設計データから艦種を特定
                        ship_type = self._get_ship_type_from_design(ship)
                        
                        if ship_type:
                            if ship_type not in composition:
                                composition[ship_type] = 0
                            composition[ship_type] += 1

        except Exception as e:
            self.logger.error(f"艦隊編成計算エラー: {e}")

        return composition

    def _get_ship_type_from_design(self, ship: dict) -> str:
        """
        艦艇データから艦種を特定
        
        Args:
            ship: 艦艇データ
            
        Returns:
            str: 艦種略号
        """
        try:
            # 設計データから艦種を取得
            design = ship.get('design', {})
            
            if isinstance(design, str):
                # 設計名から艦種を推測
                design_name = design.lower()
                
                # 設計名パターンマッチング
                if 'destroyer' in design_name or '駆逐' in design_name:
                    return 'DD'
                elif 'cruiser' in design_name and ('heavy' in design_name or '重' in design_name):
                    return 'CA'
                elif 'cruiser' in design_name and ('light' in design_name or '軽' in design_name):
                    return 'CL'
                elif 'battleship' in design_name or '戦艦' in design_name:
                    return 'BB'
                elif 'carrier' in design_name or '空母' in design_name:
                    return 'CV'
                elif 'submarine' in design_name or '潜水' in design_name:
                    return 'SS'
                elif 'battlecruiser' in design_name or '巡洋戦艦' in design_name:
                    return 'BC'
                    
            elif isinstance(design, dict):
                # 設計データがオブジェクトの場合
                ship_type = design.get('ship_type', design.get('type', ''))
                if ship_type:
                    # 日本語艦種名から略号を取得
                    return self.ship_icon_manager._get_ship_abbreviation(ship_type)
            
            # デフォルトとして不明な艦種
            return 'UNKNOWN'
            
        except Exception as e:
            self.logger.error(f"艦種特定エラー: {e}")
            return 'UNKNOWN'

    def show_fleet_details_with_icons(self, province_id):
        """艦隊の詳細情報を表示する（アイコン版）"""
        if province_id in self.fleet_data:
            fleet_info = self.fleet_data[province_id]
            
            # 艦種別隻数を計算
            composition = self._calculate_fleet_composition(fleet_info)
            
            details = "艦隊編成:\n\n"
            
            # 艦種別サマリー
            details += "=== 艦種別隻数 ===\n"
            for ship_type, count in composition.items():
                ship_name = self.ship_icon_manager._abbreviation_to_display.get(ship_type, ship_type)
                details += f"  {ship_name} ({ship_type}): {count}隻\n"
            
            details += "\n=== 詳細編成 ===\n"
            
            for fleet in fleet_info:
                # MOD内編成かどうかを表示
                mod_prefix = "[MOD] " if fleet.get('is_mod', False) else ""
                details += f"{mod_prefix}艦隊: {fleet['name']}\n"
                
                for task_force in fleet.get('task_forces', []):
                    mod_prefix = "[MOD] " if task_force.get('is_mod', False) else ""
                    details += f"  {mod_prefix}任務部隊: {task_force['name']}\n"
                    
                    # 艦艇タイプごとの集計
                    task_force_composition = {}
                    for ship in task_force.get('ships', []):
                        ship_type = self._get_ship_type_from_design(ship)
                        task_force_composition[ship_type] = task_force_composition.get(ship_type, 0) + 1
                    
                    # 艦艇タイプごとの情報を表示
                    for ship_type, count in task_force_composition.items():
                        ship_name = self.ship_icon_manager._abbreviation_to_display.get(ship_type, ship_type)
                        mod_prefix = "[MOD] " if ship.get('is_mod', False) else ""
                        details += f"    {mod_prefix}{ship_name} ({ship_type}): {count}隻\n"
                details += "\n"
            
            QMessageBox.information(self, "艦隊情報", details)

    def show_fleet_details(self, province_id):
        """艦隊の詳細情報を表示する"""
        if province_id in self.fleet_data:
            fleet_info = self.fleet_data[province_id]
            details = "艦隊編成:\n\n"

            for fleet in fleet_info:
                details += f"艦隊: {fleet['name']}\n"
                for task_force in fleet.get('task_forces', []):
                    details += f"  任務部隊: {task_force['name']}\n"
                    # 艦艇タイプごとの集計
                    ship_counts = {}
                    for ship in task_force.get('ships', []):
                        ship_type = ship.get('design', 'unknown')
                        ship_counts[ship_type] = ship_counts.get(ship_type, 0) + 1

                    # 艦艇タイプごとの情報を表示
                    for ship_type, count in ship_counts.items():
                        details += f"    {ship_type}: {count}隻\n"
                details += "\n"

            QMessageBox.information(self, "艦隊情報", details)

    def search_province(self):
        """検索機能の修正版"""
        search_text = self.search_input.text().strip()
        if not search_text:
            self.search_result_label.setText("")
            return

        try:
            search_id = int(search_text)
            if search_id in self.provinces_data_by_id:
                province = self.provinces_data_by_id[search_id]
                self.search_result_label.setText(f"プロビンス {search_id}: {province.name}")

                # 修正: 固定ズームレベルでプロビンスに移動
                success = self.move_to_province_with_zoom(search_id, zoom_level=4.0)
                if not success:
                    self.search_result_label.setText(f"プロビンス {search_id} への移動に失敗しました")
            else:
                self.search_result_label.setText(f"プロビンス {search_id} は見つかりませんでした")
        except ValueError:
            self.search_result_label.setText("有効なIDを入力してください")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 左クリックでドラッグ開始位置を記録し、アニメーションを停止
            self._last_drag_pos = event.pos()
            if self._animation and self._animation.state() == QPropertyAnimation.Running:
                self._animation.stop()
        elif event.button() == Qt.RightButton:
            # 右クリックでプロビンス情報ダイアログを表示
            pos = self.mapToScene(event.pos())
            x, y = int(pos.x()), int(pos.y())

            # ループを考慮したX座標の調整
            adjusted_x = int(x % self.original_width)
            if adjusted_x < 0:  # 負の値になった場合の調整
                adjusted_x += self.original_width

            if self.original_map_image_data is not None and \
                    0 <= adjusted_x < self.original_width and 0 <= y < self.original_height:

                r, g, b = self.original_map_image_data[y, adjusted_x]
                province_id = self._rgb_to_id_map_array[r * 256 * 256 + g * 256 + b]

                if province_id != -1:
                    # 艦隊情報がある場合は、アイコン版の詳細情報を表示
                    if province_id in self.fleet_data:
                        self.show_fleet_details_with_icons(province_id)
                    else:
                        # 既存のプロビンス情報表示処理
                        self.show_province_info(province_id)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # マウスオーバー時のツールチップ処理
        scene_pos = self.mapToScene(event.pos())
        x, y = int(scene_pos.x()), int(scene_pos.y())

        # ループを考慮したX座標の調整
        adjusted_x = int(x % self.original_width)
        if adjusted_x < 0:
            adjusted_x += self.original_width

        if self.original_map_image_data is not None and \
                0 <= adjusted_x < self.original_width and 0 <= y < self.original_height:

            pixel_rgb = tuple(self.original_map_image_data[y, adjusted_x])
            found_province = self.provinces_data_by_rgb.get(pixel_rgb)

            if found_province:
                self.hovered_province = found_province
                tooltip_text = f"ID: {found_province.id}\n名前: {found_province.name}"

                if found_province.id in self.naval_base_locations:
                    tooltip_text += f"\n海軍基地レベル: {self.naval_base_locations[found_province.id]}"
                
                # 艦隊情報がある場合はツールチップに追加
                if found_province.id in self.fleet_data:
                    tooltip_text += "\n\n艦隊が存在します（右クリックで詳細表示）"

                tooltip_pos = self.mapToGlobal(event.pos())
                self.tooltip_label.setText(tooltip_text)
                self.tooltip_label.adjustSize()

                window_rect = self.window().geometry()
                tooltip_x = window_rect.right() - self.tooltip_label.width() - 10
                tooltip_y = window_rect.top() + 10

                self.tooltip_label.move(tooltip_x, tooltip_y)
                self.tooltip_label.show()
            else:
                self.hovered_province = None
                self.tooltip_label.hide()
        else:
            self.hovered_province = None
            self.tooltip_label.hide()

        # マップドラッグ処理 (左ボタン)
        if event.buttons() & Qt.LeftButton and hasattr(self, '_last_drag_pos'):
            delta = event.pos() - self._last_drag_pos
            self._last_drag_pos = event.pos()

            # X方向のスクロールはカスタムプロパティで制御
            self.scrollOffsetX = self.scrollOffsetX - delta.x()

            # Y方向のスクロールはQGraphicsViewの標準スクロール
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())

            # 慣性スクロールのために最後の移動量を記録
            self._last_move_delta = delta

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            # ドラッグ終了時に慣性スクロールを開始
            if self._animation.state() == QPropertyAnimation.Running:
                self._animation.stop()

            inertia_factor = 2.0  # 慣性の強さ (値を大きくすると長く滑る)

            # 最後の移動量に基づいて慣性スクロールの目標値を計算
            # 修正点: 慣性スクロールの方向も反転
            target_x = self.scrollOffsetX - self._last_move_delta.x() * inertia_factor

            self._animation.setStartValue(self.scrollOffsetX)
            self._animation.setEndValue(target_x)
            self._animation.start()

            # 慣性スクロールのための最後の移動量をリセット
            self._last_move_delta = QPoint(0, 0)

        # QGraphicsViewのデフォルトのドラッグモードは使用しないため、中ボタンの処理は不要
        # elif event.button() == Qt.MiddleButton:
        #     self.setDragMode(QGraphicsView.NoDrag)

        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.tooltip_label.hide()
        self.hovered_province = None

    def on_filter_changed(self, index):
        """フィルターが変更された時の処理"""
        self.current_filter = self.filter_combo.currentData()
        self.render_map()

    def zoom_in(self):
        self.scale(1.25, 1.25)
        # ズーム後もマップアイテムの位置を更新してループ描画を維持
        self.update_map_item_position()

    def zoom_out(self):
        self.scale(1.0 / 1.25, 1.0 / 1.25)
        # ズーム後もマップアイテムの位置を更新してループ描画を維持
        self.update_map_item_position()

    def wheelEvent(self, event):
        # マウスホイールによるズームを無効化（既存の動作を維持）
        pass

    def keyPressEvent(self, event):
        # キーボードショートカット
        if event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:  # +キーまたは=キー
            self.zoom_in()
        elif event.key() == Qt.Key_Minus:  # -キー
            self.zoom_out()
        elif event.key() == Qt.Key_Left:  # 左矢印キーで左にスクロール
            target_x = self.scrollOffsetX - 50  # 50ピクセル移動
            self._animation.setStartValue(self.scrollOffsetX)
            self._animation.setEndValue(target_x)
            self._animation.start()
        elif event.key() == Qt.Key_Right:  # 右矢印キーで右にスクロール
            target_x = self.scrollOffsetX + 50  # 50ピクセル移動
            self._animation.setStartValue(self.scrollOffsetX)
            self._animation.setEndValue(target_x)
            self._animation.start()
        elif event.key() == Qt.Key_Up:  # 上矢印キーで上にスクロール
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - 50)
        elif event.key() == Qt.Key_Down:  # 下矢印キーで下にスクロール
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + 50)
        else:
            super().keyPressEvent(event)

    def load_mod_fleet_data(self, mod_path, country_tag):
        """MOD内の艦隊データを読み込む"""
        self.logger.info(f"load_mod_fleet_data called: mod_path={mod_path}, country_tag={country_tag}")
        if not mod_path or not country_tag:
            return None

        try:
            # 艦隊データを格納するディクショナリ
            fleet_data = {}

            # 艦隊データファイルのパス
            units_path = os.path.join(mod_path, "history", "units")
            if not os.path.exists(units_path):
                self.logger.info(f"艦隊データディレクトリが見つかりません: {units_path}")
                return None

            # 艦隊データファイルを検索

            pattern = re.compile(f"{country_tag}_\\d{{4}}_(?:naval|Naval|Navy|navy)(?:_mtg)?\\.txt$")

            for filename in os.listdir(units_path):
                if pattern.match(filename):
                    file_path = os.path.join(units_path, filename)
                    self.logger.info(f"艦隊データファイルを読み込み: {filename}")

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                            # NavalOOBParserを使用して艦隊データを解析
                            parser = NavalOOBParser(content)
                            parsed_data = parser.parse()

                            # 艦隊データを抽出
                            units = parsed_data.get('units', {})
                            fleets = units.get('fleet', [])

                            # 単一の艦隊の場合はリストに変換
                            if isinstance(fleets, dict):
                                fleets = [fleets]

                            # 艦隊データを処理
                            for fleet in fleets:
                                fleet_data_entry = {
                                    'name': fleet.get('name', f"MOD艦隊_{len(fleet_data)}"),
                                    'province_id': fleet.get('naval_base', 0),
                                    'task_forces': []
                                }

                                # 任務部隊を処理
                                task_forces = fleet.get('task_force', [])
                                if isinstance(task_forces, dict):
                                    task_forces = [task_forces]

                                for task_force in task_forces:
                                    task_force_entry = {
                                        'name': task_force.get('name',
                                                               f"MOD任務部隊_{len(fleet_data_entry['task_forces'])}"),
                                        'province_id': task_force.get('location', fleet_data_entry['province_id']),
                                        'ships': []
                                    }

                                    # 艦艇を処理
                                    ships = task_force.get('ship', [])
                                    if isinstance(ships, dict):
                                        ships = [ships]

                                    for ship in ships:
                                        ship_entry = {
                                            'name': ship.get('name', f"MOD艦艇_{len(task_force_entry['ships'])}"),
                                            'exp': float(ship.get('experience', 0)),
                                            'is_pride': ship.get('pride_of_the_fleet') == 'yes',
                                            'design': ship.get('definition', {})
                                        }
                                        task_force_entry['ships'].append(ship_entry)

                                    fleet_data_entry['task_forces'].append(task_force_entry)

                                # 艦隊データを保存
                                prov_id = fleet_data_entry['province_id']
                                if prov_id not in fleet_data:
                                    fleet_data[prov_id] = []
                                fleet_data[prov_id].append(fleet_data_entry)

                    except Exception as e:
                        self.logger.error(f"艦隊データファイルの読み込みエラー: {e}")
                        continue

            self.logger.info(f"MOD内の艦隊データ読み込み完了: {len(fleet_data)}個のプロビンスに艦隊が存在")
            return fleet_data

        except Exception as e:
            self.logger.error(f"MOD内の艦隊データ読み込み中にエラーが発生: {e}")
            return None

    def set_fleet_data(self, fleet_data, country_tag, show_mod_fleets=False):
        """艦隊情報を設定する"""
        self.logger.info(f"set_fleet_data called: country_tag={country_tag}, show_mod_fleets={show_mod_fleets}")
        self.logger.info(f"艦隊データのプロビンス数: {len(fleet_data) if fleet_data else 0}")

        try:
            # 艦隊データを初期化
            self.fleet_data = {}

            # 基本の艦隊データを設定
            if fleet_data:
                if not isinstance(fleet_data, dict):
                    self.logger.error(f"無効な艦隊データの型: {type(fleet_data)}")
                    return

                # 艦隊データの検証
                for prov_id, fleets in fleet_data.items():
                    if not isinstance(fleets, list):
                        self.logger.error(f"プロビンス {prov_id} の艦隊データが無効な型です: {type(fleets)}")
                        continue

                    valid_fleets = []
                    for fleet in fleets:
                        if not isinstance(fleet, dict):
                            self.logger.warning(f"無効な艦隊データ: {fleet}")
                            continue

                        if 'task_forces' not in fleet:
                            self.logger.warning(f"任務部隊情報が欠落している艦隊データ: {fleet}")
                            continue

                        valid_fleets.append(fleet)

                    if valid_fleets:
                        self.fleet_data[prov_id] = valid_fleets

                self.logger.info(f"基本の艦隊データを設定: {len(self.fleet_data)}個のプロビンス")

            self.current_country = country_tag
            self.show_fleet_info = True
            self.show_mod_fleets = show_mod_fleets

            # MOD内の艦隊データを読み込む
            if show_mod_fleets and self.app_controller:
                try:
                    current_mod = self.app_controller.get_current_mod()
                    if current_mod and "path" in current_mod:
                        mod_fleet_data = self.load_mod_fleet_data(current_mod["path"], country_tag)
                        if mod_fleet_data and isinstance(mod_fleet_data, dict):
                            # 既存の艦隊データと統合
                            for prov_id, fleets in mod_fleet_data.items():
                                if not isinstance(fleets, list):
                                    self.logger.error(
                                        f"MOD内のプロビンス {prov_id} の艦隊データが無効な型です: {type(fleets)}")
                                    continue

                                if prov_id in self.fleet_data:
                                    self.fleet_data[prov_id].extend(fleets)
                                else:
                                    self.fleet_data[prov_id] = fleets
                            self.logger.info(
                                f"MOD内の艦隊データを統合しました: {len(self.fleet_data)}個のプロビンスに艦隊が存在")
                except Exception as e:
                    self.logger.error(f"MOD内の艦隊データ読み込みエラー: {str(e)}")

            # 艦隊データの状態を確認
            self.logger.info(f"艦隊データの最終状態: {len(self.fleet_data)}個のプロビンスに艦隊が存在")
            for prov_id, fleets in self.fleet_data.items():
                self.logger.info(f"プロビンス {prov_id}: {len(fleets)}個の艦隊")

            # 国家カラーモードに変更
            self.current_filter = "countries"
            self.filter_combo.setCurrentText("国家")

            # キャッシュをクリアして再描画
            self.base_qimage_cache.clear()
            self.logger.info("マップの再描画を開始")
            self.render_map()  # マップを再描画して艦隊情報を表示
            self.logger.info("マップの再描画が完了")

        except Exception as e:
            self.logger.error(f"艦隊データの設定中にエラーが発生: {str(e)}")
            self.fleet_data = {}
            self.show_fleet_info = False

    def clear_fleet_data(self):
        """艦隊情報をクリアする"""
        self.fleet_data = {}
        self.current_country = None
        self.show_fleet_info = False  # クリア時のみFalseに設定
        self.render_map()  # マップを再描画して艦隊情報を非表示

    def get_state_owner(self, state_id):
        """ステートの所有者を取得"""
        return self.state_owners.get(state_id)

    def move_to_province(self, province_id):
        """指定されたプロビンスIDの位置に地図を移動する（型エラー修正版）"""
        if province_id in self.province_centroids and self.province_centroids[province_id] is not None:
            # プロビンスの中心座標を取得
            center_x, center_y = self.province_centroids[province_id]
            
            # アニメーションを停止
            if hasattr(self, '_animation') and self._animation.state() == QPropertyAnimation.Running:
                self._animation.stop()
            
            # 現在のスケールを取得
            current_scale = self.transform().m11()
            
            # ビューポートの中心を計算
            viewport_center_x = self.viewport().width() / 2
            viewport_center_y = self.viewport().height() / 2
            
            # Y軸の計算（既存実装を維持）
            target_y = (center_y * current_scale) - viewport_center_y
            
            # X軸の計算（original_widthの加算を削除し、正確な計算に変更）
            base_target_x = (center_x * current_scale) - viewport_center_x
            
            # ループを考慮して、現在の表示位置に最も近いプロビンス位置を選択
            # 修正: int型でmapToSceneを呼び出し
            try:
                current_center_scene = self.mapToScene(int(viewport_center_x), int(viewport_center_y))
                current_center_x = current_center_scene.x()
            except Exception as e:
                # フォールバック: エラー時は基本計算を使用
                self.logger.warning(f"mapToScene エラー: {e}, フォールバック計算を使用")
                current_center_x = center_x
            
            # プロビンスの可能な表示位置（ループ考慮）
            possible_positions = []
            for i in range(-5, 6):  # -5から+5までのループ位置を考慮
                pos_x = center_x + (i * self.original_width)
                target_scroll = (pos_x * current_scale) - viewport_center_x
                distance = abs(pos_x - current_center_x)
                possible_positions.append((target_scroll, distance))
            
            # 現在位置に最も近い位置を選択
            best_target_x = min(possible_positions, key=lambda x: x[1])[0]
            
            # スクロール位置を設定
            self.scrollOffsetX = best_target_x
            self.verticalScrollBar().setValue(int(target_y))
            
            self.logger.info(f"プロビンス {province_id} の中心 ({center_x}, {center_y}) に移動 (スケール: {current_scale})")
            self.logger.debug(f"計算結果: target_x={best_target_x}, target_y={target_y}")
            return True
        else:
            self.logger.warning(f"プロビンス {province_id} の中心座標が見つかりません")
            return False

    def move_to_province_with_zoom(self, province_id, zoom_level=3.0):
        """指定されたプロビンスIDの位置に地図を移動し、指定されたズームレベルに設定する"""
        if province_id not in self.province_centroids or self.province_centroids[province_id] is None:
            self.logger.warning(f"プロビンス {province_id} の中心座標が見つかりません")
            return False
        
        # 現在のズームレベルを取得
        current_scale = self.transform().m11()
        
        # 目標ズームレベルに設定（絶対値指定）
        if abs(current_scale - zoom_level) > 0.1:  # 現在と異なる場合のみ変更
            self.set_absolute_zoom_level(zoom_level)
        
        # プロビンスに移動
        return self.move_to_province(province_id)

    def set_absolute_zoom_level(self, target_zoom_level):
        """指定されたズームレベルに絶対値で設定する"""
        try:
            # 現在のズームレベルを取得
            current_scale = self.transform().m11()
            
            # ズームレベルの制限（1.0〜10.0）
            target_zoom_level = max(1.0, min(10.0, target_zoom_level))
            
            # 目標ズームレベルとの比率を計算
            scale_factor = target_zoom_level / current_scale
            
            # 現在のビューポート中心のシーン座標を取得
            viewport_center = QPointF(self.viewport().width() / 2, self.viewport().height() / 2)
            scene_center = self.mapToScene(viewport_center.toPoint())
            
            # 中心を維持しながらスケールを適用
            self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
            self.scale(scale_factor, scale_factor)
            
            # スケール変更後、必要に応じてマップアイテムの位置を更新
            self.update_map_item_position()
            
            self.logger.info(f"ズームレベルを {current_scale:.2f} から {target_zoom_level:.2f} に設定")
            
        except Exception as e:
            self.logger.error(f"ズームレベル設定中にエラーが発生: {e}")

    def move_to_province_debounced(self, province_id, zoom_level=None, delay_ms=150):
        """デバウンス処理付きプロビンス移動"""
        # 前の移動処理をキャンセル
        if self._move_timer.isActive():
            self._move_timer.stop()
        
        # 移動データを保存
        self._pending_move_data = {
            'province_id': province_id,
            'zoom_level': zoom_level,
            'timestamp': time.time()
        }
        
        # 指定された遅延後に実行
        self._move_timer.start(delay_ms)

    def _execute_pending_move(self):
        """デバウンス処理により遅延実行される移動処理"""
        if self._pending_move_data is None:
            return
        
        try:
            province_id = self._pending_move_data['province_id']
            zoom_level = self._pending_move_data['zoom_level']
            
            if zoom_level is not None:
                success = self.move_to_province_with_zoom(province_id, zoom_level)
            else:
                success = self.move_to_province(province_id)
                
            if success:
                self.logger.info(f"デバウンス処理によりプロビンス {province_id} への移動を実行")
            else:
                self.logger.warning(f"プロビンス {province_id} への移動に失敗")
                
        except Exception as e:
            self.logger.error(f"デバウンス移動処理中にエラー: {e}")
        finally:
            self._pending_move_data = None

    def get_current_zoom_level(self):
        """現在のズームレベルを取得"""
        return self.transform().m11()

    def is_valid_zoom_level(self, zoom_level):
        """ズームレベルが有効範囲内かチェック"""
        return self._min_zoom <= zoom_level <= self._max_zoom

    def clamp_zoom_level(self, zoom_level):
        """ズームレベルを有効範囲内に制限"""
        return max(self._min_zoom, min(self._max_zoom, zoom_level))

    def calculate_optimal_scroll_position(self, center_x, center_y, target_scale=None):
        """最適なスクロール位置を計算する（型エラー修正版）"""
        if target_scale is None:
            target_scale = self.transform().m11()
        
        # ビューポートサイズを取得
        viewport_width = self.viewport().width()
        viewport_height = self.viewport().height()
        
        # Y軸の計算（既存の実装を基準）
        target_y = (center_y * target_scale) - (viewport_height / 2)
        
        # X軸の計算（ループ考慮版）
        base_target_x = (center_x * target_scale) - (viewport_width / 2)
        
        # 現在の表示中心を取得（修正: QPoint使用）
        try:
            viewport_center_point = QPoint(int(viewport_width // 2), int(viewport_height // 2))
            current_center = self.mapToScene(viewport_center_point)
            current_x = current_center.x()
        except Exception as e:
            self.logger.warning(f"mapToScene エラー: {e}, フォールバック使用")
            current_x = center_x  # フォールバック
        
        # ループを考慮した最適位置の計算
        optimal_positions = []
        
        for i in range(-3, 4):  # -3から+3のループ位置
            loop_x = center_x + (i * self.original_width)
            scroll_x = (loop_x * target_scale) - (viewport_width / 2)
            distance = abs(loop_x - current_x)
            optimal_positions.append((scroll_x, distance))
        
        # 最も近い位置を選択
        best_scroll_x = min(optimal_positions, key=lambda x: x[1])[0]
        
        return best_scroll_x, target_y

    def safe_move_to_province(self, province_id, zoom_level=None, max_retries=3):
        """エラー処理を強化したプロビンス移動"""
        for attempt in range(max_retries):
            try:
                if zoom_level is not None:
                    success = self.move_to_province_with_zoom(province_id, zoom_level)
                else:
                    success = self.move_to_province(province_id)
                
                if success:
                    return True
                else:
                    self.logger.warning(f"プロビンス移動失敗 (試行 {attempt + 1}/{max_retries})")
                    
            except Exception as e:
                self.logger.error(f"プロビンス移動エラー (試行 {attempt + 1}/{max_retries}): {e}")
                
            # 失敗時は少し待機
            if attempt < max_retries - 1:
                QTimer.singleShot(100, lambda: None)  # 100ms待機
        
        return False

    def toggle_mod_fleets(self):
        """MOD内の艦隊表示を切り替え"""
        self.show_mod_fleets = not self.show_mod_fleets
        self.render_map()  # マップを再描画

    def test_coordinate_calculation(self, test_provinces=None):
        """座標計算のテスト用メソッド"""
        if test_provinces is None:
            # デフォルトのテスト用プロビンスID
            test_provinces = [1, 100, 500, 1000]
        
        self.logger.info("=== 座標計算テスト開始 ===")
        
        for province_id in test_provinces:
            if province_id in self.province_centroids:
                center_x, center_y = self.province_centroids[province_id]
                
                # 各ズームレベルでの計算結果をテスト
                for zoom_level in [1.0, 2.0, 3.0, 5.0]:
                    scroll_x, scroll_y = self.calculate_optimal_scroll_position(
                        center_x, center_y, zoom_level
                    )
                    
                    self.logger.info(
                        f"プロビンス {province_id}: "
                        f"座標({center_x:.1f}, {center_y:.1f}), "
                        f"ズーム{zoom_level}, "
                        f"スクロール({scroll_x:.1f}, {scroll_y:.1f})"
                    )
        
        self.logger.info("=== 座標計算テスト完了 ===")

    def validate_move_accuracy(self, province_id, tolerance=50):
        """移動精度の検証（型エラー修正版）"""
        if province_id not in self.province_centroids:
            return False
        
        # プロビンスに移動
        success = self.move_to_province(province_id)
        if not success:
            return False
        
        # 現在の表示中心を取得（修正: int型でQPointを作成）
        try:
            viewport_center = QPoint(int(self.viewport().width() // 2), int(self.viewport().height() // 2))
            current_center = self.mapToScene(viewport_center)
            
            # プロビンスの座標を取得
            target_x, target_y = self.province_centroids[province_id]
            
            # 誤差を計算
            error_x = abs(current_center.x() - target_x)
            error_y = abs(current_center.y() - target_y)
            
            # 許容誤差内かチェック
            is_accurate = error_x <= tolerance and error_y <= tolerance
            
            self.logger.info(
                f"移動精度検証 - プロビンス {province_id}: "
                f"誤差X={error_x:.1f}, 誤差Y={error_y:.1f}, "
                f"精度OK={is_accurate} (許容誤差={tolerance})"
            )
            
            return is_accurate
        
        except Exception as e:
            self.logger.error(f"移動精度検証中にエラー: {e}")
            return False

    def benchmark_move_performance(self, test_provinces, iterations=5):
        """移動パフォーマンスのベンチマーク"""
        import time
        
        self.logger.info("=== 移動パフォーマンステスト開始 ===")
        
        total_times = []
        
        for province_id in test_provinces:
            if province_id not in self.province_centroids:
                continue
            
            times = []
            for i in range(iterations):
                start_time = time.time()
                success = self.move_to_province(province_id)
                end_time = time.time()
                
                if success:
                    times.append(end_time - start_time)
            
            if times:
                avg_time = sum(times) / len(times)
                total_times.extend(times)
                self.logger.info(f"プロビンス {province_id}: 平均 {avg_time*1000:.1f}ms")
        
        if total_times:
            overall_avg = sum(total_times) / len(total_times)
            self.logger.info(f"全体平均: {overall_avg*1000:.1f}ms")
        
        self.logger.info("=== パフォーマンステスト完了 ===")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HoI4 世界地図プレビュー")
        self.setGeometry(100, 100, 1200, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        control_panel_layout = QHBoxLayout()

        self.zoom_in_button = QPushButton("ズームイン")
        self.zoom_out_button = QPushButton("ズームアウト")
        control_panel_layout.addWidget(self.zoom_in_button)
        control_panel_layout.addWidget(self.zoom_out_button)

        control_panel_layout.addStretch(1)

        self.layout.addLayout(control_panel_layout)

        self.map_viewer = MapViewer(self)
        self.layout.addWidget(self.map_viewer)

        self.init_ui()

    def init_ui(self):
        self.zoom_in_button.clicked.connect(self.map_viewer.zoom_in)
        self.zoom_out_button.clicked.connect(self.map_viewer.zoom_out)

        file_menu = self.menuBar().addMenu("ファイル")
        select_mod_action = file_menu.addAction("Modパスを指定")
        select_mod_action.triggered.connect(self.select_mod_path)
        exit_action = file_menu.addAction("終了")
        exit_action.triggered.connect(self.close)

        QMessageBox.information(self, "開始",
                                "Modディレクトリを選択してください。\n(例: your_mod_name/)\n\nprovinces.bmp と definition.csv が map/ ディレクトリ以下に、\nhistory/states/ と map/strategicregions/ 以下にファイルが存在する必要があります。")
        self.select_mod_path()

    def select_mod_path(self):
        mod_path = QFileDialog.getExistingDirectory(self, "Modディレクトリを選択")
        if mod_path:
            if not self.map_viewer.load_map_data(mod_path):
                pass
        else:
            QMessageBox.information(self, "キャンセル", "Modディレクトリの選択がキャンセルされました。")


class MapViewerSettings:
    """MapViewer用の設定管理クラス"""
    
    def __init__(self):
        self.default_zoom_level = 3.0
        self.max_zoom_level = 10.0
        self.min_zoom_level = 0.5
        self.move_debounce_delay = 150  # ms
        self.coordinate_tolerance = 50  # pixels
        self.performance_mode = False
        
    def load_from_config(self, config_dict):
        """設定辞書から読み込み"""
        self.default_zoom_level = config_dict.get('default_zoom_level', self.default_zoom_level)
        self.max_zoom_level = config_dict.get('max_zoom_level', self.max_zoom_level)
        self.min_zoom_level = config_dict.get('min_zoom_level', self.min_zoom_level)
        self.move_debounce_delay = config_dict.get('move_debounce_delay', self.move_debounce_delay)
        self.coordinate_tolerance = config_dict.get('coordinate_tolerance', self.coordinate_tolerance)
        self.performance_mode = config_dict.get('performance_mode', self.performance_mode)
    
    def to_dict(self):
        """設定を辞書として出力"""
        return {
            'default_zoom_level': self.default_zoom_level,
            'max_zoom_level': self.max_zoom_level,
            'min_zoom_level': self.min_zoom_level,
            'move_debounce_delay': self.move_debounce_delay,
            'coordinate_tolerance': self.coordinate_tolerance,
            'performance_mode': self.performance_mode
        }


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
