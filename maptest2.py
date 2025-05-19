import logging
import sys
import os
# os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ".venv/lib/python3.13/site-packages/PyQt5/Qt5/plugins/platforms"
import re
import csv
import cv2
import numpy as np
import pyopencl as cl
from enum import Enum
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QScrollArea, 
                           QFileDialog, QMessageBox, QPushButton, QVBoxLayout, 
                           QHBoxLayout, QWidget, QComboBox)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QPointF, QRectF
# Configure logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# 色表示モードの列挙型
class ColorMode(Enum):
    PROVINCE = 0  # プロヴィンスの色（definition.csvから）
    STATE = 1     # 州の色（自動生成）
    COUNTRY = 2   # 国家の色（colors.txtから）

# OpenCLカーネルコード
RENDER_KERNEL = """
__kernel void render_map(
    __global const int* prov_map,
    __global const int* state_provinces,
    __global const int* state_colors,
    __global const int* country_colors,
    __global const int* prov_colors,
    __global const int* naval_bases,
    __global const int* coastal_bunkers,
    __global uchar* output,
    const int width,
    const int height,
    const int num_states,
    const int max_provinces_per_state,
    const int show_province_borders,
    const int show_state_borders,
    const int color_mode,
    const int chunk_start_y,
    const int chunk_height
) {
    int x = get_global_id(0);
    int y = get_global_id(1) + chunk_start_y;
    
    if (x >= width || y >= chunk_start_y + chunk_height) return;
    
    int idx = y * width + x;
    int prov_id = prov_map[idx];
    
    // デフォルトの色（グレー）
    uchar3 color = (uchar3)(200, 200, 200);
    
    // 色表示モードに応じて色を設定
    if (color_mode == 0) {  // プロヴィンスの色
        color = (uchar3)(
            prov_colors[prov_id * 3],
            prov_colors[prov_id * 3 + 1],
            prov_colors[prov_id * 3 + 2]
        );
    } else if (color_mode == 1) {  // 州の色
        for (int i = 0; i < num_states; i++) {
            int state_start = i * max_provinces_per_state;
            int state_end = state_start + max_provinces_per_state;
            bool found = false;
            
            for (int j = state_start; j < state_end; j++) {
                if (state_provinces[j] == prov_id) {
                    color = (uchar3)(
                        state_colors[i * 3],
                        state_colors[i * 3 + 1],
                        state_colors[i * 3 + 2]
                    );
                    found = true;
                    break;
                }
            }
            if (found) break;
        }
    } else if (color_mode == 2) {  // 国家の色
        for (int i = 0; i < num_states; i++) {
            int state_start = i * max_provinces_per_state;
            int state_end = state_start + max_provinces_per_state;
            bool found = false;
            
            for (int j = state_start; j < state_end; j++) {
                if (state_provinces[j] == prov_id) {
                    color = (uchar3)(
                        country_colors[i * 3],
                        country_colors[i * 3 + 1],
                        country_colors[i * 3 + 2]
                    );
                    found = true;
                    break;
                }
            }
            if (found) break;
        }
    }
    
    // プロビンス境界の描画
    if (show_province_borders) {
        if (x > 0 && prov_map[y * width + (x-1)] != prov_id) {
            color = (uchar3)(0, 0, 0);
        }
        if (x < width-1 && prov_map[y * width + (x+1)] != prov_id) {
            color = (uchar3)(0, 0, 0);
        }
        if (y > 0 && prov_map[(y-1) * width + x] != prov_id) {
            color = (uchar3)(0, 0, 0);
        }
        if (y < height-1 && prov_map[(y+1) * width + x] != prov_id) {
            color = (uchar3)(0, 0, 0);
        }
    }
    
    // 出力
    output[idx * 3] = color.x;
    output[idx * 3 + 1] = color.y;
    output[idx * 3 + 2] = color.z;
}
"""

