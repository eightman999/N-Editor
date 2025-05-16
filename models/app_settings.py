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




    def verify_settings_saved(self):
        """設定が正しく保存されたか確認する"""
        try:
            # 現在のメモリ内の設定を表示
            print(f"メモリ内の設定: {self.settings}")

            # 保存先のファイルパスを表示
            print(f"設定ファイルパス: {self.settings_file}")

            # 設定ディレクトリの存在確認
            if not os.path.exists(self.settings_dir):
                print(f"警告: 設定ディレクトリが存在しません: {self.settings_dir}")
            else:
                print(f"設定ディレクトリは存在します: {self.settings_dir}")

            # 設定ファイルの存在確認
            if not os.path.exists(self.settings_file):
                print(f"警告: 設定ファイルが存在しません: {self.settings_file}")
                return False

            # 設定ファイルの内容を読み込んで確認
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                    print(f"保存された設定: {saved_settings}")

                    # current_mod関連の設定を確認
                    if 'current_mod_path' in saved_settings:
                        print(f"保存されたcurrent_mod_path: {saved_settings.get('current_mod_path')}")
                    else:
                        print("警告: current_mod_pathが設定ファイルに存在しません")

                    if 'current_mod_name' in saved_settings:
                        print(f"保存されたcurrent_mod_name: {saved_settings.get('current_mod_name')}")
                    else:
                        print("警告: current_mod_nameが設定ファイルに存在しません")

                    # メモリ内の設定と比較
                    if saved_settings.get('current_mod_path') != self.settings.get('current_mod_path'):
                        print("警告: current_mod_pathがメモリと設定ファイルで一致しません")

                    if saved_settings.get('current_mod_name') != self.settings.get('current_mod_name'):
                        print("警告: current_mod_nameがメモリと設定ファイルで一致しません")

                    return True
            except Exception as e:
                print(f"設定ファイルの読み込み中にエラーが発生しました: {e}")
                return False
        except Exception as e:
            print(f"設定検証中にエラーが発生しました: {e}")
            return False

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

            # 設定が保存されたことを確認
            self.verify_settings_saved()

    def load_settings(self):
        """設定ファイルから設定をロード"""
        try:
            print(f"設定ファイルをロード: {self.settings_file}")
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # デフォルト設定をロードした設定で更新
                    self.settings.update(loaded_settings)
                    print(f"設定ファイルを正常にロードしました: {loaded_settings}")
                    # MOD関連の設定を確認
                    if 'current_mod_path' in loaded_settings:
                        print(f"ロードしたcurrent_mod_path: {loaded_settings.get('current_mod_path')}")
                    if 'current_mod_name' in loaded_settings:
                        print(f"ロードしたcurrent_mod_name: {loaded_settings.get('current_mod_name')}")
            else:
                print(f"設定ファイルが存在しません。デフォルト設定を使用します: {self.settings}")
        except Exception as e:
            print(f"設定ファイルの読み込み中にエラーが発生しました: {e}")

    def save_settings(self):
        """設定をファイルに保存"""
        try:
            print(f"設定ファイルに保存: {self.settings_file}")

            # 設定ディレクトリの存在を確認・作成
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)

            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
                print(f"設定を保存しました: {self.settings}")

            # 保存後に設定ファイルが存在することを確認
            if os.path.exists(self.settings_file):
                print(f"設定ファイルの保存を確認: {os.path.getsize(self.settings_file)} バイト")
            else:
                print("警告: 設定ファイルが保存されていません")
        except Exception as e:
            print(f"設定ファイルの保存中にエラーが発生しました: {e}")
            # エラーの詳細情報
            import traceback
            traceback.print_exc()

            # ディレクトリ権限などの確認
            try:
                parent_dir = os.path.dirname(self.settings_file)
                if not os.path.exists(parent_dir):
                    print(f"親ディレクトリが存在しません: {parent_dir}")
                else:
                    print(f"親ディレクトリの権限: {oct(os.stat(parent_dir).st_mode)[-3:]}")
            except Exception as dir_error:
                print(f"ディレクトリ確認中にエラー: {dir_error}")
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
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"ディレクトリを確認・作成しました: {directory}")
                # ディレクトリの権限を確認
                if os.path.exists(directory):
                    print(f"ディレクトリの権限: {oct(os.stat(directory).st_mode)[-3:]}")
                else:
                    print(f"警告: ディレクトリの作成に失敗: {directory}")
            except Exception as e:
                print(f"ディレクトリの作成中にエラーが発生しました: {directory}, エラー: {e}")
                import traceback
                traceback.print_exc()