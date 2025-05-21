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

# HoI4データのパーサーユーティリティ
def parse_hoi4_file_content(content):
    data = {}

    # コメント行を除去
    content = re.sub(r'#.*', '', content)

    # より柔軟な正規表現で key = value または key = { ... } の形式を抽出
    # \s+ は1つ以上の空白文字（スペース、タブ、改行）にマッチ
    # (?:...) は非キャプチャグループ
    # block_contentは非貪欲マッチ `.+?` で、最短のマッチを試みる
    # key もしくは 数値のkey に対応 (\w+|\d+)
    pattern = re.compile(r'^\s*(\w+|\d+)\s*=\s*(?:([\"\'\w\d\.\-]+)|{\s*(.+?)\s*})', re.MULTILINE | re.DOTALL)

    for match in pattern.finditer(content):
        key = match.group(1).strip()
        value_direct = match.group(2) # name = "STATE_1" の "STATE_1" など
        value_block = match.group(3)  # { ... } の中身

        # 数値キーをintに変換
        try:
            key_converted = int(key)
        except ValueError:
            key_converted = key

        if value_direct:
            try:
                # 数値に変換を試みる (整数 -> 浮動小数点数)
                data[key_converted] = int(value_direct)
            except ValueError:
                try:
                    data[key_converted] = float(value_direct)
                except ValueError:
                    data[key_converted] = value_direct.strip().strip('"').strip("'") # 文字列のクォーテーションを除去
        elif value_block:
            # ブロック内の内容をパース
            if key == 'provinces':
                # provinces = { 1 2 3 } または provinces = { 12299 } 形式に対応
                # \b\d+\b は単語境界に囲まれた数字にマッチ (タブ区切りも対応)
                province_ids = [int(x) for x in re.findall(r'\b\d+\b', value_block) if x.isdigit()]
                data[key_converted] = province_ids
            else:
                # historyやbuildingsなどのブロックを再帰パース
                data[key_converted] = parse_hoi4_file_content(value_block)

    return data

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
        self.display_color = QColor(r, g, b) # デフォルトの表示色

