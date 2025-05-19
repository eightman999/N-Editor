import logging
import sys
import os
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ".venv/lib/python3.13/site-packages/PyQt5/Qt5/plugins/platforms"
import re
import csv
import cv2
import numpy as np
import pyopencl as cl
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QScrollArea, 
                           QFileDialog, QMessageBox, QPushButton, QVBoxLayout, 
                           QHBoxLayout, QWidget)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QPointF, QRectF
# Configure logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# OpenCLカーネルコード
RENDER_KERNEL = """
__kernel void render_map_chunk(
    __global const int* prov_map,
    __global const int* state_provinces,
    __global const int* state_colors,
    __global const int* naval_bases,
    __global const int* coastal_bunkers,
    __global uchar* output,
    const int width,
    const int height,
    const int chunk_x,
    const int chunk_y,
    const int chunk_width,
    const int chunk_height,
    const int num_states,
    const int max_provinces_per_state,
    const int show_province_borders,
    const int show_state_borders
) {
    int x = get_global_id(0) + chunk_x;
    int y = get_global_id(1) + chunk_y;
    
    if (x >= width || y >= height) return;
    
    int idx = y * width + x;
    int prov_id = prov_map[idx];
    
    // デフォルトの色（グレー）
    uchar3 color = (uchar3)(200, 200, 200);
    
    // 州の色を設定
    for (int i = 0; i < num_states; i++) {
        int state_start = i * max_provinces_per_state;
        int state_end = state_start + max_provinces_per_state;
        bool found = false;
        
        // プロビンスがこの州に属しているかチェック
        for (int j = state_start; j < state_end; j++) {
            if (state_provinces[j] == prov_id) {
                // 州の色を設定
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
    
    // 海軍基地と沿岸要塞の描画
    for (int i = 0; i < 100; i++) {
        if (naval_bases[i] == prov_id) {
            color = (uchar3)(0, 0, 255);  // 青
            break;
        }
        if (coastal_bunkers[i] == prov_id) {
            color = (uchar3)(255, 0, 0);  // 赤
            break;
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
        self.defs = self._load_definitions(defs_path)
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
        # 最も単純なパターンから順に生成
        patterns = [
            (False, False),  # 両方非表示（最も単純）
            (False, True),   # プロビンス境界のみ
            (True, False),   # 州境界のみ
            (True, True)     # 両方表示（最も複雑）
        ]
        
        h, w = self.prov_map.shape
        
        # チャンクサイズを設定（GPUのメモリ制限に応じて調整）
        CHUNK_SIZE = 256
        
        # 州のプロビンスリストを準備
        state_provinces = []
        state_colors = []
        naval_bases = []
        coastal_bunkers = []
        
        # 最大プロビンス数を計算
        max_provinces = max(len(st['provinces']) for st in self.states.values())
        logger.info(f"Maximum provinces per state: {max_provinces}")
        
        for st in self.states.values():
            provs = st['provinces']
            state_provinces.extend(provs)
            state_provinces.extend([0] * (max_provinces - len(provs)))  # パディング
            clr = self.colors.get(st['owner'], (200,200,200))
            # 色の値を0-255の範囲に収める
            clr = tuple(min(max(c, 0), 255) for c in clr)
            state_colors.extend(clr)
            logger.debug(f"State color for {st['owner']}: {clr}")
            
            # 海軍基地と沿岸要塞のリストを作成
            naval_bases.extend(list(st['naval_base'].keys()))
            coastal_bunkers.extend(list(st['coastal_bunker'].keys()))
        
        # パディングを追加して固定サイズにする
        naval_bases.extend([0] * (100 - len(naval_bases)))
        coastal_bunkers.extend([0] * (100 - len(coastal_bunkers)))
        
        # 各パターンで画像を生成
        for show_state, show_province in patterns:
            key = (show_state, show_province)
            logger.info(f"Generating pattern: state={show_state}, province={show_province}")
            
            try:
                # 出力バッファ
                output = np.zeros((h, w, 3), dtype=np.uint8)
                
                # チャンクごとに処理
                for chunk_y in range(0, h, CHUNK_SIZE):
                    for chunk_x in range(0, w, CHUNK_SIZE):
                        chunk_width = min(CHUNK_SIZE, w - chunk_x)
                        chunk_height = min(CHUNK_SIZE, h - chunk_y)
                        
                        logger.debug(f"Processing chunk: ({chunk_x}, {chunk_y}) - {chunk_width}x{chunk_height}")
                        
                        # バッファを作成
                        prov_map_buf = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                                               hostbuf=self.prov_map.astype(np.int32))
                        state_provinces_buf = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                                                     hostbuf=np.array(state_provinces, dtype=np.int32))
                        state_colors_buf = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                                                  hostbuf=np.array(state_colors, dtype=np.int32))
                        naval_bases_buf = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                                                 hostbuf=np.array(naval_bases, dtype=np.int32))
                        coastal_bunkers_buf = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR,
                                                     hostbuf=np.array(coastal_bunkers, dtype=np.int32))
                        output_buf = cl.Buffer(self.ctx, cl.mem_flags.WRITE_ONLY, output.nbytes)
                        
                        # カーネルを実行
                        self.prg.render_map_chunk(
                            self.queue, (chunk_width, chunk_height), None,
                            prov_map_buf,
                            state_provinces_buf,
                            state_colors_buf,
                            naval_bases_buf,
                            coastal_bunkers_buf,
                            output_buf,
                            np.int32(w),
                            np.int32(h),
                            np.int32(chunk_x),
                            np.int32(chunk_y),
                            np.int32(chunk_width),
                            np.int32(chunk_height),
                            np.int32(len(self.states)),
                            np.int32(max_provinces),
                            np.int32(show_province),
                            np.int32(show_state)
                        )
                        
                        # 結果を読み取り
                        chunk_output = np.zeros((chunk_height, chunk_width, 3), dtype=np.uint8)
                        cl.enqueue_copy(self.queue, chunk_output, output_buf)
                        
                        # チャンクの結果を正しい位置にコピー
                        output[chunk_y:chunk_y+chunk_height, chunk_x:chunk_x+chunk_width] = chunk_output
                        
                        # メモリを解放
                        self.queue.finish()
                        prov_map_buf.release()
                        state_provinces_buf.release()
                        state_colors_buf.release()
                        naval_bases_buf.release()
                        coastal_bunkers_buf.release()
                        output_buf.release()
                        
                        # 明示的にガベージコレクションを実行
                        import gc
                        gc.collect()
                
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
                
            except Exception as e:
                logger.error(f"Error generating pattern {key}: {e}")
                # エラーが発生した場合は、そのパターンをスキップ
                continue
        
        # 初期状態に戻す
        self.show_state_borders = True
        self.show_province_borders = True

    def _load_definitions(self, path):
        defs = {}
        try:
            with open(path, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';', fieldnames=['id','r','g','b','type','isCoastal','unknown','zero'])
                for row in reader:
                    pid_str = row['id'].lstrip('\ufeff').strip()
                    try:
                        pid = int(pid_str)
                    except ValueError:
                        continue
                    b, g, r = row['b'], row['g'], row['r']
                    try:
                        rgb = (int(b), int(g), int(r))
                    except ValueError:
                        continue
                    defs[rgb] = pid
        except Exception as e:
            logger.exception(f"Error loading definitions: {e}")
        return defs

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

    def _update_view(self):
        # キャッシュから適切な画像を選択
        key = (self.show_state_borders, self.show_province_borders)
        if key in self.render_cache:
            self.pix = self.render_cache[key]
            scaled = self.pix.scaled(self.scale * self.pix.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.label.setPixmap(scaled)
            self.label.resize(scaled.size())
        else:
            logger.error(f"Cache miss for pattern: {key}")
            # キャッシュミスの場合は初期状態（両方表示）を使用
            self.show_state_borders = True
            self.show_province_borders = True
            self._update_view()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Plus:
            self.scale *= 1.1
        elif event.key() == Qt.Key_Minus:
            self.scale *= 0.9
        self._update_view()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    modpath = QFileDialog.getExistingDirectory(None, 'Select modpath directory')
    if not modpath:
        sys.exit(0)
    view = MapView(modpath)
    view.showMaximized()
    sys.exit(app.exec_())
