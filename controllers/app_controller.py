import os
import platform
import re
import time
import json
import logging
from pathlib import Path
import concurrent.futures # 追加: マルチスレッド処理用
from typing import List, Dict, Any

from PyQt5.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QTableWidget, QHeaderView, QTableWidgetItem, QHBoxLayout, \
    QPushButton
from PyQt5.QtCore import QObject, pyqtSignal, QRunnable, QThreadPool, pyqtSlot

from views.main_window import NavalDesignSystem
from views.home_view import HomeView
from views.equipment_form import EquipmentForm
from views.hull_form import HullForm
from views.design_view import DesignView
from views.fleet_view import FleetView
from views.settings_view import SettingsView
from models.equipment_model import EquipmentModel
from models.hull_model import HullModel
from views.nation_details_view import NationDetailsView
from utils.path_utils import get_data_dir
from utils.cache_manager import CacheManager  # 追加: キャッシュマネージャー

# パーサーのインポート (コメントアウトを解除または追加)
from parser.StateParser import StateParser
from parser.StrategicRegionParser import StrategicRegionParser
from parser.EffectParser import EffectParser
from parser.NavalOOBParser import NavalOOBParser
from utils.data_loaders import load_status_definitions, get_default_status_definitions

# ロガーの設定
logger = logging.getLogger(__name__)

