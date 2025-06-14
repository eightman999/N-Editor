#!/usr/bin/env python3
r"""
MOD設計データキャッシュ機能テスト

このスクリプトはMODDataCacheManagerの設計データキャッシュ機能をテストします。
"""

import os
import sys
import time
import tempfile
import json
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.mod_data_cache_manager import MODDataCacheManager


def create_test_mod_structure(mod_path: Path):
    """テスト用のMOD構造を作成"""
    # 設計ディレクトリを作成
    designs_dir = mod_path / "designs"
    designs_dir.mkdir(parents=True, exist_ok=True)
    
    # 船体ディレクトリを作成
    units_dir = mod_path / "common" / "units"
    units_dir.mkdir(parents=True, exist_ok=True)
    
    # 装備ディレクトリを作成
    equipment_dir = mod_path / "common" / "units" / "equipment"
    equipment_dir.mkdir(parents=True, exist_ok=True)
    
    # テスト用設計ファイルを作成
    test_design = {
        "id": "TEST_DESIGN_001",
        "design_name": "テスト艦船",
        "hull": {
            "id": "destroyer_hull",
            "weight": 1000,
            "speed": 35,
            "range": 3000,
            "reliability": 0.9
        },
        "main_slots": {
            "PA": "test_gun_equipment",
            "SA": "test_secondary_gun",
            "PSA": None,
            "SSA": None,
            "PLA": None,
            "SLA": None
        },
        "internal_slots": [],
        "created_at": time.time()
    }
    
    # 設計ファイルを保存（ヘッダー付き）
    design_file = designs_dir / "TEST_DESIGN_001.json"
    with open(design_file, 'w', encoding='utf-8') as f:
        f.write("@config.design\n")
        json.dump(test_design, f, ensure_ascii=False, indent=2)
    
    # ダミー船体ファイル
    hull_file = units_dir / "destroyer.txt"
    hull_file.write_text("# Test hull file\ndestroyer_hull = { ... }")
    
    # ダミー装備ファイル
    equipment_file = equipment_dir / "guns.txt"
    equipment_file.write_text("# Test equipment file\ntest_gun_equipment = { ... }")
    
    return design_file, test_design


