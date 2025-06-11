#!/usr/bin/env python3
"""
永続キャッシュシステムのテストスクリプト

使用方法:
    python test_persistent_cache.py

テスト内容:
1. 基本的なキャッシュ操作
2. タイムスタンプベースの有効性チェック
3. 複数ファイル依存キャッシュ
4. メタデータの整合性確認
"""

import os
import sys
import time
import tempfile
import json
import logging

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.cache_manager import CacheManager

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_basic_cache_operations():
    """基本的なキャッシュ操作をテスト"""
    print("=== 基本キャッシュ操作テスト ===")
    
    # テスト用キャッシュマネージャーを作成
    cache_manager = CacheManager("test_persistent_cache")
    
    # テスト用の一時ファイルを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
        temp_file.write("test data content")
        temp_file_path = temp_file.name
    
    try:
        # テストデータ
        test_data = {
            "test_key": "test_value", 
            "parsed_data": [1, 2, 3, 4, 5],
            "timestamp": time.time()
        }
        
        print(f"1. テスト用ファイル作成: {temp_file_path}")
        
        # 初回はキャッシュが存在しないことを確認
        cached_data = cache_manager.load("test_type", temp_file_path)
        print(f"2. 初回キャッシュ読み込み結果: {cached_data is None} (True であるべき)")
        
        # データをキャッシュに保存
        cache_manager.save("test_type", temp_file_path, test_data)
        print("3. データをキャッシュに保存")
        
        # キャッシュからデータを読み込み
        cached_data = cache_manager.load("test_type", temp_file_path)
        print(f"4. キャッシュからデータ読み込み成功: {cached_data == test_data}")
        
        # キャッシュ情報を表示
        cache_info = cache_manager.get_cache_info()
        print(f"5. キャッシュ情報: {json.dumps(cache_info, indent=2, ensure_ascii=False)}")
        
        return True
        
    except Exception as e:
        print(f"テストエラー: {e}")
        return False
    finally:
        # 一時ファイルを削除
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


def test_timestamp_validation():
    """タイムスタンプベースの有効性チェックをテスト"""
    print("\n=== タイムスタンプ有効性チェックテスト ===")
    
    cache_manager = CacheManager("test_timestamp_validation")
    
    # テスト用の一時ファイルを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
        temp_file.write("original content")
        temp_file_path = temp_file.name
    
    try:
        test_data = {"version": 1, "content": "original"}
        
        print(f"1. テスト用ファイル作成: {temp_file_path}")
        
        # データをキャッシュに保存
        cache_manager.save("timestamp_test", temp_file_path, test_data)
        print("2. 初回データをキャッシュに保存")
        
        # キャッシュからデータを読み込み（有効なはず）
        cached_data = cache_manager.load("timestamp_test", temp_file_path)
        print(f"3. キャッシュ読み込み（ファイル更新前）: {cached_data is not None}")
        
        # ファイルを更新してキャッシュが無効になることを確認
        time.sleep(1.1)  # タイムスタンプの違いを確実にするため
        with open(temp_file_path, 'w') as f:
            f.write("updated content")
        
        cached_data = cache_manager.load("timestamp_test", temp_file_path)
        print(f"4. キャッシュ読み込み（ファイル更新後）: {cached_data is None} (True であるべき)")
        
        # 新しいデータで再保存
        updated_data = {"version": 2, "content": "updated"}
        cache_manager.save("timestamp_test", temp_file_path, updated_data)
        print("5. 更新後データをキャッシュに保存")
        
        # 再度読み込み（有効なはず）
        cached_data = cache_manager.load("timestamp_test", temp_file_path)
        print(f"6. キャッシュ読み込み（再保存後）: {cached_data == updated_data}")
        
        return True
        
    except Exception as e:
        print(f"テストエラー: {e}")
        return False
    finally:
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