# バックグラウンドタスクを実行するためのWorkerクラス
class Worker(QRunnable):
    """
    バックグラウンドで時間のかかる処理を実行するためのQRunnableサブクラス。
    PyQtのメインスレッドをブロックせずに処理を行うために使用します。
    """
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals() # 処理結果を通知するためのシグナル
        self.status_definitions = self._load_status_definitions()

    @pyqtSlot()
    def run(self):
        """
        ワーカーが実行するメインの処理。
        指定された関数を実行し、結果をシグナルで通知します。
        """
        try:
            # 関数を実行
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result) # 成功時に結果を送信
        except Exception as e:
            # エラー発生時にエラー情報を送信
            logger.error(f"Worker task failed: {e}", exc_info=True)
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit() # 処理完了を通知

    def _load_status_definitions(self) -> List[Dict[str, str]]:
        """ステータス定義を読み込む"""
        try:
            # configディレクトリのパスを取得
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_dir = os.path.join(root_dir, 'config')
            os.makedirs(config_dir, exist_ok=True)

            csv_file = os.path.join(config_dir, 'status_definitions.csv')
            return load_status_definitions(csv_file)

        except (FileNotFoundError, ValueError) as e:
            print(f"ステータス定義読み込みエラー: {e}")
            print("デフォルト定義を使用します")
            return get_default_status_definitions()

    def get_all_status_definitions(self) -> List[Dict[str, str]]:
        """全ステータス定義を取得"""
        return self.status_definitions

    def get_design_stats(self, design_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        設計データから実際のステータス値を取得

        Args:
            design_data: 設計データ辞書

        Returns:
            ステータスID -> 値の辞書
        """
        stats = {}

        # 現時点では計算ロジックは未実装のため、ダミー値を返す
        for stat_def in self.status_definitions:
            stat_id = stat_def['id']
            # 実装時は実際の計算ロジックに置き換える
            stats[stat_id] = self._calculate_stat_value(design_data, stat_id)

        return stats

    def _calculate_stat_value(self, design_data: Dict[str, Any], stat_id: str) -> Any:
        """
        個別のステータス値を計算（将来実装予定）

        現時点ではダミー値を返す
        """
        # ダミー値のマッピング
        dummy_values = {
            'build_cost_ic': 0.4,
            'manpower': 300,
            'reliability': 0.9,
            'naval_speed': 28,
            'lg_armor_piercing': 12,
            'lg_attack': 18,
            'hg_armor_piercing': 25,
            'hg_attack': 12,
            'torpedo_attack': 1,
            'anti_air_attack': 5,
            'surface_detection': 12,
            'sub_attack': 10,
            'sub_detection': 5,
            'surface_visibility': 25,
            'sub_visibility': 20,
            'naval_range': 3000,
            'port_capacity_usage': 1,
            'search_and_destroy_coordination': 0.1,
            'convoy_raiding_coordination': 0.1,
            'carrier_size': 0
        }

        return dummy_values.get(stat_id, 0)


class WorkerSignals(QObject):
    """
    Workerからの通信を処理するためのシグナルを定義するQObjectサブクラス。
    """
    finished = pyqtSignal() # 処理完了時に発射
    error = pyqtSignal(str) # エラー発生時に発射（エラーメッセージを送信）
    result = pyqtSignal(object) # 処理結果を送信（任意のオブジェクトを送信）
    progress = pyqtSignal(int) # 進捗を送信（0-100の整数）


class AppController(QObject):
    """アプリケーション全体のコントローラークラス"""

    # シグナル定義
    mod_changed = pyqtSignal(str)  # MODが変更されたときに発射（MODパスを送信）
    # バックグラウンド処理用のシグナル
    background_task_started = pyqtSignal(str)
    background_task_progress = pyqtSignal(str, int) # タスク名, 進捗
    background_task_finished = pyqtSignal(str, object) # タスク名, 結果
    background_task_error = pyqtSignal(str, str) # タスク名, エラーメッセージ

    def __init__(self, app_settings):
        super().__init__()  # QObjectの初期化

        # ロガーの初期化
        self.logger = logging.getLogger(__name__)

        self.app_settings = app_settings
        self.main_window = None
        self.nation_details_view = None

        # キャッシュマネージャーの初期化（初期はNone）
        self.cache_manager = None

        # マップデータ格納用辞書を初期化
        self.states = {}
        self.strategic_regions = {}

        # QThreadPoolの初期化
        self.threadpool = QThreadPool()
        logger.info(f"QThreadPool initialized with max thread count: {self.threadpool.maxThreadCount()}")

        # 装備モデルの初期化（データディレクトリをapp_settingsから取得）
        self.equipment_model = EquipmentModel(data_dir=self.app_settings.equipment_dir)

        # 船体モデルの初期化
        self.hull_model = HullModel(data_dir=os.path.join(self.app_settings.data_dir, "hulls"))

        # 装備テンプレートの読み込み
        self.equipment_templates = self.load_equipment_templates()

        # 初回起動時の処理
        if self.app_settings.get_setting("first_run"):
            self.on_first_run()

        # 現在のMODを確認
        self.current_mod = self.app_settings.get_current_mod()
        print(f"AppController初期化: current_mod = {self.current_mod}")

        # 現在のMODが設定されている場合、キャッシュマネージャーを初期化
        if self.current_mod and self.current_mod.get("path"):
            self._initialize_cache_manager()

    def load_equipment_templates(self):
        """装備テンプレートの読み込み"""
        try:
            import yaml
            template_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'equipments_templates.yml')
            
            if not os.path.exists(template_file):
                print(f"警告: 装備テンプレートファイル '{template_file}' が見つかりません。")
                return {}

            with open(template_file, 'r', encoding='utf-8') as f:
                templates = yaml.safe_load(f)
                print(f"テンプレート読み込み完了: {len(templates)}カテゴリー")
                for category, types in templates.items():
                    print(f"カテゴリー '{category}': {len(types)}タイプ")
                    for type_key, type_data in types.items():
                        print(f"  - {type_key}: {type_data.get('display_name', 'N/A')}")

            return templates
        except Exception as e:
            print(f"装備テンプレート読み込みエラー: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def get_equipment_template(self, equipment_type):
        """装備タイプに対応するテンプレートを取得"""
        try:
            # 各カテゴリーを検索
            for category in self.equipment_templates.values():
                if isinstance(category, dict):
                    # キー名で直接検索
                    if equipment_type in category:
                        return category[equipment_type]
                    # display_nameで検索
                    for type_key, type_data in category.items():
                        if isinstance(type_data, dict) and 'display_name' in type_data:
                            if type_data['display_name'] == equipment_type:
                                return type_data
            return None
        except Exception as e:
            print(f"テンプレート取得エラー: {e}")
            return None

    def on_first_run(self):
        """初回起動時の処理"""
        # 初回起動フラグをオフに
        self.app_settings.set_setting("first_run", False)

        # その他の初期設定やセットアップ処理
        self.setup_config_file()

    def setup_config_file(self):
        """設定ファイルのセットアップ"""
        config_file = os.path.join(self.app_settings.data_dir, 'config.json')

        # デフォルト設定を作成
        default_config = {
            "app_name": "Naval Design System",
            "version": "1.0.0",
            "data_paths": {
                "equipment": os.path.join(self.app_settings.data_dir, "equipments"),
                "hull": os.path.join(self.app_settings.data_dir, "hulls"),
                "design": os.path.join(self.app_settings.data_dir, "designs"),
                "fleet": os.path.join(self.app_settings.data_dir, "fleets")
            },
            "display": {
                "width": 800,
                "height": 600,
                "theme": "Windows95",
                "language": "ja_JP"
            },
            "calculation": {
                "stats_mode": "add_stats",
                "formula_version": "1.0"
            }
        }

        # 設定ファイルが存在しない場合は作成
        if not os.path.exists(config_file):
            try:
                import json
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
                print(f"デフォルト設定ファイルを作成: {config_file}")
            except Exception as e:
                print(f"設定ファイルの作成に失敗しました: {e}")

    def show_main_window(self):
        """メインウィンドウを表示"""
        if self.main_window is None:
            self.main_window = NavalDesignSystem(self, self.app_settings)

            # ウィンドウサイズとポジションを復元
            window_size = self.app_settings.get_setting("window_size")
            window_position = self.app_settings.get_setting("window_position")

            if window_size:
                self.main_window.resize(*window_size)
            if window_position:
                self.main_window.move(*window_position)

        # ホーム画面を表示
        self.main_window.show_view("home")
        self.main_window.show()

        # 前回開いていたMODがあれば状態を復元
        current_mod = self.app_settings.get_current_mod()
        print(f"show_main_window: settings.get_current_mod() = {current_mod}")

        if current_mod and current_mod.get("path"):
            mod_path = current_mod.get("path")
            mod_name = current_mod.get("name", os.path.basename(mod_path))

            if os.path.exists(mod_path):
                # MODのオープン処理をバックグラウンドで実行
                self.open_mod_async(mod_path, mod_name)
                print(f"前回のMOD '{mod_name}' をバックグラウンドで復元しています。")

                # MOD設定後、ホーム画面のMOD情報を更新（これはUIスレッドで安全に実行）
                if hasattr(self.main_window, 'views') and 'home' in self.main_window.views:
                    home_view = self.main_window.views['home']
                    if hasattr(home_view, 'update_current_mod_info'):
                        home_view.update_current_mod_info()

                    # ModSelectorWidgetのリスト表示も更新
                    if hasattr(home_view, 'mod_selector') and hasattr(home_view.mod_selector, 'update_list_widget'):
                        home_view.mod_selector.update_list_widget()
            else:
                print(f"前回のMOD '{mod_name}' は見つかりません。パス: {mod_path}")
                # MODが見つからない場合はcurrent_modをクリア
                self.current_mod = None
                self.app_settings.set_current_mod(None, None)

    def navigate_to(self, view_name):
        """指定したビューに移動"""
        if self.main_window:
            self.main_window.show_view(view_name)

    def save_app_state(self):
        """アプリケーションの状態を保存"""
        # ウィンドウサイズとポジション
        if self.main_window:
            size = self.main_window.size()
            pos = self.main_window.pos()

            self.app_settings.set_setting("window_size", [size.width(), size.height()])
            self.app_settings.set_setting("window_position", [pos.x(), pos.y()])

    def on_quit(self):
        """アプリケーション終了時の処理"""
        self.save_app_state()
        # その他の必要な終了処理があればここに追加
        print("アプリケーションを終了します。")

    # MOD関連機能

    def open_mod(self, mod_path, mod_name=None):
        """MODを開く処理（同期版）"""
        if not mod_path or not os.path.exists(mod_path):
            print(f"エラー: MODパス '{mod_path}' が見つかりません。")
            return False

        descriptor_path = os.path.join(mod_path, "descriptor.mod")
        if not os.path.exists(descriptor_path):
            print(f"エラー: MODディレクトリにdescriptor.modファイルが見つかりません。")
            return False

        if not mod_name:
            mod_info = self.parse_descriptor_mod(descriptor_path)
            if mod_info and "name" in mod_info:
                mod_name = mod_info["name"]
            else:
                mod_name = os.path.basename(mod_path)

        self.app_settings.set_current_mod(mod_path, mod_name)
        self.current_mod = {"path": mod_path, "name": mod_name}

        # キャッシュマネージャーを初期化
        self._initialize_cache_manager()

        # MOD変更シグナルを発射
        self.mod_changed.emit(mod_path)

        print(f"MOD '{mod_name}' を開きました。パス: {mod_path}")
        return True

    def open_mod_async(self, mod_path, mod_name=None):
        """
        MODを開く処理をバックグラウンドで実行します。
        このメソッドはUIスレッドから呼び出され、実際の重い処理はWorkerスレッドで行われます。
        """
        task_name = f"MODロード: {mod_name or os.path.basename(mod_path)}"
        self.background_task_started.emit(task_name)

        # Workerを作成し、open_mod_background_taskをバックグラウンドで実行
        worker = Worker(self._open_mod_background_task, mod_path, mod_name)
        worker.signals.result.connect(lambda result: self._on_mod_opened(task_name, result))
        worker.signals.error.connect(lambda error: self.background_task_error.emit(task_name, error))
        worker.signals.finished.connect(lambda: logger.info(f"Task '{task_name}' finished."))

        self.threadpool.start(worker)

    def _find_files_recursive(self, directory, pattern):
        """
        指定されたディレクトリとそのサブディレクトリから、パターンに一致するファイルを再帰的に検索します。
        """
        found_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(pattern):
                    found_files.append(os.path.join(root, file))
        return found_files

    def _parse_state_file_worker(self, file_path):
        """
        個別のstateファイルを解析するワーカー関数（キャッシュ対応）
        """
        try:
            # キャッシュからデータを読み込み試行
            cached_data = None
            if self.cache_manager:
                cached_data = self.cache_manager.load("states", file_path)
                if cached_data is not None:
                    self.logger.debug(f"キャッシュからstateデータを読み込み: {file_path}")
                    return cached_data

            # キャッシュミスまたは古い場合は通常のパース処理を実行
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            parser = StateParser(content)
            parsed_data = parser.parse()
            
            # パース成功後、キャッシュに保存
            if parsed_data and self.cache_manager:
                self.cache_manager.save("states", file_path, parsed_data)
                self.logger.debug(f"stateデータをキャッシュに保存: {file_path}")
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error parsing state file {file_path}: {e}", exc_info=True)
            return None

    def _parse_strategic_region_file_worker(self, file_path):
        """
        個別のstrategic regionファイルを解析するワーカー関数（キャッシュ対応）
        """
        try:
            # キャッシュからデータを読み込み試行
            cached_data = None
            if self.cache_manager:
                cached_data = self.cache_manager.load("strategic_regions", file_path)
                if cached_data is not None:
                    self.logger.debug(f"キャッシュからstrategic regionデータを読み込み: {file_path}")
                    return cached_data

            # キャッシュミスまたは古い場合は通常のパース処理を実行
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            parser = StrategicRegionParser(content)
            parsed_data = parser.parse()
            
            # パース成功後、キャッシュに保存
            if parsed_data and self.cache_manager:
                self.cache_manager.save("strategic_regions", file_path, parsed_data)
                self.logger.debug(f"strategic regionデータをキャッシュに保存: {file_path}")
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error parsing strategic region file {file_path}: {e}", exc_info=True)
            return None

    def _open_mod_background_task(self, mod_path, mod_name):
        """
        MODロードの実際のバックグラウンド処理。
        ここでは、複数のデータロード処理をマルチスレッドで実行します。
        """
        logger.info(f"バックグラウンドでMOD '{mod_name}' のロードを開始します。")
        results = {}

        # 1. descriptor.modの解析
        descriptor_path = os.path.join(mod_path, "descriptor.mod")
        mod_info = self.parse_descriptor_mod(descriptor_path)
        if mod_info and "name" in mod_info:
            mod_name = mod_info["name"]
        results["mod_info"] = mod_info
        self.background_task_progress.emit(f"MODロード: {mod_name}", 10) # 進捗更新

        # 2. 国家情報のロード (I/Oバウンドではないため、そのまま)
        nations = self.get_nations(mod_path)
        results["nations"] = nations
        self.background_task_progress.emit(f"MODロード: {mod_name}", 30) # 進捗更新

        # 3. マップデータ（Stateファイル）のロードとパース (マルチスレッド化)
        state_files_dir = os.path.join(mod_path, "history", "states")
        state_files = self._find_files_recursive(state_files_dir, ".txt")
        logger.info(f"Found {len(state_files)} state files.")

        temp_states = {}
        if state_files:
            with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
                future_to_state = {executor.submit(self._parse_state_file_worker, file_path): file_path for file_path in state_files}
                for i, future in enumerate(concurrent.futures.as_completed(future_to_state)):
                    file_path = future_to_state[future]
                    try:
                        data = future.result()
                        if data:
                            temp_states.update(data) # 各スレッドの結果をマージ
                    except Exception as exc:
                        logger.error(f'State file {file_path} generated an exception: {exc}', exc_info=True)
                    # 進捗を報告
                    progress_percent = 30 + int(40 * (i + 1) / len(state_files))
                    self.background_task_progress.emit(f"MODロード: {mod_name}", progress_percent)

        self.states = temp_states # 最終的な結果をコントローラーの属性に設定
        results["states_count"] = len(self.states)
        logger.info(f"Loaded {len(self.states)} states.")
        self.background_task_progress.emit(f"MODロード: {mod_name}", 70) # 進捗更新

        # 4. マップデータ（Strategic Regionファイル）のロードとパース (マルチスレッド化)
        strategic_regions_dir = os.path.join(mod_path, "map", "strategicregions")
        strategic_region_files = self._find_files_recursive(strategic_regions_dir, ".txt")
        logger.info(f"Found {len(strategic_region_files)} strategic region files.")

        temp_strategic_regions = {}
        if strategic_region_files:
            with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
                future_to_region = {executor.submit(self._parse_strategic_region_file_worker, file_path): file_path for file_path in strategic_region_files}
                for i, future in enumerate(concurrent.futures.as_completed(future_to_region)):
                    file_path = future_to_region[future]
                    try:
                        data = future.result()
                        if data:
                            temp_strategic_regions.update(data) # 各スレッドの結果をマージ
                    except Exception as exc:
                        logger.error(f'Strategic region file {file_path} generated an exception: {exc}', exc_info=True)
                    # 進捗を報告
                    progress_percent = 70 + int(20 * (i + 1) / len(strategic_region_files))
                    self.background_task_progress.emit(f"MODロード: {mod_name}", progress_percent)

        self.strategic_regions = temp_strategic_regions # 最終的な結果をコントローラーの属性に設定
        results["strategic_regions_count"] = len(self.strategic_regions)
        logger.info(f"Loaded {len(self.strategic_regions)} strategic regions.")
        self.background_task_progress.emit(f"MODロード: {mod_name}", 90) # 進捗更新

        # 最終的にAppControllerのMOD設定を更新
        self.app_settings.set_current_mod(mod_path, mod_name)
        self.current_mod = {"path": mod_path, "name": mod_name}

        self.background_task_progress.emit(f"MODロード: {mod_name}", 100) # 最終進捗
        logger.info(f"MOD '{mod_name}' のロードが完了しました。")
        return results

    def _on_mod_opened(self, task_name, results):
        """
        MODロードが完了したときにUIスレッドで呼び出されるスロット。
        UIの更新や後処理を行います。
        """
        logger.info(f"Task '{task_name}' completed. Results received: {results.keys()}")
        # MOD変更シグナルを発射 (UIスレッドで安全)
        self.mod_changed.emit(self.current_mod["path"])
        self.background_task_finished.emit(task_name, results)
        print(f"MOD '{self.current_mod['name']}' のバックグラウンドロードが完了しました。")

        # ホーム画面のMOD情報を更新
        if hasattr(self.main_window, 'views') and 'home' in self.main_window.views:
            home_view = self.main_window.views['home']
            if hasattr(home_view, 'update_current_mod_info'):
                home_view.update_current_mod_info()
            if hasattr(home_view, 'mod_selector') and hasattr(home_view.mod_selector, 'update_list_widget'):
                home_view.mod_selector.update_list_widget()


    def parse_descriptor_mod(self, file_path):
        """descriptor.modファイルを解析して情報を抽出"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 正規表現でパターンマッチ
            name_match = re.search(r'name\s*=\s*"([^"]+)"', content)
            version_match = re.search(r'version\s*=\s*"([^"]+)"', content)
            supported_version_match = re.search(r'supported_version\s*=\s*"([^"]+)"', content)

            result = {}

            if name_match:
                result["name"] = name_match.group(1)
            if version_match:
                result["version"] = version_match.group(1)
            if supported_version_match:
                result["supported_version"] = supported_version_match.group(1)

            return result

        except Exception as e:
            print(f"Error parsing descriptor.mod: {e}")
            return None

    def get_current_mod(self):
        """現在開いているMODの情報を取得"""
        return self.current_mod

    def set_current_mod(self, mod_path, mod_name=None):
        """現在選択中のMODを設定"""
        print(f"AppController.set_current_mod: mod_path={mod_path}, mod_name={mod_name}")

        if mod_path is None:
            # MODをクリアする場合
            self.app_settings.set_setting("current_mod_path", None)
            self.app_settings.set_setting("current_mod_name", None)
            self.current_mod = None
            print("MOD設定をクリアしました")
            # クリア時もシグナルを発射
            self.mod_changed.emit("")
        else:
            # MODを設定する場合
            self.app_settings.set_setting("current_mod_path", mod_path)
            if mod_name:
                self.app_settings.set_setting("current_mod_name", mod_name)
            self.current_mod = {"path": mod_path, "name": mod_name}
            print(f"MOD設定を更新しました: path={mod_path}, name={mod_name}")
            # 設定時もシグナルを発射
            self.mod_changed.emit(mod_path)

    # 装備関連機能

    def save_equipment(self, equipment_data):
        """
        装備データの保存

        Args:
            equipment_data (dict): 保存する装備データ

        Returns:
            bool: 保存成功時はTrue、失敗時はFalse
        """
        try:
            # モデルを使って装備データを保存
            result = self.equipment_model.save_equipment(equipment_data)

            # 保存結果をログに出力
            if result:
                equipment_id = equipment_data.get('common', {}).get('ID', '不明')
                equipment_name = equipment_data.get('common', {}).get('名前', '不明')
                print(f"装備「{equipment_name}」(ID: {equipment_id})を保存しました。")
            else:
                print("装備データの保存に失敗しました。")

            return result
        except Exception as e:
            print(f"装備データ保存中にエラーが発生しました: {e}")
            return False

    def load_equipment(self, equipment_id):
        """
        装備データの読み込み

        Args:
            equipment_id (str): 読み込む装備のID

        Returns:
            dict or None: 装備データ辞書、存在しない場合はNone
        """
        try:
            # モデルを使って装備データを読み込み
            equipment_data = self.equipment_model.load_equipment(equipment_id)

            if equipment_data:
                equipment_name = equipment_data.get('common', {}).get('名前', '不明')
                print(f"装備「{equipment_name}」(ID: {equipment_id})を読み込みました。")
            else:
                print(f"装備ID '{equipment_id}' のデータが見つかりません。")

            return equipment_data
        except Exception as e:
            print(f"装備データ読み込み中にエラーが発生しました: {e}")
            return None

    def get_all_equipment(self, equipment_type=None):
        """
        全装備データまたは指定タイプの装備データを取得

        Args:
            equipment_type (str, optional): 装備タイプ（指定しない場合は全装備）

        Returns:
            list: 装備データのリスト
        """
        try:
            return self.equipment_model.get_all_equipment(equipment_type)
        except Exception as e:
            print(f"装備データ取得中にエラーが発生しました: {e}")
            return []

    def delete_equipment(self, equipment_id):
        """
        装備データの削除

        Args:
            equipment_id (str): 削除する装備のID

        Returns:
            bool: 削除成功時はTrue、失敗時はFalse
        """
        try:
            result = self.equipment_model.delete_equipment(equipment_id)

            if result:
                print(f"装備ID '{equipment_id}' のデータを削除しました。")
            else:
                print(f"装備ID '{equipment_id}' のデータ削除に失敗しました。")

            return result
        except Exception as e:
            print(f"装備データ削除中にエラーが発生しました: {e}")
            return False

    def get_equipment_types(self):
        """
        利用可能な装備タイプの一覧を取得

        Returns:
            List[str]: 装備タイプのリスト
        """
        try:
            return self.equipment_model.get_equipment_types()
        except Exception as e:
            print(f"装備タイプ取得中にエラーが発生しました: {e}")
            return []

    def get_equipment_type_mapping(self):
        """
        装備タイプのマッピング（キー名→表示名）を取得

        Returns:
            dict: 装備タイプのマッピング辞書
        """
        try:
            # デフォルトのマッピング
            default_mapping = {
                "小口径砲": "小口径砲",
                "中口径砲": "中口径砲",
                "大口径砲": "大口径砲",
                "超大口径砲": "超大口径砲",
                "対空砲": "対空砲",
                "魚雷": "魚雷",
                "潜水艦魚雷": "潜水艦魚雷",
                "対艦ミサイル": "対艦ミサイル",
                "対空ミサイル": "対空ミサイル",
                "水上機": "水上機",
                "艦上偵察機": "艦上偵察機",
                "回転翼機": "回転翼機",
                "対潜哨戒機": "対潜哨戒機",
                "大型飛行艇": "大型飛行艇",
                "爆雷投射機": "爆雷投射機",
                "爆雷": "爆雷",
                "対潜迫撃砲": "対潜迫撃砲",
                "ソナー": "ソナー",
                "大型ソナー": "大型ソナー",
                "小型電探": "小型電探",
                "大型電探": "大型電探",
                "測距儀": "測距儀",
                "機関": "機関",
                "増設バルジ(中型艦)": "増設バルジ(中型艦)",
                "増設バルジ(大型艦)": "増設バルジ(大型艦)",
                "格納庫": "格納庫",
                "その他": "その他"
            }
            return default_mapping
        except Exception as e:
            print(f"装備タイプマッピング取得中にエラーが発生しました: {e}")
            return {}

    def get_next_equipment_id(self, equipment_type):
        """
        次の装備IDを取得

        Args:
            equipment_type (str): 装備タイプ

        Returns:
            str: 次の装備ID
        """
        try:
            return self.equipment_model.get_next_id(equipment_type)
        except Exception as e:
            print(f"次の装備ID取得中にエラーが発生しました: {e}")
            return ""

    # 船体関連機能

    def save_hull(self, hull_data):
        """
        船体データの保存

        Args:
            hull_data: 船体データ辞書

        Returns:
            bool: 保存成功時はTrue、失敗時はFalse
        """
        try:
            # モデルを使って船体データを保存
            result = self.hull_model.save_hull(hull_data)

            # 保存結果をログに出力
            if result:
                hull_id = hull_data.get('id', '不明')
                hull_name = hull_data.get('name', '不明')
                print(f"船体「{hull_name}」(ID: {hull_id})を保存しました。")
            else:
                print("船体データの保存に失敗しました。")

            return result
        except Exception as e:
            print(f"船体データ保存中にエラーが発生しました: {e}")
            return False

    def load_hull(self, hull_id):
        """
        船体データの読み込み

        Args:
            hull_id: 読み込む船体のID

        Returns:
            dict or None: 船体データ辞書、存在しない場合はNone
        """
        try:
            # モデルを使って船体データを読み込み
            hull_data = self.hull_model.load_hull(hull_id)

            if hull_data:
                hull_name = hull_data.get('name', '不明')
                print(f"船体「{hull_name}」(ID: {hull_id})を読み込みました。")
            else:
                print(f"船体ID '{hull_id}' のデータが見つかりません。")

            return hull_data
        except Exception as e:
            print(f"船体データ読み込み中にエラーが発生しました: {e}")
            return None

    def get_all_hulls(self):
        """
        全船体データを取得

        Returns:
            list: 船体データのリスト
        """
        try:
            return self.hull_model.get_all_hulls()
        except Exception as e:
            print(f"船体データ取得中にエラーが発生しました: {e}")
            return []

    def delete_hull(self, hull_id):
        """
        船体データの削除

        Args:
            hull_id: 削除する船体のID

        Returns:
            bool: 削除成功時はTrue、失敗時はFalse
        """
        try:
            result = self.hull_model.delete_hull(hull_id)

            if result:
                print(f"船体ID '{hull_id}' のデータを削除しました。")
            else:
                print(f"船体ID '{hull_id}' のデータ削除に失敗しました。")

            return result
        except Exception as e:
            print(f"船体データ削除中にエラーが発生しました: {e}")
            return False

    def delete_all_hulls(self):
        """
        すべての船体データを削除

        Returns:
            bool: 削除成功時はTrue、失敗時はFalse
        """
        try:
            # ディレクトリ内のすべてのJSONファイルを削除
            import os
            import shutil

            data_dir = self.hull_model.data_dir

            if os.path.exists(data_dir):
                # バックアップディレクトリの作成
                backup_dir = f"{data_dir}_backup_{int(time.time())}"

                # 現在のデータをバックアップ
                shutil.copytree(data_dir, backup_dir)

                # データディレクトリ内のすべてのファイルを削除
                for file_name in os.listdir(data_dir):
                    if file_name.endswith('.json'):
                        file_path = os.path.join(data_dir, file_name)
                        os.remove(file_path)

                # キャッシュをクリア
                self.hull_model.hull_cache = {}

                print(f"すべての船体データを削除しました。バックアップ: {backup_dir}")
                return True
            else:
                print("船体データディレクトリが見つかりません。")
                return False

        except Exception as e:
            print(f"船体データの全削除中にエラーが発生しました: {e}")
            return False

    def import_from_csv(self, file_path, json_export=False, json_dir=None):
        """
        CSVから船体データをインポート

        Args:
            file_path: CSVファイルのパス
            json_export: JSONファイルとしても出力するかどうか
            json_dir: JSON出力先ディレクトリ

        Returns:
            list: インポートされた船体データのリスト
        """
        try:
            # CSVデータのインポート
            imported_hulls = self.hull_model.import_from_csv(file_path)

            # JSON出力（必要な場合）
            if json_export and imported_hulls and json_dir:
                for hull_data in imported_hulls:
                    hull_id = hull_data.get('id', '')
                    if hull_id:
                        json_path = os.path.join(json_dir, f"{hull_id}.json")
                        with open(json_path, 'w', encoding='utf-8') as f:
                            json.dump(hull_data, f, ensure_ascii=False, indent=2)

                print(f"{len(imported_hulls)}件の船体データをJSONとして '{json_dir}' に出力しました。")

            return imported_hulls

        except Exception as e:
            print(f"CSVからのインポート中にエラーが発生しました: {e}")
            return []

    def import_first_hull_from_csv(self, file_path):
        """
        CSVファイルから最初の船体データをインポート

        Args:
            file_path: CSVファイルのパス

        Returns:
            dict: インポートされた船体データ（失敗時はNone）
        """
        try:
            import csv

            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                try:
                    # 最初の行のみ取得してパース
                    row = next(reader)
                    return self.hull_model._convert_csv_row_to_hull_data(row)

                except StopIteration:
                    print("CSVファイルにデータがありません。")
                    return None

        except Exception as e:
            print(f"CSVからの最初の船体インポート中にエラーが発生しました: {e}")
            return None

    def get_nations(self, mod_path):
        """
        MODから国家情報を取得（キャッシュ対応）
        """
        try:
            # キャッシュキーとしてmod_pathのハッシュまたは特定ファイルを使用
            country_tags_dir = os.path.join(mod_path, "common", "country_tags")
            
            # キャッシュからデータを読み込み試行
            cached_data = None
            if self.cache_manager and os.path.exists(country_tags_dir):
                # ディレクトリ全体のキャッシュキーを生成（代表的なファイルを使用）
                cache_key_file = os.path.join(country_tags_dir, "00_countries.txt")
                if not os.path.exists(cache_key_file):
                    # 最初に見つかったファイルを使用
                    for filename in os.listdir(country_tags_dir):
                        if filename.endswith(".txt"):
                            cache_key_file = os.path.join(country_tags_dir, filename)
                            break
                
                if os.path.exists(cache_key_file):
                    cached_data = self.cache_manager.load("country_tags", cache_key_file)
                    if cached_data is not None:
                        self.logger.debug(f"キャッシュから国家データを読み込み: {country_tags_dir}")
                        return cached_data

            # キャッシュミスまたは古い場合は通常の処理を実行
            nations = []
            logger.info(f"国家情報の取得を開始: MODパス={mod_path}")

            # 国旗ディレクトリ
            flags_dir = os.path.join(mod_path, "gfx", "flags")

            # ディレクトリが存在しない場合は空リストを返す
            if not os.path.exists(country_tags_dir):
                logger.error(f"国家タグディレクトリが見つかりません: {country_tags_dir}")
                return nations

            # 国家タグファイルを探索
            for filename in os.listdir(country_tags_dir):
                if not filename.endswith(".txt"):
                    continue

                file_path = os.path.join(country_tags_dir, filename)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 国家タグと参照ファイルのパターンを検索
                    pattern = r'([A-Z]{3})\s*=\s*"([^"]+)"\s*#?\s*(.*)'
                    matches = re.findall(pattern, content)

                    for match in matches:
                        tag = match[0]  # 国家TAG
                        country_file = match[1]  # 参照ファイル
                        display_name = match[2].strip() if match[2] else tag  # 表示名（コメントがあれば使用）

                        # 国旗ファイルのパス
                        flag_path = os.path.join(flags_dir, f"{tag}.tga")
                        flag_exists = os.path.exists(flag_path)

                        nations.append({
                            "tag": tag,
                            "name": display_name,
                            "flag_path": flag_path if flag_exists else None
                        })

                except Exception as e:
                    logger.error(f"国家タグファイル '{filename}' の解析エラー: {e}")

            # パース成功後、キャッシュに保存
            if nations and self.cache_manager and os.path.exists(cache_key_file):
                self.cache_manager.save("country_tags", cache_key_file, nations)
                self.logger.debug(f"国家データをキャッシュに保存: {country_tags_dir}")

            logger.info(f"国家情報の取得完了: {len(nations)}件の国家を処理")
            return nations
            
        except Exception as e:
            logger.error(f"国家情報取得中にエラーが発生しました: {e}")
            return []

    # 設計関連機能（残りのメソッドも同様に実装...）

    def save_design(self, design_data):
        """設計データを保存する"""
        try:
            # 設計ID（未設定の場合は生成）
            design_id = design_data.get("id", "")
            if not design_id:
                # 設計名から一意のIDを生成
                base_id = ''.join(e for e in design_data["design_name"] if e.isalnum())
                design_id = f"DESIGN_{base_id}_{int(time.time())}"
                design_data["id"] = design_id

            # 保存先ディレクトリの作成
            base_dir = get_data_dir('designs')
            os.makedirs(base_dir, exist_ok=True)

            # ファイル名は設計IDを使用
            file_name = f"{design_id}.json"
            file_path = os.path.join(base_dir, file_name)

            # JSONに変換して保存
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(design_data, f, ensure_ascii=False, indent=2)

            # print(f"設計データ '{design_id}' を保存しました。")
            return True

        except Exception as e:
            print(f"設計データの保存中にエラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_design(self, design_id):
        """
        船体設計データの読み込み

        Args:
            design_id (str): 設計ID

        Returns:
            dict or None: 設計データ、存在しない場合はNone
        """
        try:
            # 設計データを読み込み
            designs_dir = self.app_settings.design_dir
            file_path = os.path.join(designs_dir, f"{design_id}.json")

            if not os.path.exists(file_path):
                print(f"設計ID '{design_id}' のデータが見つかりません。")
                return None

            # JSONから読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                design_data = json.load(f)

            # print(f"設計ID '{design_id}' のデータを読み込みました。")
            return design_data

        except Exception as e:
            print(f"設計データ読み込み中にエラーが発生しました: {e}")
            return None

    def get_all_designs(self):
        """
        全ての船体設計データを取得

        Returns:
            list: 設計データのリスト
        """
        try:
            designs = []
            designs_dir = self.app_settings.design_dir

            # ディレクトリが存在しない場合は空リストを返す
            import os
            if not os.path.exists(designs_dir):
                return designs

            # ディレクトリ内のJSONファイルを全て読み込む
            for file_name in os.listdir(designs_dir):
                if file_name.endswith('.json'):
                    file_path = os.path.join(designs_dir, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            design_data = json.load(f)
                        designs.append(design_data)
                    except Exception as e:
                        print(f"設計ファイル '{file_name}' の読み込みエラー: {e}")

            return designs

        except Exception as e:
            print(f"設計データ一覧取得中にエラーが発生しました: {e}")
            return []

    def delete_design(self, design_id):
        """
        船体設計データの削除

        Args:
            design_id (str): 設計ID

        Returns:
            bool: 削除成功時はTrue、失敗時はFalse
        """
        try:
            # 設計データを削除
            designs_dir = self.app_settings.design_dir
            file_path = os.path.join(designs_dir, f"{design_id}.json")

            if not os.path.exists(file_path):
                print(f"設計ID '{design_id}' のデータが見つかりません。")
                return False

            # ファイルを削除
            os.remove(file_path)
            print(f"設計ID '{design_id}' のデータを削除しました。")
            return True

        except Exception as e:
            print(f"設計データ削除中にエラーが発生しました: {e}")
            return False

    def show_nation_details(self, nation_tag):
        """国家詳細画面を表示"""
        if not self.nation_details_view:
            self.nation_details_view = NationDetailsView(self.main_window, self)
            self.main_window.add_view("nation_details", self.nation_details_view)

        self.nation_details_view.load_nation_data(nation_tag)
        self.main_window.show_view("nation_details")
        self.nation_details_view.show()

    def show_nation_list(self):
        """国家リスト画面を表示"""
        if hasattr(self, 'nation_details_view'):
            self.nation_details_view.hide()
        if hasattr(self, 'nation_view'):
            self.nation_view.show()
            self.nation_view.refresh_nation_list()
        else:
            # NationViewが存在しない場合は作成
            from views.nation_view import NationView
            self.nation_view = NationView(self.main_window, self)
            self.main_window.add_view("nation", self.nation_view)
            self.nation_view.show()
            self.nation_view.refresh_nation_list()

    def get_nation_equipment(self, nation_tag):
        """国家の装備データを取得"""
        try:
            equipment_list = []
            equipment_dir = os.path.join(self.app_settings.data_dir, "equipments")

            if not os.path.exists(equipment_dir):
                return equipment_list

            for filename in os.listdir(equipment_dir):
                if not filename.endswith('.json'):
                    continue

                file_path = os.path.join(equipment_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        equipment_data = json.load(f)

                    # 国家タグが一致するものをフィルタリング
                    if equipment_data.get('country') == nation_tag:
                        equipment_list.append({
                            'id': equipment_data.get('id', ''),
                            'name': equipment_data.get('name', ''),
                            'type': equipment_data.get('type', ''),
                            'stats': equipment_data.get('stats', {})
                        })
                except Exception as e:
                    print(f"装備ファイル '{filename}' の読み込みエラー: {e}")

            # 名前でソート
            equipment_list.sort(key=lambda x: x['name'])
            return equipment_list

        except Exception as e:
            print(f"国家装備データ取得中にエラーが発生しました: {e}")
            return []

    def get_nation_hulls(self, nation_tag):
        """国家の船体データを取得"""
        try:
            hull_list = []
            hull_dir = os.path.join(self.app_settings.data_dir, "hulls")

            if not os.path.exists(hull_dir):
                return hull_list

            for filename in os.listdir(hull_dir):
                if not filename.endswith('.json'):
                    continue

                file_path = os.path.join(hull_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        hull_data = json.load(f)

                    # 国家タグが一致するものをフィルタリング
                    if hull_data.get('country') == nation_tag:
                        hull_list.append({
                            'id': hull_data.get('id', ''),
                            'name': hull_data.get('name', ''),
                            'type': hull_data.get('type', ''),
                            'stats': hull_data.get('stats', {})
                        })
                except Exception as e:
                    print(f"船体ファイル '{filename}' の読み込みエラー: {e}")

            # 名前でソート
            hull_list.sort(key=lambda x: x['name'])
            return hull_list

        except Exception as e:
            print(f"国家船体データ取得中にエラーが発生しました: {e}")
            return []

    def get_nation_designs(self, nation_tag):
        """国家の設計データを取得"""
        try:
            design_list = []
            design_dir = os.path.join(self.app_settings.data_dir, "designs")

            if not os.path.exists(design_dir):
                return design_list

            for filename in os.listdir(design_dir):
                if not filename.endswith('.json'):
                    continue

                file_path = os.path.join(design_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        design_data = json.load(f)

                    # 国家タグが一致するものをフィルタリング
                    if design_data.get('country') == nation_tag:
                        design_list.append({
                            'id': design_data.get('id', ''),
                            'design_name': design_data.get('design_name', design_data.get('name', '')),
                            'ship_type': design_data.get('ship_type', design_data.get('hull', '')),
                            'hull_name': design_data.get('hull_name', ''),
                            'year': design_data.get('year', ''),
                            'main_slots': design_data.get('main_slots', {}),
                            'slot_categories': design_data.get('slot_categories', {}),
                            'internal_slots': design_data.get('internal_slots', [])
                        })
                except Exception as e:
                    print(f"設計ファイル '{filename}' の読み込みエラー: {e}")

            # 名前でソート
            design_list.sort(key=lambda x: x['design_name'])
            return design_list

        except Exception as e:
            print(f"国家設計データ取得中にエラーが発生しました: {e}")
            return []

    def get_nation_mod_designs(self, nation_tag):
        """MODから国家の設計データを取得"""
        try:
            design_list = []
            current_mod = self.get_current_mod()
            logger.info(
                f"MOD設計データの取得を開始: 国家タグ={nation_tag}, MOD={current_mod.get('name') if current_mod else 'None'}")

            if not current_mod or not current_mod.get("path"):
                logger.warning("MODが選択されていません")
                return design_list

            # MODの設計データディレクトリ
            design_dir = os.path.join(current_mod["path"], "common", "scripted_effects")

            if not os.path.exists(design_dir):
                logger.warning(f"設計データディレクトリが見つかりません: {design_dir}")
                return design_list

            for filename in os.listdir(design_dir):
                if not filename.endswith('.txt'):
                    continue

                file_path = os.path.join(design_dir, filename)
                logger.info(f"設計ファイルを処理中: {file_path}")

                try:
                    # キャッシュからデータを読み込み試行
                    cached_data = None
                    if self.cache_manager:
                        cached_data = self.cache_manager.load("designs", file_path, nation_tag)
                        if cached_data is not None:
                            logger.debug(f"キャッシュから設計データを読み込み: {file_path}")
                            design_list.extend(cached_data)
                            continue

                    # キャッシュミスまたは古い場合は通常のパース処理を実行
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # EffectParserを使用して設計データをパース
                    parser = EffectParser(content, filename=file_path)
                    designs_by_country = parser.parse_designs()

                    # 指定された国家の設計データを取得
                    if nation_tag in designs_by_country:
                        country_designs = []
                        for design_id, design_data in designs_by_country[nation_tag].items():
                            design_info = {
                                'id': design_id,
                                'name': design_id,
                                'data': design_data
                            }
                            country_designs.append(design_info)
                            design_list.append(design_info)
                            logger.info(f"設計データを追加: ID={design_id}")

                        # パース成功後、キャッシュに保存
                        if country_designs and self.cache_manager:
                            self.cache_manager.save("designs", file_path, country_designs, nation_tag)
                            logger.debug(f"設計データをキャッシュに保存: {file_path}")

                except Exception as e:
                    logger.error(f"設計ファイル '{filename}' の読み込みエラー: {e}")

            logger.info(f"MOD設計データの取得完了: {len(design_list)}件の設計を処理")
            return design_list

        except Exception as e:
            logger.error(f"MOD設計データ取得中にエラーが発生しました: {e}")
            return []

    def get_nation_mod_formations(self, nation_tag):
        """MODから国家の編成データを取得"""
        try:
            formation_list = []
            current_mod = self.get_current_mod()
            logger.info(
                f"MOD編成データの取得を開始: 国家タグ={nation_tag}, MOD={current_mod.get('name') if current_mod else 'None'}")

            if not current_mod or not current_mod.get("path"):
                logger.warning("MODが選択されていません")
                return formation_list

            # MODの編成データディレクトリ
            formation_dir = os.path.join(current_mod["path"], "history", "units")

            if not os.path.exists(formation_dir):
                logger.warning(f"編成データディレクトリが見つかりません: {formation_dir}")
                return formation_list

            # 国家タグに基づくファイル名パターン
            import re
            patterns = [
                f"{nation_tag}_naval_oob.txt",  # 標準的な命名規則
                f"{nation_tag}_\\d{{4}}_(?:naval|Naval|Navy|navy)(?:_mtg)?\\.txt$"  # 年付きの命名規則
            ]

            for filename in os.listdir(formation_dir):
                if not any(re.match(pattern, filename) for pattern in patterns):
                    continue

                file_path = os.path.join(formation_dir, filename)
                logger.info(f"編成ファイルを処理中: {file_path}")

                try:
                    # キャッシュからデータを読み込み試行
                    cached_data = None
                    if self.cache_manager:
                        cached_data = self.cache_manager.load("naval_oob", file_path, nation_tag)
                        if cached_data is not None:
                            logger.debug(f"キャッシュから編成データを読み込み: {file_path}")
                            formation_list.extend(cached_data)
                            continue

                    # キャッシュミスまたは古い場合は通常のパース処理を実行
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # NavalOOBParserを使用して編成データをパース
                    parser = NavalOOBParser(content)
                    fleets = parser.extract_fleets()

                    # 艦隊データを編成リストに変換
                    country_formations = []
                    for fleet in fleets:
                        formation_info = {
                            'id': fleet.get('name', ''),
                            'name': fleet.get('name', ''),
                            'data': fleet
                        }
                        country_formations.append(formation_info)
                        formation_list.append(formation_info)
                        logger.info(f"編成データを追加: ID={fleet.get('name', '')}")

                    # パース成功後、キャッシュに保存
                    if country_formations and self.cache_manager:
                        self.cache_manager.save("naval_oob", file_path, country_formations, nation_tag)
                        logger.debug(f"編成データをキャッシュに保存: {file_path}")

                except Exception as e:
                    logger.error(f"編成ファイル '{filename}' の読み込みエラー: {e}")

            logger.info(f"MOD編成データの取得完了: {len(formation_list)}件の編成を処理")
            return formation_list

        except Exception as e:
            logger.error(f"MOD編成データ取得中にエラーが発生しました: {e}")
            return []

    def save_fleet_data(self, fleet_data):
        """
        艦隊データを保存

        Args:
            fleet_data (dict): 保存する艦隊データ

        Returns:
            bool: 保存成功時はTrue、失敗時はFalse
        """
        try:
            # 保存先ディレクトリの作成
            fleet_dir = os.path.join(self.app_settings.data_dir, "fleets")
            os.makedirs(fleet_dir, exist_ok=True)

            # 国家タグを取得
            country_tag = fleet_data.get("country")
            if not country_tag:
                print("国家タグが指定されていません。")
                return False

            # ファイル名は国家タグを使用
            file_name = f"{country_tag}_fleets.json"
            file_path = os.path.join(fleet_dir, file_name)

            # JSONに変換して保存
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(fleet_data, f, ensure_ascii=False, indent=2)

            print(f"艦隊データを保存しました: {file_path}")
            return True

        except Exception as e:
            print(f"艦隊データの保存中にエラーが発生しました: {e}")
            return False

    def load_fleet_data(self, country_tag):
        """
        艦隊データを読み込み

        Args:
            country_tag (str): 国家タグ

        Returns:
            dict or None: 艦隊データ、存在しない場合はNone
        """
        try:
            # 艦隊データのディレクトリ
            fleet_dir = os.path.join(self.app_settings.data_dir, "fleets")

            if not os.path.exists(fleet_dir):
                return None

            # ファイル名は国家タグを使用
            file_name = f"{country_tag}_fleets.json"
            file_path = os.path.join(fleet_dir, file_name)

            if not os.path.exists(file_path):
                return None

            # JSONから読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                fleet_data = json.load(f)

            print(f"艦隊データを読み込みました: {file_path}")
            return fleet_data

        except Exception as e:
            print(f"艦隊データの読み込み中にエラーが発生しました: {e}")
            return None

    # 追加のダミーメソッド（エラー回避用）
    def show_equipment_form(self, equipment_data):
        """装備フォームを表示（簡易実装）"""
        print(f"装備フォーム表示: {equipment_data}")

    def show_hull_form(self, hull_data=None):
        """船体フォームを表示（簡易実装）"""
        print(f"船体フォーム表示: {hull_data}")

    def show_design_view(self, hull_data=None, ship_type=None):
        """設計ビューを表示"""
        try:
            if hull_data:
                # 船体IDからJSONファイルをロード
                hull_id = hull_data.get('id')
                if hull_id:
                    loaded_hull_data = self.load_hull(hull_id)
                    if loaded_hull_data:
                        # ロードした船体データと艦種を渡して設計ビューを表示
                        self.main_window.views['design'].on_hull_selected(loaded_hull_data)
                        # 艦種が指定されている場合は設定
                        if ship_type:
                            design_view = self.main_window.views['design']
                            index = design_view.ship_type_combo.findText(ship_type)
                            if index >= 0:
                                design_view.ship_type_combo.setCurrentIndex(index)
            self.main_window.show_view('design')
        except Exception as e:
            self.logger.error(f"設計ビューの表示中にエラーが発生: {e}")
            QMessageBox.critical(self.main_window, "エラー", "設計ビューの表示に失敗しました。")

    def get_equipment_type_mapping(self):
        """
        装備タイプのキー名→表示名マッピングを取得

        Returns:
            Dict[str, str]: キー名をキー、表示名を値とする辞書
        """
        try:
            return self.equipment_model.get_equipment_type_mapping()
        except Exception as e:
            print(f"装備タイプマッピング取得中にエラーが発生しました: {e}")
            return {}

    def get_equipment_display_name(self, equipment_type):
        """
        装備タイプの表示名を取得

        Args:
            equipment_type: 装備タイプのキー名

        Returns:
            str: 表示名
        """
        try:
            return self.equipment_model.get_equipment_display_name(equipment_type)
        except Exception as e:
            print(f"装備表示名取得中にエラーが発生しました: {e}")
            return equipment_type

    def get_ships(self, nation_tag=None, ship_type=None):
        """
        艦艇データを取得

        Args:
            nation_tag (str, optional): 国家タグでフィルタリング
            ship_type (str, optional): 艦種でフィルタリング

        Returns:
            list: 艦艇データのリスト
        """
        try:
            ships = []
            ships_dir = os.path.join(self.app_settings.data_dir, "ships")

            if not os.path.exists(ships_dir):
                return ships

            for filename in os.listdir(ships_dir):
                if not filename.endswith('.json'):
                    continue

                file_path = os.path.join(ships_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        ship_data = json.load(f)

                    # フィルタリング
                    if nation_tag and ship_data.get('nation') != nation_tag:
                        continue
                    if ship_type and ship_data.get('type') != ship_type:
                        continue

                    ships.append(ship_data)
                except Exception as e:
                    print(f"艦艇ファイル '{filename}' の読み込みエラー: {e}")

            # 名前でソート
            ships.sort(key=lambda x: x.get('name', ''))
            return ships

        except Exception as e:
            print(f"艦艇データ取得中にエラーが発生しました: {e}")
            return []

    def save_ship(self, ship_data):
        """
        艦艇データを保存

        Args:
            ship_data (dict): 保存する艦艇データ

        Returns:
            bool: 保存成功時はTrue、失敗時はFalse
        """
        try:
            # 保存先ディレクトリの作成
            ships_dir = os.path.join(self.app_settings.data_dir, "ships")
            os.makedirs(ships_dir, exist_ok=True)

            # 艦艇ID（未設定の場合は生成）
            ship_id = ship_data.get("id", "")
            if not ship_id:
                # 艦名から一意のIDを生成
                base_id = ''.join(e for e in ship_data["name"] if e.isalnum())
                ship_id = f"SHIP_{base_id}_{int(time.time())}"
                ship_data["id"] = ship_id

            # ファイル名は艦艇IDを使用
            file_name = f"{ship_id}.json"
            file_path = os.path.join(ships_dir, file_name)

            # JSONに変換して保存
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(ship_data, f, ensure_ascii=False, indent=2)

            print(f"艦艇データ '{ship_id}' を保存しました。")
            return True

        except Exception as e:
            print(f"艦艇データの保存中にエラーが発生しました: {e}")
            return False

    def delete_ship(self, ship_id):
        """
        艦艇データを削除

        Args:
            ship_id (str): 削除する艦艇のID

        Returns:
            bool: 削除成功時はTrue、失敗時はFalse
        """
        try:
            # 艦艇データを削除
            ships_dir = os.path.join(self.app_settings.data_dir, "ships")
            file_path = os.path.join(ships_dir, f"{ship_id}.json")

            if not os.path.exists(file_path):
                print(f"艦艇ID '{ship_id}' のデータが見つかりません。")
                return False

            # ファイルを削除
            os.remove(file_path)
            print(f"艦艇ID '{ship_id}' のデータを削除しました。")
            return True

        except Exception as e:
            print(f"艦艇データ削除中にエラーが発生しました: {e}")
            return False

    def get_ship_types(self):
        """
        利用可能な艦種の一覧を取得

        Returns:
            List[str]: 艦種のリスト
        """
        return [
            "戦艦", "巡洋戦艦", "重巡洋艦", "軽巡洋艦", "駆逐艦", "潜水艦",
            "空母", "軽空母", "水上機母艦", "輸送艦", "補給艦"
        ]

    def refresh_mod_ships(self, nation_tag):
        """MODから国家の艦艇データを更新（キャッシュ対応版）"""
        try:
            ship_list = []
            current_mod = self.get_current_mod()
            logger.info(
                f"MOD艦艇データの更新を開始: 国家タグ={nation_tag}, MOD={current_mod.get('name') if current_mod else 'None'}")

            if not current_mod or not current_mod.get("path"):
                logger.warning("MODが選択されていません")
                return ship_list

            # MODの編成データディレクトリ
            naval_oob_dir = os.path.join(current_mod["path"], "history", "units")

            if not os.path.exists(naval_oob_dir):
                logger.warning(f"編成データディレクトリが見つかりません: {naval_oob_dir}")
                return ship_list

            # 国家タグに基づくファイル名パターン
            import re
            patterns = [
                f"{nation_tag}_naval_oob.txt",  # 標準的な命名規則
                f"{nation_tag}_\\d{{4}}_(?:naval|Naval|Navy|navy)(?:_mtg)?\\.txt$"  # 年付きの命名規則
            ]

            for filename in os.listdir(naval_oob_dir):
                # パターンマッチング
                matches_pattern = False
                for pattern in patterns:
                    if re.match(pattern, filename):
                        matches_pattern = True
                        break
                
                if not matches_pattern:
                    continue

                file_path = os.path.join(naval_oob_dir, filename)
                logger.info(f"艦艇ファイルを処理中: {file_path}")

                try:
                    # キャッシュからデータを読み込み試行
                    cached_data = None
                    if self.cache_manager:
                        cached_data = self.cache_manager.load("ships", file_path, nation_tag)
                        if cached_data is not None:
                            logger.debug(f"キャッシュから艦艇データを読み込み: {file_path}")
                            ship_list.extend(cached_data)
                            continue

                    # キャッシュミスまたは古い場合は通常のパース処理を実行
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # NavalOOBParserを使用して艦艇データをパース
                    parser = NavalOOBParser(content)
                    ships = parser.extract_ships()

                    # 艦艇データをリストに変換
                    file_ships = []
                    for ship in ships:
                        ship_data = {
                            'id': ship.get('name', ''),
                            'name': ship.get('name', ''),
                            'type': ship.get('type', ''),
                            'design': ship.get('design', ''),
                            'fleet': ship.get('fleet', ''),
                            'task_force': ship.get('task_force', ''),
                            'data': ship
                        }
                        file_ships.append(ship_data)
                        ship_list.append(ship_data)
                        logger.info(f"艦艇データを追加: ID={ship.get('name', '')}, 設計={ship.get('design', '')}, 所属艦隊={ship.get('fleet', '')}")

                    # パース成功後、キャッシュに保存
                    if file_ships and self.cache_manager:
                        self.cache_manager.save("ships", file_path, file_ships, nation_tag)
                        logger.debug(f"艦艇データをキャッシュに保存: {file_path}")

                except Exception as e:
                    logger.error(f"艦艇ファイル '{filename}' の読み込みエラー: {e}")

            logger.info(f"MOD艦艇データの更新完了: {len(ship_list)}件の艦艇を処理")
            return ship_list

        except Exception as e:
            logger.error(f"MOD艦艇データ更新中にエラーが発生しました: {e}")
            return []

    def _initialize_cache_manager(self):
        """現在のMODに基づいてキャッシュマネージャーを初期化"""
        try:
            if self.current_mod and self.current_mod.get("path"):
                # MOD名を取得（ディレクトリ名を使用）
                mod_path = self.current_mod["path"]
                mod_name = os.path.basename(mod_path)
                
                # バニラの場合は特別な識別子を使用
                if not mod_name or mod_name.lower() == "hoi4" or "vanilla" in mod_name.lower():
                    mod_name = "_vanilla_"
                
                self.cache_manager = CacheManager(mod_name)
                self.logger.info(f"CacheManager初期化完了: {mod_name}")
            else:
                # バニラまたはMODが未選択の場合
                self.cache_manager = CacheManager("_vanilla_")
                self.logger.info("CacheManager初期化完了: バニラモード")
                
        except Exception as e:
            self.logger.error(f"CacheManager初期化エラー: {e}")
            self.cache_manager = None

    def clear_cache(self, file_type=None):
        """
        キャッシュをクリアする
        
        Args:
            file_type: 特定のファイル種別のキャッシュのみクリアする場合に指定
        """
        try:
            if self.cache_manager:
                self.cache_manager.clear_cache(file_type)
                self.logger.info(f"キャッシュクリア完了: {file_type or '全種別'}")
            else:
                self.logger.warning("CacheManagerが初期化されていません")
        except Exception as e:
            self.logger.error(f"キャッシュクリアエラー: {e}")

    def get_cache_info(self):
        """
        キャッシュ情報を取得する（デバッグ用）
        
        Returns:
            キャッシュ情報の辞書
        """
        try:
            if self.cache_manager:
                return self.cache_manager.get_cache_info()
            else:
                return {"error": "CacheManagerが初期化されていません"}
        except Exception as e:
            self.logger.error(f"キャッシュ情報取得エラー: {e}")
            return {"error": str(e)}
