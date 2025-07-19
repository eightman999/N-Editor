# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: data_loadersユーティリティ
import csv
import os
import time
import logging
from typing import List, Dict, Any

# ロガーの設定
logger = logging.getLogger(__name__)


def load_status_definitions(file_path: str, cache_manager=None) -> List[Dict[str, str]]:
    """
    ステータス定義CSVファイルを読み込む（キャッシュ対応）

    Args:
        file_path: CSVファイルのパス
        cache_manager: キャッシュマネージャーのインスタンス

    Returns:
        ステータス定義のリスト [{'id': str, 'japanese': str, 'english': str}, ...]

    Raises:
        FileNotFoundError: ファイルが見つからない場合
        ValueError: CSV形式が不正な場合
    """
    start_time = time.time()
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"ステータス定義ファイルが見つかりません: {file_path}")

    # キャッシュから読み込み試行
    if cache_manager:
        cached_data = cache_manager.load("status_definitions", file_path)
        if cached_data is not None:
            duration = time.time() - start_time
            logger.debug(f"ステータス定義をキャッシュから読み込み: {len(cached_data)}件, 時間: {duration:.3f}秒")
            return cached_data

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

        # キャッシュに保存
        if definitions and cache_manager:
            cache_manager.save("status_definitions", file_path, definitions)

    except Exception as e:
        raise ValueError(f"CSV読み込みエラー: {e}")

    duration = time.time() - start_time
    logger.info(f"ステータス定義読み込み完了: {len(definitions)}件, 時間: {duration:.3f}秒")
    
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