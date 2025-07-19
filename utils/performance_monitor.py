# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: performance_monitorユーティリティ
import time
import logging
import functools
from typing import Dict, Any, Callable
import json
import os

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    パフォーマンス測定とキャッシュ効果検証のためのクラス
    """
    
    def __init__(self, cache_manager=None):
        """
        初期化
        
        Args:
            cache_manager: キャッシュマネージャーのインスタンス
        """
        self.cache_manager = cache_manager
        self.performance_data = {}
        
    def measure_execution_time(self, operation_name: str):
        """
        実行時間測定デコレータ
        
        Args:
            operation_name: 操作名
        """
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    success = True
                    error = None
                except Exception as e:
                    result = None
                    success = False
                    error = str(e)
                    raise
                finally:
                    duration = time.time() - start_time
                    self._record_performance(
                        operation_name, 
                        duration, 
                        success, 
                        error,
                        len(result) if hasattr(result, '__len__') else 0
                    )
                
                return result
            return wrapper
        return decorator
    
    def _record_performance(self, operation_name: str, duration: float, 
                           success: bool, error: str = None, data_count: int = 0):
        """
        パフォーマンスデータを記録
        
        Args:
            operation_name: 操作名
            duration: 実行時間（秒）
            success: 成功フラグ
            error: エラーメッセージ
            data_count: 処理したデータ数
        """
        if operation_name not in self.performance_data:
            self.performance_data[operation_name] = {
                'total_calls': 0,
                'successful_calls': 0,
                'failed_calls': 0,
                'total_duration': 0.0,
                'min_duration': float('inf'),
                'max_duration': 0.0,
                'average_duration': 0.0,
                'cache_hits': 0,
                'cache_misses': 0,
                'total_data_count': 0,
                'last_error': None
            }
        
        stats = self.performance_data[operation_name]
        stats['total_calls'] += 1
        stats['total_duration'] += duration
        stats['min_duration'] = min(stats['min_duration'], duration)
        stats['max_duration'] = max(stats['max_duration'], duration)
        stats['average_duration'] = stats['total_duration'] / stats['total_calls']
        stats['total_data_count'] += data_count
        
        if success:
            stats['successful_calls'] += 1
        else:
            stats['failed_calls'] += 1
            stats['last_error'] = error
        
        logger.debug(f"パフォーマンス記録: {operation_name}, 時間: {duration:.3f}秒, "
                    f"成功: {success}, データ数: {data_count}")
    
    def record_cache_hit(self, operation_name: str):
        """キャッシュヒットを記録"""
        if operation_name in self.performance_data:
            self.performance_data[operation_name]['cache_hits'] += 1
    
    def record_cache_miss(self, operation_name: str):
        """キャッシュミスを記録"""
        if operation_name in self.performance_data:
            self.performance_data[operation_name]['cache_misses'] += 1
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        パフォーマンス統計のサマリーを取得
        
        Returns:
            パフォーマンス統計辞書
        """
        summary = {
            'total_operations': len(self.performance_data),
            'operations': {}
        }
        
        total_time = 0.0
        total_calls = 0
        total_cache_hits = 0
        total_cache_misses = 0
        
        for operation_name, stats in self.performance_data.items():
            # キャッシュヒット率計算
            total_cache_operations = stats['cache_hits'] + stats['cache_misses']
            cache_hit_rate = (stats['cache_hits'] / total_cache_operations * 100) if total_cache_operations > 0 else 0
            
            operation_summary = {
                'calls': stats['total_calls'],
                'success_rate': (stats['successful_calls'] / stats['total_calls'] * 100) if stats['total_calls'] > 0 else 0,
                'total_duration': stats['total_duration'],
                'average_duration': stats['average_duration'],
                'min_duration': stats['min_duration'] if stats['min_duration'] != float('inf') else 0,
                'max_duration': stats['max_duration'],
                'cache_hit_rate': cache_hit_rate,
                'cache_hits': stats['cache_hits'],
                'cache_misses': stats['cache_misses'],
                'total_data_processed': stats['total_data_count'],
                'last_error': stats['last_error']
            }
            
            summary['operations'][operation_name] = operation_summary
            
            total_time += stats['total_duration']
            total_calls += stats['total_calls']
            total_cache_hits += stats['cache_hits']
            total_cache_misses += stats['cache_misses']
        
        # 全体統計
        total_cache_operations = total_cache_hits + total_cache_misses
        summary['overall'] = {
            'total_calls': total_calls,
            'total_duration': total_time,
            'average_duration_per_call': total_time / total_calls if total_calls > 0 else 0,
            'overall_cache_hit_rate': (total_cache_hits / total_cache_operations * 100) if total_cache_operations > 0 else 0,
            'total_cache_hits': total_cache_hits,
            'total_cache_misses': total_cache_misses
        }
        
        return summary
    
    def save_performance_report(self, output_path: str):
        """
        パフォーマンスレポートをファイルに保存
        
        Args:
            output_path: 出力ファイルパス
        """
        try:
            summary = self.get_performance_summary()
            summary['generated_at'] = time.time()
            summary['cache_manager_info'] = {}
            
            if self.cache_manager:
                summary['cache_manager_info'] = self.cache_manager.get_cache_info()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            logger.info(f"パフォーマンスレポートを保存: {output_path}")
            
        except Exception as e:
            logger.error(f"パフォーマンスレポート保存エラー: {e}")
    
    def print_performance_summary(self):
        """パフォーマンス統計をコンソールに出力"""
        summary = self.get_performance_summary()
        
        print("\n" + "="*80)
        print("パフォーマンス統計サマリー")
        print("="*80)
        
        overall = summary.get('overall', {})
        print(f"総操作数: {overall.get('total_calls', 0)}")
        print(f"総実行時間: {overall.get('total_duration', 0):.3f}秒")
        print(f"平均実行時間: {overall.get('average_duration_per_call', 0):.3f}秒")
        print(f"全体キャッシュヒット率: {overall.get('overall_cache_hit_rate', 0):.1f}%")
        
        print("\n操作別統計:")
        print("-"*80)
        
        for operation_name, stats in summary.get('operations', {}).items():
            print(f"\n{operation_name}:")
            print(f"  呼び出し回数: {stats['calls']}")
            print(f"  成功率: {stats['success_rate']:.1f}%")
            print(f"  平均実行時間: {stats['average_duration']:.3f}秒")
            print(f"  最小/最大実行時間: {stats['min_duration']:.3f}秒 / {stats['max_duration']:.3f}秒")
            print(f"  キャッシュヒット率: {stats['cache_hit_rate']:.1f}%")
            print(f"  処理データ数: {stats['total_data_processed']}")
            
            if stats['last_error']:
                print(f"  最後のエラー: {stats['last_error']}")
        
        print("\n" + "="*80)


# グローバルなパフォーマンスモニターインスタンス
_global_monitor = None


def get_performance_monitor(cache_manager=None):
    """
    グローバルなパフォーマンスモニターを取得
    
    Args:
        cache_manager: キャッシュマネージャーのインスタンス
        
    Returns:
        PerformanceMonitor: パフォーマンスモニターのインスタンス
    """
    global _global_monitor
    
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor(cache_manager)
    elif cache_manager and _global_monitor.cache_manager != cache_manager:
        _global_monitor.cache_manager = cache_manager
    
    return _global_monitor


def performance_measure(operation_name: str):
    """
    パフォーマンス測定デコレータ（グローバルモニター使用）
    
    Args:
        operation_name: 操作名
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            return monitor.measure_execution_time(operation_name)(func)(*args, **kwargs)
        return wrapper
    return decorator