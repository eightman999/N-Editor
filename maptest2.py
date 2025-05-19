import logging
import sys
import os
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ".venv/lib/python3.13/site-packages/PyQt5/Qt5/plugins/platforms"
import re
import csv
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QScrollArea, 
                           QFileDialog, QMessageBox, QPushButton, QVBoxLayout, 
                           QHBoxLayout, QWidget)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QPointF, QRectF
# Configure logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class MapView(QMainWindow):
    def __init__(self, modpath):
        super().__init__()
        self.modpath = modpath
        self.show_state_borders = True
        self.show_province_borders = True
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
        self._render_map()

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
        self._render_map()

    def _toggle_province_borders(self):
        self.show_province_borders = not self.show_province_borders
        self._render_map()

    def _render_map(self):
        logger.info("Rendering map...")
        if not self.states:
            logger.warning("No states to render; displaying raw province image.")
            img = cv2.cvtColor(self.prov_img[:, :, :3], cv2.COLOR_BGR2RGB)
            h, w = img.shape[:2]
            qimg = QImage(img.data, w, h, 3*w, QImage.Format_RGB888)
            self.pix = QPixmap.fromImage(qimg)
            self._update_view()
            return

        h, w = self.prov_map.shape
        canvas = np.zeros((h, w, 3), dtype=np.uint8)
        
        # Render states
        for st in self.states.values():
            logger.debug(f"Rendering state {st['name']} with {len(st['provinces'])} provinces")
            clr = self.colors.get(st['owner'], (200,200,200))
            clr = tuple(min(max(c, 0), 255) for c in clr)
            mask = np.isin(self.prov_map, st['provinces'])
            canvas[mask] = clr

        # Draw province boundaries if enabled
        if self.show_province_borders:
            for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                shifted = np.roll(self.prov_map, shift=(dy,dx), axis=(0,1))
                canvas[self.prov_map != shifted] = (0,0,0)

        # Draw state boundaries if enabled
        if self.show_state_borders:
            for st in self.states.values():
                for pid in st['provinces']:
                    ys, xs = np.where(self.prov_map == pid)
                    if xs.size:
                        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
                        cv2.rectangle(canvas, (x0,y0), (x1,y1), (128,128,128), 1)

        # Draw naval bases
        for st in self.states.values():
            for pid in st['naval_base']:
                logger.debug(f"Rendering naval base for province {pid}")
                ys, xs = np.where(self.prov_map == pid)
                if xs.size:
                    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
                    cv2.rectangle(canvas, (x0,y0), (x1,y1), (0,0,255), 1)

        # Draw coastal bunkers
        for st in self.states.values():
            for pid in st['coastal_bunker']:
                logger.debug(f"Rendering coastal bunker for province {pid}")
                ys, xs = np.where(self.prov_map == pid)
                if xs.size:
                    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
                    cv2.rectangle(canvas, (x0,y0), (x1,y1), (255,0,0), 1)

        img = QImage(canvas.data, w, h, 3*w, QImage.Format_RGB888).rgbSwapped()
        self.pix = QPixmap.fromImage(img)
        self._update_view()

    def _update_view(self):
        scaled = self.pix.scaled(self.scale * self.pix.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label.setPixmap(scaled)
        self.label.resize(scaled.size())

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