class MapView(QMainWindow):
    def __init__(self, modpath):
        super().__init__()
        self.modpath = modpath
        self.show_state_borders = True
        self.show_province_borders = True
        self.color_mode = ColorMode.PROVINCE
        
        # クリック可能な領域の情報を保持
        self.clickable_regions = []
        
        # ツールチップ用のラベル
        self.tooltip_label = QLabel(self)
        self.tooltip_label.setStyleSheet("background-color: rgba(0, 0, 0, 0.7); color: white; padding: 5px; border-radius: 3px;")
        self.tooltip_label.hide()
        
        # キャッシュ用の辞書
        self.render_cache = {}
        
        # OpenCLの初期化（GPUを優先）
        platforms = cl.get_platforms()
        gpu_device = None
        
        # 利用可能なGPUを探す
        for platform in platforms:
            devices = platform.get_devices(device_type=cl.device_type.GPU)
            if devices:
                gpu_device = devices[0]
                logger.info(f"Using GPU: {gpu_device.name}")
                break
        
        if gpu_device is None:
            logger.warning("No GPU found, falling back to CPU")
            # CPUデバイスを探す
            for platform in platforms:
                devices = platform.get_devices(device_type=cl.device_type.CPU)
                if devices:
                    gpu_device = devices[0]
                    logger.info(f"Using CPU: {gpu_device.name}")
                    break
        
        if gpu_device is None:
            logger.error("No OpenCL device found")
            QMessageBox.critical(self, 'Error', 'No OpenCL device found')
            sys.exit(1)
        
        self.ctx = cl.Context([gpu_device])
        self.queue = cl.CommandQueue(self.ctx)
        self.prg = cl.Program(self.ctx, RENDER_KERNEL).build()
        
        logger.info(f"Initializing MapView with modpath: {modpath}")
        # Load province image
        prov_path = os.path.join(modpath, 'map', 'provinces.bmp')
        logger.debug(f"Loading province image from {prov_path}")
        self.prov_img = cv2.imread(prov_path, cv2.IMREAD_UNCHANGED)
        if self.prov_img is None:
            logger.error(f"Failed to load provinces.bmp at {prov_path}")
            QMessageBox.critical(self, 'Error', 'Failed to load provinces.bmp')
            sys.exit(1)
        # Load definitions
        defs_path = os.path.join(modpath, 'map', 'definition.csv')
        logger.debug(f"Loading definitions from {defs_path}")
        self.defs, self.prov_colors = self._load_definitions(defs_path)
        logger.info(f"Loaded {len(self.defs)} province definitions")
        # Build province mapping
        self.prov_map = self._build_province_mapping()
        logger.info(f"Built province mapping: shape={self.prov_map.shape}")
        # Load states
        states_dir = os.path.join(modpath, 'history', 'states')
        logger.debug(f"Loading states from {states_dir}")
        self.states = self._load_states(states_dir)
        logger.info(f"Loaded {len(self.states)} states")
        if not self.states:
            logger.warning("No states loaded; displaying raw province image.")
            QMessageBox.warning(self, 'Warning', 'No states loaded. Displaying raw province map.')
        # Load country colors
        colors_path = os.path.join(modpath, 'common', 'countries', 'colors.txt')
        logger.debug(f"Loading country colors from {colors_path}")
        self.colors = self._load_country_colors(colors_path)
        logger.info(f"Loaded {len(self.colors)} country colors")
        
        # 全パターンの画像を事前生成
        self._generate_all_patterns()
        
        # Setup view
        self.label = QLabel()
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.label)
        
        # Create control buttons
        zoom_in_btn = QPushButton("+")
        zoom_out_btn = QPushButton("-")
        state_btn = QPushButton("State Borders")
        province_btn = QPushButton("Province Borders")
        
        # 色表示モードのコンボボックス
        self.color_mode_combo = QComboBox()
        self.color_mode_combo.addItems(["Province Colors", "State Colors", "Country Colors"])
        self.color_mode_combo.currentIndexChanged.connect(self._change_color_mode)
        
        # Set button states
        state_btn.setCheckable(True)
        state_btn.setChecked(True)
        province_btn.setCheckable(True)
        province_btn.setChecked(True)
        
        # Connect button signals
        zoom_in_btn.clicked.connect(lambda: self._zoom(1.1))
        zoom_out_btn.clicked.connect(lambda: self._zoom(0.9))
        state_btn.clicked.connect(self._toggle_state_borders)
        province_btn.clicked.connect(self._toggle_province_borders)
        
        # Create button layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(zoom_in_btn)
        button_layout.addWidget(zoom_out_btn)
        button_layout.addWidget(state_btn)
        button_layout.addWidget(province_btn)
        button_layout.addWidget(self.color_mode_combo)
        
        # Create main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.scroll)
        
        # Create central widget and set layout
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        self.scale = 1.0
        self.setWindowTitle('MapView')
        self._update_view()

    def _generate_all_patterns(self):
        """全パターンの画像を事前生成"""
        logger.info("Generating all pattern images...")
        # 全てのパターンの組み合わせを生成
        patterns = []
        for show_state in [False, True]:
            for show_province in [False, True]:
                for color_mode in ColorMode:
                    patterns.append((show_state, show_province, color_mode))
        
        h, w = self.prov_map.shape
        
        # チャンクサイズを設定（GPUのメモリ制限に応じて調整）
        CHUNK_HEIGHT = 256  # チャンクの高さ
        NUM_CHUNKS = (h + CHUNK_HEIGHT - 1) // CHUNK_HEIGHT  # 必要なチャンク数
        
        # 州のプロビンスリストを準備
        state_provinces = []
        state_colors = []
        country_colors = []
        prov_colors = []
        naval_bases = []
        coastal_bunkers = []
        
        # 最大プロビンス数を計算
        max_provinces = max(len(st['provinces']) for st in self.states.values())
        logger.info(f"Maximum provinces per state: {max_provinces}")
        
        # クリック可能な領域の情報をクリア
        self.clickable_regions = []
        
        # プロヴィンスの色情報を準備
        max_prov_id = max(self.defs.values())
        for pid in range(max_prov_id + 1):
            rgb = self.prov_colors.get(pid, (200, 200, 200))
            prov_colors.extend(rgb)
        
        for st in self.states.values():
            provs = st['provinces']
            state_provinces.extend(provs)
            state_provinces.extend([0] * (max_provinces - len(provs)))  # パディング
            
            # 州の色（自動生成）
            clr = self.colors.get(st['owner'], (200,200,200))
            clr = tuple(min(max(c, 0), 255) for c in clr)
            state_colors.extend(clr)
            
            # 国家の色
            country_clr = self.colors.get(st['owner'], (200,200,200))
            country_clr = tuple(min(max(c, 0), 255) for c in country_clr)
            country_colors.extend(country_clr)
            
            logger.debug(f"State color for {st['owner']}: {clr}")
            
            # 海軍基地と沿岸要塞のリストを作成
            naval_bases.extend(list(st['naval_base'].keys()))
            coastal_bunkers.extend(list(st['coastal_bunker'].keys()))
            
            # クリック可能な領域の情報を追加
            for pid in st['naval_base']:
                ys, xs = np.where(self.prov_map == pid)
                if xs.size:
                    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
                    self.clickable_regions.append({
                        'type': 'naval_base',
                        'province_id': pid,
                        'rect': QRectF(x0, y0, x1-x0, y1-y0)
                    })
            
            for pid in st['coastal_bunker']:
                ys, xs = np.where(self.prov_map == pid)
                if xs.size:
                    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
                    self.clickable_regions.append({
                        'type': 'coastal_bunker',
                        'province_id': pid,
                        'rect': QRectF(x0, y0, x1-x0, y1-y0)
                    })
        
        # パディングを追加して固定サイズにする
        naval_bases.extend([0] * (100 - len(naval_bases)))
        coastal_bunkers.extend([0] * (100 - len(coastal_bunkers)))
        
        # 各パターンで画像を生成
        for show_state, show_province, color_mode in patterns:
            key = (show_state, show_province, color_mode)
            logger.info(f"Generating pattern: state={show_state}, province={show_province}, color_mode={color_mode}")
            
            try:
                # 出力バッファ
                output = np.zeros((h, w, 3), dtype=np.uint8)
                output_buf = cl.Buffer(self.ctx, cl.mem_flags.WRITE_ONLY, output.nbytes)
                
                # 各チャンクを処理
                for chunk_idx in range(NUM_CHUNKS):
                    chunk_start_y = chunk_idx * CHUNK_HEIGHT
                    chunk_h = min(CHUNK_HEIGHT, h - chunk_start_y)
                    logger.debug(f"Processing chunk {chunk_idx + 1}/{NUM_CHUNKS} (y={chunk_start_y}, height={chunk_h})")
                    
                    # バッファを作成
                    prov_map_buf = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                                           hostbuf=self.prov_map.astype(np.int32))
                    state_provinces_buf = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                                                 hostbuf=np.array(state_provinces, dtype=np.int32))
                    state_colors_buf = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                                              hostbuf=np.array(state_colors, dtype=np.int32))
                    country_colors_buf = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                                                hostbuf=np.array(country_colors, dtype=np.int32))
                    prov_colors_buf = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                                             hostbuf=np.array(prov_colors, dtype=np.int32))
                    naval_bases_buf = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                                             hostbuf=np.array(naval_bases, dtype=np.int32))
                    coastal_bunkers_buf = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                                                 hostbuf=np.array(coastal_bunkers, dtype=np.int32))
                    
                    # カーネルを実行
                    self.prg.render_map(
                        self.queue, (w, chunk_h), None,
                        prov_map_buf,
                        state_provinces_buf,
                        state_colors_buf,
                        country_colors_buf,
                        prov_colors_buf,
                        naval_bases_buf,
                        coastal_bunkers_buf,
                        output_buf,
                        np.int32(w),
                        np.int32(h),
                        np.int32(len(self.states)),
                        np.int32(max_provinces),
                        np.int32(show_province),
                        np.int32(show_state),
                        np.int32(color_mode.value),
                        np.int32(chunk_start_y),
                        np.int32(chunk_h)
                    )
                    
                    # バッファを解放
                    prov_map_buf.release()
                    state_provinces_buf.release()
                    state_colors_buf.release()
                    country_colors_buf.release()
                    prov_colors_buf.release()
                    naval_bases_buf.release()
                    coastal_bunkers_buf.release()
                    
                    # メモリを解放
                    self.queue.finish()
                
                # 結果を読み取り
                cl.enqueue_copy(self.queue, output, output_buf)
                
                # 海軍基地と沿岸要塞を描画（CPUで実行）
                for st in self.states.values():
                    for pid in st['naval_base']:
                        ys, xs = np.where(self.prov_map == pid)
                        if xs.size:
                            x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
                            cv2.rectangle(output, (x0,y0), (x1,y1), (0,0,255), 1)
                    
                    for pid in st['coastal_bunker']:
                        ys, xs = np.where(self.prov_map == pid)
                        if xs.size:
                            x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
                            cv2.rectangle(output, (x0,y0), (x1,y1), (255,0,0), 1)
                
                # 画像をキャッシュに保存
                img = QImage(output.data, w, h, 3*w, QImage.Format_RGB888)
                self.render_cache[key] = QPixmap.fromImage(img)
                
                # 出力バッファを解放
                output_buf.release()
                
                # 明示的にガベージコレクションを実行
                import gc
                gc.collect()
                
            except Exception as e:
                logger.error(f"Error generating pattern {key}: {e}")
                # エラーが発生した場合は、そのパターンをスキップ
                continue
        
        # 初期状態に戻す
        self.show_state_borders = True
        self.show_province_borders = True
        self.color_mode = ColorMode.PROVINCE

    def _load_definitions(self, path):
        defs = {}
        prov_colors = {}  # プロヴィンスIDをキーとする色情報
        try:
            with open(path, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';', fieldnames=['id','r','g','b','type','isCoastal','unknown','zero'])
                for row in reader:
                    pid_str = row['id'].lstrip('\ufeff').strip()
                    try:
                        pid = int(pid_str)
                    except ValueError:
                        continue
                    r, g, b = row['r'], row['g'], row['b']  # RとBの順序を修正
                    try:
                        rgb = (int(r), int(g), int(b))  # RとBの順序を修正
                        prov_colors[pid] = rgb
                    except ValueError:
                        continue
                    defs[rgb] = pid
        except Exception as e:
            logger.exception(f"Error loading definitions: {e}")
        return defs, prov_colors

    def _build_province_mapping(self):
        h, w = self.prov_img.shape[:2]
        prov_map = np.zeros((h, w), dtype=np.int32)
        for y in range(h):
            for x in range(w):
                rgb = tuple(int(c) for c in self.prov_img[y, x][:3])
                prov_map[y, x] = self.defs.get(rgb, 0)
        return prov_map

    def _load_states(self, states_dir):
        states = {}
        if not os.path.isdir(states_dir):
            logger.warning(f"States directory not found: {states_dir}")
            return states
        for fn in os.listdir(states_dir):
            if not fn.lower().endswith('.txt'):
                continue
            path = os.path.join(states_dir, fn)
            try:
                with open(path, encoding='utf-8') as f:
                    text = f.read()
            except Exception as e:
                logger.error(f"Failed to read state file {path}: {e}")
                continue
            # iterate over each 'state = {' occurrence with nested brace matching
            for m in re.finditer(r'state\s*=\s*\{', text):
                start = m.end()
                depth = 1
                idx = start
                while idx < len(text) and depth > 0:
                    if text[idx] == '{': depth += 1
                    elif text[idx] == '}': depth -= 1
                    idx += 1
                block = text[start:idx-1]
                # parse id, name, owner
                id_m = re.search(r'id\s*=\s*"?(\d+)"?', block)
                if not id_m: continue
                sid = int(id_m.group(1))
                name_m = re.search(r'name\s*=\s*"([^"]+)"', block)
                owner_m = re.search(r'owner\s*=\s*"?([A-Za-z0-9_]+)"?', block)
                # provinces list (space/tab separated)
                provs = []
                prov_block = re.search(r'provinces\s*=\s*\{([\s\S]*?)\}', block)
                if prov_block:
                    nums = re.findall(r'\d+', prov_block.group(1))
                    provs = [int(n) for n in nums]
                # naval bases
                nbases = {}
                for m2 in re.finditer(r'(\d+)\s*=\s*\{[\s\S]*?naval_base\s*=\s*(\d+)[\s\S]*?\}', block):
                    nbases[int(m2.group(1))] = int(m2.group(2))
                # coastal_bunker
                cbunkers = {}
                for m2 in re.finditer(r'(\d+)\s*=\s*\{[\s\S]*?coastal_bunker\s*=\s*(\d+)[\s\S]*?\}', block):
                    cbunkers[int(m2.group(1))] = int(m2.group(2))
                states[sid] = {
                    'name': name_m.group(1) if name_m else '',
                    'owner': owner_m.group(1) if owner_m else '',
                    'provinces': provs,
                    'naval_base': nbases,
                    'coastal_bunker': cbunkers
                }
                logger.debug(f"Loaded state {sid}: {len(provs)} provinces, {len(nbases)} naval bases, {len(cbunkers)} coastal bunkers")
        return states

    def _load_country_colors(self, path):
        colors = {}
        if not os.path.isfile(path):
            logger.warning(f"Colors file not found: {path}")
            return colors
        tag = None
        lines = []
        try:
            with open(path, encoding='utf-8') as f:
                for line in f:
                    m_tag = re.match(r'^([A-Za-z0-9_]+)\s*=\s*\{', line)
                    if m_tag:
                        tag = m_tag.group(1)
                        lines = []
                    elif tag:
                        if line.strip() == '}':
                            body = ''.join(lines)
                            m_col = re.search(r'color\s*=\s*rgb\s*{([\s\d\t]+)}', body)
                            if m_col:
                                parts = re.split(r'[\s\t]+', m_col.group(1).strip())
                                if len(parts) == 3:
                                    colors[tag] = tuple(int(p) for p in parts)
                                    logger.debug(f"Loaded color {colors[tag]} for country {tag}")
                            tag = None
                        else:
                            lines.append(line)
        except Exception as e:
            logger.error(f"Error reading colors file {path}: {e}")
        return colors

    def _zoom(self, factor):
        self.scale *= factor
        self._update_view()

    def _toggle_state_borders(self):
        self.show_state_borders = not self.show_state_borders
        self._update_view()

    def _toggle_province_borders(self):
        self.show_province_borders = not self.show_province_borders
        self._update_view()

    def _change_color_mode(self, index):
        self.color_mode = ColorMode(index)
        self._update_view()

    def _update_view(self):
        # キャッシュから適切な画像を選択
        key = (self.show_state_borders, self.show_province_borders, self.color_mode)
        if key in self.render_cache:
            self.pix = self.render_cache[key]
            scaled = self.pix.scaled(self.scale * self.pix.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.label.setPixmap(scaled)
            self.label.resize(scaled.size())
        else:
            logger.error(f"Cache miss for pattern: {key}")
            # キャッシュミスの場合は初期状態を使用
            self.show_state_borders = True
            self.show_province_borders = True
            self.color_mode = ColorMode.PROVINCE
            self._update_view()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Plus:
            self.scale *= 1.1
        elif event.key() == Qt.Key_Minus:
            self.scale *= 0.9
        self._update_view()

    def mousePressEvent(self, event):
        # クリック位置を画像座標に変換
        pos = event.pos()
        label_pos = self.label.mapFrom(self, pos)
        scaled_pos = QPointF(label_pos.x() / self.scale, label_pos.y() / self.scale)
        
        # クリック可能な領域をチェック
        for region in self.clickable_regions:
            if region['rect'].contains(scaled_pos):
                # ツールチップを表示
                tooltip_text = f"Province ID: {region['province_id']}\nType: {region['type']}"
                self.tooltip_label.setText(tooltip_text)
                self.tooltip_label.adjustSize()
                
                # ツールチップの位置を設定
                tooltip_pos = self.mapToGlobal(pos)
                self.tooltip_label.move(tooltip_pos)
                self.tooltip_label.show()
                return
        
        # クリックされた領域がなければツールチップを非表示
        self.tooltip_label.hide()

    def mouseMoveEvent(self, event):
        # マウスが移動したらツールチップを非表示
        self.tooltip_label.hide()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    modpath = QFileDialog.getExistingDirectory(None, 'Select modpath directory')
    if not modpath:
        sys.exit(0)
    view = MapView(modpath)
    view.showMaximized()
    sys.exit(app.exec_())
