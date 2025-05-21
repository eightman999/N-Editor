import logging
import sys
import os
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ".venv/lib/python3.13/site-packages/PyQt5/Qt5/plugins/platforms"
import sys
import os
import csv
import re
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QFileDialog, QVBoxLayout, QWidget, QMessageBox, QLabel,
    QPushButton, QHBoxLayout, QComboBox
)
from PyQt5.QtGui import QPixmap, QImage, QColor, QPainter
from PyQt5.QtCore import Qt, QRectF, QPointF
from PIL import Image
import numpy as np
import random # 色をランダムに割り当てるため
import time # パフォーマンス計測用

# HoI4データのパーサーユーティリティ (ブレースカウント方式に修正)
def parse_hoi4_file_content(content):
    # 行頭の 形式を除去
    content = re.sub(r'^\s*\\s*', '', content, flags=re.MULTILINE)

    # コメント行を除去
    content = re.sub(r'#.*', '', content)

    # provincesブロックを先に抽出
    provinces_match = re.search(r'provinces\s*=\s*{([^}]+)}', content, re.DOTALL)
    provinces_data = []
    if provinces_match:
        provinces_content = provinces_match.group(1)
        # 数字のみを抽出
        provinces_data = [int(x) for x in re.findall(r'\d+', provinces_content) if x.isdigit()]

    # トップレベルに "state = { ... }" または "strategic_region = { ... }" のようなブロックがあるか検索
    main_block_match = re.search(
        r'^\s*([a-zA-Z_][a-zA-Z0-9_]*|\d+)\s*=\s*{\s*(.+?)\s*}',
        content,
        re.MULTILINE | re.DOTALL
    )

    if main_block_match:
        main_key = main_block_match.group(1).strip()
        main_content = main_block_match.group(2)
        print(f"DEBUG: parse_hoi4_file_content - Found top-level block '{main_key}'. Content start: '{main_content[:100]}...'")
        parsed_data = _parse_block_content(main_content)
        # provincesデータを追加
        if provinces_data:
            parsed_data['provinces'] = provinces_data
        return parsed_data
    else:
        print("DEBUG: parse_hoi4_file_content - No top-level block 'key = { ... }' found. Parsing entire file content directly.")
        parsed_data = _parse_block_content(content)
        # provincesデータを追加
        if provinces_data:
            parsed_data['provinces'] = provinces_data
        return parsed_data