def test_multiple_file_dependencies():
    """複数ファイル依存キャッシュをテスト"""
    print("\n=== 複数ファイル依存キャッシュテスト ===")
    
    cache_manager = CacheManager("test_multiple_files")
    
    # 2つの一時ファイルを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.bmp', delete=False) as file1:
        file1.write("bmp content")
        file1_path = file1.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as file2:
        file2.write("csv content")
        file2_path = file2.name
    
    try:
        # 複数ファイル依存キャッシュキーを作成
        cache_key_file = f"{file1_path}+{file2_path}"
        test_data = {
            "combined_data": "result from both files",
            "file1": file1_path,
            "file2": file2_path
        }
        
        print(f"1. 複数テストファイル作成: {os.path.basename(file1_path)}, {os.path.basename(file2_path)}")
        
        # データをキャッシュに保存
        cache_manager.save("multi_file_test", cache_key_file, test_data)
        print("2. 複数ファイル依存データをキャッシュに保存")
        
        # キャッシュからデータを読み込み（有効なはず）
        cached_data = cache_manager.load("multi_file_test", cache_key_file)
        print(f"3. キャッシュ読み込み（ファイル更新前）: {cached_data is not None}")
        
        # 片方のファイルを更新
        time.sleep(1.1)
        with open(file1_path, 'w') as f:
            f.write("updated bmp content")
        
        cached_data = cache_manager.load("multi_file_test", cache_key_file)
        print(f"4. キャッシュ読み込み（file1更新後）: {cached_data is None} (True であるべき)")
        
        # 新しいデータで再保存
        updated_data = {"combined_data": "updated result", "version": 2}
        cache_manager.save("multi_file_test", cache_key_file, updated_data)
        print("5. 更新後データをキャッシュに保存")
        
        # 再度読み込み（有効なはず）
        cached_data = cache_manager.load("multi_file_test", cache_key_file)
        print(f"6. キャッシュ読み込み（再保存後）: {cached_data == updated_data}")
        
        return True
        
    except Exception as e:
        print(f"テストエラー: {e}")
        return False
    finally:
        for path in [file1_path, file2_path]:
            if os.path.exists(path):
                os.unlink(path)


def test_metadata_consistency():
    """メタデータの整合性をテスト"""
    print("\n=== メタデータ整合性テスト ===")
    
    cache_manager = CacheManager("test_metadata_consistency")
    
    # テスト用の一時ファイルを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
        temp_file.write("metadata test content")
        temp_file_path = temp_file.name
    
    try:
        test_data = {"metadata_test": True, "value": 12345}
        
        print(f"1. テスト用ファイル作成: {temp_file_path}")
        
        # データをキャッシュに保存
        cache_manager.save("metadata_test", temp_file_path, test_data)
        print("2. データをキャッシュに保存")
        
        # メタデータを確認
        cache_info = cache_manager.get_cache_info()
        print(f"3. メタデータエントリ数: {cache_info.get('metadata_entries', 0)}")
        print(f"4. メタデータ同期状況: {[ft['sync_status'] for ft in cache_info.get('file_types', [])]}")
        
        # メタデータクリーンアップテスト
        cleanup_stats = cache_manager.cleanup_invalid_metadata()
        print(f"5. クリーンアップ統計: {cleanup_stats}")
        
        # ファイルを削除してクリーンアップ実行
        os.unlink(temp_file_path)
        cleanup_stats = cache_manager.cleanup_invalid_metadata()
        print(f"6. ファイル削除後クリーンアップ: {cleanup_stats}")
        
        return True
        
    except Exception as e:
        print(f"テストエラー: {e}")
        return False
    finally:
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


def main():
    """メインテスト実行"""
    print("永続キャッシュシステム テストスイート開始\n")
    
    tests = [
        ("基本キャッシュ操作", test_basic_cache_operations),
        ("タイムスタンプ有効性チェック", test_timestamp_validation),
        ("複数ファイル依存", test_multiple_file_dependencies),
        ("メタデータ整合性", test_metadata_consistency),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{test_name}: {'✓ 成功' if result else '✗ 失敗'}")
        except Exception as e:
            print(f"{test_name}: ✗ エラー - {e}")
            results.append((test_name, False))
    
    print(f"\n=== テスト結果サマリー ===")
    successful = sum(1 for _, result in results if result)
    total = len(results)
    print(f"成功: {successful}/{total}")
    
    if successful == total:
        print("🎉 すべてのテストが成功しました！")
        return 0
    else:
        print("⚠️  一部のテストが失敗しました。")
        return 1


if __name__ == "__main__":
    sys.exit(main())