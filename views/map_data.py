import os
import csv
from PIL import Image
import json
import logging
import threading
import queue
import numpy as np
import cv2
from PyQt5.QtCore import QObject, pyqtSignal
import concurrent.futures
import pickle
from pathlib import Path
import traceback
import time
import psutil
import gc
import sys

class MapData(QObject):
    # シグナルの定義
    progress_updated = pyqtSignal(int, str)  # 進捗率とメッセージ
    loading_complete = pyqtSignal()
    loading_error = pyqtSignal(str)
    detailed_progress = pyqtSignal(str)  # 詳細な進捗情報

    def __init__(self):
        super().__init__()
        self.provinces = {}  # id -> (r,g,b,type,isCoastal)
        self.province_coords = {}  # id -> [(x,y), ...]
        self.states = {}     # id -> (name,provinces,owner)
        self.naval_bases = {} # province_id -> level
        self.country_colors = {} # tag -> (r,g,b)
        self.loading_queue = queue.Queue()
        self.loading_complete = threading.Event()
        self.loading_error = None
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.is_cancelled = False
        self.start_time = None
        
        # ロガーの設定
        self.logger = logging.getLogger('MapData')
        self.logger.setLevel(logging.DEBUG)
        
        # 既存のハンドラをクリア
        self.logger.handlers.clear()
        
        # ログディレクトリの作成
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # ファイルハンドラの設定（日付ごとにログファイルを分割）
        current_time = time.strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f"map_data_{current_time}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # コンソールハンドラの設定
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # フォーマッタの設定
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # ハンドラの追加
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # プロセスの情報を取得
        self.process = psutil.Process()
        
        # OpenCVのGPUサポート確認
        self.gpu_available = cv2.cuda.getCudaEnabledDeviceCount() > 0
        self.logger.info(f"OpenCV GPU利用可能: {self.gpu_available}")
        
        # システム情報のログ出力
        self.logger.info(f"Pythonバージョン: {sys.version}")
        self.logger.info(f"OpenCVバージョン: {cv2.__version__}")
        self.logger.info(f"NumPyバージョン: {np.__version__}")
        self.logger.info(f"CPUコア数: {os.cpu_count()}")
        self.logger.info(f"メモリ情報: {psutil.virtual_memory()}")
        
        # メモリ使用量の初期値を記録
        self._log_memory_usage("初期化完了")

    def _log_memory_usage(self, context=""):
        """メモリ使用量をログに記録"""
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        cpu_percent = self.process.cpu_percent()
        
        extra = {
            'memory_usage': f"{memory_mb:.1f}",
            'cpu_percent': f"{cpu_percent:.1f}",
            'thread_name': threading.current_thread().name
        }
        
        self.logger.info(f"メモリ使用量: {context}", extra=extra)

    def cancel_loading(self):
        """読み込みをキャンセル"""
        self.is_cancelled = True
        self.logger.info("マップデータの読み込みをキャンセルしました")
        self.detailed_progress.emit("読み込みをキャンセルしました")

    def _log_error(self, error_msg, exc_info=None):
        """エラーをログに記録"""
        if exc_info:
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
        else:
            self.logger.error(error_msg)
        self.loading_error.emit(error_msg)

    def _update_progress(self, value, message, detailed_message=None):
        """進捗状況を更新"""
        self.progress_updated.emit(value, message)
        if detailed_message:
            self.detailed_progress.emit(detailed_message)
            self.logger.debug(detailed_message)
            self._log_memory_usage(f"進捗更新: {message}")

    def _get_elapsed_time(self):
        """経過時間を取得"""
        if self.start_time:
            return time.time() - self.start_time
        return 0

    def _get_cache_path(self, mod_path, data_type):
        """キャッシュファイルのパスを取得"""
        mod_hash = str(hash(mod_path))
        return self.cache_dir / f"{data_type}_{mod_hash}.cache"

    def _save_to_cache(self, data, cache_path):
        """データをキャッシュに保存"""
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            self.logger.error(f"キャッシュの保存に失敗: {e}")

    def _load_from_cache(self, cache_path):
        """キャッシュからデータを読み込み"""
        try:
            if cache_path.exists():
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            self.logger.error(f"キャッシュの読み込みに失敗: {e}")
        return None

    def _process_province_coordinates_parallel(self, img_array, province_data):
        """プロヴィンス座標を並列処理"""
        try:
            # 画像を小さなチャンクに分割して処理
            chunk_size = 1000  # 一度に処理するピクセル数
            height, width = img_array.shape[:2]
            total_pixels = height * width
            
            # プロヴィンスのRGB値をNumPy配列に変換
            province_colors = np.array([(b, g, r) for _, (r, g, b, _, _) in province_data.items()])
            province_ids = np.array(list(province_data.keys()))
            
            results = {prov_id: [] for prov_id in province_ids}
            
            # チャンク単位で処理
            for start_idx in range(0, total_pixels, chunk_size):
                if self.is_cancelled:
                    break
                    
                end_idx = min(start_idx + chunk_size, total_pixels)
                chunk = img_array.reshape(-1, 3)[start_idx:end_idx]
                
                # 各プロヴィンスの色に対して処理
                for i, (prov_id, color) in enumerate(zip(province_ids, province_colors)):
                    # 色が一致するピクセルのインデックスを取得
                    matches = np.all(chunk == color, axis=1)
                    if np.any(matches):
                        # インデックスを座標に変換
                        chunk_coords = np.where(matches)[0] + start_idx
                        y_coords = chunk_coords // width
                        x_coords = chunk_coords % width
                        results[prov_id].extend(zip(x_coords, y_coords))
                
                # 進捗状況の更新
                progress = int((start_idx + chunk_size) / total_pixels * 100)
                self._update_progress(
                    progress,
                    f"プロヴィンス座標の処理中... ({start_idx + chunk_size}/{total_pixels})",
                    f"チャンク処理完了: {start_idx + chunk_size}/{total_pixels} ピクセル"
                )
                
                # メモリ解放
                gc.collect()
            
            return results
            
        except Exception as e:
            self._log_error("並列処理中にエラーが発生", exc_info=True)
            raise

    def _load_province_coordinates_gpu(self, img_array):
        """OpenCVを使用してGPUでプロヴィンスの座標情報を読み込む"""
        try:
            self.logger.info("GPUを使用して座標情報の読み込みを開始")
            self.progress_updated.emit(40, "GPUで座標情報を処理中...")
            
            # NumPy配列をOpenCV形式に変換
            img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # GPUメモリに画像をアップロード
            gpu_img = cv2.cuda_GpuMat()
            gpu_img.upload(img)
            
            # 並列処理用のデータ準備
            province_data = list(self.provinces.items())
            chunk_size = max(1, len(province_data) // (os.cpu_count() or 1))
            chunks = [province_data[i:i + chunk_size] for i in range(0, len(province_data), chunk_size)]
            
            # 並列処理の実行
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                for chunk in chunks:
                    future = executor.submit(self._process_province_coordinates_parallel, img_array, dict(chunk))
                    futures.append(future)
                
                # 結果の収集
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    self.province_coords.update(result)
            
            self.logger.info("GPUを使用して座標情報の読み込みが完了しました")
            self.progress_updated.emit(70, "座標情報の処理が完了しました")
            
        except Exception as e:
            self.logger.error(f"GPU処理中にエラーが発生しました: {str(e)}")
            self.loading_error.emit(str(e))
            raise

    def _load_province_coordinates_cpu(self, img_array):
        """OpenCVを使用してCPUでプロヴィンスの座標情報を読み込む"""
        try:
            self.logger.info("CPUを使用して座標情報の読み込みを開始")
            self.progress_updated.emit(40, "CPUで座標情報を処理中...")
            
            # NumPy配列をOpenCV形式に変換
            img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            total_provinces = len(self.provinces)
            for i, (prov_id, (r, g, b, _, _)) in enumerate(self.provinces.items()):
                # 進捗状況の更新
                progress = 40 + int((i / total_provinces) * 30)
                self.progress_updated.emit(progress, f"プロヴィンス {prov_id} の座標を処理中...")
                
                # RGB値が一致するピクセルを検索
                mask = cv2.inRange(img, np.array([b, g, r]), np.array([b, g, r]))
                
                # 座標を取得
                coords = np.where(mask > 0)
                if len(coords[0]) > 0:
                    coords_list = list(zip(coords[1], coords[0]))
                    self.province_coords[prov_id] = coords_list
                    
            self.logger.info("CPUを使用して座標情報の読み込みが完了しました")
            self.progress_updated.emit(70, "座標情報の処理が完了しました")
            
        except Exception as e:
            self.logger.error(f"CPU処理中にエラーが発生しました: {str(e)}")
            self.loading_error.emit(str(e))
            raise

    def start_loading(self, mod_path):
        """非同期でのデータ読み込みを開始"""
        self.is_cancelled = False
        self.start_time = time.time()
        self.loading_complete.clear()
        self.loading_error = None
        
        self.logger.info(f"マップデータの読み込みを開始: {mod_path}")
        self.logger.info(f"キャッシュディレクトリ: {self.cache_dir}")
        self._log_memory_usage("読み込み開始")
        self.detailed_progress.emit(f"マップデータの読み込みを開始: {mod_path}")
        
        # キャッシュの確認
        cache_path = self._get_cache_path(mod_path, "map_data")
        self.logger.info(f"キャッシュファイルパス: {cache_path}")
        cached_data = self._load_from_cache(cache_path)
        
        if cached_data:
            try:
                self.logger.info("キャッシュからデータを読み込みます")
                self.logger.debug(f"キャッシュデータの内容: {list(cached_data.keys())}")
                self._log_memory_usage("キャッシュ読み込み前")
                self.detailed_progress.emit("キャッシュからデータを読み込みます")
                
                # データを段階的に読み込み
                self.provinces = cached_data.get('provinces', {})
                gc.collect()
                
                self.province_coords = cached_data.get('province_coords', {})
                gc.collect()
                
                self.states = cached_data.get('states', {})
                gc.collect()
                
                self.naval_bases = cached_data.get('naval_bases', {})
                gc.collect()
                
                self.country_colors = cached_data.get('country_colors', {})
                gc.collect()
                
                self.logger.info(f"キャッシュから読み込んだデータ: {len(self.provinces)}プロヴィンス, {len(self.states)}ステート")
                self._log_memory_usage("キャッシュ読み込み後")
                self.loading_complete.set()
                self.loading_complete.emit()
                
                elapsed = self._get_elapsed_time()
                self.logger.info(f"キャッシュからの読み込み完了: {elapsed:.2f}秒")
                self.detailed_progress.emit(f"キャッシュからの読み込み完了: {elapsed:.2f}秒")
                return None
                
            except Exception as e:
                self.logger.error(f"キャッシュからの読み込みに失敗: {e}")
                # キャッシュが壊れている場合は新規読み込みを実行
                self.provinces = {}
                self.province_coords = {}
                self.states = {}
                self.naval_bases = {}
                self.country_colors = {}
        
        # ワーカースレッドの開始
        self.logger.info("新しいワーカースレッドを開始します")
        worker = threading.Thread(target=self._loading_worker, args=(mod_path,))
        worker.daemon = True
        worker.start()
        
        return worker

    def _loading_worker(self, mod_path):
        """バックグラウンドでのデータ読み込みを実行"""
        try:
            self.logger.info("データ読み込みワーカーを開始")
            self._log_memory_usage("ワーカー開始")
            self.detailed_progress.emit("データ読み込みワーカーを開始")
            
            # プロヴィンス定義の読み込み
            self._update_progress(10, "プロヴィンス定義を読み込み中...", "プロヴィンス定義ファイルを読み込み中...")
            self.load_province_definitions(os.path.join(mod_path, 'map', 'definition.csv'))
            
            if self.is_cancelled:
                self.logger.info("プロヴィンス定義の読み込みをキャンセル")
                return
            
            # プロヴィンス画像の読み込み
            self._update_progress(30, "プロヴィンス画像を読み込み中...", "プロヴィンス画像を読み込み中...")
            self._log_memory_usage("画像読み込み前")
            
            with Image.open(os.path.join(mod_path, 'map', 'provinces.bmp')) as img:
                img_array = np.array(img)
                self._log_memory_usage("画像読み込み後")
                
                if self.gpu_available:
                    self._load_province_coordinates_gpu(img_array)
                else:
                    self._process_province_coordinates_parallel(img_array, self.provinces)
            
            if self.is_cancelled:
                self.logger.info("プロヴィンス座標の処理をキャンセル")
                return
            
            # ステート情報の読み込み
            self._update_progress(70, "ステート情報を読み込み中...", "ステート情報を読み込み中...")
            self.load_states(os.path.join(mod_path, 'history', 'states'))
            
            if self.is_cancelled:
                self.logger.info("ステート情報の読み込みをキャンセル")
                return
            
            # 国家の色定義を読み込み
            self._update_progress(90, "国家の色定義を読み込み中...", "国家の色定義を読み込み中...")
            self.load_country_colors(os.path.join(mod_path, 'common', 'countries', 'colors.txt'))
            
            if self.is_cancelled:
                self.logger.info("国家の色定義の読み込みをキャンセル")
                return
            
            # データをキャッシュに保存
            self._update_progress(95, "データをキャッシュに保存中...", "データをキャッシュに保存中...")
            self._log_memory_usage("キャッシュ保存前")
            
            cache_data = {
                'provinces': self.provinces,
                'province_coords': self.province_coords,
                'states': self.states,
                'naval_bases': self.naval_bases,
                'country_colors': self.country_colors
            }
            self._save_to_cache(cache_data, self._get_cache_path(mod_path, "map_data"))
            
            self._log_memory_usage("キャッシュ保存後")
            self.loading_complete.set()
            self.loading_complete.emit()
            
            elapsed = self._get_elapsed_time()
            self.logger.info(f"データ読み込み完了: {elapsed:.2f}秒")
            self.detailed_progress.emit(f"データ読み込み完了: {elapsed:.2f}秒")
            
            # メモリ解放を試みる
            gc.collect()
            self._log_memory_usage("メモリ解放後")
            
        except Exception as e:
            self._log_error("データ読み込み中にエラーが発生", exc_info=True)
            self.loading_complete.set()

    def is_loading_complete(self):
        """読み込みが完了したかどうかを確認"""
        return self.loading_complete.is_set()

    def get_loading_error(self):
        """読み込み中のエラーを取得"""
        return self.loading_error

    def load_province_definitions(self, file_path):
        """プロヴィンス定義ファイルを読み込む"""
        self.logger.info(f"プロヴィンス定義ファイルを読み込み中: {file_path}")
        self.progress_updated.emit(20, "プロヴィンス定義を読み込み中...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=';')
                next(reader)  # ヘッダーをスキップ
                count = 0
                for row in reader:
                    if len(row) >= 5:
                        province_id = int(row[0])
                        r, g, b = map(int, row[1:4])
                        province_type = row[4]
                        is_coastal = row[5] == 'true'
                        self.provinces[province_id] = (r, g, b, province_type, is_coastal)
                        count += 1
                self.logger.info(f"プロヴィンス定義の読み込み完了: {count}件")
                self.progress_updated.emit(30, f"プロヴィンス定義の読み込み完了: {count}件")
        except Exception as e:
            self.logger.error(f"プロヴィンス定義ファイルの読み込みエラー: {str(e)}")
            self.loading_error.emit(str(e))
            raise

    def load_states(self, states_dir):
        """ステートファイルを読み込む"""
        self.logger.info(f"ステートファイルを読み込み中: {states_dir}")
        self.progress_updated.emit(70, "ステート情報を読み込み中...")
        try:
            state_count = 0
            naval_base_count = 0
            for filename in os.listdir(states_dir):
                if filename.endswith('.txt'):
                    file_path = os.path.join(states_dir, filename)
                    self.logger.info(f"ステートファイルを処理中: {filename}")
                    self.progress_updated.emit(75, f"ステートファイルを処理中: {filename}")
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 簡易的なパース処理
                        state_id = None
                        state_name = None
                        provinces = []
                        owner = None
                        naval_bases = {}
                        
                        # 各行を処理
                        for line in content.split('\n'):
                            line = line.strip()
                            if 'id =' in line:
                                state_id = int(line.split('=')[1].strip())
                            elif 'name =' in line:
                                state_name = line.split('=')[1].strip().strip('"')
                            elif 'owner =' in line:
                                owner = line.split('=')[1].strip()
                            elif 'provinces = {' in line:
                                # プロヴィンスリストの解析
                                start = content.find('provinces = {')
                                end = content.find('}', start)
                                if start != -1 and end != -1:
                                    prov_str = content[start:end]
                                    provinces = [int(p.strip()) for p in prov_str.split('{')[1].split() if p.strip().isdigit()]
                            elif 'naval_base =' in line:
                                # 海軍基地の解析
                                prov_id = int(line.split('=')[0].strip())
                                level = int(line.split('=')[1].strip())
                                naval_bases[prov_id] = level
                                naval_base_count += 1
                        
                        if state_id is not None:
                            self.states[state_id] = (state_name, provinces, owner)
                            for prov_id, level in naval_bases.items():
                                self.naval_bases[prov_id] = level
                            state_count += 1
            
            self.logger.info(f"ステートファイルの読み込み完了: {state_count}ステート, {naval_base_count}海軍基地")
            self.progress_updated.emit(85, f"ステート情報の読み込み完了: {state_count}ステート, {naval_base_count}海軍基地")
        except Exception as e:
            self.logger.error(f"ステートファイルの読み込みエラー: {str(e)}")
            self.loading_error.emit(str(e))
            raise

    def load_country_colors(self, colors_file):
        """国家の色定義を読み込む"""
        self.logger.info(f"国家の色定義を読み込み中: {colors_file}")
        self.progress_updated.emit(85, "国家の色定義を読み込み中...")
        try:
            with open(colors_file, 'r', encoding='utf-8') as f:
                content = f.read()
                current_tag = None
                color_count = 0
                for line in content.split('\n'):
                    line = line.strip()
                    if '=' in line and '#' not in line:
                        if 'color = rgb' in line:
                            if current_tag:
                                rgb_str = line.split('{')[1].split('}')[0]
                                r, g, b = map(int, rgb_str.split())
                                self.country_colors[current_tag] = (r, g, b)
                                color_count += 1
                        else:
                            current_tag = line.split('=')[0].strip()
                
                self.logger.info(f"国家の色定義の読み込み完了: {color_count}国家")
                self.progress_updated.emit(100, f"国家の色定義の読み込み完了: {color_count}国家")
        except Exception as e:
            self.logger.error(f"国家の色定義ファイルの読み込みエラー: {str(e)}")
            self.loading_error.emit(str(e))
            raise

    def is_valid_deployment_location(self, province_id):
        """配備可能な場所かどうかを判定"""
        if province_id not in self.provinces:
            self.logger.warning(f"無効なプロヴィンスID: {province_id}")
            return False
            
        _, _, _, province_type, is_coastal = self.provinces[province_id]
        
        # 沿岸部でない、または湖/海の場合は配備不可
        if not is_coastal or province_type in ['lake', 'sea']:
            self.logger.warning(f"配備不可のプロヴィンス: {province_id} (type: {province_type}, isCoastal: {is_coastal})")
            return False
            
        return True

    def get_province_coordinates(self, province_id):
        """プロヴィンスの座標情報を取得"""
        return self.province_coords.get(province_id, [])

    def get_province_info(self, province_id):
        """プロヴィンスの情報を取得"""
        return self.provinces.get(province_id)

    def get_state_info(self, state_id):
        """ステートの情報を取得"""
        return self.states.get(state_id)

    def get_naval_base_level(self, province_id):
        """海軍基地のレベルを取得"""
        return self.naval_bases.get(province_id, 0)

    def get_country_color(self, tag):
        """国家の色を取得"""
        return self.country_colors.get(tag, (128, 128, 128))  # デフォルトは灰色 