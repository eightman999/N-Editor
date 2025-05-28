# utils/cache_debug.py - キャッシュ機能のデバッグ用ヘルパー

import os
import time
import tempfile
from utils.cache_manager import CacheManager

def test_cache_functionality():
    """
    キャッシュ機能のテスト用関数
    """
    print("=== キャッシュ機能テスト開始 ===")

    # テスト用のCacheManagerを作成
    cache_manager = CacheManager("test_mod")

    # テスト用の一時ファイルを作成
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
        temp_file.write("test data content")
        temp_file_path = temp_file.name

    try:
        # テストデータ
        test_data = {"test_key": "test_value", "parsed_data": [1, 2, 3, 4, 5]}

        print(f"1. 一時ファイル作成: {temp_file_path}")

        # 初回はキャッシュが存在しないことを確認
        cached_data = cache_manager.load("test_type", temp_file_path)
        print(f"2. 初回キャッシュ読み込み結果: {cached_data} (None であるべき)")

        # データをキャッシュに保存
        cache_manager.save("test_type", temp_file_path, test_data)
        print("3. データをキャッシュに保存")

        # キャッシュからデータを読み込み
        cached_data = cache_manager.load("test_type", temp_file_path)
        print(f"4. キャッシュからデータ読み込み成功: {cached_data == test_data}")

        # 元ファイルを更新してキャッシュが無効になることを確認
        time.sleep(1)  # ファイル更新時刻を確実に変更するため
        with open(temp_file_path, 'a') as f:
            f.write("\nupdated content")

        cached_data = cache_manager.load("test_type", temp_file_path)
        print(f"5. ファイル更新後のキャッシュ読み込み結果: {cached_data} (None であるべき)")

        # キャッシュ情報を表示
        cache_info = cache_manager.get_cache_info()
        print(f"6. キャッシュ情報: {cache_info}")

        print("=== キャッシュ機能テスト完了 ===")

    finally:
        # 一時ファイルを削除
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

        # テスト用キャッシュをクリア
        cache_manager.clear_cache()

def measure_parse_performance(app_controller, file_path, file_type, iterations=3):
    """
    パース処理のパフォーマンスを測定する

    Args:
        app_controller: AppControllerのインスタンス
        file_path: 測定対象のファイルパス
        file_type: ファイル種別
        iterations: 測定回数
    """
    print(f"=== パフォーマンス測定開始: {file_type} ===")

    if not app_controller.cache_manager:
        print("CacheManagerが初期化されていません")
        return

    # キャッシュをクリア
    app_controller.cache_manager.clear_cache(file_type)

    # キャッシュなしの測定
    no_cache_times = []
    for i in range(iterations):
        start_time = time.time()

        # パース処理（キャッシュなし）
        if file_type == "states":
            app_controller._parse_state_file_worker(file_path)
        elif file_type == "strategic_regions":
            app_controller._parse_strategic_region_file_worker(file_path)

        end_time = time.time()
        no_cache_times.append(end_time - start_time)

        # 次回測定のためにキャッシュをクリア
        app_controller.cache_manager.clear_cache(file_type)

    # キャッシュありの測定（1回目でキャッシュ作成、2回目以降でキャッシュ使用）
    cache_times = []

    # 最初の1回でキャッシュを作成
    if file_type == "states":
        app_controller._parse_state_file_worker(file_path)
    elif file_type == "strategic_regions":
        app_controller._parse_strategic_region_file_worker(file_path)

    # キャッシュありの測定
    for i in range(iterations):
        start_time = time.time()

        # パース処理（キャッシュあり）
        if file_type == "states":
            app_controller._parse_state_file_worker(file_path)
        elif file_type == "strategic_regions":
            app_controller._parse_strategic_region_file_worker(file_path)

        end_time = time.time()
        cache_times.append(end_time - start_time)

    # 結果を表示
    avg_no_cache = sum(no_cache_times) / len(no_cache_times)
    avg_cache = sum(cache_times) / len(cache_times)
    improvement = ((avg_no_cache - avg_cache) / avg_no_cache) * 100

    print(f"キャッシュなし平均時間: {avg_no_cache:.4f}秒")
    print(f"キャッシュあり平均時間: {avg_cache:.4f}秒")
    print(f"パフォーマンス向上: {improvement:.1f}%")
    print(f"=== パフォーマンス測定完了 ===")

if __name__ == "__main__":
    test_cache_functionality()