class MapViewer(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)

        self.setDragMode(QGraphicsView.NoDrag) # デフォルトはNoDrag
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        self.map_image_item = None
        self.original_map_image_data = None # 元のプロビンス画像データ (RGB配列)
        self.provinces_data_by_rgb = {} # (R, G, B) -> Province オブジェクト
        self.provinces_data_by_id = {} # province_id -> Province オブジェクト

        self.states_data = {} # state_id -> {'name': ..., 'provinces': [...], 'color': ..., 'raw_data': {...}}
        self.strategic_regions_data = {} # region_id -> {'name': ..., 'provinces': [...], 'color': ..., 'raw_data': {...}}

        self.original_width = 0
        self.original_height = 0

        self.current_filter = "provinces" # デフォルトはプロビンス表示
        self.base_qimage_cache = {} # フィルターごとのQImageをキャッシュ

    def load_map_data(self, mod_path):
        self.scene.clear() # 既存のマップがあればクリア
        self.map_image_item = None
        self.original_map_image_data = None
        self.provinces_data_by_rgb = {}
        self.provinces_data_by_id = {}
        self.states_data = {}
        self.strategic_regions_data = {}
        self.base_qimage_cache = {} # キャッシュをクリア

        # Modディレクトリのみを対象とする
        base_mod_dir = mod_path

        # provinces.bmp をロード
        provinces_img_path = os.path.join(base_mod_dir, 'map', 'provinces.bmp')
        print(f"Searching for provinces.bmp at: {provinces_img_path}")
        if not os.path.exists(provinces_img_path):
            QMessageBox.critical(self, "エラー", f"provinces.bmp が指定されたModパスのmap/ ディレクトリ以下に見つかりません。\n({provinces_img_path})")
            return False

        # definition.csv をロード
        definition_csv_path = os.path.join(base_mod_dir, 'map', 'definition.csv')
        print(f"Searching for definition.csv at: {definition_csv_path}")
        if not os.path.exists(definition_csv_path):
            QMessageBox.critical(self, "エラー", f"definition.csv が指定されたModパスのmap/ ディレクトリ以下に見つかりません。\n({definition_csv_path})")
            return False

        try:
            # provinces.bmp をPillowで読み込み、NumPy配列に変換
            print(f"Loading provinces image from: {provinces_img_path}")
            img_pil = Image.open(provinces_img_path).convert("RGB")
            self.original_width, self.original_height = img_pil.size
            self.original_map_image_data = np.array(img_pil) # 元の画像データを保存

            # definition.csv を読み込み
            print(f"Loading definition.csv from: {definition_csv_path}")
            self.provinces_data_by_rgb = {}
            self.provinces_data_by_id = {}
            with open(definition_csv_path, 'r', encoding='latin-1') as f:
                reader = csv.reader(f, delimiter=';')
                next(reader) # ヘッダー行をスキップ
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
                        except ValueError as e:
                            print(f"Skipping malformed row in definition.csv: {row} - Error: {e}")
                            continue
            print(f"Loaded {len(self.provinces_data_by_id)} provinces from definition.csv.")

            # ステートデータの読み込み
            self.states_data = {}
            states_dir = os.path.join(base_mod_dir, 'history', 'states')

            if os.path.exists(states_dir):
                print(f"Loading states from: {states_dir}")
                for filename in os.listdir(states_dir):
                    if filename.endswith('.txt'):
                        file_path = os.path.join(states_dir, filename)
                        content = get_file_content(file_path)
                        if content:
                            state_raw_data = parse_hoi4_file_content(content)
                            state_id = state_raw_data.get('id')

                            if state_id is None:
                                try:
                                    # ファイル名からIDを推測 (例: 1-France.txt -> ID 1)
                                    # ファイル名が 'ID-Name.txt' の形式の場合
                                    match = re.match(r'(\d+)[-].*\.txt', filename)
                                    if match:
                                        state_id = int(match.group(1))
                                    else: # IDのみのファイル名の場合
                                        state_id = int(os.path.splitext(filename)[0])
                                except ValueError:
                                    state_id = None

                            if state_id is not None and 'provinces' in state_raw_data and isinstance(state_raw_data['provinces'], list):
                                state_name = state_raw_data.get('name', f"State {state_id}").strip('"')
                                state_color = QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                                self.states_data[state_id] = {
                                    'name': state_name,
                                    'provinces': state_raw_data['provinces'],
                                    'color': state_color,
                                    'raw_data': state_raw_data # 元のデータを保存
                                }
                                for prov_id in state_raw_data['provinces']:
                                    if prov_id in self.provinces_data_by_id:
                                        self.provinces_data_by_id[prov_id].state_id = state_id
                            else:
                                print(f"Skipping state file {filename}: Missing 'id' or 'provinces' (or provinces not a list). Parsed data: {state_raw_data}")
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
                            region_raw_data = parse_hoi4_file_content(content)
                            region_id = region_raw_data.get('id')

                            # IDがなければファイル名から推測
                            if region_id is None:
                                try:
                                    # ファイル名が 'ID-Name.txt' の形式の場合
                                    match = re.match(r'(\d+)[-].*\.txt', filename)
                                    if match:
                                        region_id = int(match.group(1))
                                    else: # IDのみのファイル名の場合
                                        region_id = int(os.path.splitext(filename)[0])
                                except ValueError:
                                    region_id = None

                            if region_id is not None and 'provinces' in region_raw_data and isinstance(region_raw_data['provinces'], list):
                                region_name = region_raw_data.get('name', f"Strategic Region {region_id}").strip('"')
                                region_color = QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                                self.strategic_regions_data[region_id] = {
                                    'name': region_name,
                                    'provinces': region_raw_data['provinces'],
                                    'color': region_color,
                                    'raw_data': region_raw_data # 元のデータを保存
                                }
                                for prov_id in region_raw_data['provinces']:
                                    if prov_id in self.provinces_data_by_id:
                                        self.provinces_data_by_id[prov_id].strategic_region_id = region_id
                            else:
                                print(f"Skipping strategic region file {filename}: Missing 'id' or 'provinces' (or provinces not a list). Parsed data: {region_raw_data}")
            else:
                print(f"Strategic region directory not found: {strategic_regions_dir}")
            print(f"Loaded {len(self.strategic_regions_data)} strategic regions.")


            self.render_map() # 初期表示を現在のフィルターで描画
            print("All map data loaded successfully.")
            return True

        except Exception as e:
            QMessageBox.critical(self, "ロードエラー", f"地図データの読み込み中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc() # 詳細なエラー情報を出力
            return False

    def render_map(self):
        if self.original_map_image_data is None:
            return

        # キャッシュからQImageをロード、なければ生成
        if self.current_filter not in self.base_qimage_cache:
            print(f"Rendering map for filter: {self.current_filter} (and caching)")
            # NumPy配列を直接操作して色を割り当てる
            display_array = np.copy(self.original_map_image_data) # 元のデータをコピーして変更

            # 各ピクセルに対して色を適用
            # このループは依然として時間がかかり得るが、Python-NumPyの範囲ではこれが一般的
            for y in range(self.original_height):
                for x in range(self.original_width):
                    pixel_rgb = tuple(self.original_map_image_data[y, x])
                    province = self.provinces_data_by_rgb.get(pixel_rgb)

                    color_to_apply = (0, 0, 0) # デフォルトは黒 (海など)

                    if province:
                        if self.current_filter == "provinces":
                            color_to_apply = province.color_rgb
                        elif self.current_filter == "states":
                            if province.state_id is not None and province.state_id in self.states_data:
                                color = self.states_data[province.state_id]['color']
                                color_to_apply = (color.red(), color.green(), color.blue())
                            else:
                                color_to_apply = (50, 50, 50) # 未定義のステートは灰色
                        elif self.current_filter == "strategic_regions":
                            if province.strategic_region_id is not None and province.strategic_region_id in self.strategic_regions_data:
                                color = self.strategic_regions_data[province.strategic_region_id]['color']
                                color_to_apply = (color.red(), color.green(), color.blue())
                            else:
                                color_to_apply = (50, 50, 50) # 未定義の戦略地域は灰色

                    display_array[y, x] = color_to_apply

            # NumPy配列からQImageを作成 (これが最も時間のかかる部分)
            # `display_array.data` を直接使うことで、メモリコピーを減らす
            height, width, channel = display_array.shape
            bytes_per_line = channel * width
            q_image = QImage(display_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
            self.base_qimage_cache[self.current_filter] = q_image.copy() # QImageは参照を渡すのでコピーを保存
        else:
            print(f"Loading map from cache for filter: {self.current_filter}")

        pixmap = QPixmap.fromImage(self.base_qimage_cache[self.current_filter])

        self.scene.clear()
        self.map_image_item = self.scene.addPixmap(pixmap)
        self.setSceneRect(QRectF(pixmap.rect()))
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def set_filter(self, filter_type):
        self.current_filter = filter_type
        self.render_map()

    def zoom_in(self):
        self.scale(1.15, 1.15)

    def zoom_out(self):
        self.scale(1.0 / 1.15, 1.0 / 1.15)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # クリックされた位置のプロビンス情報を表示
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
                                        if isinstance(h_val, dict): # buildings = { infrastructure = 2 } や 12299 = { naval_base = 3 }
                                            if h_key == 'buildings':
                                                info_text += "  建物:\n"
                                                for b_key, b_val in h_val.items():
                                                    if isinstance(b_val, dict):
                                                        info_text += f"    {b_key}: {', '.join([f'{k}={v}' for k, v in b_val.items()])}\n"
                                                    else:
                                                        info_text += f"    {b_key}: {b_val}\n"
                                            else:
                                                info_text += f"  {h_key}: {', '.join([f'{k}={v}' for k, v in h_val.items()])}\n"
                                        elif isinstance(h_val, list): # victory_points = { 3838 3 }
                                            info_text += f"  {h_key}: {', '.join(map(str, h_val))}\n"
                                        else:
                                            info_text += f"  {h_key}: {h_val}\n"

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
                                # 天候情報も簡易的に表示
                                weather_data = raw_data.get('weather', {})
                                if weather_data:
                                    info_text += "天気情報:\n"
                                    # weatherブロック内のperiodもパースできるように改善されたため、表示
                                    for w_key, w_val in weather_data.items():
                                        if isinstance(w_val, list): # periodブロックが複数ある場合
                                            info_text += f"  {w_key} ({len(w_val)} periods):\n"
                                            for i, period in enumerate(w_val):
                                                if isinstance(period, dict):
                                                    info_text += f"    Period {i+1}: {', '.join([f'{k}={v}' for k, v in period.items()])}\n"
                                                else:
                                                    info_text += f"    Period {i+1}: {period}\n"
                                        elif isinstance(w_val, dict): # 単一のperiodブロック
                                            info_text += f"  {w_key}: {', '.join([f'{k}={v}' for k, v in w_val.items()])}\n"
                                        else:
                                            info_text += f"  {w_key}: {w_val}\n"
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
        elif event.button() == Qt.MiddleButton: # 中ボタンでドラッグ開始
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            super().mousePressEvent(event) # デフォルトのハンドドラッグ動作を呼び出す
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton: # 中ボタンを離したらドラッグ終了
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

        # コントロールパネル
        control_panel_layout = QHBoxLayout()

        # ズームボタン
        self.zoom_in_button = QPushButton("ズームイン")
        self.zoom_out_button = QPushButton("ズームアウト")
        control_panel_layout.addWidget(self.zoom_in_button)
        control_panel_layout.addWidget(self.zoom_out_button)

        # 地図フィルター選択
        self.filter_combobox = QComboBox()
        self.filter_combobox.addItem("プロビンス")
        self.filter_combobox.addItem("ステート")
        self.filter_combobox.addItem("戦略地域")
        control_panel_layout.addWidget(QLabel("表示フィルター:"))
        control_panel_layout.addWidget(self.filter_combobox)

        control_panel_layout.addStretch(1) # 右寄せにするためにスペーサーを追加

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
                pass # エラーメッセージはload_map_data内で表示される
        else:
            QMessageBox.information(self, "キャンセル", "Modディレクトリの選択がキャンセルされました。")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())