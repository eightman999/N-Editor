import os
import json
import shutil
import sqlite3

# プロジェクトのルートディレクトリ
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# データディレクトリ
DATA_DIR = os.path.join(ROOT_DIR, 'data')
EQUIPMENT_DIR = os.path.join(DATA_DIR, 'equipments')
HULL_DIR = os.path.join(DATA_DIR, 'hulls')
DESIGN_DIR = os.path.join(DATA_DIR, 'designs')
FLEET_DIR = os.path.join(DATA_DIR, 'fleets')

# SQLiteデータベースファイル
DB_FILE = os.path.join(DATA_DIR, 'naval_design.db')

# 設定ファイル
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')

# ステータス定義ファイル
STATS_FILE = os.path.join(ROOT_DIR, 'スーテータス一覧')

# テンプレート定義ファイル
TEMPLATE_FILE = os.path.join(ROOT_DIR, 'paste.txt')

def ensure_directory_structure():
    """必要なディレクトリ構造を確保する"""
    directories = [
        DATA_DIR,
        EQUIPMENT_DIR,
        HULL_DIR,
        DESIGN_DIR,
        FLEET_DIR
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"ディレクトリを確認: {directory}")

def initialize_database():
    """SQLiteデータベースを初期化する"""
    # データベースが既に存在する場合はバックアップ
    if os.path.exists(DB_FILE):
        backup_file = f"{DB_FILE}.bak"
        shutil.copy2(DB_FILE, backup_file)
        print(f"既存のデータベースをバックアップ: {backup_file}")

    # データベース接続
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # テーブル作成
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS equipment_types (
        id TEXT PRIMARY KEY,
        name TEXT,
        prefix TEXT,
        description TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS hull_types (
        id TEXT PRIMARY KEY,
        name TEXT,
        description TEXT,
        displacement_min REAL,
        displacement_max REAL
    )
    ''')

    # 初期設定の保存
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                   ("version", "1.0.0"))

    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                   ("created_at", "2025-05-15"))

    # コミットして閉じる
    conn.commit()
    conn.close()

    print(f"データベースを初期化: {DB_FILE}")

def create_default_config():
    """デフォルト設定ファイルを作成する"""
    default_config = {
        "app_name": "Naval Design System",
        "version": "1.0.0",
        "data_paths": {
            "equipment": "data/equipments",
            "hull": "data/hulls",
            "design": "data/designs",
            "fleet": "data/fleets"
        },
        "display": {
            "width": 800,
            "height": 600,
            "theme": "Windows95",
            "language": "ja_JP"
        },
        "calculation": {
            "stats_mode": "add_stats",  # デフォルトは単純加算
            "formula_version": "1.0"
        }
    }

    # 設定ファイルの書き込み
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, ensure_ascii=False, indent=2)

    print(f"デフォルト設定ファイルを作成: {CONFIG_FILE}")

def ensure_equipment_templates():
    """装備テンプレートディレクトリを初期化する"""
    # ステータス定義が存在するか確認
    if not os.path.exists(STATS_FILE):
        print(f"警告: ステータス定義ファイルが見つかりません: {STATS_FILE}")
    else:
        print(f"ステータス定義ファイルを確認: {STATS_FILE}")

    # テンプレート定義が存在するか確認
    if not os.path.exists(TEMPLATE_FILE):
        print(f"警告: テンプレート定義ファイルが見つかりません: {TEMPLATE_FILE}")
    else:
        print(f"テンプレート定義ファイルを確認: {TEMPLATE_FILE}")

        # テンプレート定義からIDプレフィックスを抽出し、サブディレクトリを作成
        try:
            with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                content = f.read()

            # プレフィックスを抽出する簡易パーサー
            prefixes = []
            for line in content.split('\n'):
                if 'id_prefix:' in line:
                    prefix = line.split('id_prefix:')[1].strip()
                    prefixes.append(prefix)

            # 装備タイプごとのディレクトリを作成
            for prefix in prefixes:
                type_dir = os.path.join(EQUIPMENT_DIR, prefix)
                os.makedirs(type_dir, exist_ok=True)
                print(f"装備タイプディレクトリを確認: {type_dir}")

        except Exception as e:
            print(f"テンプレート処理でエラーが発生しました: {e}")

def main():
    """セットアップ処理のメイン関数"""
    print("Naval Design System セットアップを開始します...")

    # 必要なディレクトリ構造を確保
    ensure_directory_structure()

    # データベース初期化
    initialize_database()

    # デフォルト設定ファイルの作成
    create_default_config()

    # 装備テンプレートの確認
    ensure_equipment_templates()

    print("セットアップが完了しました。")

if __name__ == "__main__":
    main()