def test_design_cache_basic():
    """基本的な設計キャッシュ機能をテスト"""
    print("=== 基本的な設計キャッシュ機能テスト ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        mod_path = Path(temp_dir) / "test_mod"
        mod_path.mkdir()
        
        # テスト用MOD構造を作成
        design_file, test_design = create_test_mod_structure(mod_path)
        
        # MODDataCacheManagerを初期化
        cache_manager = MODDataCacheManager(str(mod_path))
        
        print(f"MOD パス: {mod_path}")
        print(f"キャッシュディレクトリ: {cache_manager.cache_dir}")
        
        # キャッシュが存在しないことを確認
        cached_data = cache_manager.load_design_cache(str(design_file))
        assert cached_data is None, "初期状態でキャッシュが存在してはいけません"
        print("✓ 初期状態でキャッシュが存在しないことを確認")
        
        # 設計データをキャッシュに保存
        cache_manager.save_design_cache(str(design_file), test_design)
        print("✓ 設計データをキャッシュに保存")
        
        # キャッシュから読み込み
        cached_data = cache_manager.load_design_cache(str(design_file))
        assert cached_data is not None, "キャッシュからデータが読み込めません"
        assert cached_data['id'] == test_design['id'], "キャッシュされたデータのIDが一致しません"
        assert cached_data['design_name'] == test_design['design_name'], "キャッシュされたデータの名前が一致しません"
        print("✓ キャッシュからデータを正常に読み込み")
        
        print("基本的な設計キャッシュ機能テスト: 成功")


def test_design_cache_invalidation():
    """設計キャッシュの無効化機能をテスト"""
    print("\n=== 設計キャッシュ無効化機能テスト ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        mod_path = Path(temp_dir) / "test_mod"
        mod_path.mkdir()
        
        # テスト用MOD構造を作成
        design_file, test_design = create_test_mod_structure(mod_path)
        
        # MODDataCacheManagerを初期化
        cache_manager = MODDataCacheManager(str(mod_path))
        
        # 設計データをキャッシュに保存
        cache_manager.save_design_cache(str(design_file), test_design)
        
        # キャッシュが有効であることを確認
        cached_data = cache_manager.load_design_cache(str(design_file))
        assert cached_data is not None, "キャッシュが無効です"
        print("✓ キャッシュが有効であることを確認")
        
        # ファイルを少し待ってから更新（タイムスタンプを変更）
        time.sleep(0.1)
        with open(design_file, 'a', encoding='utf-8') as f:
            f.write("# Updated")
        
        # キャッシュが無効化されることを確認
        cached_data = cache_manager.load_design_cache(str(design_file))
        assert cached_data is None, "ファイル更新後もキャッシュが有効です"
        print("✓ ファイル更新後にキャッシュが無効化されることを確認")
        
        print("設計キャッシュ無効化機能テスト: 成功")


def test_bulk_design_cache():
    """一括設計データキャッシュ機能をテスト"""
    print("\n=== 一括設計データキャッシュ機能テスト ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        mod_path = Path(temp_dir) / "test_mod"
        mod_path.mkdir()
        
        # テスト用MOD構造を作成
        design_file, test_design = create_test_mod_structure(mod_path)
        
        # MODDataCacheManagerを初期化
        cache_manager = MODDataCacheManager(str(mod_path))
        
        # 複数の設計データを準備
        designs_list = [test_design]
        for i in range(2, 5):
            design = test_design.copy()
            design['id'] = f"TEST_DESIGN_{i:03d}"
            design['design_name'] = f"テスト艦船{i}"
            designs_list.append(design)
        
        # 設計一覧をキャッシュに保存
        cache_manager.save_cached_data('designs', designs_list)
        print(f"✓ {len(designs_list)}個の設計データをキャッシュに保存")
        
        # キャッシュから読み込み
        cached_designs = cache_manager.load_cached_data('designs')
        assert cached_designs is not None, "一括キャッシュからデータが読み込めません"
        assert len(cached_designs) == len(designs_list), "キャッシュされた設計数が一致しません"
        print("✓ 一括キャッシュからデータを正常に読み込み")
        
        # キャッシュクリア
        cache_manager.clear_cache('designs')
        cached_designs = cache_manager.load_cached_data('designs')
        assert cached_designs is None, "キャッシュクリア後もデータが残っています"
        print("✓ キャッシュクリア機能が正常に動作")
        
        print("一括設計データキャッシュ機能テスト: 成功")


def test_design_stats_cache():
    """設計統計キャッシュ機能をテスト"""
    print("\n=== 設計統計キャッシュ機能テスト ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        mod_path = Path(temp_dir) / "test_mod"
        mod_path.mkdir()
        
        # テスト用MOD構造を作成
        design_file, test_design = create_test_mod_structure(mod_path)
        
        # MODDataCacheManagerを初期化
        cache_manager = MODDataCacheManager(str(mod_path))
        
        # テスト用統計データ
        test_stats = {
            'naval_speed': 35.0,
            'naval_range': 3000.0,
            'reliability': 0.9,
            'attack': 12.5,
            'piercing': 8.0,
            'armor': 2.0
        }
        
        design_id = test_design['id']
        
        # 統計データをキャッシュに保存
        cache_manager.save_design_stats_cache(design_id, test_stats)
        print("✓ 設計統計データをキャッシュに保存")
        
        # キャッシュから読み込み
        cached_stats = cache_manager.load_design_stats_cache(design_id)
        assert cached_stats is not None, "統計キャッシュからデータが読み込めません"
        assert cached_stats['naval_speed'] == test_stats['naval_speed'], "統計データが一致しません"
        assert len(cached_stats) == len(test_stats), "統計データの項目数が一致しません"
        print("✓ 統計キャッシュからデータを正常に読み込み")
        
        # 設計特定のキャッシュクリア
        cache_manager.clear_design_cache(design_id)
        cached_stats = cache_manager.load_design_stats_cache(design_id)
        assert cached_stats is None, "設計特定キャッシュクリア後もデータが残っています"
        print("✓ 設計特定キャッシュクリア機能が正常に動作")
        
        print("設計統計キャッシュ機能テスト: 成功")


def test_cache_performance():
    """キャッシュパフォーマンステスト"""
    print("\n=== キャッシュパフォーマンステスト ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        mod_path = Path(temp_dir) / "test_mod"
        mod_path.mkdir()
        
        # テスト用MOD構造を作成
        design_file, test_design = create_test_mod_structure(mod_path)
        
        # MODDataCacheManagerを初期化
        cache_manager = MODDataCacheManager(str(mod_path))
        
        # 大きな設計データを作成
        large_design = test_design.copy()
        large_design['large_data'] = ['dummy_data'] * 1000  # 大きなデータを追加
        
        # 保存時間測定
        start_time = time.time()
        cache_manager.save_design_cache(str(design_file), large_design)
        save_time = time.time() - start_time
        print(f"✓ 大きなデータの保存時間: {save_time:.4f}秒")
        
        # 読み込み時間測定
        start_time = time.time()
        cached_data = cache_manager.load_design_cache(str(design_file))
        load_time = time.time() - start_time
        assert cached_data is not None, "大きなデータのキャッシュ読み込みに失敗"
        print(f"✓ 大きなデータの読み込み時間: {load_time:.4f}秒")
        
        # パフォーマンス統計を取得
        stats = cache_manager.get_cache_stats()
        print(f"✓ キャッシュ統計: {stats}")
        
        print("キャッシュパフォーマンステスト: 成功")


def main():
    """メインテスト実行"""
    print("MOD設計データキャッシュ機能テスト開始")
    print("=" * 50)
    
    try:
        test_design_cache_basic()
        test_design_cache_invalidation()
        test_bulk_design_cache()
        test_design_stats_cache()
        test_cache_performance()
        
        print("\n" + "=" * 50)
        print("🎉 全てのテストが成功しました！")
        print("MOD設計データキャッシュ機能は正常に動作しています。")
        
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()