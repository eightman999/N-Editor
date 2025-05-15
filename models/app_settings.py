import os
import json
import platform
from pathlib import Path

class AppSettings:
    """アプリケーション設定を管理するクラス"""
    def __init__(self):
        # アプリケーション名
        self.app_name = "NavalDesignSystem"

        # 設定ディレクトリ
        self.settings_dir = self._get_settings_dir()

        # データディレクトリ
        self.data_dir = self._get_data_dir()

        # 設定ファイルのパス
        self.settings_file = os.path.join(self.settings_dir, "settings.json")

        # MOD情報ファイルのパス
        self.mods_file = os.path.join(self.settings_dir, "mods.json")

        # データディレクトリのパス
        self.equipment_dir = os.path.join(self.data_dir, "equipments")
        self.hull_dir = os.path.join(self.data_dir, "hulls")
        self.design_dir = os.path.join(self.data_dir, "designs")
        self.fleet_dir = os.path.join(self.data_dir, "fleets")

        # 必要なディレクトリを作成
        self._ensure_directories()

        # デフォルト設定
        self.settings = {
            "theme": "light",
            "language": "ja",
            "last_mod_id": None,
            "current_mod_path": None,
            "current_mod_name": None,
            "window_size": [800, 600],
            "window_position": [100, 100],
            "first_run": True
        }

        # MOD情報のリスト
        self.mods = []

        # 設定をロード
        self.load_settings()
        self.load_mods()

    def _get_settings_dir(self):
        """OSに応じた設定ディレクトリのパスを返す"""
        return self._get_app_dir()

    def _get_data_dir(self):
        """OSに応じたデータディレクトリのパスを返す"""
        return self._get_app_dir()

    def _get_app_dir(self):
        """OSに応じたアプリケーションディレクトリのパスを返す"""
        system = platform.system()
        home = Path.home()

        if system == "Windows":
            # Windows: ドキュメント/NavalDesignSystem
            documents = os.path.join(home, "Documents")
            return os.path.join(documents, self.app_name)
        elif system == "Darwin":
            # macOS: ~/Library/Application Support/NavalDesignSystem
            return os.path.join(home, "Library", "Application Support", self.app_name)
        else:
            # Linux: ~/.local/share/navaldesignsystem
            return os.path.join(home, ".local", "share", self.app_name.lower())

    def _ensure_directories(self):
        """必要なディレクトリを作成する"""
        directories = [
            self.settings_dir,
            self.data_dir,
            self.equipment_dir,
            self.hull_dir,
            self.design_dir,
            self.fleet_dir
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    def load_settings(self):
        """設定ファイルから設定をロード"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # デフォルト設定をロードした設定で更新
                    self.settings.update(loaded_settings)
        except Exception as e:
            print(f"設定ファイルの読み込み中にエラーが発生しました: {e}")

    def save_settings(self):
        """設定をファイルに保存"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"設定ファイルの保存中にエラーが発生しました: {e}")

    def load_mods(self):
        """MOD情報をファイルからロード"""
        try:
            if os.path.exists(self.mods_file):
                with open(self.mods_file, 'r', encoding='utf-8') as f:
                    self.mods = json.load(f)
        except Exception as e:
            print(f"MOD情報の読み込み中にエラーが発生しました: {e}")

    def save_mods(self):
        """MOD情報をファイルに保存"""
        try:
            with open(self.mods_file, 'w', encoding='utf-8') as f:
                json.dump(self.mods, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"MOD情報の保存中にエラーが発生しました: {e}")

    def get_setting(self, key, default=None):
        """設定値を取得"""
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        """設定値を設定して保存"""
        self.settings[key] = value
        self.save_settings()

    def add_mod(self, mod_info):
        """MODをリストに追加"""
        # 既存のMODを更新または新規追加
        for i, mod in enumerate(self.mods):
            if mod.get("path") == mod_info.get("path"):
                self.mods[i] = mod_info
                self.save_mods()
                return

        # 新規追加
        self.mods.append(mod_info)
        self.save_mods()

    def remove_mod(self, mod_path):
        """指定したパスのMODをリストから削除"""
        self.mods = [mod for mod in self.mods if mod.get("path") != mod_path]
        self.save_mods()

    def get_mods(self):
        """MODリストを取得"""
        return self.mods

    def get_current_mod(self):
        """現在選択中のMOD情報を取得"""
        mod_path = self.get_setting("current_mod_path")
        mod_name = self.get_setting("current_mod_name")

        if mod_path:
            return {
                "path": mod_path,
                "name": mod_name
            }
        return None

    def set_current_mod(self, mod_path, mod_name=None):
        """現在選択中のMODを設定"""
        self.set_setting("current_mod_path", mod_path)
        if mod_name:
            self.set_setting("current_mod_name", mod_name)