import os
import platform
import re
import time
import json
import logging
from pathlib import Path
import concurrent.futures # 追加: マルチスレッド処理用
from typing import List, Dict, Any, Optional
import math

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
from utils.sync_manager import SyncManager  # 追加: 同期マネージャー

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
        """スーテータス一覧.txtからステータス定義を読み込む"""
        try:
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            stats_file = os.path.join(root_dir, 'スーテータス一覧.txt')
            
            definitions = []
            
            if os.path.exists(stats_file):
                with open(stats_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line in lines[2:]:  # ヘッダー行をスキップ
                    line = line.strip()
                    if line and '=' in line and '#' in line:
                        # "stat_name = value # description" の形式をパース
                        parts = line.split('=')
                        if len(parts) >= 2:
                            stat_id = parts[0].strip()
                            right_part = '='.join(parts[1:])
                            
                            if '#' in right_part:
                                comment_parts = right_part.split('#')
                                if len(comment_parts) >= 2:
                                    english_name = comment_parts[1].strip()
                                    
                                    # 日本語名のマッピング（必要に応じて拡張）
                                    japanese_mapping = {
                                        'build_cost_ic': '生産コスト',
                                        'manpower': '人員',
                                        'reliability': '信頼性',
                                        'naval_speed': '最大速力',
                                        'lg_armor_piercing': '軽砲装甲貫通',
                                        'lg_attack': '軽砲攻撃力',
                                        'hg_armor_piercing': '重砲装甲貫通',
                                        'hg_attack': '重砲攻撃力',
                                        'torpedo_attack': '魚雷攻撃力',
                                        'anti_air_attack': '対空攻撃力',
                                        'surface_detection': '水上発見',
                                        'sub_attack': '対潜攻撃力',
                                        'sub_detection': '潜水艦発見',
                                        'surface_visibility': '水上視認性',
                                        'sub_visibility': '潜水艦視認性',
                                        'naval_range': '航続距離',
                                        'port_capacity_usage': '港湾容量使用',
                                        'search_and_destroy_coordination': '捜索撃滅協調',
                                        'convoy_raiding_coordination': '通商破壊協調',
                                        'carrier_size': '空母サイズ',
                                        'equipment_weight': '装備重量',
                                        'weight_ratio': '重量比率'
                                    }
                                    
                                    japanese_name = japanese_mapping.get(stat_id, stat_id)
                                    
                                    definitions.append({
                                        'id': stat_id,
                                        'japanese': japanese_name,
                                        'english': english_name
                                    })
            
            # 重量関連のステータスを追加（ファイルに存在しない場合）
            weight_stats = [
                {'id': 'equipment_weight', 'japanese': '装備重量', 'english': 'Equipment Weight'},
                {'id': 'weight_ratio', 'japanese': '重量比率', 'english': 'Weight Ratio'}
            ]
            
            existing_ids = {d['id'] for d in definitions}
            for weight_stat in weight_stats:
                if weight_stat['id'] not in existing_ids:
                    definitions.append(weight_stat)
            
            return definitions
            
        except Exception as e:
            print(f"ステータス定義読み込みエラー: {e}")
            return self._get_default_status_definitions()
    
    def _get_default_status_definitions(self) -> List[Dict[str, str]]:
        """デフォルトのステータス定義を返す"""
        return [
            {'id': 'build_cost_ic', 'japanese': '生産コスト', 'english': 'Production Cost'},
            {'id': 'manpower', 'japanese': '人員', 'english': 'Manpower'},
            {'id': 'reliability', 'japanese': '信頼性', 'english': 'Reliability'},
            {'id': 'naval_speed', 'japanese': '最大速力', 'english': 'Max Speed'},
            {'id': 'lg_armor_piercing', 'japanese': '軽砲装甲貫通', 'english': 'Light gun armor piercing'},
            {'id': 'lg_attack', 'japanese': '軽砲攻撃力', 'english': 'Light gun attack'},
            {'id': 'hg_armor_piercing', 'japanese': '重砲装甲貫通', 'english': 'Heavy gun armor piercing'},
            {'id': 'hg_attack', 'japanese': '重砲攻撃力', 'english': 'Heavy gun attack'},
            {'id': 'torpedo_attack', 'japanese': '魚雷攻撃力', 'english': 'Torpedo attack'},
            {'id': 'anti_air_attack', 'japanese': '対空攻撃力', 'english': 'Anti-air attack'},
            {'id': 'surface_detection', 'japanese': '水上発見', 'english': 'Surface detection'},
            {'id': 'sub_attack', 'japanese': '対潜攻撃力', 'english': 'Anti-submarine attack'},
            {'id': 'sub_detection', 'japanese': '潜水艦発見', 'english': 'Sub detection'},
            {'id': 'surface_visibility', 'japanese': '水上視認性', 'english': 'Surface Visibility'},
            {'id': 'sub_visibility', 'japanese': '潜水艦視認性', 'english': 'Sub Visibility'},
            {'id': 'naval_range', 'japanese': '航続距離', 'english': 'Naval Range'},
            {'id': 'port_capacity_usage', 'japanese': '港湾容量使用', 'english': 'Port capacity usage'},
            {'id': 'search_and_destroy_coordination', 'japanese': '捜索撃滅協調', 'english': 'Search and destroy coordination'},
            {'id': 'convoy_raiding_coordination', 'japanese': '通商破壊協調', 'english': 'Convoy raiding coordination'},
            {'id': 'carrier_size', 'japanese': '空母サイズ', 'english': 'Carrier Size'},
            {'id': 'equipment_weight', 'japanese': '装備重量', 'english': 'Equipment Weight'},
            {'id': 'weight_ratio', 'japanese': '重量比率', 'english': 'Weight Ratio'}
        ]
    
    def get_all_status_definitions(self) -> List[Dict[str, str]]:
        """全ステータス定義を取得"""
        return self.status_definitions


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

        # 同期マネージャーの初期化
        self.sync_manager = SyncManager(self.app_settings)
        self.sync_manager.sync_completed.connect(self.on_sync_completed)

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

        # ステータス定義の読み込み
        self.status_definitions = self._load_status_definitions()

    def _load_status_definitions(self) -> List[Dict[str, str]]:
        """スーテータス一覧.txtからステータス定義を読み込む"""
        try:
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            stats_file = os.path.join(root_dir, 'スーテータス一覧.txt')
            
            definitions = []
            
            if os.path.exists(stats_file):
                with open(stats_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line in lines[2:]:  # ヘッダー行をスキップ
                    line = line.strip()
                    if line and '=' in line and '#' in line:
                        # "stat_name = value # description" の形式をパース
                        parts = line.split('=')
                        if len(parts) >= 2:
                            stat_id = parts[0].strip()
                            right_part = '='.join(parts[1:])
                            
                            if '#' in right_part:
                                comment_parts = right_part.split('#')
                                if len(comment_parts) >= 2:
                                    english_name = comment_parts[1].strip()
                                    
                                    # 日本語名のマッピング（必要に応じて拡張）
                                    japanese_mapping = {
                                        'build_cost_ic': '生産コスト',
                                        'manpower': '人員',
                                        'reliability': '信頼性',
                                        'naval_speed': '最大速力',
                                        'lg_armor_piercing': '軽砲装甲貫通',
                                        'lg_attack': '軽砲攻撃力',
                                        'hg_armor_piercing': '重砲装甲貫通',
                                        'hg_attack': '重砲攻撃力',
                                        'torpedo_attack': '魚雷攻撃力',
                                        'anti_air_attack': '対空攻撃力',
                                        'surface_detection': '水上発見',
                                        'sub_attack': '対潜攻撃力',
                                        'sub_detection': '潜水艦発見',
                                        'surface_visibility': '水上視認性',
                                        'sub_visibility': '潜水艦視認性',
                                        'naval_range': '航続距離',
                                        'port_capacity_usage': '港湾容量使用',
                                        'search_and_destroy_coordination': '捜索撃滅協調',
                                        'convoy_raiding_coordination': '通商破壊協調',
                                        'carrier_size': '空母サイズ',
                                        'equipment_weight': '装備重量',
                                        'weight_ratio': '重量比率'
                                    }
                                    
                                    japanese_name = japanese_mapping.get(stat_id, stat_id)
                                    
                                    definitions.append({
                                        'id': stat_id,
                                        'japanese': japanese_name,
                                        'english': english_name
                                    })
            
            # 重量関連のステータスを追加（ファイルに存在しない場合）
            weight_stats = [
                {'id': 'equipment_weight', 'japanese': '装備重量', 'english': 'Equipment Weight'},
                {'id': 'weight_ratio', 'japanese': '重量比率', 'english': 'Weight Ratio'}
            ]
            
            existing_ids = {d['id'] for d in definitions}
            for weight_stat in weight_stats:
                if weight_stat['id'] not in existing_ids:
                    definitions.append(weight_stat)
            
            return definitions
            
        except Exception as e:
            print(f"ステータス定義読み込みエラー: {e}")
            return self._get_default_status_definitions()

    def _get_default_status_definitions(self) -> List[Dict[str, str]]:
        """デフォルトのステータス定義を返す"""
        return [
            {'id': 'build_cost_ic', 'japanese': '生産コスト', 'english': 'Production Cost'},
            {'id': 'manpower', 'japanese': '人員', 'english': 'Manpower'},
            {'id': 'reliability', 'japanese': '信頼性', 'english': 'Reliability'},
            {'id': 'naval_speed', 'japanese': '最大速力', 'english': 'Max Speed'},
            {'id': 'lg_armor_piercing', 'japanese': '軽砲装甲貫通', 'english': 'Light gun armor piercing'},
            {'id': 'lg_attack', 'japanese': '軽砲攻撃力', 'english': 'Light gun attack'},
            {'id': 'hg_armor_piercing', 'japanese': '重砲装甲貫通', 'english': 'Heavy gun armor piercing'},
            {'id': 'hg_attack', 'japanese': '重砲攻撃力', 'english': 'Heavy gun attack'},
            {'id': 'torpedo_attack', 'japanese': '魚雷攻撃力', 'english': 'Torpedo attack'},
            {'id': 'anti_air_attack', 'japanese': '対空攻撃力', 'english': 'Anti-air attack'},
            {'id': 'surface_detection', 'japanese': '水上発見', 'english': 'Surface detection'},
            {'id': 'sub_attack', 'japanese': '対潜攻撃力', 'english': 'Anti-submarine attack'},
            {'id': 'sub_detection', 'japanese': '潜水艦発見', 'english': 'Sub detection'},
            {'id': 'surface_visibility', 'japanese': '水上視認性', 'english': 'Surface Visibility'},
            {'id': 'sub_visibility', 'japanese': '潜水艦視認性', 'english': 'Sub Visibility'},
            {'id': 'naval_range', 'japanese': '航続距離', 'english': 'Naval Range'},
            {'id': 'port_capacity_usage', 'japanese': '港湾容量使用', 'english': 'Port capacity usage'},
            {'id': 'search_and_destroy_coordination', 'japanese': '捜索撃滅協調', 'english': 'Search and destroy coordination'},
            {'id': 'convoy_raiding_coordination', 'japanese': '通商破壊協調', 'english': 'Convoy raiding coordination'},
            {'id': 'carrier_size', 'japanese': '空母サイズ', 'english': 'Carrier Size'},
            {'id': 'equipment_weight', 'japanese': '装備重量', 'english': 'Equipment Weight'},
            {'id': 'weight_ratio', 'japanese': '重量比率', 'english': 'Weight Ratio'}
        ]

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
        """アプリケーション終了時の処理（同期機能追加）"""
        # 既存の終了処理
        self.save_app_state()
        
        # 終了時同期実行
        if self.sync_manager.sync_on_exit and self.sync_manager.is_configured():
            print("終了時データ同期を実行中...")
            self.sync_manager.sync_on_exit()
        
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
        装備データの保存（同期機能付き）

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
                
                # 自動同期実行
                self.sync_manager.auto_sync_on_save()
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
        船体データの保存（同期機能付き）

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
                
                # 自動同期実行
                self.sync_manager.auto_sync_on_save()
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
        """設計データを保存する（同期機能付き）"""
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

            print(f"設計データ '{design_id}' を保存しました。")
            
            # 自動同期実行
            self.sync_manager.auto_sync_on_save()
            
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
        艦隊データを保存（同期機能付き）

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
            
            # 自動同期実行
            self.sync_manager.auto_sync_on_save()
            
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
        """現在のMODに基づいてキャッシュマネージャーを初期化（重複初期化防止版）"""
        try:
            if self.current_mod and self.current_mod.get("path"):
                mod_path = self.current_mod["path"]
                mod_name = os.path.basename(mod_path)
                
                if not mod_name or mod_name.lower() == "hoi4" or "vanilla" in mod_name.lower():
                    mod_name = "_vanilla_"
                
                # 既に同じMODのキャッシュマネージャーが存在する場合は再利用
                if (hasattr(self, 'cache_manager') and 
                    self.cache_manager is not None and
                    hasattr(self.cache_manager, 'mod_name') and
                    self.cache_manager.mod_name == mod_name):
                    self.logger.info(f"既存のCacheManagerを再利用: {mod_name}")
                    return
                
                # 古いキャッシュマネージャーがある場合の情報保存
                old_cache_info = None
                if hasattr(self, 'cache_manager') and self.cache_manager is not None:
                    old_cache_info = self.cache_manager.get_cache_info()
                    self.logger.info(f"CacheManager切り替え: {old_cache_info.get('mod_name', 'Unknown')} -> {mod_name}")
                
                self.cache_manager = CacheManager(mod_name)
                self.logger.info(f"CacheManager初期化完了: {mod_name}")
                
            else:
                # バニラまたはMODが未選択の場合
                if not hasattr(self, 'cache_manager') or self.cache_manager is None:
                    self.cache_manager = CacheManager("_vanilla_")
                    self.logger.info("CacheManager初期化完了: バニラモード")
                
        except Exception as e:
            self.logger.error(f"CacheManager初期化エラー: {e}")
            self.cache_manager = None

    def clear_cache(self, file_type=None, confirm=True):
        """
        キャッシュをクリアする（安全版）
        
        Args:
            file_type: 特定のファイル種別のキャッシュのみクリアする場合に指定
            confirm: 確認ログを出力するかどうか
        """
        try:
            if self.cache_manager:
                if confirm:
                    cache_info = self.cache_manager.get_cache_info()
                    self.logger.warning(f"キャッシュクリア要求: MOD={cache_info.get('mod_name', 'Unknown')}, タイプ={file_type or '全種別'}")
                
                self.cache_manager.clear_cache(file_type)
                self.logger.info(f"キャッシュクリア完了: {file_type or '全種別'}")
            else:
                self.logger.warning("CacheManagerが初期化されていません")
        except Exception as e:
            self.logger.error(f"キャッシュクリアエラー: {e}")

    def get_cache_info(self):
        """
        キャッシュ情報を取得する（デバッグ用・エラーハンドリング強化版）
        
        Returns:
            キャッシュ情報の辞書
        """
        try:
            if self.cache_manager:
                return self.cache_manager.get_cache_info()
            else:
                return {
                    "error": "CacheManagerが初期化されていません",
                    "mod_name": "N/A",
                    "base_cache_dir": "N/A",
                    "cache_exists": False
                }
        except Exception as e:
            self.logger.error(f"キャッシュ情報取得エラー: {e}")
            return {"error": str(e)}

    def safe_cache_operation(self, operation_name, operation_func, *args, **kwargs):
        """
        キャッシュ操作を安全に実行するヘルパーメソッド
        
        Args:
            operation_name: 操作名（ログ用）
            operation_func: 実行する関数
            *args, **kwargs: 関数に渡す引数
            
        Returns:
            操作結果（失敗時はNone）
        """
        try:
            if not self.cache_manager:
                self.logger.warning(f"{operation_name}: CacheManagerが初期化されていません")
                return None
                
            self.logger.debug(f"{operation_name}: 開始")
            result = operation_func(*args, **kwargs)
            self.logger.debug(f"{operation_name}: 完了")
            return result
            
        except Exception as e:
            self.logger.error(f"{operation_name}: エラー - {e}")
            return None

    def get_province_center_coords(self, province_id):
        """
        指定されたプロヴィンスIDの中心座標を取得
        
        Args:
            province_id: プロヴィンスID
            
        Returns:
            tuple: (x, y) 座標のタプル、見つからない場合はNone
        """
        # メインウィンドウのマップビューアーから中心座標を取得
        if (hasattr(self, 'main_window') and 
            self.main_window and 
            hasattr(self.main_window, 'views') and 
            'fleet' in self.main_window.views):
            
            fleet_view = self.main_window.views['fleet']
            if hasattr(fleet_view, 'map_widget') and fleet_view.map_widget:
                return fleet_view.map_widget.get_province_center_coords(province_id)
        
        return None

    def get_all_province_centroids(self):
        """
        すべてのプロヴィンス中心座標を取得
        
        Returns:
            dict: プロヴィンスID -> (x, y) 座標の辞書
        """
        # メインウィンドウのマップビューアーから全中心座標を取得
        if (hasattr(self, 'main_window') and 
            self.main_window and 
            hasattr(self.main_window, 'views') and 
            'fleet' in self.main_window.views):
            
            fleet_view = self.main_window.views['fleet']
            if hasattr(fleet_view, 'map_widget') and fleet_view.map_widget:
                return fleet_view.map_widget.get_all_province_centroids()
        
        return {}

    def clear_province_centroids_cache(self):
        """
        プロヴィンス中心座標のキャッシュをクリア
        """
        try:
            if self.cache_manager:
                self.cache_manager.clear_cache("province_centroids")
                self.logger.info("プロヴィンス中心座標のキャッシュをクリアしました")
                
                # マップビューアーのキャッシュもクリア
                if (hasattr(self, 'main_window') and 
                    self.main_window and 
                    hasattr(self.main_window, 'views') and 
                    'fleet' in self.main_window.views):
                    
                    fleet_view = self.main_window.views['fleet']
                    if hasattr(fleet_view, 'map_widget') and fleet_view.map_widget:
                        fleet_view.map_widget.clear_province_centroids_cache()
        except Exception as e:
            self.logger.error(f"キャッシュクリア中にエラーが発生: {e}")

    def benchmark_province_centroids_calculation(self, iterations=3):
        """
        プロヴィンス中心座標計算のベンチマーク
        
        Args:
            iterations: ベンチマーク実行回数
            
        Returns:
            dict: ベンチマーク結果
        """
        # メインウィンドウのマップビューアーでベンチマークを実行
        if (hasattr(self, 'main_window') and 
            self.main_window and 
            hasattr(self.main_window, 'views') and 
            'fleet' in self.main_window.views):
            
            fleet_view = self.main_window.views['fleet']
            if hasattr(fleet_view, 'map_widget') and fleet_view.map_widget:
                return fleet_view.map_widget.benchmark_province_centroids_calculation(iterations)
        
        return None

    def _get_gun_parameters(self, caliber_cm: float) -> tuple:
        """
        口径に基づいてmagic_numberと傾斜係数を取得

        Args:
            caliber_cm: 口径（cm）

        Returns:
            (magic_number, l_inclination, h_inclination)のタプル
        """
        if caliber_cm > 29:
            return 90000000, 0, 1
        elif caliber_cm > 25:
            return 80000000, 0.01, 0.99
        elif caliber_cm > 23:
            return 70000000, 0.1, 0.9
        elif caliber_cm > 20:
            return 65000000, 0.2, 0.8
        elif caliber_cm > 16:
            return 50000000, 0.4, 0.6
        elif caliber_cm > 13:
            return 40000000, 0.6, 0.4
        elif caliber_cm > 11:
            return 30000000, 0.8, 0.2
        elif caliber_cm > 9:
            return 20000000, 1, 0
        elif caliber_cm > 7:
            return 10000000, 1, 0
        elif caliber_cm > 5:
            return 5000000, 1, 0
        else:
            return 1000000, 1, 0  # 極小口径用のデフォルト値


    def get_design_stats(self, design_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        設計データから実際のステータス値を取得（統合ロジック修正版）
        """
        print(f"=== get_design_stats 開始 ===")
        print(f"design_data: {design_data is not None}")

        stats = {}

        # 初期値を設定
        for stat_def in self.status_definitions:
            stat_id = stat_def['id']
            stats[stat_id] = 0.0

        print(f"初期ステータス定義数: {len(stats)}")

        if not design_data:
            print("design_dataがNoneのため、デフォルト値を返します")
            return stats

        # 船体データを取得
        hull_data = design_data.get('hull', {})
        hull_weight = hull_data.get('weight', 0)
        print(f"船体重量: {hull_weight}")

        # 船体の基本ステータス
        base_stats = {
            'naval_speed': float(hull_data.get('speed', 0)),
            'naval_range': float(hull_data.get('range', 0)),
            'reliability': float(hull_data.get('reliability', 0.9)),
        }
        print(f"基本ステータス: {base_stats}")

        # 装備リストを収集
        equipment_list = []

        # メインスロットから装備を収集
        main_slots = design_data.get('main_slots', {})
        print(f"メインスロット: {main_slots}")

        for slot_type, equipment_id in main_slots.items():
            if equipment_id:
                print(f"装備読み込み: {slot_type} -> {equipment_id}")
                equipment_data = self.load_equipment(equipment_id)
                if equipment_data:
                    print(f"装備データ取得成功: {equipment_data.get('common', {}).get('名前', 'Unknown')}")
                    equipment_list.append(equipment_data)
                else:
                    print(f"装備データ取得失敗: {equipment_id}")

        # 内部スロットから装備を収集
        internal_slots = design_data.get('internal_slots', [])
        print(f"内部スロット数: {len(internal_slots)}")

        for slot_data in internal_slots:
            equipment_id = slot_data.get('equipment_id')
            if equipment_id:
                print(f"内部スロット装備読み込み: {equipment_id}")
                equipment_data = self.load_equipment(equipment_id)
                if equipment_data:
                    equipment_list.append(equipment_data)

        print(f"総装備数: {len(equipment_list)}")

        # 装備ごとに計算されたステータスを収集
        calculated_equipment_stats = []
        total_equipment_weight = 0.0
        total_manpower = 0.0

        for i, equipment_data in enumerate(equipment_list):
            print(f"\n--- 装備 {i+1}: {equipment_data.get('common', {}).get('名前', 'Unknown')} ---")
            print(f"装備タイプ: {equipment_data.get('equipment_type', 'Unknown')}")

            # 計算ステータス（砲系統など）を取得
            calculated_stats = self._calculate_equipment_stats(equipment_data)
            print(f"計算されたステータス: {calculated_stats}")

            # 装備のJSONデータからstatsセクションを取得
            json_stats = equipment_data.get('stats', {})
            print(f"JSON内ステータス: {json_stats}")

            # ステータス統合：計算値とJSON値を適切にマージ
            equipment_stats_data = {
                'add_stats': {},
                'multiply_stats': {},
                'add_average_stats': {}
            }

            # 1. まずJSONデータから値を設定（基本値として）
            for mode in ['add_stats', 'multiply_stats', 'add_average_stats']:
                if mode in json_stats:
                    equipment_stats_data[mode] = json_stats[mode].copy()

            # 2. 計算された値で上書き（計算値を優先）
            for stat_id, calc_value in calculated_stats.items():
                # 計算値が0でない場合のみ上書き
                if calc_value != 0:
                    equipment_stats_data['add_stats'][stat_id] = calc_value
                    print(f"計算値で上書き: {stat_id} = {calc_value}")

            # 3. JSONの値で0でないものは加算（手動補正値として扱う）
            if 'add_stats' in json_stats:
                for stat_id, json_value in json_stats['add_stats'].items():
                    if json_value != 0 and stat_id in calculated_stats:
                        # 計算値がある場合は加算
                        equipment_stats_data['add_stats'][stat_id] = calculated_stats.get(stat_id, 0) + json_value
                        print(f"JSON補正値を加算: {stat_id} = {calculated_stats.get(stat_id, 0)} + {json_value} = {equipment_stats_data['add_stats'][stat_id]}")
                    elif json_value != 0:
                        # 計算値がない場合はJSONの値をそのまま使用
                        equipment_stats_data['add_stats'][stat_id] = json_value
                        print(f"JSON値を使用: {stat_id} = {json_value}")

            print(f"統合後ステータス: {equipment_stats_data}")

            # 変換されたデータを装備データに追加
            equipment_with_stats = equipment_data.copy()
            equipment_with_stats['stats'] = equipment_stats_data
            calculated_equipment_stats.append(equipment_with_stats)

            # 重量と人員を集計
            equipment_weight = equipment_data.get('common', {}).get('重量', 0)
            equipment_manpower = equipment_data.get('common', {}).get('人員', 0)

            total_equipment_weight += float(equipment_weight) if equipment_weight else 0.0
            total_manpower += float(equipment_manpower) if equipment_manpower else 0.0

        print(f"\n=== ステータス統合処理 ===")
        print(f"装備重量合計: {total_equipment_weight}")
        print(f"人員合計: {total_manpower}")

        # 統計モードを適用
        final_stats = self._apply_stats_modes(calculated_equipment_stats, base_stats)
        print(f"統合後最終ステータス: {final_stats}")

        # 重量関連の計算
        final_stats['equipment_weight'] = total_equipment_weight
        final_stats['manpower'] = total_manpower

        # 重量比率を計算
        if hull_weight > 0:
            final_stats['weight_ratio'] = (total_equipment_weight / hull_weight) * 100.0
        else:
            final_stats['weight_ratio'] = 0.0

        # 初期値からfinal_statsに値をコピー
        for stat_id in stats.keys():
            if stat_id in final_stats:
                stats[stat_id] = final_stats[stat_id]
                if final_stats[stat_id] != 0:
                    print(f"ステータス設定: {stat_id} = {final_stats[stat_id]}")

        print(f"=== 最終結果 ===")
        # 0以外の値のみ表示
        non_zero_stats = {k: v for k, v in stats.items() if v != 0}
        print(f"0以外のステータス: {non_zero_stats}")

        return stats

    # _apply_stats_modes メソッドもデバッグ出力を追加
    def _apply_stats_modes(self, equipment_list: List[Dict[str, Any]], base_stats: Dict[str, float]) -> Dict[str, float]:
        """
        装備のステータスを3つのモード（add_stats、multiply_stats、add_average_stats）で統合（デバッグ版）
        """
        print("=== _apply_stats_modes 開始 ===")
        final_stats = base_stats.copy()

        # 各モードのステータスを分離して集計
        add_stats_total = {}
        multiply_stats_total = {}
        add_average_stats_list = {}

        for i, equipment_data in enumerate(equipment_list):
            equipment_name = equipment_data.get('common', {}).get('名前', f'装備{i+1}')
            print(f"装備 {equipment_name} のステータス処理")

            stats_data = equipment_data.get('stats', {})

            # add_stats（単純加算）
            add_stats = stats_data.get('add_stats', {})
            print(f"  add_stats: {add_stats}")

            for stat_id, value in add_stats.items():
                if value != 0:  # 0でない値のみ処理
                    if stat_id not in add_stats_total:
                        add_stats_total[stat_id] = 0.0
                    add_stats_total[stat_id] += float(value)
                    print(f"    {stat_id}: {value} -> 合計 {add_stats_total[stat_id]}")

            # multiply_stats（%調整）
            multiply_stats = stats_data.get('multiply_stats', {})
            for stat_id, value in multiply_stats.items():
                if value != 0:
                    if stat_id not in multiply_stats_total:
                        multiply_stats_total[stat_id] = 0.0
                    multiply_stats_total[stat_id] += float(value)

            # add_average_stats（全装備平均）
            add_average_stats = stats_data.get('add_average_stats', {})
            for stat_id, value in add_average_stats.items():
                if value != 0:
                    if stat_id not in add_average_stats_list:
                        add_average_stats_list[stat_id] = []
                    add_average_stats_list[stat_id].append(float(value))

        print(f"加算ステータス合計: {add_stats_total}")
        print(f"乗算ステータス合計: {multiply_stats_total}")
        print(f"平均ステータス: {add_average_stats_list}")

        # 各モードを適用

        # 1. add_stats（単純加算）
        for stat_id, value in add_stats_total.items():
            if stat_id in final_stats:
                final_stats[stat_id] += value
            else:
                final_stats[stat_id] = value
            print(f"加算適用: {stat_id} = {final_stats[stat_id]}")

        # 2. multiply_stats（%調整）
        for stat_id, percentage in multiply_stats_total.items():
            if stat_id in final_stats:
                multiplier = 1.0 + (percentage / 100.0)
                old_value = final_stats[stat_id]
                final_stats[stat_id] *= multiplier
                print(f"乗算適用: {stat_id} = {old_value} * {multiplier} = {final_stats[stat_id]}")

        # 3. add_average_stats（全装備平均）
        for stat_id, values_list in add_average_stats_list.items():
            if values_list:
                average_value = sum(values_list) / len(values_list)
                if stat_id in final_stats:
                    final_stats[stat_id] += average_value
                else:
                    final_stats[stat_id] = average_value
                print(f"平均適用: {stat_id} += {average_value} = {final_stats[stat_id]}")

        print("=== _apply_stats_modes 完了 ===")
        return final_stats

    def _calculate_equipment_stats(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        """
        個別装備のステータスを計算（デバッグ版）
        """
        stats = {}
        equipment_type = equipment_data.get('equipment_type', '')

        print(f"装備ステータス計算開始: タイプ={equipment_type}")

        # 砲系統かどうかを判定
        gun_types = [
            'small_caliber_gun', 'medium_caliber_gun', 'large_caliber_gun',
            'super_large_caliber_gun', 'anti_aircraft_gun'
        ]

        # 日本語表示名でも判定
        gun_display_names = [
            '小口径砲', '中口径砲', '大口径砲', '超大口径砲', '対空砲'
        ]

        is_gun = equipment_type in gun_types or equipment_type in gun_display_names
        print(f"砲系統判定: {is_gun}")

        if is_gun:
            # 砲系統の計算
            gun_stats = self._calculate_gun_stats(equipment_data)
            print(f"砲系統計算結果: {gun_stats}")
            stats.update(gun_stats)

        print(f"最終計算結果: {stats}")
        return stats

    def _calculate_gun_stats(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        """
        砲系統装備のステータスを計算（デバッグ版）
        """
        stats = {}

        try:
            print("砲系統ステータス計算開始")
            #commonデータから必要な値を取得
            common_data = equipment_data.get('common', {})
            print(f"common_data: {common_data}")
            # 重量
            weight = float(common_data.get('重量', 0))
            crew = float(common_data.get('人員', 0))
            print(f"重量: {weight}, 人員: {crew}")
            dev_year = common_data.get('開発年', 1900)


            # specificデータから必要な値を取得
            specific_data = equipment_data.get('specific', {})
            print(f"specific_data: {specific_data}")

            # 必要なパラメータを取得
            caliber_cm = float(specific_data.get('caliber_cm', 0))
            shell_weight_kg = float(specific_data.get('shell_weight_kg', 0))
            initial_velocity_mps = float(specific_data.get('initial_velocity_mps', 0))
            rounds_per_minute = float(specific_data.get('rounds_per_minute', 0))
            barrel_length = float(specific_data.get('barrel_length', 0))
            barrel_count = float(specific_data.get('barrel_count', 1))
            turret_count = float(specific_data.get('turret_count', 1))
            max_elevation = specific_data.get('max_elevation', '+85/-10 度')

            print(f"パラメータ:")
            print(f"  口径: {caliber_cm}cm")
            print(f"  砲弾重量: {shell_weight_kg}kg")
            print(f"  初速: {initial_velocity_mps}m/s")
            print(f"  発射速度: {rounds_per_minute}rpm")
            print(f"  砲身長: {barrel_length}")
            print(f"  砲身数: {barrel_count}")
            print(f"  砲塔数: {turret_count}")

            # パラメータが不正な場合は計算をスキップ
            if caliber_cm <= 0 or shell_weight_kg <= 0 or initial_velocity_mps <= 0:
                print("パラメータが不正のため計算をスキップ")
                return stats

            # 口径に基づいてmagic_numberと傾斜係数を決定
            magic_number, l_inclination, h_inclination = self._get_gun_parameters(caliber_cm)
            print(f"砲パラメータ: magic={magic_number}, l={l_inclination}, h={h_inclination}")

            # Attack値を計算
            if magic_number > 0:
                attack = (initial_velocity_mps * shell_weight_kg * caliber_cm *
                          barrel_length * barrel_count / magic_number *
                          rounds_per_minute * turret_count)

                print(f"基本攻撃力: {attack}")

                # 軽砲・重砲攻撃力を計算
                stats['lg_attack'] = attack * l_inclination
                stats['hg_attack'] = attack * h_inclination

                print(f"軽砲攻撃力: {stats['lg_attack']}")
                print(f"重砲攻撃力: {stats['hg_attack']}")

            #コスト計算
            if weight > 0 and crew > 0:
                cost = (weight * 1000 + crew * 10) / 1000000.0* dev_year
                stats['build_cost_ic'] = cost
                print(f"コスト: {stats['cost']}")



            # 装甲貫通力を計算
            if caliber_cm > 0 and barrel_length > 0:
                import math
                armor_piercing = ((2.54e-10 * 2 / math.pi) *
                                  (shell_weight_kg * 1000 * initial_velocity_mps**2 / caliber_cm**2) *
                                  barrel_length**0.5 * 132)

                # 軽砲・重砲装甲貫通を計算
                stats['lg_armor_piercing'] = armor_piercing * l_inclination
                stats['hg_armor_piercing'] = armor_piercing * h_inclination

                print(f"軽砲装甲貫通: {stats['lg_armor_piercing']}")
                print(f"重砲装甲貫通: {stats['hg_armor_piercing']}")

            # 対空攻撃力を計算
            if shell_weight_kg > 0 and rounds_per_minute > 0:
                try:
                    # max_elevationから数値を抽出
                    max_elevation_value = 85.0
                    if isinstance(max_elevation, str):
                        import re
                        elevation_match = re.search(r'\+?(\d+)', max_elevation)
                        if elevation_match:
                            max_elevation_value = float(elevation_match.group(1))

                    print(f"最大仰角: {max_elevation_value}")

                    # 指数計算の安全性チェック
                    exponent = l_inclination + 0.2
                    if exponent > 0 and rounds_per_minute > 0:
                        base_power = min(shell_weight_kg * 1000, 1000)
                        rpm_power = min(rounds_per_minute, 1000)

                        if exponent <= 10:
                            anti_air_base = base_power * (rpm_power ** exponent) * max_elevation_value / 1000000  # スケール調整
                            lg_attack_contribution = stats.get('lg_attack', 0) / 10
                            stats['anti_air_attack'] = anti_air_base + lg_attack_contribution

                            print(f"対空攻撃力: {stats['anti_air_attack']}")
                        else:
                            stats['anti_air_attack'] = 0.0
                    else:
                        stats['anti_air_attack'] = 0.0

                except (OverflowError, ValueError) as e:
                    print(f"対空攻撃力計算エラー: {e}")
                    stats['anti_air_attack'] = 0.0

            print(f"砲系統計算完了: {stats}")

        except Exception as e:
            print(f"砲ステータス計算エラー: {e}")
            import traceback
            traceback.print_exc()
            return {}

        return stats

    def on_sync_completed(self, success, message):
        """同期完了時の処理"""
        if success:
            print(f"同期成功: {message}")
            if hasattr(self, 'main_window') and self.main_window:
                self.main_window.statusBar().showMessage(f"同期完了: {message}", 3000)
        else:
            print(f"同期失敗: {message}")
            if hasattr(self, 'main_window') and self.main_window:
                QMessageBox.warning(self.main_window, "同期エラー", f"データ同期に失敗しました:\n{message}")

    def sync_data_manually(self, operation='full_sync'):
        """手動でデータ同期を実行"""
        if not self.sync_manager.is_configured():
            if hasattr(self, 'main_window') and self.main_window:
                reply = QMessageBox.question(
                    self.main_window, 
                    "同期設定",
                    "同期設定が完了していません。設定画面を開きますか？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.show_sync_settings()
            return False
        
        # 設定を同期マネージャーに反映
        self.sync_manager.reload_settings()
        
        # 同期実行
        self.sync_manager.sync_data_async(operation)
        return True

    def show_sync_settings(self):
        """同期設定画面を表示（SettingsViewの同期タブを表示）"""
        if hasattr(self, 'main_window') and self.main_window:
            # SettingsViewを表示
            self.main_window.show_view("settings")
            
            # 設定画面の同期タブを選択
            if hasattr(self.main_window, 'views') and 'settings' in self.main_window.views:
                settings_view = self.main_window.views['settings']
                if hasattr(settings_view, 'tab_widget'):
                    # 同期設定タブ（インデックス1）を選択
                    settings_view.tab_widget.setCurrentIndex(1)
                    
            return True
        return False