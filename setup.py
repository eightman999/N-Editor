import os
import sys

# ディレクトリ構造を確認・作成する関数
def create_directory_structure():
    """
    プロジェクトのディレクトリ構造を確認・作成する関数
    """
    # プロジェクトのルートディレクトリ
    root_dir = os.path.dirname(os.path.abspath(__file__))

    # 必要なディレクトリとファイルのリスト
    directories = [
        "assets",
        "controllers",
        "models",
        "views"
    ]

    # ディレクトリが存在しなければ作成
    for directory in directories:
        dir_path = os.path.join(root_dir, directory)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"ディレクトリを作成しました: {dir_path}")

    # __init__.pyファイルを作成
    for directory in directories:
        init_file = os.path.join(root_dir, directory, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write("# このファイルはPythonパッケージを示します\n")
            print(f"__init__.pyファイルを作成しました: {init_file}")

# 必要なファイルを生成・確認する関数
def create_required_files():
    """必要なファイルを生成・確認する関数"""
    root_dir = os.path.dirname(os.path.abspath(__file__))

    # AppSettings クラスを models/app_settings.py に保存
    app_settings_path = os.path.join(root_dir, "models", "app_settings.py")
    if not os.path.exists(app_settings_path):
        app_settings_code = '''import os
import json
import platform
from pathlib import Path

class AppSettings:
    """アプリケーション設定を管理するクラス"""
    def __init__(self):
        self.settings_dir = self._get_settings_dir()
        self.settings_file = os.path.join(self.settings_dir, "settings.json")
        self.mods_file = os.path.join(self.settings_dir, "mods.json")
        
        # 設定ディレクトリが存在しない場合は作成
        os.makedirs(self.settings_dir, exist_ok=True)
        
        # デフォルト設定
        self.settings = {
            "theme": "light",
            "language": "ja",
            "last_mod_id": None,
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
        system = platform.system()
        home = Path.home()
        
        if system == "Windows":
            # Windows: ドキュメント/N-Editor
            documents = os.path.join(home, "Documents")
            return os.path.join(documents, "N-Editor")
        elif system == "Darwin":
            # macOS: ~/Library/Application Support/N-Editor
            return os.path.join(home, "Library", "Application Support", "N-Editor")
        else:
            # Linux: ~/.config/n-editor
            return os.path.join(home, ".config", "n-editor")
    
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
'''
        with open(app_settings_path, 'w', encoding='utf-8') as f:
            f.write(app_settings_code)
        print(f"ファイルを作成しました: {app_settings_path}")

    # 空のフォームファイルを作成
    for form_name in ['equipment_form.py', 'hull_form.py', 'design_view.py', 'fleet_view.py', 'settings_view.py']:
        form_path = os.path.join(root_dir, "views", form_name)
        if not os.path.exists(form_path):
            form_code = f'''from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

class {form_name.split('.')[0].title().replace('_', '')}(QWidget):
    """{''.join(word.capitalize() for word in form_name.split('.')[0].split('_'))} ビュー"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # 仮のラベル
        label = QLabel("{''.join(word.capitalize() for word in form_name.split('.')[0].split('_'))} - 開発中", self)
        layout.addWidget(label)
        
        self.setLayout(layout)
'''
            with open(form_path, 'w', encoding='utf-8') as f:
                f.write(form_code)
            print(f"ファイルを作成しました: {form_path}")

if __name__ == "__main__":
    create_directory_structure()
    create_required_files()
    print("セットアップが完了しました。")