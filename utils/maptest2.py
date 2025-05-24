import logging
import sys
import os
import sys
import os
import csv
import re
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QFileDialog, QVBoxLayout, QWidget, QMessageBox, QLabel,
    QPushButton, QHBoxLayout, QComboBox, QLineEdit
)
from PyQt5.QtGui import QPixmap, QImage, QColor, QPainter, QFont, QPen, QBrush
from PyQt5.QtCore import Qt, QRectF, QPointF, QPoint
from PIL import Image
import numpy as np
import random # 色をランダムに割り当てるため
import time # パフォーマンス計測用
from parser.StateParser import StateParser
from parser.StateParser import ParserError
from parser.StrategicRegionParser import StrategicRegionParser
from parser.CountryColorParser import CountryColorParser
from parser.NavalOOBParser import NavalOOBParser

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
        
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing, False)

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

        self._rgb_to_id_map_array = np.full(256*256*256, -1, dtype=np.int32)

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
                # デバッグ: 国家の色情報を出力
                # print("\n=== 国家の色情報 ===")
                # for country, color_data in self.country_colors.items():
                #     print(f"国家: {country}, 色: {color_data['color']}")
                # print("===================\n")

        provinces_img_path = os.path.join(base_mod_dir, 'map', 'provinces.bmp')
        # print(f"Searching for provinces.bmp at: {provinces_img_path}")
        if not os.path.exists(provinces_img_path):
            QMessageBox.critical(self, "エラー", f"provinces.bmp が指定されたModパスのmap/ ディレクトリ以下に見つかりません。\n({provinces_img_path})")
            return False

        definition_csv_path = os.path.join(base_mod_dir, 'map', 'definition.csv')
        # print(f"Searching for definition.csv at: {definition_csv_path}")
        if not os.path.exists(definition_csv_path):
            QMessageBox.critical(self, "エラー", f"definition.csv が指定されたModパスのmap/ ディレクトリ以下に見つかりません。\n({definition_csv_path})")
            return False

        try:
            # print(f"Loading provinces image from: {provinces_img_path}")
            img_pil = Image.open(provinces_img_path).convert("RGB")
            self.original_width, self.original_height = img_pil.size
            self.original_map_image_data = np.array(img_pil)

            # print(f"Loading definition.csv from: {definition_csv_path}")
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
                            # print(f"Skipping malformed row in definition.csv: {row} - Error: {e}")
                            pass
            # print(f"Loaded {len(self.provinces_data_by_id)} provinces from definition.csv.")

            # ステートデータの読み込み
            states_dir = os.path.join(base_mod_dir, 'history', 'states')

            if os.path.exists(states_dir):
                # print(f"Loading states from: {states_dir}")
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
                                    state_color = QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                                    self.states_data[state_id] = {
                                        'name': state_name,
                                        'provinces': state_data['provinces'],
                                        'color': (state_color.red(), state_color.green(), state_color.blue()),
                                        'raw_data': state_data
                                    }
                                    # デバッグ: ステートの所有者情報を出力
                                    owner = state_data.get('owner')
                                    if owner:
                                        self.state_owners[state_id] = owner  # 所有者情報を保存
                                        # print(f"ステート {state_id} ({state_name}) の所有者: {owner}")
                                        pass
                                    else:
                                        # print(f"ステート {state_id} ({state_name}) の所有者: なし")
                                        pass
                                    for prov_id in state_data['provinces']:
                                        if prov_id in self.provinces_data_by_id:
                                            self.provinces_data_by_id[prov_id].state_id = state_id

                                    # 海軍基地情報の取得
                                    if 'province_buildings' in state_data:
                                        for prov_id, buildings in state_data['province_buildings'].items():
                                            if isinstance(buildings, dict) and 'naval_base' in buildings:
                                                self.naval_base_locations[prov_id] = buildings['naval_base']
                                                # print(f"Found naval base in province {prov_id} with level {buildings['naval_base']}")

                                    # print(f"Successfully loaded state file: {filename} (ID: {state_id}, Provinces: {len(state_data['provinces'])})")
                                else:
                                    # print(f"Skipping state file {filename}: Missing 'id', 'provinces' key, or 'provinces' is empty.")
                                    pass
                            except ParserError as e:
                                # print(f"Error parsing state file {filename}: {e}")
                                pass
                            except Exception as e:
                                # print(f"Unexpected error processing state file {filename}: {e}")
                                pass
                        else:
                            # print(f"Skipping state file {filename}: Could not read content.")
                            pass
            else:
                # print(f"State directory not found: {states_dir}")
                pass
            # print(f"Loaded {len(self.states_data)} states.")

            # 戦略地域の読み込み (map/strategicregions)
            self.strategic_regions_data = {}
            strategic_regions_dir = os.path.join(base_mod_dir, 'map', 'strategicregions')

            if os.path.exists(strategic_regions_dir):
                # print(f"Loading strategic regions from: {strategic_regions_dir}")
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
                                    region_color = QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                                    self.strategic_regions_data[region_id] = {
                                        'name': region_name,
                                        'provinces': region_data['provinces'],
                                        'color': (region_color.red(), region_color.green(), region_color.blue()),
                                        'raw_data': region_data
                                    }
                                    for prov_id in region_data['provinces']:
                                        if prov_id in self.provinces_data_by_id:
                                            self.provinces_data_by_id[prov_id].strategic_region_id = region_id
                                    # print(f"Successfully loaded strategic region file: {filename} (ID: {region_id}, Provinces: {len(region_data['provinces'])})")
                                else:
                                    # print(f"Skipping strategic region file {filename}: Missing 'id', 'provinces' key, or 'provinces' is empty.")
                                    pass
                            except ParserError as e:
                                # print(f"Error parsing strategic region file {filename}: {e}")
                                pass
                            except Exception as e:
                                # print(f"Unexpected error processing strategic region file {filename}: {e}")
                                pass
                        else:
                            # print(f"Skipping strategic region file {filename}: Could not read content.")
                            pass
            else:
                # print(f"Strategic region directory not found: {strategic_regions_dir}")
                pass
            # print(f"Loaded {len(self.strategic_regions_data)} strategic regions.")

            # プロビンス重心の計算
            self.calculate_province_centroids()

            # ステートの境界線を計算
            self.calculate_state_boundaries()

            # 高速化用の色マップを構築 (NumPy配列として)
            max_prov_id = max(self.provinces_data_by_id.keys()) if self.provinces_data_by_id else 0

            default_unknown_color = (50, 50, 50)

            self._palette_province = np.full((max_prov_id + 1, 3), (0,0,0), dtype=np.uint8)
            self._palette_state = np.full((max_prov_id + 1, 3), default_unknown_color, dtype=np.uint8)
            self._palette_region = np.full((max_prov_id + 1, 3), default_unknown_color, dtype=np.uint8)

            for prov_id, prov_obj in self.provinces_data_by_id.items():
                if prov_id <= max_prov_id:
                    self._palette_province[prov_id] = prov_obj.color_rgb

                    if prov_obj.state_id is not None and prov_obj.state_id in self.states_data:
                        self._palette_state[prov_id] = self.states_data[prov_obj.state_id]['color']

                    # strategic_regions_dataが空の場合もあるためチェック
                    if prov_obj.strategic_region_id is not None and self.strategic_regions_data and prov_obj.strategic_region_id in self.strategic_regions_data:
                        self._palette_region[prov_id] = self.strategic_regions_data[prov_obj.strategic_region_id]['color']

            self.render_map()
            end_time = time.time()
            # print(f"Total map data loading and initial rendering time: {end_time - start_time:.2f} seconds.")
            # print(f"DEBUG: naval_base_locations: {self.naval_base_locations}")
            return True

        except Exception as e:
            QMessageBox.critical(self, "ロードエラー", f"地図データの読み込み中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            return False

    def calculate_province_centroids(self):
        # print("Calculating province centroids (highly optimized)...")
        start_time = time.time()
        if self.original_map_image_data is None:
            return

        height, width, _ = self.original_map_image_data.shape

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
        for prov_id in self.provinces_data_by_id.keys():
            if prov_id <= max_prov_id and count_per_prov[prov_id] > 0:
                center_x = sum_x_per_prov[prov_id] / count_per_prov[prov_id]
                center_y = sum_y_per_prov[prov_id] / count_per_prov[prov_id]
                self.province_centroids[prov_id] = (center_x, center_y)
            else:
                self.province_centroids[prov_id] = None # プロビンスが存在しない、または画像中に見つからない場合

        end_time = time.time()
        # print(f"Province centroid calculation time (highly optimized): {end_time - start_time:.2f} seconds.")

    def calculate_state_boundaries(self):
        # print("Calculating state boundaries...")
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
        # print(f"State boundary calculation time: {end_time - start_time:.2f} seconds")

    def render_map(self):
        start_time = time.time()
        if self.original_map_image_data is None:
            print("マップデータが読み込まれていません")
            return

        print(f"render_map called: current_filter={self.current_filter}, show_fleet_info={self.show_fleet_info}")
        print(f"艦隊データの状態: {self.fleet_data}")
        
        if self.current_filter not in self.base_qimage_cache:
            print("キャッシュからマップを生成")
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
                selected_palette = np.full((max(self.provinces_data_by_id.keys()) + 1 if self.provinces_data_by_id else 1, 3), (50, 50, 50), dtype=np.uint8)
                for state_id, state_data in self.states_data.items():
                    owner = state_data['raw_data'].get('owner', None)
                    if owner and owner in self.country_colors:
                        color = self.country_colors[owner]['color']
                        for prov_id in state_data['provinces']:
                            if prov_id <= max(self.provinces_data_by_id.keys()):
                                selected_palette[prov_id] = color
            else:
                selected_palette = np.full((max(self.provinces_data_by_id.keys()) + 1 if self.provinces_data_by_id else 1, 3), (0,0,0), dtype=np.uint8)

            default_unknown_color = (50, 50, 50)
            filtered_colors_flat = np.full_like(original_pixels_flat, default_unknown_color, dtype=np.uint8)

            max_id_in_palette = selected_palette.shape[0] - 1
            valid_indices_for_palette_lookup = (prov_ids_flat >= 0) & (prov_ids_flat <= max_id_in_palette)

            filtered_colors_flat[valid_indices_for_palette_lookup] = selected_palette[prov_ids_flat[valid_indices_for_palette_lookup]]

            display_array = filtered_colors_flat.reshape(self.original_height, self.original_width, 3)

            height, width, channel = display_array.shape
            bytes_per_line = channel * width
            q_image = QImage(display_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
            self.base_qimage_cache[self.current_filter] = q_image.copy()
        else:
            print("キャッシュからマップを読み込み")
            pass

        current_pixmap = QPixmap.fromImage(self.base_qimage_cache[self.current_filter])

        # 国家モードの場合、ステートの境界線を描画
        if self.current_filter == "countries":
            print("ステートの境界線を描画")
            self.draw_state_boundaries(current_pixmap)

        self.draw_naval_bases(current_pixmap)
        
        # 艦隊情報を描画
        print(f"艦隊情報の描画条件チェック: show_fleet_info={self.show_fleet_info}, fleet_data={bool(self.fleet_data)}")
        if self.show_fleet_info and self.fleet_data:
            print("艦隊情報を描画")
            self.draw_fleet_info(current_pixmap)
        else:
            print(f"艦隊情報の描画をスキップ: show_fleet_info={self.show_fleet_info}, fleet_data={bool(self.fleet_data)}")

        self.scene.clear()
        self.map_image_item = self.scene.addPixmap(current_pixmap)
        self.setSceneRect(QRectF(current_pixmap.rect()))
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

        self.scale(4.0, 4.0)

        end_time = time.time()
        print(f"マップの描画が完了: 所要時間 {end_time - start_time:.2f}秒")

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
        """艦隊情報を描画"""
        if not self.show_fleet_info:
            self.logger.debug("艦隊情報の表示が無効です")
            return

        if not self.fleet_data:
            self.logger.debug("艦隊データが空です")
            return

        self.logger.info(f"draw_fleet_info called: show_fleet_info={self.show_fleet_info}, fleet_data={bool(self.fleet_data)}")
        self.logger.info(f"艦隊データのプロビンス数: {len(self.fleet_data)}")

        try:
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)

            # プロビンスごとに艦隊情報を描画
            for province_id, fleets in self.fleet_data.items():
                try:
                    self.logger.info(f"プロビンス {province_id} の処理開始")
                    
                    # プロビンスの中心座標を取得
                    if province_id not in self.province_centroids:
                        self.logger.warning(f"プロビンス {province_id} の中心座標が見つかりません")
                        continue

                    center_x, center_y = self.province_centroids[province_id]
                    # NumPyの浮動小数点数を整数に変換
                    center_x = int(center_x)
                    center_y = int(center_y)
                    self.logger.info(f"プロビンス {province_id} の中心座標: ({center_x}, {center_y})")

                    # 艦隊情報を描画
                    total_ships = 0
                    for fleet in fleets:
                        if not isinstance(fleet, dict):
                            self.logger.warning(f"無効な艦隊データ: {fleet}")
                            continue
                            
                        # 艦隊名のオーバーライドを確認
                        fleet_name = fleet.get('name', '')
                        if isinstance(fleet_name, dict) and 'override' in fleet_name:
                            fleet_name = fleet_name['override']
                            
                        for task_force in fleet.get('task_forces', []):
                            if not isinstance(task_force, dict):
                                self.logger.warning(f"無効な任務部隊データ: {task_force}")
                                continue
                                
                            # 任務部隊名のオーバーライドを確認
                            task_force_name = task_force.get('name', '')
                            if isinstance(task_force_name, dict) and 'override' in task_force_name:
                                task_force_name = task_force_name['override']
                                
                            ships = task_force.get('ships', [])
                            if not isinstance(ships, list):
                                self.logger.warning(f"無効な艦艇リスト: {ships}")
                                continue
                                
                            total_ships += len(ships)

                    self.logger.info(f"プロビンス {province_id} の総隻数: {total_ships}")

                    # 四角形のサイズを計算（艦艇数に応じて調整）
                    size = min(40, max(20, total_ships * 2))
                    rect_size = int(size)  # 整数に変換
                    rect_x = int(center_x - rect_size / 2)  # 整数に変換
                    rect_y = int(center_y - rect_size / 2)  # 整数に変換

                    self.logger.info(f"四角形の描画位置: ({rect_x}, {rect_y}), サイズ: {rect_size}")

                    # 四角形を描画
                    painter.setPen(QPen(Qt.black, 2))
                    painter.setBrush(QBrush(Qt.white))
                    painter.drawRect(rect_x, rect_y, rect_size, rect_size)

                    # 艦艇数を描画
                    painter.setPen(QPen(Qt.black))
                    font = QFont()
                    font.setPointSize(8)
                    painter.setFont(font)
                    painter.drawText(rect_x, rect_y, rect_size, rect_size, Qt.AlignCenter, str(total_ships))

                except Exception as e:
                    self.logger.error(f"プロビンス {province_id} の処理中にエラーが発生: {str(e)}")
                    continue

            painter.end()
            
        except Exception as e:
            self.logger.error(f"艦隊情報の描画中にエラーが発生: {str(e)}")
            if painter:
                painter.end()

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
        search_text = self.search_input.text().strip()
        if not search_text:
            self.search_result_label.setText("")
            return

        try:
            search_id = int(search_text)
            if search_id in self.provinces_data_by_id:
                province = self.provinces_data_by_id[search_id]
                self.search_result_label.setText(f"プロビンス {search_id}: {province.name}")
                
                # プロビンスの中心座標を取得
                if search_id in self.province_centroids and self.province_centroids[search_id] is not None:
                    center_x, center_y = self.province_centroids[search_id]
                    # その位置に移動
                    self.centerOn(center_x, center_y)
                    # ズームイン
                    self.scale(2.0, 2.0)
            else:
                self.search_result_label.setText(f"プロビンス {search_id} は見つかりませんでした")
        except ValueError:
            self.search_result_label.setText("有効なIDを入力してください")

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        
        # マウス位置をシーンの座標に変換
        scene_pos = self.mapToScene(event.pos())
        x, y = int(scene_pos.x()), int(scene_pos.y())

        # マウス位置が有効な範囲内かチェック
        if self.original_map_image_data is not None and \
                0 <= y < self.original_height and 0 <= x < self.original_width:
            
            # マウス位置のRGB値を取得
            pixel_rgb = tuple(self.original_map_image_data[y, x])
            found_province = self.provinces_data_by_rgb.get(pixel_rgb)

            # プロビンスが見つかった場合
            if found_province:
                self.hovered_province = found_province
                tooltip_text = f"ID: {found_province.id}\n名前: {found_province.name}"
                
                if found_province.id in self.naval_base_locations:
                    tooltip_text += f"\n海軍基地レベル: {self.naval_base_locations[found_province.id]}"
                
                # ツールチップの位置を右上に固定
                tooltip_pos = self.mapToGlobal(event.pos())
                self.tooltip_label.setText(tooltip_text)
                self.tooltip_label.adjustSize()
                
                # ウィンドウの右上に表示
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

    def zoom_out(self):
        self.scale(1.0 / 1.25, 1.0 / 1.25)

    def wheelEvent(self, event):
        # マウスホイールによるズームを無効化
        pass

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # マウス位置からプロビンスIDを取得
            pos = self.mapToScene(event.pos())
            x, y = int(pos.x()), int(pos.y())
            
            if 0 <= x < self.original_width and 0 <= y < self.original_height:
                r, g, b = self.original_map_image_data[y, x]
                rgb_key = (r, g, b)
                
                if rgb_key in self.provinces_data_by_rgb:
                    province = self.provinces_data_by_rgb[rgb_key]
                    if self.show_fleet_info:
                        self.show_fleet_details(province.id)
                    else:
                        # 既存のプロビンス情報表示処理
                        info = f"プロビンスID: {province.id}\n"
                        if province.name:
                            info += f"名前: {province.name}\n"
                        if province.type:
                            info += f"タイプ: {province.type}\n"
                        if province.state_id:
                            info += f"ステートID: {province.state_id}\n"
                        if province.strategic_region_id:
                            info += f"戦略地域ID: {province.strategic_region_id}\n"
                        
                        QMessageBox.information(self, "プロビンス情報", info)
        elif event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.NoDrag)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        # キーボードショートカット
        if event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:  # +キーまたは=キー
            self.zoom_in()
        elif event.key() == Qt.Key_Minus:  # -キー
            self.zoom_out()
        else:
            super().keyPressEvent(event)

    def load_mod_fleet_data(self, mod_path, country_tag):
        """MOD内の艦隊データを読み込む"""
        print(f"load_mod_fleet_data called: mod_path={mod_path}, country_tag={country_tag}")
        if not mod_path or not country_tag:
            return None

        try:
            # 艦隊データを格納するディクショナリ
            fleet_data = {}
            
            # 艦隊データファイルのパス
            units_path = os.path.join(mod_path, "history", "units")
            if not os.path.exists(units_path):
                print(f"艦隊データディレクトリが見つかりません: {units_path}")
                return None

            # 艦隊データファイルを検索
            import re
            pattern = re.compile(f"{country_tag}_\\d{{4}}_(?:naval|Naval|Navy|navy)(?:_mtg)?\\.txt$")
            
            for filename in os.listdir(units_path):
                if pattern.match(filename):
                    file_path = os.path.join(units_path, filename)
                    print(f"艦隊データファイルを読み込み: {filename}")
                    
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
                                        'name': task_force.get('name', f"MOD任務部隊_{len(fleet_data_entry['task_forces'])}"),
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
                        print(f"艦隊データファイルの読み込みエラー: {e}")
                        continue

            print(f"MOD内の艦隊データ読み込み完了: {len(fleet_data)}個のプロビンスに艦隊が存在")
            return fleet_data

        except Exception as e:
            print(f"MOD内の艦隊データ読み込み中にエラーが発生: {e}")
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
                                    self.logger.error(f"MOD内のプロビンス {prov_id} の艦隊データが無効な型です: {type(fleets)}")
                                    continue
                                    
                                if prov_id in self.fleet_data:
                                    self.fleet_data[prov_id].extend(fleets)
                                else:
                                    self.fleet_data[prov_id] = fleets
                            self.logger.info(f"MOD内の艦隊データを統合しました: {len(self.fleet_data)}個のプロビンスに艦隊が存在")
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

    def toggle_mod_fleets(self):
        """MOD内の艦隊表示を切り替え"""
        self.show_mod_fleets = not self.show_mod_fleets
        self.render_map()  # マップを再描画

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

        QMessageBox.information(self, "開始", "Modディレクトリを選択してください。\n(例: your_mod_name/)\n\nprovinces.bmp と definition.csv が map/ ディレクトリ以下に、\nhistory/states/ と map/strategicregions/ 以下にファイルが存在する必要があります。")
        self.select_mod_path()

    def select_mod_path(self):
        mod_path = QFileDialog.getExistingDirectory(self, "Modディレクトリを選択")
        if mod_path:
            if not self.map_viewer.load_map_data(mod_path):
                pass
        else:
            QMessageBox.information(self, "キャンセル", "Modディレクトリの選択がキャンセルされました。")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())