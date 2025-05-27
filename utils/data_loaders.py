import csv
import os
from typing import List, Dict, Any


def load_status_definitions(file_path: str) -> List[Dict[str, str]]:
    """
    ステータス定義CSVファイルを読み込む

    Args:
        file_path: CSVファイルのパス

    Returns:
        ステータス定義のリスト [{'id': str, 'japanese': str, 'english': str}, ...]

    Raises:
        FileNotFoundError: ファイルが見つからない場合
        ValueError: CSV形式が不正な場合
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"ステータス定義ファイルが見つかりません: {file_path}")

    definitions = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):  # ヘッダー行を除いて2行目から
                if not all(key in row for key in ['id', 'japanese', 'english']):
                    raise ValueError(f"必要なカラムが不足しています（行{row_num}）: {row}")

                definitions.append({
                    'id': row['id'].strip(),
                    'japanese': row['japanese'].strip(),
                    'english': row['english'].strip()
                })

    except Exception as e:
        raise ValueError(f"CSV読み込みエラー: {e}")

    return definitions


def get_default_status_definitions() -> List[Dict[str, str]]:
    """
    デフォルトのステータス定義を返す（ファイルが見つからない場合のフォールバック）
    """
    return [
        {'id': 'build_cost_ic', 'japanese': '生産コスト', 'english': 'Production Cost'},
        {'id': 'manpower', 'japanese': '人員', 'english': 'Manpower'},
        {'id': 'reliability', 'japanese': '信頼性', 'english': 'Reliability'},
        {'id': 'naval_speed', 'japanese': '最大速度', 'english': 'Max Speed'},
        # 必要に応じて他の項目を追加
    ]