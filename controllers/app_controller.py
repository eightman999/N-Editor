import os
import platform
import re
import time
import json
from pathlib import Path

from PyQt5.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QTableWidget, QHeaderView, QTableWidgetItem, QHBoxLayout, \
    QPushButton

from views.main_window import NavalDesignSystem
from views.home_view import HomeView
from views.equipment_form import EquipmentForm
from views.hull_form import HullForm
from views.design_view import DesignView
from views.fleet_view import FleetView
from views.settings_view import SettingsView
from models.equipment_model import EquipmentModel
from models.hull_model import HullModel

class AppController:
    """アプリケーション全体のコントローラークラス"""
    def __init__(self, app_settings):
        self.app_settings = app_settings
        self.main_window = None

        # 装備モデルの初期化（データディレクトリをapp_settingsから取得）
        self.equipment_model = EquipmentModel(data_dir=self.app_settings.equipment_dir)

        # 船体モデルの初期化
        self.hull_model = HullModel(data_dir=os.path.join(self.app_settings.data_dir, "hulls"))

        # 初回起動時の処理
        if self.app_settings.get_setting("first_run"):
            self.on_first_run()

        # 現在のMODを確認
        self.current_mod = self.app_settings.get_current_mod()
        print(f"AppController初期化: current_mod = {self.current_mod}")

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
                self.open_mod(mod_path, mod_name)
                print(f"前回のMOD '{mod_name}' を復元しました。")

                # MOD設定後、ホーム画面のMOD情報を更新
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
    def set_current_mod(self, mod_path, mod_name=None):
        """現在選択中のMODを設定"""
        print(f"AppSettings.set_current_mod: mod_path={mod_path}, mod_name={mod_name}")

        if mod_path is None:
            # MODをクリアする場合
            self.set_setting("current_mod_path", None)
            self.set_setting("current_mod_name", None)
            print("MOD設定をクリアしました")
        else:
            # MODを設定する場合
            self.set_setting("current_mod_path", mod_path)
            if mod_name:
                self.set_setting("current_mod_name", mod_name)
            print(f"MOD設定を更新しました: path={mod_path}, name={mod_name}")
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
        MODから国家情報を取得

        Args:
            mod_path: MODのパス

        Returns:
            list: 国家情報のリスト（画像パス、TAG、国家名）
        """
        nations = []

        # 国家タグファイルのディレクトリ
        country_tags_dir = os.path.join(mod_path, "common", "country_tags")
        # 国旗ディレクトリ
        flags_dir = os.path.join(mod_path, "gfx", "flags")

        # ディレクトリが存在しない場合は空リストを返す
        if not os.path.exists(country_tags_dir):
            print(f"国家タグディレクトリが見つかりません: {country_tags_dir}")
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
                # 例: "TAG = "countries/CountryName.txt" #表示名"
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
                print(f"国家タグファイル '{filename}' の解析エラー: {e}")

        return nations

    def refresh_nation_list(self):
        """国家リストを更新"""
        # 現在のMODを取得
        if self.app_controller:
            current_mod = self.app_controller.get_current_mod()
            print(f"NationView.refresh_nation_list: current_mod = {current_mod}")

            if current_mod and current_mod.get("path"):
                self.current_mod_label.setText(f"現在のMOD: {current_mod.get('name', '')}")
                # 国家情報を取得して表示
                self.load_nations(current_mod["path"])
            else:
                self.current_mod_label.setText("MODが選択されていません")
                self.nation_list.clear()
                QMessageBox.warning(self, "警告", "MODが選択されていません。\nホーム画面からMODを選択してください。")


    # controllers/app_controller.py の既存のコードに追加

    def save_design(self, design_data):
        """
        船体設計データの保存

        Args:
            design_data (dict): 設計データ

        Returns:
            bool: 保存成功時はTrue、失敗時はFalse
        """
        try:
            # 設計ID（未設定の場合は生成）
            design_id = design_data.get("id", "")
            if not design_id:
                # 設計名から一意のIDを生成
                import re
                import time
                design_name = design_data.get("design_name", "")
                base_id = re.sub(r'[^a-zA-Z0-9]', '_', design_name)
                design_id = f"DESIGN_{base_id}_{int(time.time())}"
                design_data["id"] = design_id

            # 設計データを保存
            designs_dir = self.app_settings.design_dir

            # ディレクトリがなければ作成
            import os
            if not os.path.exists(designs_dir):
                os.makedirs(designs_dir, exist_ok=True)

            # ファイルパス
            file_path = os.path.join(designs_dir, f"{design_id}.json")

            # JSONに変換して保存
            import json
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(design_data, f, ensure_ascii=False, indent=2)

            print(f"設計データ '{design_id}' を保存しました。")
            return True

        except Exception as e:
            print(f"設計データ保存中にエラーが発生しました: {e}")
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

            print(f"設計ID '{design_id}' のデータを読み込みました。")
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

    def calculate_design_stats(self, hull_data, equipment_data):
        """
        船体設計の性能計算

        Args:
            hull_data (dict): 船体データ
            equipment_data (list): 装備データのリスト

        Returns:
            dict: 計算された性能値
        """
        try:
            # 性能値の初期値（船体から取得）
            stats = {
                "build_cost_ic": 0.0,
                "manpower": 0,
                "reliability": 0.0,
                "naval_speed": 0.0,
                "fire_range": 0.0,
                "lg_armor_piercing": 0.0,
                "lg_attack": 0.0,
                "hg_armor_piercing": 0.0,
                "hg_attack": 0.0,
                "torpedo_attack": 0.0,
                "anti_air_attack": 0.0,
                "shore_bombardment": 0.0,
                "evasion": 0.0,
                "surface_detection": 0.0,
                "sub_attack": 0.0,
                "sub_detection": 0.0,
                "surface_visibility": 0.0,
                "sub_visibility": 0.0,
                "naval_range": 0.0,
                "port_capacity_usage": 0.0,
                "search_and_destroy_coordination": 0.0,
                "convoy_raiding_coordination": 0.0
            }

            # 船体の基本性能を設定
            # 実際の実装では船体タイプ、排水量などから基本性能を計算
            # 現時点ではダミー値を設定
            base_stats = {
                "build_cost_ic": 10.0,
                "manpower": 500,
                "reliability": 0.8,
                "naval_speed": hull_data.get("speed", 0),  # 船体の速力を使用
                "naval_range": hull_data.get("range", 0),  # 船体の航続距離を使用
                "surface_visibility": hull_data.get("weight", 0) * 0.01,  # 排水量に比例
                "port_capacity_usage": hull_data.get("weight", 0) * 0.0001  # 排水量に比例
            }

            # 基本性能を反映
            for key, value in base_stats.items():
                if key in stats:
                    stats[key] = value

            # 装備による性能加算（本来は装備種別ごとに処理が必要）
            for eq_data in equipment_data:
                eq_stats = eq_data.get("stats", {}).get("add_stats", {})

                # 各統計値を加算
                for key, value in eq_stats.items():
                    if key in stats:
                        stats[key] += float(value)

            # 値の調整（例: 信頼性は0.0〜1.0に制限）
            if stats["reliability"] > 1.0:
                stats["reliability"] = 1.0
            elif stats["reliability"] < 0.0:
                stats["reliability"] = 0.0

            # shore_bombardmentはlg_attackとhg_attackから計算（仮実装）
            stats["shore_bombardment"] = (stats["lg_attack"] * 0.3 + stats["hg_attack"] * 0.7)

            # evasionはnaval_speedから計算（仮実装）
            stats["evasion"] = stats["naval_speed"] * 0.5

            return stats

        except Exception as e:
            print(f"設計性能計算中にエラーが発生しました: {e}")
            return {}

    def get_equipment_for_design(self, design_data):
        """
        設計に使用されている装備データを取得

        Args:
            design_data (dict): 設計データ

        Returns:
            dict: スロットごとの装備データ
        """
        try:
            result = {}
            slots = design_data.get("slots", {})

            # 各スロットの装備IDから装備データを取得
            for slot_type, equipment_id in slots.items():
                equipment_data = self.load_equipment(equipment_id)
                if equipment_data:
                    result[slot_type] = equipment_data

            return result

        except Exception as e:
            print(f"設計の装備データ取得中にエラーが発生しました: {e}")
            return {}

    def load_equipment_templates(self):
        """YAMLファイルから装備テンプレートを読み込む"""
        try:
            import yaml
            import os

            # ファイルパスの取得
            template_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'equipments_templates.yml'
            )

            if not os.path.exists(template_file):
                print(f"警告: 装備テンプレートファイル '{template_file}' が見つかりません。")
                return {}

            # YAMLファイルの読み込み
            with open(template_file, 'r', encoding='utf-8') as f:
                templates = yaml.safe_load(f)

            return templates
        except Exception as e:
            print(f"装備テンプレート読み込みエラー: {e}")
            return {}

    def get_equipment_categories(self):
        """装備カテゴリのリストを取得"""
        try:
            templates = self.load_equipment_templates()
            return list(templates.keys())
        except Exception as e:
            print(f"装備カテゴリ取得中にエラーが発生しました: {e}")
            return []

    def get_equipment_types(self):
        """全ての装備タイプとその表示名を取得"""
        try:
            templates = self.load_equipment_templates()
            equipment_types = []

            # カテゴリごとに装備タイプを収集
            for category_key, category_data in templates.items():
                if isinstance(category_data, dict):
                    for type_key, type_data in category_data.items():
                        if isinstance(type_data, dict) and 'display_name' in type_data:
                            equipment_types.append(type_data['display_name'])

            return equipment_types
        except Exception as e:
            print(f"装備タイプ取得中にエラーが発生しました: {e}")
            return []

    def get_equipment_types_by_category(self, category):
        """特定のカテゴリに属する装備タイプのリストを取得"""
        try:
            templates = self.load_equipment_templates()
            if category in templates and isinstance(templates[category], dict):
                return [type_data['display_name']
                        for type_key, type_data in templates[category].items()
                        if isinstance(type_data, dict) and 'display_name' in type_data]
            return []
        except Exception as e:
            print(f"カテゴリ別装備タイプ取得中にエラーが発生しました: {e}")
            return []