# 修正: ブレースカウント方式によるブロック内容のパース
def _parse_block_content(block_content):
    parsed_data = {}
    lines = block_content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # 行コメント除去（念のため）
        line = re.sub(r'#.*', '', line).strip()

        if not line:
            i += 1
            continue

        # キー = 値; の形式
        match_direct = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*|\d+)\s*=\s*([\"\'\w\d\.\-]+)', line)
        if match_direct:
            key_str = match_direct.group(1).strip()
            value_str = match_direct.group(2).strip()

            try:
                key = int(key_str)
            except ValueError:
                key = key_str

            try:
                parsed_data[key] = int(value_str)
            except ValueError:
                try:
                    parsed_data[key] = float(value_str)
                except ValueError:
                    parsed_data[key] = value_str.strip('"').strip("'")
            i += 1
            continue

        # キー = { ブロック } の形式
        match_block_start = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*|\d+)\s*=\s*\{', line)
        if match_block_start:
            key_str = match_block_start.group(1).strip()

            try:
                key = int(key_str)
            except ValueError:
                key = key_str

            block_level = 1 # 現在のブロックレベル
            block_content_lines = []

            # ブロックの開始行から次の行へ
            current_line_index = i + 1

            while current_line_index < len(lines):
                sub_line = lines[current_line_index]
                block_level += sub_line.count('{')
                block_level -= sub_line.count('}')

                if block_level == 0:
                    # ブロック終了
                    break

                block_content_lines.append(sub_line)
                current_line_index += 1

            if block_level != 0:
                print(f"WARNING: Unbalanced braces for key '{key_str}' starting at line {i+1}. Block not closed.")
                # 不完全なブロックでも、可能な限りパースを試みる

            block_content_str = "\n".join(block_content_lines)

            if key_str == 'resources': # resourcesブロックの特別処理
                # resourcesブロックは空でも有効なデータとして扱う
                if not block_content_str.strip():
                    parsed_data[key] = {}
                else:
                    parsed_data[key] = _parse_block_content(block_content_str)
            elif key_str == 'buildings': # buildingsブロックの特別処理
                # buildingsブロック内のプロビンスIDをキーとした特殊な構造を処理
                buildings_data = {}
                for sub_line in block_content_lines:
                    sub_line = sub_line.strip()
                    if not sub_line:
                        continue
                    
                    # プロビンスID = { ... } の形式を処理
                    prov_match = re.match(r'(\d+)\s*=\s*\{', sub_line)
                    if prov_match:
                        prov_id = int(prov_match.group(1))
                        # プロビンスIDのブロック内容を抽出
                        prov_block_start = sub_line.find('{')
                        prov_block_end = sub_line.rfind('}')
                        if prov_block_start != -1 and prov_block_end != -1:
                            prov_block_content = sub_line[prov_block_start+1:prov_block_end].strip()
                            # プロビンス内の建物データをパース
                            prov_buildings = {}
                            for building_line in prov_block_content.split(';'):
                                building_line = building_line.strip()
                                if not building_line:
                                    continue
                                building_match = re.match(r'(\w+)\s*=\s*(\d+)', building_line)
                                if building_match:
                                    building_type = building_match.group(1)
                                    building_level = int(building_match.group(2))
                                    prov_buildings[building_type] = building_level
                            buildings_data[prov_id] = prov_buildings
                    else:
                        # 通常の建物データ（プロビンスIDなし）を処理
                        building_match = re.match(r'(\w+)\s*=\s*(\d+)', sub_line)
                        if building_match:
                            building_type = building_match.group(1)
                            building_level = int(building_match.group(2))
                            buildings_data[building_type] = building_level
                
                parsed_data[key] = buildings_data
            elif key_str == 'history': # historyブロックの特別処理
                # historyブロックの内容を再帰的にパース
                history_data = _parse_block_content(block_content_str)
                parsed_data[key] = history_data
            else:
                # ネストされたブロックを再帰的にパース
                parsed_data[key] = _parse_block_content(block_content_str)

            i = current_line_index + 1 # 次のブロックの開始行へ
            continue

        # どのパターンにもマッチしない行はスキップ
        i += 1

    return parsed_data


def get_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            print(f"Failed to read {file_path} with utf-8 or latin-1: {e}")
            return None
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
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
        self.setRenderHint(QPainter.Antialiasing)

        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        self.map_image_item = None
        self.original_map_image_data = None # 元のプロビンス画像データ (RGB配列)
        self.provinces_data_by_rgb = {} # (R, G, B) -> Province オブジェクト
        self.provinces_data_by_id = {} # province_id -> Province オブジェクト

        self.states_data = {}
        self.strategic_regions_data = {}

        self.original_width = 0
        self.original_height = 0

        self.current_filter = "provinces"
        self.base_qimage_cache = {} # フィルターごとのQImageをキャッシュ

        # 高速化のためのルックアップ配列を準備
        self._rgb_to_id_map_array = np.full(256*256*256, -1, dtype=np.int32)

    def load_map_data(self, mod_path):
        start_time = time.time()
        self.scene.clear()
        self.map_image_item = None
        self.original_map_image_data = None
        self.provinces_data_by_rgb = {}
        self.provinces_data_by_id = {}
        self.states_data = {}
        self.strategic_regions_data = {}
        self.base_qimage_cache = {} # キャッシュをクリア

        self._rgb_to_id_map_array.fill(-1)

        base_mod_dir = mod_path

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
            self.original_map_image_data = np.array(img_pil) # 元の画像データを保存

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
                            if rgb_hash < len(self._rgb_to_id_map_array): # 範囲チェック
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
                            state_raw_data = parse_hoi4_file_content(content) # 直接パース結果を取得

                            state_id = state_raw_data.get('id')

                            if state_id is None: # ファイル名からIDを推測するフォールバック
                                try:
                                    match = re.match(r'(\d+)[-].*\.txt', filename)
                                    state_id = int(match.group(1)) if match else int(os.path.splitext(filename)[0])
                                    print(f"DEBUG: Guessed state ID {state_id} from filename {filename}")
                                except ValueError:
                                    state_id = None

                            # `provinces` キーのチェックを強化
                            if state_id is not None and \
                                    'provinces' in state_raw_data and \
                                    isinstance(state_raw_data['provinces'], list) and \
                                    len(state_raw_data['provinces']) > 0: # プロビンスリストが空でないことも確認
                                state_name = state_raw_data.get('name', f"State {state_id}").strip('"')
                                state_color = QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                                self.states_data[state_id] = {
                                    'name': state_name,
                                    'provinces': state_raw_data['provinces'],
                                    'color': (state_color.red(), state_color.green(), state_color.blue()),
                                    'raw_data': state_raw_data
                                }
                                for prov_id in state_raw_data['provinces']:
                                    if prov_id in self.provinces_data_by_id:
                                        self.provinces_data_by_id[prov_id].state_id = state_id
                                print(f"Successfully loaded state file: {filename} (ID: {state_id}, Provinces: {len(state_raw_data['provinces'])})")
                            else:
                                print(f"Skipping state file {filename}: Missing 'id', 'provinces' key, or 'provinces' is not a non-empty list. Parsed data: {state_raw_data}")
                        else:
                            print(f"Skipping state file {filename}: Could not read content.")
            else:
                print(f"State directory not found: {states_dir}")
            print(f"Loaded {len(self.states_data)} states.")

            # 戦略地域の読み込み (map/strategicregions)
            self.strategic_regions_data = {}
            strategic_regions_dir = os.path.join(base_mod_dir, 'map', 'strategicregions') # 's' を削除

            if os.path.exists(strategic_regions_dir):
                print(f"Loading strategic regions from: {strategic_regions_dir}")
                for filename in os.listdir(strategic_regions_dir):
                    if filename.endswith('.txt'):
                        file_path = os.path.join(strategic_regions_dir, filename)
                        content = get_file_content(file_path)
                        if content:
                            region_raw_data = parse_hoi4_file_content(content) # 直接パース結果を取得

                            region_id = region_raw_data.get('id')

                            if region_id is None: # ファイル名からIDを推測するフォールバック
                                try:
                                    match = re.match(r'(\d+)[-].*\.txt', filename)
                                    region_id = int(match.group(1)) if match else int(os.path.splitext(filename)[0])
                                    print(f"DEBUG: Guessed strategic region ID {region_id} from filename {filename}")
                                except ValueError:
                                    region_id = None

                            if region_id is not None and \
                                    'provinces' in region_raw_data and \
                                    isinstance(region_raw_data['provinces'], list) and \
                                    len(region_raw_data['provinces']) > 0: # プロビンスリストが空でないことも確認
                                region_name = region_raw_data.get('name', f"Strategic Region {region_id}").strip('"')
                                region_color = QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                                self.strategic_regions_data[region_id] = {
                                    'name': region_name,
                                    'provinces': region_raw_data['provinces'],
                                    'color': (region_color.red(), region_color.green(), region_color.blue()),
                                    'raw_data': region_raw_data
                                }
                                for prov_id in region_raw_data['provinces']:
                                    if prov_id in self.provinces_data_by_id:
                                        self.provinces_data_by_id[prov_id].strategic_region_id = region_id
                                print(f"Successfully loaded strategic region file: {filename} (ID: {region_id}, Provinces: {len(region_raw_data['provinces'])})")
                            else:
                                print(f"Skipping strategic region file {filename}: Missing 'id', 'provinces' key, or 'provinces' is not a non-empty list. Parsed data: {region_raw_data}")
                        else:
                            print(f"Skipping strategic region file {filename}: Could not read content.")
            else:
                print(f"Strategic region directory not found: {strategic_regions_dir}")
            print(f"Loaded {len(self.strategic_regions_data)} strategic regions.")

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

                    if prov_obj.strategic_region_id is not None and prov_obj.strategic_region_id in self.strategic_regions_data:
                        self._palette_region[prov_id] = self.strategic_regions_data[prov_obj.strategic_region_id]['color']

            self.render_map()
            end_time = time.time()
            print(f"Total map data loading and initial rendering time: {end_time - start_time:.2f} seconds.")
            return True

        except Exception as e:
            QMessageBox.critical(self, "ロードエラー", f"地図データの読み込み中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            return False

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

        pixmap = QPixmap.fromImage(self.base_qimage_cache[self.current_filter])

        self.scene.clear()
        self.map_image_item = self.scene.addPixmap(pixmap)
        self.setSceneRect(QRectF(pixmap.rect()))
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        end_time = time.time()
        print(f"Map rendering time for filter '{self.current_filter}': {end_time - start_time:.2f} seconds.")

    def set_filter(self, filter_type):
        self.current_filter = filter_type
        self.render_map()

    def zoom_in(self):
        self.scale(1.15, 1.15)

    def zoom_out(self):
        self.scale(1.0 / 1.15, 1.0 / 1.15)

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
                            info_text += f"所属戦略地域ID: {found_province.strategic_region_id} (名前: {region_name})"
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
                                info_text = f"--- 戦略地域情報 (プロビンスID: {found_province.id}) ---\n"
                                raw_data = region_info['raw_data']
                                info_text += f"ID: {raw_data.get('id', 'N/A')}\n"
                                info_text += f"名前: {raw_data.get('name', 'N/A')}\n"
                                weather_data = raw_data.get('weather', {})
                                if weather_data:
                                    info_text += "天気情報:\n"
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
                                info_text += f"含むプロビンス数: {len(region_info['provinces'])}"
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

        self.filter_combobox = QComboBox()
        self.filter_combobox.addItem("プロビンス")
        self.filter_combobox.addItem("ステート")
        self.filter_combobox.addItem("戦略地域")
        control_panel_layout.addWidget(QLabel("表示フィルター:"))
        control_panel_layout.addWidget(self.filter_combobox)

        control_panel_layout.addStretch(1)

        self.layout.addLayout(control_panel_layout)

        self.map_viewer = MapViewer(self)
        self.layout.addWidget(self.map_viewer)

        self.init_ui()

    def init_ui(self):
        self.zoom_in_button.clicked.connect(self.map_viewer.zoom_in)
        self.zoom_out_button.clicked.connect(self.map_viewer.zoom_out)
        self.filter_combobox.currentIndexChanged.connect(self.on_filter_changed)

        file_menu = self.menuBar().addMenu("ファイル")
        select_mod_action = file_menu.addAction("Modパスを指定")
        select_mod_action.triggered.connect(self.select_mod_path)
        exit_action = file_menu.addAction("終了")
        exit_action.triggered.connect(self.close)

        QMessageBox.information(self, "開始", "Modディレクトリを選択してください。\n(例: your_mod_name/)\n\nprovinces.bmp と definition.csv が map/ ディレクトリ以下に、\nhistory/states/ と map/strategicregions/ 以下にファイルが存在する必要があります。")
        self.select_mod_path()

    def on_filter_changed(self, index):
        filter_type = self.filter_combobox.currentText()
        if filter_type == "プロビンス":
            self.map_viewer.set_filter("provinces")
        elif filter_type == "ステート":
            self.map_viewer.set_filter("states")
        elif filter_type == "戦略地域":
            self.map_viewer.set_filter("strategic_regions")

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