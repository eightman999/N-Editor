#!/usr/bin/env python3
"""
国家リスト表示のパフォーマンステスト

新しいキャッシュシステムと国旗スプライトシートの効果を測定します。
"""

import os
import sys
import time
import psutil
import logging
from typing import List, Dict, Tuple

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controllers.app_controller import AppController
from models.app_settings import AppSettings
from utils.cache_manager import CacheManager
from utils.flag_sprite_manager import FlagSpriteManager

# ログの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NationPerformanceTest:
    """国家リスト表示のパフォーマンステストクラス"""
    
    def __init__(self, mod_path: str):
        """
        テストクラスを初期化
        
        Args:
            mod_path: テスト対象のMODパス
        """
        self.mod_path = mod_path
        self.app_settings = AppSettings()
        self.results = {}
        
        logger.info(f"パフォーマンステスト初期化: MODパス={mod_path}")

    def measure_memory_usage(self) -> float:
        """
        現在のメモリ使用量を取得（MB単位）
        
        Returns:
            メモリ使用量（MB）
        """
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    def test_legacy_method(self) -> Dict:
        """
        従来の方法（キャッシュなし、個別国旗読み込み）でのパフォーマンステスト
        
        Returns:
            テスト結果の辞書
        """
        logger.info("従来の方法でのテスト開始")
        
        # メモリ使用量の初期値
        initial_memory = self.measure_memory_usage()
        
        # 時間計測開始
        start_time = time.time()
        
        try:
            # AppControllerを直接使用（キャッシュ無効化）
            app_controller = AppController(self.app_settings)
            app_controller.cache_manager = None  # キャッシュを無効化
            
            # 国家情報取得
            nations = app_controller.get_nations(self.mod_path)
            
            # 個別の国旗読み込み（スプライトシートなし）
            flag_load_times = []
            for nation in nations[:20]:  # 最初の20個の国旗のみテスト
                flag_start = time.time()
                
                flag_path = nation.get('flag_path')
                if flag_path and os.path.exists(flag_path):
                    try:
                        from PIL import Image
                        img = Image.open(flag_path)
                        img = img.resize((32, 20), Image.LANCZOS)
                        # 実際の描画処理をシミュレート
                        img.convert('RGBA')
                    except Exception as e:
                        logger.warning(f"国旗読み込みエラー: {e}")
                
                flag_load_times.append(time.time() - flag_start)
            
            end_time = time.time()
            final_memory = self.measure_memory_usage()
            
            result = {
                'method': 'legacy',
                'nation_count': len(nations),
                'total_time': end_time - start_time,
                'memory_usage': final_memory - initial_memory,
                'average_flag_load_time': sum(flag_load_times) / len(flag_load_times) if flag_load_times else 0,
                'cache_hit_rate': 0,  # キャッシュなし
                'sprite_sheet_used': False
            }
            
            logger.info(f"従来の方法テスト完了: {result}")
            return result
            
        except Exception as e:
            logger.error(f"従来の方法テストエラー: {e}")
            return {'method': 'legacy', 'error': str(e)}

    def test_optimized_method(self) -> Dict:
        """
        最適化された方法（キャッシュ + スプライトシート）でのパフォーマンステスト
        
        Returns:
            テスト結果の辞書
        """
        logger.info("最適化された方法でのテスト開始")
        
        # メモリ使用量の初期値
        initial_memory = self.measure_memory_usage()
        
        # 時間計測開始
        start_time = time.time()
        
        try:
            # AppControllerを初期化（キャッシュ有効）
            app_controller = AppController(self.app_settings)
            
            # キャッシュマネージャーが初期化されていることを確認
            if not app_controller.cache_manager:
                app_controller.cache_manager = CacheManager("test_mod")
            
            # 1回目: キャッシュミス（データ生成）
            first_call_start = time.time()
            nations = app_controller.get_nations(self.mod_path)
            first_call_time = time.time() - first_call_start
            
            # 2回目: キャッシュヒット
            second_call_start = time.time()
            nations_cached = app_controller.get_nations(self.mod_path)
            second_call_time = time.time() - second_call_start
            
            # スプライトシートからの国旗読み込み
            flag_sprite_manager = app_controller.get_flag_sprite_manager()
            sprite_sheet_load_times = []
            
            if flag_sprite_manager:
                for nation in nations[:20]:  # 最初の20個の国旗のみテスト
                    flag_start = time.time()
                    
                    flag_img = flag_sprite_manager.extract_flag(nation['tag'])
                    if flag_img:
                        # PIL ImageをQPixmapに変換のシミュレート
                        pass
                    
                    sprite_sheet_load_times.append(time.time() - flag_start)
            
            end_time = time.time()
            final_memory = self.measure_memory_usage()
            
            # キャッシュ情報を取得
            cache_info = app_controller.cache_manager.get_cache_info() if app_controller.cache_manager else {}
            sprite_info = flag_sprite_manager.get_cache_info() if flag_sprite_manager else {}
            
            result = {
                'method': 'optimized',
                'nation_count': len(nations),
                'total_time': end_time - start_time,
                'first_call_time': first_call_time,
                'second_call_time': second_call_time,
                'cache_speedup': first_call_time / second_call_time if second_call_time > 0 else 0,
                'memory_usage': final_memory - initial_memory,
                'average_sprite_load_time': sum(sprite_sheet_load_times) / len(sprite_sheet_load_times) if sprite_sheet_load_times else 0,
                'sprite_sheet_used': bool(flag_sprite_manager),
                'sprite_sheet_size': sprite_info.get('sprite_sheet_size', 0),
                'cache_entries': cache_info.get('metadata_entries', 0)
            }
            
            logger.info(f"最適化された方法テスト完了: {result}")
            return result
            
        except Exception as e:
            logger.error(f"最適化された方法テストエラー: {e}")
            return {'method': 'optimized', 'error': str(e)}

    def test_cache_invalidation(self) -> Dict:
        """
        キャッシュ無効化とタイムスタンプベースの更新テスト
        
        Returns:
            テスト結果の辞書
        """
        logger.info("キャッシュ無効化テスト開始")
        
        try:
            # AppControllerを初期化
            app_controller = AppController(self.app_settings)
            
            if not app_controller.cache_manager:
                app_controller.cache_manager = CacheManager("test_mod")
            
            # 1回目の読み込み（キャッシュ生成）
            start_time = time.time()
            nations1 = app_controller.get_nations(self.mod_path)
            first_load_time = time.time() - start_time
            
            # 2回目の読み込み（キャッシュヒット）
            start_time = time.time()
            nations2 = app_controller.get_nations(self.mod_path)
            second_load_time = time.time() - start_time
            
            # キャッシュクリア
            app_controller.cache_manager.clear_cache("nations_cache")
            
            # 3回目の読み込み（キャッシュ再生成）
            start_time = time.time()
            nations3 = app_controller.get_nations(self.mod_path)
            third_load_time = time.time() - start_time
            
            result = {
                'method': 'cache_invalidation',
                'first_load_time': first_load_time,
                'cached_load_time': second_load_time,
                'regenerated_load_time': third_load_time,
                'cache_efficiency': first_load_time / second_load_time if second_load_time > 0 else 0,
                'nation_count': len(nations1),
                'data_consistency': len(nations1) == len(nations2) == len(nations3)
            }
            
            logger.info(f"キャッシュ無効化テスト完了: {result}")
            return result
            
        except Exception as e:
            logger.error(f"キャッシュ無効化テストエラー: {e}")
            return {'method': 'cache_invalidation', 'error': str(e)}

    def run_all_tests(self) -> Dict:
        """
        全てのテストを実行
        
        Returns:
            全テスト結果の辞書
        """
        logger.info("全体的なパフォーマンステスト開始")
        
        results = {}
        
        # 従来の方法テスト
        results['legacy'] = self.test_legacy_method()
        
        # 少し間隔を空ける
        time.sleep(1)
        
        # 最適化された方法テスト
        results['optimized'] = self.test_optimized_method()
        
        # 少し間隔を空ける
        time.sleep(1)
        
        # キャッシュ無効化テスト
        results['cache_invalidation'] = self.test_cache_invalidation()
        
        # パフォーマンス比較を計算
        if 'error' not in results['legacy'] and 'error' not in results['optimized']:
            legacy_time = results['legacy'].get('total_time', 0)
            optimized_time = results['optimized'].get('total_time', 0)
            
            if legacy_time > 0 and optimized_time > 0:
                results['performance_comparison'] = {
                    'speed_improvement': legacy_time / optimized_time,
                    'memory_difference': results['legacy'].get('memory_usage', 0) - results['optimized'].get('memory_usage', 0),
                    'flag_load_improvement': (results['legacy'].get('average_flag_load_time', 0) / 
                                            results['optimized'].get('average_sprite_load_time', 1)) if results['optimized'].get('average_sprite_load_time', 0) > 0 else 0
                }
        
        logger.info("全体的なパフォーマンステスト完了")
        return results

    def print_results(self, results: Dict):
        """
        テスト結果を整形して出力
        
        Args:
            results: テスト結果の辞書
        """
        print("\n" + "="*60)
        print("国家リスト表示パフォーマンステスト結果")
        print("="*60)
        
        for test_name, result in results.items():
            if test_name == 'performance_comparison':
                continue
                
            print(f"\n【{test_name.upper()}】")
            
            if 'error' in result:
                print(f"  エラー: {result['error']}")
                continue
            
            for key, value in result.items():
                if key == 'method':
                    continue
                elif 'time' in key.lower():
                    print(f"  {key}: {value:.4f}秒")
                elif 'memory' in key.lower():
                    print(f"  {key}: {value:.2f}MB")
                elif 'size' in key.lower():
                    print(f"  {key}: {value:,} bytes")
                else:
                    print(f"  {key}: {value}")
        
        # パフォーマンス比較
        if 'performance_comparison' in results:
            comp = results['performance_comparison']
            print(f"\n【パフォーマンス比較】")
            print(f"  処理速度向上: {comp.get('speed_improvement', 0):.2f}倍")
            print(f"  メモリ使用量差分: {comp.get('memory_difference', 0):.2f}MB")
            print(f"  国旗読み込み速度向上: {comp.get('flag_load_improvement', 0):.2f}倍")
        
        print("\n" + "="*60)

def main():
    """メイン関数"""
    # MODパスの設定（実際のパスに変更してください）
    mod_path = input("テスト対象のMODパスを入力してください: ").strip()
    
    if not mod_path or not os.path.exists(mod_path):
        print("有効なMODパスを入力してください。")
        return
    
    # テスト実行
    test = NationPerformanceTest(mod_path)
    results = test.run_all_tests()
    
    # 結果出力
    test.print_results(results)
    
    # 結果をファイルに保存
    import json
    output_file = "performance_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n詳細な結果は {output_file} に保存されました。")

if __name__ == "__main__":
    main()