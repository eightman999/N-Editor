from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QColor
import csv
import re
import traceback
import numpy as np
import os
import logging
import time
from PIL import Image

class MapData(QObject):
    """マップデータを管理するクラス"""
    
    # 進捗状況を通知するためのシグナル
    detailed_progress = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()  # QObjectの初期化
        
        # プロヴィンス情報
        self.provinces = {}  # id -> (r, g, b, type, isCoastal)
        self.province_coords = {}  # id -> [(x, y), ...]
        
        # ステート情報
        self.states = {}  # id -> (name, provinces, owner)
        self.naval_bases = {}  # province_id -> level
        self.country_colors = {}  # tag -> (r, g, b)
        
        # ロード状態の管理
        self.loading_complete = False
        self.loading_error = None
        self.is_cancelled = False
        
        # ロガーの設定
        self.logger = logging.getLogger('MapData')
        self.logger.setLevel(logging.DEBUG)
        
        # ファイルハンドラの設定
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(log_dir, f"map_data_{time.strftime('%Y%m%d_%H%M%S')}.log"))
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
        
        # プロヴィンスデータの保持
        self.provinces_data_by_rgb = {}
        self.provinces_data_by_id = {}
        self._rgb_to_id_map_array = np.full(256*256*256, -1, dtype=np.int32)
        self.province_centroids = {}
        self.original_map_image_data = None
        self.original_width = 0
        self.original_height = 0
    
    def cancel_loading(self):
        """読み込みをキャンセル"""
        self.is_cancelled = True
        self.logger.info("マップデータの読み込みをキャンセルしました")
    
    def is_loading_complete(self):
        """読み込みが完了したかどうかを確認"""
        return self.loading_complete
    
    def get_loading_error(self):
        """読み込み中のエラーを取得"""
        return self.loading_error
    
    def start_loading(self, mod_path):
        """マップデータの読み込みを開始する"""
        self.is_cancelled = False
        self.loading_complete = False
        self.loading_error = None
        
        self.logger.info(f"マップデータの読み込みを開始: {mod_path}")
        
        # バックグラウンド処理として実行するためのスレッドを作成
        import threading
        worker_thread = threading.Thread(target=self._load_data, args=(mod_path,))
        worker_thread.daemon = True
        worker_thread.start()
        
        return worker_thread
    
    def _load_data(self, mod_path):
        """マップデータを読み込む（バックグラウンド処理）"""
        try:
            # プロヴィンス定義の読み込み
            self.detailed_progress.emit("プロヴィンス定義を読み込み中...")
            self.load_province_definitions(os.path.join(mod_path, 'map', 'definition.csv'))
            
            if self.is_cancelled:
                return
            
            # プロヴィンス画像の読み込みと座標抽出
            self.detailed_progress.emit("プロヴィンス画像を読み込み中...")
            self.load_province_coordinates(os.path.join(mod_path, 'map', 'provinces.bmp'))
            
            if self.is_cancelled:
                return
            
            # ステート情報の読み込み
            self.detailed_progress.emit("ステート情報を読み込み中...")
            self.load_states(os.path.join(mod_path, 'history', 'states'))
            
            if self.is_cancelled:
                return
            
            # 国家の色定義を読み込み
            self.detailed_progress.emit("国家の色定義を読み込み中...")
            self.load_country_colors(os.path.join(mod_path, 'common', 'countries', 'colors.txt'))
            
            self.loading_complete = True
            self.detailed_progress.emit("読み込みが完了しました")
            self.logger.info("マップデータの読み込みが完了しました")
            
        except Exception as e:
            self.loading_error = str(e)
            self.logger.error(f"マップデータの読み込み中にエラーが発生しました: {e}")
            self.logger.error(traceback.format_exc())
    
    def load_province_definitions(self, file_path):
        """プロヴィンス定義ファイルを読み込む"""
        self.logger.info(f"プロヴィンス定義ファイルを読み込み中: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=';')
                next(reader)  # ヘッダーをスキップ
                
                for row in reader:
                    if len(row) >= 5:
                        try:
                            province_id = int(row[0])
                            r = int(row[1])
                            g = int(row[2])
                            b = int(row[3])
                            province_type = row[4]  # land/lake/sea
                            is_coastal = row[5] == 'true' if len(row) > 5 else False
                            
                            self.provinces[province_id] = (r, g, b, province_type, is_coastal)
                            
                            # プロヴィンスデータの保持
                            rgb_hash = r * 65536 + g * 256 + b
                            if rgb_hash < len(self._rgb_to_id_map_array):
                                self._rgb_to_id_map_array[rgb_hash] = province_id
                            
                            self.logger.debug(f"プロヴィンス定義を読み込み: ID={province_id}, RGB=({r},{g},{b}), タイプ={province_type}, 沿岸={is_coastal}")
                        except (ValueError, IndexError) as e:
                            self.logger.warning(f"プロヴィンス定義の読み込みでエラー: {row} - {str(e)}")
                            continue
            
            self.logger.info(f"プロヴィンス定義の読み込みが完了しました: {len(self.provinces)}件")
            
        except Exception as e:
            self.logger.error(f"プロヴィンス定義ファイルの読み込みエラー: {e}")
            self.logger.error(traceback.format_exc())
            raise
    
    def load_province_coordinates(self, file_path):
        """プロヴィンス画像を読み込み、各プロヴィンスの座標を抽出する"""
        self.logger.info(f"プロヴィンス画像を読み込み中: {file_path}")
        
        try:
            # PILで画像を読み込み
            img = Image.open(file_path)
            self.logger.info(f"プロヴィンス画像サイズ: {img.size}")
            
            # NumPy配列に変換
            self.original_map_image_data = np.array(img)
            self.original_width, self.original_height = img.size
            
            # プロヴィンス重心の計算
            self.calculate_province_centroids()
            
            self.logger.info(f"プロヴィンス画像の読み込みが完了しました")
            
        except Exception as e:
            self.logger.error(f"プロヴィンス画像の読み込みエラー: {e}")
            self.logger.error(traceback.format_exc())
            raise
    
    def calculate_province_centroids(self):
        """プロヴィンスの重心を計算"""
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

        # 各ピクセルの座標配列を生成
        x_indices, y_indices = np.meshgrid(np.arange(width), np.arange(height))
        x_coords_flat = x_indices.flatten()
        y_coords_flat = y_indices.flatten()

        # 有効なプロビンスピクセルに属するX, Y座標を抽出
        valid_x_coords = x_coords_flat[valid_prov_pixel_indices]
        valid_y_coords = y_coords_flat[valid_prov_pixel_indices]

        # NumPyのbincountを使って、プロビンスIDごとのX座標の合計、Y座標の合計、ピクセル数を高速に計算
        max_prov_id = valid_prov_ids.max() if len(valid_prov_ids) > 0 else 0

        sum_x_per_prov = np.bincount(valid_prov_ids, weights=valid_x_coords, minlength=max_prov_id + 1)
        sum_y_per_prov = np.bincount(valid_prov_ids, weights=valid_y_coords, minlength=max_prov_id + 1)
        count_per_prov = np.bincount(valid_prov_ids, minlength=max_prov_id + 1)

        self.province_centroids = {}
        for prov_id in self.provinces.keys():
            if prov_id <= max_prov_id and count_per_prov[prov_id] > 0:
                center_x = sum_x_per_prov[prov_id] / count_per_prov[prov_id]
                center_y = sum_y_per_prov[prov_id] / count_per_prov[prov_id]
                self.province_centroids[prov_id] = (center_x, center_y)
            else:
                self.province_centroids[prov_id] = None

        end_time = time.time()
        print(f"Province centroid calculation time (highly optimized): {end_time - start_time:.2f} seconds.")
    
    def load_states(self, states_dir):
        """ステートファイルを読み込む"""
        self.logger.info(f"ステートファイルを読み込み中: {states_dir}")
        
        try:
            for filename in os.listdir(states_dir):
                if self.is_cancelled:
                    return
                
                if filename.endswith('.txt'):
                    file_path = os.path.join(states_dir, filename)
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # IDを抽出
                        id_match = re.search(r'id\s*=\s*(\d+)', content)
                        if not id_match:
                            continue
                        
                        state_id = int(id_match.group(1))
                        
                        # 名前を抽出
                        name_match = re.search(r'name\s*=\s*"([^"]+)"', content)
                        state_name = name_match.group(1) if name_match else f"State_{state_id}"
                        
                        # 所有国を抽出
                        owner_match = re.search(r'owner\s*=\s*(\w+)', content)
                        owner = owner_match.group(1) if owner_match else None
                        
                        # プロヴィンスリストを抽出
                        provinces_match = re.search(r'provinces\s*=\s*{([^}]+)}', content)
                        if not provinces_match:
                            continue
                        
                        provinces_str = provinces_match.group(1)
                        provinces = [int(p.strip()) for p in provinces_str.split() if p.strip().isdigit()]
                        
                        # ステート情報を保存
                        self.states[state_id] = (state_name, provinces, owner)
                        
                        # 海軍基地を抽出
                        naval_base_matches = re.findall(r'(\d+)\s*=\s*{\s*naval_base\s*=\s*(\d+)\s*}', content)
                        for province_id_str, level_str in naval_base_matches:
                            province_id = int(province_id_str)
                            level = int(level_str)
                            self.naval_bases[province_id] = level
            
            self.logger.info(f"ステートファイルの読み込みが完了しました: {len(self.states)}件のステート, {len(self.naval_bases)}件の海軍基地")
            
        except Exception as e:
            self.logger.error(f"ステートファイルの読み込みエラー: {e}")
            raise
    
    def load_country_colors(self, file_path):
        """国家の色定義ファイルを読み込む"""
        self.logger.info(f"国家の色定義ファイルを読み込み中: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 色定義を正規表現で抽出
                color_matches = re.finditer(r'(\w+)\s*=\s*{[^}]*color\s*=\s*rgb\s*{\s*(\d+)\s+(\d+)\s+(\d+)\s*}', content)
                
                for match in color_matches:
                    tag = match.group(1)
                    r = int(match.group(2))
                    g = int(match.group(3))
                    b = int(match.group(4))
                    
                    self.country_colors[tag] = (r, g, b)
            
            self.logger.info(f"国家の色定義の読み込みが完了しました: {len(self.country_colors)}件")
            
        except Exception as e:
            self.logger.error(f"国家の色定義ファイルの読み込みエラー: {e}")
            raise
    
    def get_province_coordinates(self, province_id):
        """プロヴィンスの座標情報を取得"""
        return self.province_centroids.get(province_id)
    
    def get_province_color(self, province_id):
        """プロヴィンスの色を取得"""
        if province_id in self.provinces:
            r, g, b, _, _ = self.provinces[province_id]
            return QColor(r, g, b)
        return QColor(0, 0, 0)
    
    def get_country_color(self, tag):
        """国家の色を取得"""
        if tag in self.country_colors:
            r, g, b = self.country_colors[tag]
            return QColor(r, g, b)
        return QColor(128, 128, 128)  # デフォルトは灰色
    
    def get_provinces_by_state(self, state_id):
        """ステートに属するプロヴィンスのリストを取得"""
        if state_id in self.states:
            _, provinces, _ = self.states[state_id]
            return provinces
        return []
    
    def is_valid_deployment_location(self, province_id):
        """配備可能な場所かどうかを判定"""
        if province_id not in self.provinces:
            return False
            
        _, _, _, province_type, is_coastal = self.provinces[province_id]
        
        # 沿岸部でない、または湖/海の場合は配備不可
        if not is_coastal or province_type in ['lake', 'sea']:
            return False
            
        return True