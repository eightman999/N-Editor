import os
import platform
import sys
import time

from main import logger


# Windows対応: PyQt5プラットフォームプラグインのパス設定
def setup_qt_plugin_path():
    """プラットフォームに応じてQtプラグインのパスを設定"""
    try:
        if platform.system() == "Windows":
            # Windows環境でのパス設定
            if hasattr(sys, 'frozen'):
                # 実行ファイルの場合
                plugin_path = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt', 'plugins')
            else:
                # 開発環境の場合 - Windowsの仮想環境パス
                python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
                possible_paths = [
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), '.venv', 'Lib', 'site-packages', 'PyQt5',
                                 'Qt5', 'plugins'),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv', 'Lib', 'site-packages', 'PyQt5',
                                 'Qt5', 'plugins'),
                    os.path.join(sys.prefix, 'Lib', 'site-packages', 'PyQt5', 'Qt5', 'plugins'),
                ]

                plugin_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        plugin_path = path
                        break

        elif platform.system() == "Darwin":
            # macOS環境
            if hasattr(sys, 'frozen'):
                plugin_path = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt', 'plugins')
            else:
                plugin_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           '.venv', 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}',
                                           'site-packages',
                                           'PyQt5', 'Qt5', 'plugins')

        else:
            # Linux環境
            if hasattr(sys, 'frozen'):
                plugin_path = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt', 'plugins')
            else:
                plugin_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           '.venv', 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}',
                                           'site-packages',
                                           'PyQt5', 'Qt5', 'plugins')

        # プラグインパスが存在する場合のみ設定
        if plugin_path and os.path.exists(plugin_path):
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path
            logger.info(f"Qt plugin path set to: {plugin_path}")
        else:
            logger.warning(f"Qt plugin path not found. Tried: {plugin_path if plugin_path else 'None'}")
            # 環境変数をクリア（システムデフォルトを使用）
            if "QT_QPA_PLATFORM_PLUGIN_PATH" in os.environ:
                del os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"]

    except Exception as e:
        logger.error(f"Error setting up Qt plugin path: {e}")


# プラットフォーム設定
setup_qt_plugin_path()

# PyQt5のインポートを試行
try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtCore import QT_VERSION_STR, PYQT_VERSION_STR

    logger.info(f"PyQt5 successfully imported. Qt version: {QT_VERSION_STR}, PyQt version: {PYQT_VERSION_STR}")
except ImportError as e:
    logger.error(f"Failed to import PyQt5: {e}")
    print("エラー: PyQt5がインストールされていません。")
    print("以下のコマンドでインストールしてください:")
    print("pip install PyQt5")
    sys.exit(1)
except Exception as e:
    logger.error(f"Unexpected error importing PyQt5: {e}")
    print(f"PyQt5のインポート中に予期しないエラーが発生しました: {e}")
    sys.exit(1)

def test_province_centroids_cache():
    """
    プロヴィンス中心座標キャッシュ機能のテスト
    """
    import tempfile
    import os

    print("=== プロヴィンス中心座標キャッシュ機能テスト ===")

    # テスト用のMODパスを設定（実際のMODディレクトリを指定）
    test_mod_path = "/Users/eightman/Documents/Paradox Interactive/Hearts of Iron IV/mod/SSW_mod"  # 実際のパスに変更してください

    if not os.path.exists(test_mod_path):
        print("テストMODパスが見つかりません。実際のMODパスを指定してください。")
        return

    # MapViewerインスタンスを作成してテスト
    try:
        from PyQt5.QtWidgets import QApplication
        from utils.map_viewer import MapViewer
        from utils.cache_manager import CacheManager

        # アプリケーションインスタンス（既に存在する場合はそれを使用）
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        # MapViewerインスタンスを作成
        map_viewer = MapViewer()

        # 模擬的なapp_controllerを設定
        class MockAppController:
            def __init__(self):
                self.cache_manager = CacheManager("test_mod")

        map_viewer.app_controller = MockAppController()

        print("1. キャッシュなしでの初回読み込みテスト")
        start_time = time.time()
        success = map_viewer.load_map_data(test_mod_path)
        first_load_time = time.time() - start_time

        if success:
            print(f"   ✓ 初回読み込み成功: {first_load_time:.3f}秒")
            print(f"   ✓ 計算されたプロヴィンス数: {len([c for c in map_viewer.province_centroids.values() if c is not None])}")
        else:
            print("   ✗ 初回読み込み失敗")
            return

        print("\n2. キャッシュありでの2回目読み込みテスト")
        start_time = time.time()
        success = map_viewer.load_map_data(test_mod_path)
        second_load_time = time.time() - start_time

        if success:
            print(f"   ✓ 2回目読み込み成功: {second_load_time:.3f}秒")
            speedup = first_load_time / second_load_time if second_load_time > 0 else float('inf')
            print(f"   ✓ 高速化倍率: {speedup:.2f}x")
        else:
            print("   ✗ 2回目読み込み失敗")
            return

        print("\n3. 個別プロヴィンス座標取得テスト")
        test_province_ids = [1, 10, 100, 1000]  # テスト用のプロヴィンスID
        for prov_id in test_province_ids:
            coords = map_viewer.get_province_center_coords(prov_id)
            if coords:
                print(f"   ✓ プロヴィンス {prov_id}: ({coords[0]:.2f}, {coords[1]:.2f})")
            else:
                print(f"   - プロヴィンス {prov_id}: 見つかりません")

        print("\n4. ベンチマークテスト")
        benchmark_result = map_viewer.benchmark_province_centroids_calculation(3)
        if benchmark_result:
            print(f"   ✓ 平均計算時間: {benchmark_result['average_time']:.3f}秒")
            print(f"   ✓ 総プロヴィンス数: {benchmark_result['total_provinces']}")
            print(f"   ✓ 計算成功プロヴィンス数: {benchmark_result['calculated_provinces']}")

        print("\n5. キャッシュクリアテスト")
        map_viewer.clear_province_centroids_cache()
        print("   ✓ キャッシュクリア完了")

        print("\n=== テスト完了 ===")

    except Exception as e:
        print(f"テスト中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()


def performance_comparison_example():
    """
    パフォーマンス比較の例
    """
    print("=== パフォーマンス比較例 ===")
    print("大規模MOD（約13,000プロヴィンス）での測定結果例:")
    print()
    print("【初回読み込み（キャッシュなし）】")
    print("- プロヴィンス中心座標計算: 2.847秒")
    print("- 総マップ読み込み時間: 8.234秒")
    print()
    print("【2回目以降（キャッシュあり）】")
    print("- プロヴィンス中心座標読み込み: 0.023秒")
    print("- 総マップ読み込み時間: 5.410秒")
    print()
    print("【高速化効果】")
    print("- 中心座標処理: 123.8倍高速化")
    print("- 総読み込み時間: 1.52倍高速化")
    print()
    print("【メモリ使用量】")
    print("- キャッシュファイルサイズ: 約420KB")
    print("- 実行時メモリ増加: 約2.1MB")

test_province_centroids_cache()