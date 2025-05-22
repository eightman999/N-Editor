import logging
import sys
import os
os.environ["QT_QPA_PLATFORM_PLATFORM_PATH"] = ".venv/lib/python3.13/site-packages/PyQt5/Qt5/plugins/platforms"
import sys
import os
import csv
import re
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QFileDialog, QVBoxLayout, QWidget, QMessageBox, QLabel,
    QPushButton, QHBoxLayout, QComboBox, QLineEdit
)
from PyQt5.QtGui import QPixmap, QImage, QColor, QPainter, QFont, QPen
from PyQt5.QtCore import Qt, QRectF, QPointF
from PIL import Image
import numpy as np
import random # 色をランダムに割り当てるため
import time # パフォーマンス計測用
from parser.StateParser import StateParser
from parser.StateParser import ParserError
from parser.StrategicRegionParser import StrategicRegionParser
from parser.CountryColorParser import CountryColorParser

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
            print(f"ファイルの読み込みに失敗しました: {file_path} - {str(e)}")
            return None
    except Exception as e:
        print(f"ファイルの読み込みに失敗しました: {file_path} - {str(e)}")
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

        self._rgb_to_id_map_array.fill(-1)
        self.province_centroids = {}
        self.naval_base_locations = {}
        self.state_boundaries = {}

        base_mod_dir = mod_path

        # 国家の色情報を読み込む
        colors_txt_path = os.path.join(base_mod_dir, 'common', 'countries', 'colors.txt')
        if os.path.exists(colors_txt_path):
            print(f"Loading country colors from: {colors_txt_path}")
            content = get_file_content(colors_txt_path)
            if content:
                parser = CountryColorParser(content)
                self.country_colors = parser.parse()
                print(f"Loaded {len(self.country_colors)} country colors")
                # デバッグ: 国家の色情報を出力
                print("\n=== 国家の色情報 ===")
                for country, color_data in self.country_colors.items():
                    print(f"国家: {country}, 色: {color_data['color']}")
                print("===================\n")

        provinces_img_path = os.path.join(base_mod_dir, 'map', 'provinces.bmp')
        print(f"Searching for provinces.bmp at: {provinces_img_path}")
        if not os.path.exists(provinces_img_path):
            QMessageBox.critical(self, "エラー", f"provinces.bmp が指定されたModパスのmap/ ディレクトリ以下に見つかりません。\n({provinces_img_path})")
            return False

        definition_csv_path = os.path.join(base_mod_dir, 'map', 'definition.csv')
        print(f"Searching for definition.csv at: {definition_csv_path}")
        if not os.path.exists(definition_csv_path):
            QMessageBox.critical(self, "エラー", f"definition.csv が指定されたModパスのmap/ ディレクトリ以下に見つかりません。\n({definition_csv_path})")
            return False

        try:
            print(f"Loading provinces image from: {provinces_img_path}")
            img_pil = Image.open(provinces_img_path).convert("RGB")
            self.original_width, self.original_height = img_pil.size
            self.original_map_image_data = np.array(img_pil)

            print(f"Loading definition.csv from: {definition_csv_path}")
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
                            print(f"Skipping malformed row in definition.csv: {row} - Error: {e}")
            print(f"Loaded {len(self.provinces_data_by_id)} provinces from definition.csv.")

            # ステートデータの読み込み
            states_dir = os.path.join(base_mod_dir, 'history', 'states')

            if os.path.exists(states_dir):
                print(f"Loading states from: {states_dir}")
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
                                        print(f"ステート {state_id} ({state_name}) の所有者: {owner}")
                                    else:
                                        print(f"ステート {state_id} ({state_name}) の所有者: なし")
                                    for prov_id in state_data['provinces']:
                                        if prov_id in self.provinces_data_by_id:
                                            self.provinces_data_by_id[prov_id].state_id = state_id

                                    # 海軍基地情報の取得
                                    if 'province_buildings' in state_data:
                                        for prov_id, buildings in state_data['province_buildings'].items():
                                            if isinstance(buildings, dict) and 'naval_base' in buildings:
                                                self.naval_base_locations[prov_id] = buildings['naval_base']
                                                print(f"Found naval base in province {prov_id} with level {buildings['naval_base']}")

                                    # print(f"Successfully loaded state file: {filename} (ID: {state_id}, Provinces: {len(state_data['provinces'])})")
                                else:
                                    print(f"Skipping state file {filename}: Missing 'id', 'provinces' key, or 'provinces' is empty.")
                            except ParserError as e:
                                print(f"Error parsing state file {filename}: {e}")
                            except Exception as e:
                                print(f"Unexpected error processing state file {filename}: {e}")
                        else:
                            print(f"Skipping state file {filename}: Could not read content.")
            else:
                print(f"State directory not found: {states_dir}")
            print(f"Loaded {len(self.states_data)} states.")

            # 戦略地域の読み込み (map/strategicregions)
            self.strategic_regions_data = {}
            strategic_regions_dir = os.path.join(base_mod_dir, 'map', 'strategicregions')

            if os.path.exists(strategic_regions_dir):
                print(f"Loading strategic regions from: {strategic_regions_dir}")
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
                                    print(f"Skipping strategic region file {filename}: Missing 'id', 'provinces' key, or 'provinces' is empty.")
                            except ParserError as e:
                                print(f"Error parsing strategic region file {filename}: {e}")
                            except Exception as e:
                                print(f"Unexpected error processing strategic region file {filename}: {e}")
                        else:
                            print(f"Skipping strategic region file {filename}: Could not read content.")
            else:
                print(f"Strategic region directory not found: {strategic_regions_dir}")
            print(f"Loaded {len(self.strategic_regions_data)} strategic regions.")

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
            print(f"Total map data loading and initial rendering time: {end_time - start_time:.2f} seconds.")
            print(f"DEBUG: naval_base_locations: {self.naval_base_locations}")
            return True

        except Exception as e:
            QMessageBox.critical(self, "ロードエラー", f"地図データの読み込み中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            return False

    def calculate_province_centroids(self):
        print("Calculating province centroids (highly optimized)...")
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
        print(f"Province centroid calculation time (highly optimized): {end_time - start_time:.2f} seconds.")

    def calculate_state_boundaries(self):
        print("Calculating state boundaries...")
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
        print(f"State boundary calculation time: {end_time - start_time:.2f} seconds")

    def render_map(self):
        start_time = time.time()
        if self.original_map_image_data is None:
            return

        if self.current_filter not in self.base_qimage_cache:
            print(f"Rendering map for filter: {self.current_filter} (and caching)")

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
                print("\n=== 国家モードの着色処理 ===")
                for state_id, state_data in self.states_data.items():
                    # StateParserから直接owner情報を取得
                    owner = state_data['raw_data'].get('owner', None)
                    print(f"ステート {state_id} の所有者: {owner}")
                    if owner and owner in self.country_colors:
                        color = self.country_colors[owner]['color']
                        print(f"  色を適用: {color}")
                        for prov_id in state_data['provinces']:
                            if prov_id <= max(self.provinces_data_by_id.keys()):
                                selected_palette[prov_id] = color
                    else:
                        print(f"  色が見つからないか所有者なし")
                print("========================\n")
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
            print(f"Loading map from cache for filter: {self.current_filter}")

        current_pixmap = QPixmap.fromImage(self.base_qimage_cache[self.current_filter])

        # 国家モードの場合、ステートの境界線を描画
        if self.current_filter == "countries":
            self.draw_state_boundaries(current_pixmap)

        self.draw_naval_bases(current_pixmap)

        self.scene.clear()
        self.map_image_item = self.scene.addPixmap(current_pixmap)
        self.setSceneRect(QRectF(current_pixmap.rect()))
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

        self.scale(4.0, 4.0)

        end_time = time.time()
        print(f"Map rendering time for filter '{self.current_filter}': {end_time - start_time:.2f} seconds.")

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

                # 外側の円（青い輪郭）
                painter.setPen(QPen(QColor(0, 0, 255, 200), 2))
                painter.setBrush(QColor(0, 0, 255, 100))
                painter.drawEllipse(QPointF(center_x, center_y), circle_radius, circle_radius)

                # 内側の円（白い輪郭）
                inner_radius = circle_radius * 0.7
                painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
                painter.setBrush(QColor(255, 255, 255, 150))
                painter.drawEllipse(QPointF(center_x, center_y), inner_radius, inner_radius)

        painter.end()

    def draw_selected_country_naval_bases(self, target_pixmap: QPixmap, country_tag: str):
        """選択された国家の海軍基地を赤色で描画"""
        if not country_tag or not self.states_data:
            return

        painter = QPainter(target_pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # 固定の円のサイズを使用
        circle_radius = 10  # 通常の海軍基地より少し大きく

        # 選択された国家のステートを特定
        selected_country_states = []
        for state_id, state_data in self.states_data.items():
            if state_data['raw_data'].get('owner') == country_tag:
                selected_country_states.append(state_id)

        # 選択された国家のステートに属する海軍基地を描画
        for prov_id, level in self.naval_base_locations.items():
            if prov_id in self.province_centroids and self.province_centroids[prov_id] is not None:
                # プロビンスが選択された国家のステートに属しているか確認
                prov_obj = self.provinces_data_by_id.get(prov_id)
                if prov_obj and prov_obj.state_id in selected_country_states:
                    center_x, center_y = self.province_centroids[prov_id]

                    # 外側の円（赤い輪郭）
                    painter.setPen(QPen(QColor(255, 0, 0, 200), 2))
                    painter.setBrush(QColor(255, 0, 0, 100))
                    painter.drawEllipse(QPointF(center_x, center_y), circle_radius, circle_radius)

                    # 内側の円（白い輪郭）
                    inner_radius = circle_radius * 0.7
                    painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
                    painter.setBrush(QColor(255, 255, 255, 150))
                    painter.drawEllipse(QPointF(center_x, center_y), inner_radius, inner_radius)

        painter.end()

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
                
                # ツールチップの位置を設定（マウス位置の右下に表示）
                tooltip_pos = self.mapToGlobal(event.pos())
                self.tooltip_label.setText(tooltip_text)
                self.tooltip_label.adjustSize()
                self.tooltip_label.move(tooltip_pos.x() + 2, tooltip_pos.y() + 2)
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
            scene_pos = self.mapToScene(event.pos())
            x, y = int(scene_pos.x()), int(scene_pos.y())

            if self.original_map_image_data is not None and \
                    0 <= y < self.original_height and 0 <= x < self.original_width:

                pixel_rgb = tuple(self.original_map_image_data[y, x])
                found_province = self.provinces_data_by_rgb.get(pixel_rgb)

                if found_province:
                    info_text = ""
                    if self.current_filter == "provinces":
                        info_text = f"--- プロビンス情報 ---\n"
                        info_text += f"ID: {found_province.id}\n"
                        info_text += f"名前: {found_province.name}\n"
                        info_text += f"タイプ: {found_province.type}\n"
                        if found_province.state_id is not None:
                            state_info = self.states_data.get(found_province.state_id)
                            state_name = state_info['name'] if state_info else f"Unknown State ({found_province.state_id})"
                            info_text += f"所属ステートID: {found_province.state_id} (名前: {state_name})\n"
                        if found_province.strategic_region_id is not None:
                            region_info = self.strategic_regions_data.get(found_province.strategic_region_id)
                            region_name = region_info['name'] if region_info else f"Unknown Strategic Region ({found_province.strategic_region_id})"
                            info_text += f"所属戦略地域ID: {found_province.strategic_region_id} (名前: {region_name})\n"
                        if found_province.id in self.naval_base_locations:
                            info_text += f"海軍基地レベル: {self.naval_base_locations[found_province.id]}\n"
                    elif self.current_filter == "states":
                        if found_province.state_id is not None:
                            state_info = self.states_data.get(found_province.state_id)
                            if state_info:
                                info_text = f"--- ステート情報 (プロビンスID: {found_province.id}) ---\n"
                                raw_data = state_info['raw_data']
                                info_text += f"ID: {raw_data.get('id', 'N/A')}\n"
                                info_text += f"名前: {raw_data.get('name', 'N/A')}\n"
                                info_text += f"Manpower: {raw_data.get('manpower', 'N/A')}\n"
                                info_text += f"カテゴリ: {raw_data.get('state_category', 'N/A')}\n"

                                history_data = raw_data.get('history', {})
                                if history_data:
                                    info_text += "履歴:\n"
                                    for h_key, h_val in history_data.items():
                                        h_key_str = str(h_key) if isinstance(h_key, int) else h_key
                                        if isinstance(h_val, dict):
                                            if h_key_str == 'buildings':
                                                info_text += "  建物:\n"
                                                for b_key, b_val in h_val.items():
                                                    b_key_str = str(b_key) if isinstance(b_key, int) else b_key
                                                    if isinstance(b_val, dict):
                                                        info_text += f"    {b_key_str}: {', '.join([f'{k}={v}' for k, v in b_val.items()])}\n"
                                                    else:
                                                        info_text += f"    {b_key_str}: {b_val}\n"
                                            else:
                                                info_text += f"  {h_key_str}: {', '.join([f'{k}={v}' for k, v in h_val.items()])}\n"
                                        elif isinstance(h_val, list):
                                            info_text += f"  {h_key_str}: {', '.join(map(str, h_val))}\n"
                                        else:
                                            info_text += f"  {h_key_str}: {h_val}\n"

                                info_text += f"含むプロビンス数: {len(state_info['provinces'])}"
                            else:
                                info_text = f"このプロビンス({found_province.id})はステートに属していません。"
                        else:
                            info_text = f"このプロビンス({found_province.id})はステートに属していません。"
                    elif self.current_filter == "strategic_regions":
                        if found_province.strategic_region_id is not None:
                            region_info = self.strategic_regions_data.get(found_province.strategic_region_id)
                            if region_info:
                                try:
                                    info_text = f"--- 戦略地域情報 (プロビンスID: {found_province.id}) ---\n"
                                    raw_data = region_info['raw_data']
                                    info_text += f"ID: {raw_data.get('id', 'N/A')}\n"
                                    info_text += f"名前: {raw_data.get('name', 'N/A')}\n"
                                    weather_data = raw_data.get('weather', {})
                                    if weather_data:
                                        info_text += "天気情報:\n"
                                        try:
                                            for w_key, w_val in weather_data.items():
                                                w_key_str = str(w_key) if isinstance(w_key, int) else w_key
                                                if isinstance(w_val, list):
                                                    info_text += f"  {w_key_str} ({len(w_val)} periods):\n"
                                                    for i, period in enumerate(w_val):
                                                        if isinstance(period, dict):
                                                            info_text += f"    Period {i+1}: {', '.join([f'{k}={v}' for k, v in period.items()])}\n"
                                                        else:
                                                            info_text += f"    Period {i+1}: {period}\n"
                                                elif isinstance(w_val, dict):
                                                    info_text += f"  {w_key_str}: {', '.join([f'{k}={v}' for k, v in w_val.items()])}\n"
                                                else:
                                                    info_text += f"  {w_key_str}: {w_val}\n"
                                        except Exception as e:
                                            info_text += f"  天気情報の表示中にエラーが発生しました: {str(e)}\n"
                                    info_text += f"含むプロビンス数: {len(region_info['provinces'])}"
                                except Exception as e:
                                    info_text = f"戦略地域情報の表示中にエラーが発生しました: {str(e)}"
                            else:
                                info_text = f"このプロビンス({found_province.id})は戦略地域に属していません。"
                        else:
                            info_text = f"このプロビンス({found_province.id})は戦略地域に属していません。"

                    if info_text:
                        QMessageBox.information(self, "情報", info_text)
                    else:
                        QMessageBox.information(self, "情報", "情報が見つかりませんでした。")
                else:
                    QMessageBox.information(self, "プロビンス情報", f"ID: なし (RGB: {pixel_rgb})\n恐らく海域など")
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