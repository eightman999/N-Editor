#!/usr/bin/env python3
"""
キャッシュパフォーマンステストスクリプト

このスクリプトはキャッシュシステムの効果を測定します。
"""

import os
import sys
import time
import logging

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.hull_model import HullModel
from models.equipment_model import EquipmentModel
from utils.cache_manager import CacheManager
from utils.performance_monitor import PerformanceMonitor

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_hull_model_performance():
    """船体モデルのパフォーマンステスト"""
    print("="*60)
    print("船体モデル パフォーマンステスト")
    print("="*60)
    
    # テスト用データディレクトリ
    test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data', 'hulls')
    
    # キャッシュマネージャー初期化
    cache_manager = CacheManager("_test_mod_")
    performance_monitor = PerformanceMonitor(cache_manager)
    
    # キャッシュクリア
    cache_manager.clear_cache("hulls_all")
    
    # 1回目: キャッシュなし
    print("\n--- 1回目の読み込み（キャッシュなし） ---")
    hull_model_1 = HullModel(data_dir=test_data_dir, cache_manager=cache_manager)
    
    start_time = time.time()
    hulls_1 = hull_model_1.get_all_hulls()
    duration_1 = time.time() - start_time
    
    print(f"読み込み時間: {duration_1:.3f}秒")
    print(f"読み込み件数: {len(hulls_1)}件")
    
    # 2回目: キャッシュあり
    print("\n--- 2回目の読み込み（キャッシュあり） ---")
    hull_model_2 = HullModel(data_dir=test_data_dir, cache_manager=cache_manager)
    
    start_time = time.time()
    hulls_2 = hull_model_2.get_all_hulls()
    duration_2 = time.time() - start_time
    
    print(f"読み込み時間: {duration_2:.3f}秒")
    print(f"読み込み件数: {len(hulls_2)}件")
    
    # パフォーマンス改善計算
    if duration_1 > 0:
        improvement_ratio = (duration_1 - duration_2) / duration_1 * 100
        speedup = duration_1 / duration_2 if duration_2 > 0 else float('inf')
        print(f"\nパフォーマンス改善:")
        print(f"  改善率: {improvement_ratio:.1f}%")
        print(f"  高速化: {speedup:.1f}倍")
    
    # キャッシュ情報
    cache_info = cache_manager.get_cache_info()
    print(f"\nキャッシュ情報:")
    print(f"  キャッシュディレクトリ: {cache_info['base_cache_dir']}")
    print(f"  キャッシュファイル種別数: {len(cache_info['file_types'])}")


def test_equipment_model_performance():
    """装備モデルのパフォーマンステスト"""
    print("\n" + "="*60)
    print("装備モデル パフォーマンステスト")
    print("="*60)
    
    # テスト用データディレクトリ
    test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data', 'equipments')
    
    # キャッシュマネージャー初期化
    cache_manager = CacheManager("_test_mod_")
    
    # キャッシュクリア
    cache_manager.clear_cache("equipment_all")
    cache_manager.clear_cache("equipment_templates")
    
    # 1回目: キャッシュなし
    print("\n--- 1回目の読み込み（キャッシュなし） ---")
    equipment_model_1 = EquipmentModel(data_dir=test_data_dir, cache_manager=cache_manager)
    
    start_time = time.time()
    equipments_1 = equipment_model_1.get_all_equipment()
    duration_1 = time.time() - start_time
    
    print(f"読み込み時間: {duration_1:.3f}秒")
    print(f"読み込み件数: {len(equipments_1)}件")
    print(f"テンプレート種類: {len(equipment_model_1.equipment_templates)}種類")
    
    # 2回目: キャッシュあり
    print("\n--- 2回目の読み込み（キャッシュあり） ---")
    equipment_model_2 = EquipmentModel(data_dir=test_data_dir, cache_manager=cache_manager)
    
    start_time = time.time()
    equipments_2 = equipment_model_2.get_all_equipment()
    duration_2 = time.time() - start_time
    
    print(f"読み込み時間: {duration_2:.3f}秒")
    print(f"読み込み件数: {len(equipments_2)}件")
    print(f"テンプレート種類: {len(equipment_model_2.equipment_templates)}種類")
    
    # パフォーマンス改善計算
    if duration_1 > 0:
        improvement_ratio = (duration_1 - duration_2) / duration_1 * 100
        speedup = duration_1 / duration_2 if duration_2 > 0 else float('inf')
        print(f"\nパフォーマンス改善:")
        print(f"  改善率: {improvement_ratio:.1f}%")
        print(f"  高速化: {speedup:.1f}倍")


def create_test_data():
    """テスト用データを作成"""
    print("テスト用データを作成中...")
    
    # テスト用データディレクトリを作成
    test_dir = os.path.join(os.path.dirname(__file__), 'test_data')
    hulls_dir = os.path.join(test_dir, 'hulls')
    equipments_dir = os.path.join(test_dir, 'equipments')
    
    os.makedirs(hulls_dir, exist_ok=True)
    os.makedirs(equipments_dir, exist_ok=True)
    
    # テスト用船体データを作成
    for i in range(50):  # 50件のテストデータ
        hull_data = {
            "id": f"TEST_HULL_{i:03d}",
            "name": f"テスト船体{i}",
            "type": "DD - 駆逐艦",
            "country": "JPN",
            "weight": 1000 + i * 10,
            "length": 100 + i,
            "width": 10 + i * 0.1,
            "speed": 30 + i * 0.5,
            "crew": 200 + i * 5
        }
        
        hull_file = os.path.join(hulls_dir, f"TEST_HULL_{i:03d}.json")
        with open(hull_file, 'w', encoding='utf-8') as f:
            import json
            json.dump(hull_data, f, ensure_ascii=False, indent=2)
    
    print(f"テスト用船体データを作成: {hulls_dir}")


def main():
    """メイン関数"""
    print("キャッシュパフォーマンステストを開始")
    
    try:
        # テスト用データを作成
        create_test_data()
        
        # 船体モデルテスト
        test_hull_model_performance()
        
        # 装備モデルテスト（データがある場合のみ）
        test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data', 'equipments')
        if os.path.exists(test_data_dir) and os.listdir(test_data_dir):
            test_equipment_model_performance()
        else:
            print("\n装備テストデータが見つからないため、装備モデルテストをスキップします")
        
        print("\n" + "="*60)
        print("キャッシュパフォーマンステスト完了")
        print("="*60)
        
    except Exception as e:
        logger.error(f"テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()