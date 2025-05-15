import os
import platform
import re
from pathlib import Path

from views.main_window import NavalDesignSystem
from views.home_view import HomeView
from views.equipment_form import EquipmentForm
from views.hull_form import HullForm
from views.design_view import DesignView
from views.fleet_view import FleetView
from views.settings_view import SettingsView
from models.equipment_model import EquipmentModel

class AppController:
    """アプリケーション全体のコントローラークラス"""
    def __init__(self, app_settings):
        self.app_settings = app_settings
        self.main_window = None

        # 装備モデルの初期化（データディレクトリをapp_settingsから取得）
        self.equipment_model = EquipmentModel(data_dir=self.app_settings.equipment_dir)

        # 初回起動時の処理
        if self.app_settings.get_setting("first_run"):
            self.on_first_run()

        # 現在のMODを確認
        self.current_mod = self.app_settings.get_current_mod()

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
        if current_mod and current_mod.get("path"):
            mod_path = current_mod.get("path")
            mod_name = current_mod.get("name", os.path.basename(mod_path))

            if os.path.exists(mod_path):
                self.open_mod(mod_path, mod_name)
                print(f"前回のMOD '{mod_name}' を復元しました。")
            else:
                print(f"前回のMOD '{mod_name}' は見つかりません。パス: {mod_path}")

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
        """MODを開く処理"""
        if not mod_path or not os.path.exists(mod_path):
            print(f"エラー: MODパス '{mod_path}' が見つかりません。")
            return False

        # MODのデータをロードするロジック
        # ここではまずMODの情報を確認
        descriptor_path = os.path.join(mod_path, "descriptor.mod")

        if not os.path.exists(descriptor_path):
            print(f"エラー: MODディレクトリにdescriptor.modファイルが見つかりません。")
            return False

        # MOD名が指定されていない場合はdescriptor.modから取得
        if not mod_name:
            mod_info = self.parse_descriptor_mod(descriptor_path)
            if mod_info and "name" in mod_info:
                mod_name = mod_info["name"]
            else:
                # 情報が取得できない場合はディレクトリ名を使用
                mod_name = os.path.basename(mod_path)

        # 現在開いているMODのパスと名前を設定として保存
        self.app_settings.set_current_mod(mod_path, mod_name)
        self.current_mod = {"path": mod_path, "name": mod_name}

        print(f"MOD '{mod_name}' を開きました。パス: {mod_path}")
        return True

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
        利用可能な装備タイプのリストを取得

        Returns:
            list: 装備タイプのリスト
        """
        try:
            return self.equipment_model.get_equipment_types()
        except Exception as e:
            print(f"装備タイプ取得中にエラーが発生しました: {e}")
            return []

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


    def save_hull(self, hull_data):
        """
        船体データの保存

        Args:
            hull_data: 船体データ辞書

        Returns:
            bool: 保存成功時はTrue、失敗時はFalse
        """
        try:
            # HullModelのインスタンスがまだ作成されていない場合は作成
            if not hasattr(self, 'hull_model'):
                from models.hull_model import HullModel
                self.hull_model = HullModel(data_dir=os.path.join(self.app_settings.data_dir, "hulls"))

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
            # HullModelのインスタンスがまだ作成されていない場合は作成
            if not hasattr(self, 'hull_model'):
                from models.hull_model import HullModel
                self.hull_model = HullModel(data_dir=os.path.join(self.app_settings.data_dir, "hulls"))

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
            # HullModelのインスタンスがまだ作成されていない場合は作成
            if not hasattr(self, 'hull_model'):
                from models.hull_model import HullModel
                self.hull_model = HullModel(data_dir=os.path.join(self.app_settings.data_dir, "hulls"))

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
            # HullModelのインスタンスがまだ作成されていない場合は作成
            if not hasattr(self, 'hull_model'):
                from models.hull_model import HullModel
                self.hull_model = HullModel(data_dir=os.path.join(self.app_settings.data_dir, "hulls"))

            result = self.hull_model.delete_hull(hull_id)

            if result:
                print(f"船体ID '{hull_id}' のデータを削除しました。")
            else:
                print(f"船体ID '{hull_id}' のデータ削除に失敗しました。")

            return result
        except Exception as e:
            print(f"船体データ削除中にエラーが発生しました: {e}")
            return False

    def calculate_design_stats(self, hull_id, equipment_list):
        """艦艇設計の性能計算"""
        # 設計計算ロジックを実装
        # ここでは、装備のステータスから船体の性能を計算する
        pass