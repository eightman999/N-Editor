import os
import json
import time
import logging
import hashlib
from typing import Dict, List, Any, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class MODDataCacheManager:
    """
    MOD設計データ専用の永続キャッシュマネージャー
    
    特徴:
    - 複数ディレクトリ監視によるタイムスタンプベース有効性チェック
    - データタイプ別キャッシュ管理 (hulls, equipments, modules)
    - パフォーマンス測定とロギング機能
    - 堅牢なエラーハンドリング
    """
    
    # 監視対象ディレクトリパターン
    WATCHED_DIRECTORIES = [
        "common/units/equipment",
        "common/units/equipment/modules", 
        "common/units"
    ]
    
    # データタイプ別設定
    DATA_TYPES = {
        'hulls': {
            'cache_key': 'hulls_cache',
            'directories': ["common/units"],
            'file_patterns': ['*.txt']
        },
        'equipments': {
            'cache_key': 'equipments_cache', 
            'directories': ["common/units/equipment"],
            'file_patterns': ['*.txt']
        },
        'modules': {
            'cache_key': 'modules_cache',
            'directories': ["common/units/equipment/modules"],
            'file_patterns': ['*.txt']
        },
        'designs': {
            'cache_key': 'designs_cache',
            'directories': ["designs"],
            'file_patterns': ['*.json']
        },
        'resolved_designs': {
            'cache_key': 'resolved_designs_cache',
            'directories': ["designs", "common/units", "common/units/equipment"],
            'file_patterns': ['*.json', '*.txt']
        },
        'design_stats': {
            'cache_key': 'design_stats_cache',
            'directories': ["designs", "common/units", "common/units/equipment"],
            'file_patterns': ['*.json', '*.txt']
        }
    }
    
    def __init__(self, mod_path: str, cache_dir: Optional[str] = None):
        """
        初期化
        
        Args:
            mod_path: MODのルートパス
            cache_dir: キャッシュディレクトリ（省略時は自動生成）
        """
        self.mod_path = Path(mod_path).resolve()
        
        # キャッシュディレクトリの設定
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # デフォルトでは mod_path の親/cache に作成
            self.cache_dir = self.mod_path.parent / "cache"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # キャッシュファイルパス
        self.cache_file = self.cache_dir / "mod_design_cache.json"
        self.metadata_file = self.cache_dir / "mod_cache_metadata.json"
        self.stats_file = self.cache_dir / "performance_stats.json"
        
        # MOD固有の識別子
        self.mod_id = self._generate_mod_id()
        
        logger.info(f"MODDataCacheManager初期化: MOD={self.mod_path}, キャッシュ={self.cache_dir}")
    
    def _generate_mod_id(self) -> str:
        """MODパスから一意のIDを生成"""
        return hashlib.md5(str(self.mod_path).encode()).hexdigest()[:16]
    
    def _get_file_dependencies(self, data_type: str) -> List[Path]:
        """データタイプの依存ファイル一覧を取得"""
        dependencies = []
        config = self.DATA_TYPES.get(data_type, {})
        
        for dir_pattern in config.get('directories', []):
            target_dir = self.mod_path / dir_pattern
            if target_dir.exists():
                # パターンに応じてファイルを検索
                file_patterns = config.get('file_patterns', ['*.txt'])
                for pattern in file_patterns:
                    for file_path in target_dir.rglob(pattern):
                        dependencies.append(file_path)
        
        return sorted(dependencies)
    
    def _calculate_dependencies_hash(self, dependencies: List[Path]) -> str:
        """依存ファイルの統合ハッシュを計算"""
        hash_data = []
        
        for file_path in dependencies:
            try:
                if file_path.exists():
                    stat = file_path.stat()
                    hash_data.append(f"{file_path}:{stat.st_mtime}:{stat.st_size}")
            except Exception as e:
                logger.warning(f"ファイル統計取得エラー: {file_path}, {e}")
        
        combined = "|".join(hash_data)
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _load_cache_data(self) -> Dict[str, Any]:
        """キャッシュデータを読み込み"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"キャッシュデータ読み込みエラー: {e}")
        return {}
    
    def _save_cache_data(self, data: Dict[str, Any]) -> None:
        """キャッシュデータを保存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"キャッシュデータ保存エラー: {e}")
    
    def _load_metadata(self) -> Dict[str, Any]:
        """メタデータを読み込み"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"メタデータ読み込みエラー: {e}")
        return {}
    
    def _save_metadata(self, metadata: Dict[str, Any]) -> None:
        """メタデータを保存"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"メタデータ保存エラー: {e}")
    
    def _record_performance_stats(self, data_type: str, operation: str, 
                                  duration: float, cache_hit: bool, 
                                  file_count: int = 0, data_size: int = 0):
        """パフォーマンス統計を記録"""
        try:
            stats = {}
            if self.stats_file.exists():
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            
            if data_type not in stats:
                stats[data_type] = {
                    'cache_hits': 0,
                    'cache_misses': 0,
                    'total_load_time': 0.0,
                    'average_load_time': 0.0,
                    'file_count': 0,
                    'data_size': 0
                }
            
            entry = stats[data_type]
            entry['total_load_time'] += duration
            
            if cache_hit:
                entry['cache_hits'] += 1
            else:
                entry['cache_misses'] += 1
            
            total_operations = entry['cache_hits'] + entry['cache_misses']
            entry['average_load_time'] = entry['total_load_time'] / total_operations
            
            if file_count > 0:
                entry['file_count'] = file_count
            if data_size > 0:
                entry['data_size'] = data_size
            
            # 最終更新時刻を記録
            stats['last_updated'] = time.time()
            
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.warning(f"パフォーマンス統計記録エラー: {e}")
    
    def is_cache_valid(self, data_type: str) -> bool:
        """
        指定データタイプのキャッシュが有効かチェック
        
        Args:
            data_type: データタイプ (hulls, equipments, modules)
            
        Returns:
            キャッシュが有効な場合True
        """
        try:
            if data_type not in self.DATA_TYPES:
                return False
            
            # メタデータを読み込み
            metadata = self._load_metadata()
            cache_key = f"{self.mod_id}_{data_type}"
            
            if cache_key not in metadata:
                logger.debug(f"キャッシュメタデータが存在しない: {cache_key}")
                return False
            
            cache_info = metadata[cache_key]
            
            # 依存ファイル一覧を取得
            dependencies = self._get_file_dependencies(data_type)
            
            if not dependencies:
                logger.debug(f"依存ファイルが見つからない: {data_type}")
                return False
            
            # 依存ファイルの統合ハッシュを計算
            current_hash = self._calculate_dependencies_hash(dependencies)
            cached_hash = cache_info.get('dependencies_hash', '')
            
            # ハッシュが一致するかチェック
            is_valid = current_hash == cached_hash
            
            if is_valid:
                logger.debug(f"キャッシュ有効: {data_type} (ファイル数: {len(dependencies)})")
            else:
                logger.debug(f"キャッシュ無効: {data_type} - ハッシュ不一致")
            
            return is_valid
            
        except Exception as e:
            logger.warning(f"キャッシュ有効性チェックエラー ({data_type}): {e}")
            return False
    
    def load_cached_data(self, data_type: str) -> Optional[Any]:
        """
        キャッシュからデータを読み込み
        
        Args:
            data_type: データタイプ
            
        Returns:
            キャッシュされたデータ、またはNone
        """
        start_time = time.time()
        
        try:
            if not self.is_cache_valid(data_type):
                duration = time.time() - start_time
                self._record_performance_stats(data_type, 'load', duration, False)
                return None
            
            # キャッシュデータを読み込み
            cache_data = self._load_cache_data()
            cache_key = f"{self.mod_id}_{data_type}"
            
            if cache_key in cache_data:
                data = cache_data[cache_key].get('data')
                duration = time.time() - start_time
                
                # 統計情報を記録
                data_size = len(json.dumps(data)) if data else 0
                self._record_performance_stats(data_type, 'load', duration, True, 
                                             data_size=data_size)
                
                logger.info(f"キャッシュヒット: {data_type} (読み込み時間: {duration:.3f}秒)")
                return data
            
            duration = time.time() - start_time
            self._record_performance_stats(data_type, 'load', duration, False)
            return None
            
        except Exception as e:
            duration = time.time() - start_time
            self._record_performance_stats(data_type, 'load', duration, False)
            logger.error(f"キャッシュ読み込みエラー ({data_type}): {e}")
            return None
    
    def save_cached_data(self, data_type: str, data: Any) -> None:
        """
        データをキャッシュに保存
        
        Args:
            data_type: データタイプ
            data: 保存するデータ
        """
        start_time = time.time()
        
        try:
            if data_type not in self.DATA_TYPES:
                logger.warning(f"未知のデータタイプ: {data_type}")
                return
            
            # 依存ファイル情報を取得
            dependencies = self._get_file_dependencies(data_type)
            dependencies_hash = self._calculate_dependencies_hash(dependencies)
            
            # キャッシュデータを準備
            cache_data = self._load_cache_data()
            cache_key = f"{self.mod_id}_{data_type}"
            
            cache_data[cache_key] = {
                'data': data,
                'cached_at': time.time(),
                'data_type': data_type,
                'mod_path': str(self.mod_path),
                'file_count': len(dependencies)
            }
            
            # メタデータを準備
            metadata = self._load_metadata()
            metadata[cache_key] = {
                'data_type': data_type,
                'mod_path': str(self.mod_path),
                'mod_id': self.mod_id,
                'dependencies_hash': dependencies_hash,
                'dependencies_count': len(dependencies),
                'cached_at': time.time(),
                'dependencies': [str(dep) for dep in dependencies]
            }
            
            # 保存
            self._save_cache_data(cache_data)
            self._save_metadata(metadata)
            
            duration = time.time() - start_time
            data_size = len(json.dumps(data)) if data else 0
            self._record_performance_stats(data_type, 'save', duration, False, 
                                         len(dependencies), data_size)
            
            logger.info(f"キャッシュ保存完了: {data_type} (ファイル数: {len(dependencies)}, "
                       f"保存時間: {duration:.3f}秒)")
            
        except Exception as e:
            duration = time.time() - start_time
            self._record_performance_stats(data_type, 'save', duration, False)
            logger.error(f"キャッシュ保存エラー ({data_type}): {e}")
    
    def clear_cache(self, data_type: Optional[str] = None) -> None:
        """
        キャッシュをクリア
        
        Args:
            data_type: 特定のデータタイプのみクリア（省略時は全体）
        """
        try:
            if data_type:
                # 特定データタイプのキャッシュをクリア
                cache_data = self._load_cache_data()
                metadata = self._load_metadata()
                
                cache_key = f"{self.mod_id}_{data_type}"
                
                if cache_key in cache_data:
                    del cache_data[cache_key]
                    self._save_cache_data(cache_data)
                
                if cache_key in metadata:
                    del metadata[cache_key]
                    self._save_metadata(metadata)
                
                logger.info(f"キャッシュクリア完了: {data_type}")
            else:
                # 全キャッシュをクリア
                if self.cache_file.exists():
                    self.cache_file.unlink()
                if self.metadata_file.exists():
                    self.metadata_file.unlink()
                if self.stats_file.exists():
                    self.stats_file.unlink()
                
                logger.info("全キャッシュクリア完了")
                
        except Exception as e:
            logger.error(f"キャッシュクリアエラー: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        キャッシュの統計情報を取得
        
        Returns:
            統計情報辞書
        """
        try:
            stats = {
                'mod_path': str(self.mod_path),
                'mod_id': self.mod_id,
                'cache_dir': str(self.cache_dir),
                'cache_exists': self.cache_file.exists(),
                'metadata_exists': self.metadata_file.exists(),
                'data_types': {},
                'performance': {}
            }
            
            # メタデータ情報
            metadata = self._load_metadata()
            for cache_key, info in metadata.items():
                if cache_key.startswith(self.mod_id):
                    data_type = info.get('data_type', 'unknown')
                    stats['data_types'][data_type] = {
                        'dependencies_count': info.get('dependencies_count', 0),
                        'cached_at': info.get('cached_at', 0),
                        'is_valid': self.is_cache_valid(data_type)
                    }
            
            # パフォーマンス統計
            if self.stats_file.exists():
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats['performance'] = json.load(f)
            
            return stats
            
        except Exception as e:
            logger.error(f"統計情報取得エラー: {e}")
            return {}
    
    def cleanup_invalid_cache(self) -> Dict[str, int]:
        """
        無効なキャッシュエントリを削除
        
        Returns:
            クリーンアップ統計
        """
        cleanup_stats = {
            'removed_cache_entries': 0,
            'removed_metadata_entries': 0,
            'total_entries_before': 0,
            'total_entries_after': 0
        }
        
        try:
            cache_data = self._load_cache_data()
            metadata = self._load_metadata()
            
            cleanup_stats['total_entries_before'] = len(metadata)
            
            # このMODに関連するエントリのみ処理
            mod_keys = [k for k in metadata.keys() if k.startswith(self.mod_id)]
            
            keys_to_remove = []
            
            for cache_key in mod_keys:
                cache_info = metadata[cache_key]
                data_type = cache_info.get('data_type')
                
                # データタイプが有効で、依存ファイルが存在するかチェック
                if data_type not in self.DATA_TYPES:
                    keys_to_remove.append(cache_key)
                    continue
                
                dependencies = self._get_file_dependencies(data_type)
                if not dependencies:
                    keys_to_remove.append(cache_key)
                    continue
            
            # 無効エントリを削除
            for key in keys_to_remove:
                if key in cache_data:
                    del cache_data[key]
                    cleanup_stats['removed_cache_entries'] += 1
                
                if key in metadata:
                    del metadata[key]
                    cleanup_stats['removed_metadata_entries'] += 1
            
            # 変更を保存
            if keys_to_remove:
                self._save_cache_data(cache_data)
                self._save_metadata(metadata)
            
            cleanup_stats['total_entries_after'] = len(metadata)
            
            if keys_to_remove:
                logger.info(f"無効キャッシュクリーンアップ完了: {len(keys_to_remove)}個のエントリを削除")
            
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"キャッシュクリーンアップエラー: {e}")
            return cleanup_stats
    
    # === 設計データ専用メソッド ===
    
    def load_design_cache(self, design_file_path: str) -> Optional[Dict[str, Any]]:
        """
        個別設計ファイルのキャッシュを読み込み
        
        Args:
            design_file_path: 設計ファイルのパス
            
        Returns:
            キャッシュされた設計データ、またはNone
        """
        try:
            # 設計ファイルの相対パスをキーとして使用
            design_path = Path(design_file_path)
            if design_path.is_absolute():
                try:
                    design_path = design_path.relative_to(self.mod_path)
                except ValueError:
                    # パスがmod_pathのサブパスでない場合の処理
                    # 実際のパスの解決を試行
                    try:
                        resolved_design_path = design_path.resolve()
                        resolved_mod_path = self.mod_path.resolve()
                        design_path = resolved_design_path.relative_to(resolved_mod_path)
                    except ValueError:
                        logger.warning(f"設計ファイルパスがMODパス外です: {design_file_path}")
                        return None
            
            cache_key = f"{self.mod_id}_design_{str(design_path).replace('/', '_')}"
            
            # キャッシュデータを読み込み
            cache_data = self._load_cache_data()
            
            if cache_key in cache_data:
                cached_entry = cache_data[cache_key]
                
                # ファイルの更新時間をチェック
                file_path = self.mod_path / design_path
                if file_path.exists():
                    file_mtime = file_path.stat().st_mtime
                    cached_mtime = cached_entry.get('file_mtime', 0)
                    
                    if file_mtime <= cached_mtime:
                        logger.debug(f"設計キャッシュヒット: {design_path}")
                        return cached_entry.get('data')
                    else:
                        logger.debug(f"設計キャッシュ期限切れ: {design_path}")
                        # 期限切れエントリを削除
                        del cache_data[cache_key]
                        self._save_cache_data(cache_data)
            
            return None
            
        except Exception as e:
            logger.warning(f"設計キャッシュ読み込みエラー ({design_file_path}): {e}")
            return None
    
    def save_design_cache(self, design_file_path: str, design_data: Dict[str, Any]) -> None:
        """
        個別設計ファイルのキャッシュを保存
        
        Args:
            design_file_path: 設計ファイルのパス
            design_data: 設計データ
        """
        try:
            # 設計ファイルの相対パスをキーとして使用
            design_path = Path(design_file_path)
            if design_path.is_absolute():
                try:
                    design_path = design_path.relative_to(self.mod_path)
                except ValueError:
                    # パスがmod_pathのサブパスでない場合の処理
                    # 実際のパスの解決を試行
                    try:
                        resolved_design_path = design_path.resolve()
                        resolved_mod_path = self.mod_path.resolve()
                        design_path = resolved_design_path.relative_to(resolved_mod_path)
                    except ValueError:
                        logger.warning(f"設計ファイルパスがMODパス外です: {design_file_path}")
                        return
            
            cache_key = f"{self.mod_id}_design_{str(design_path).replace('/', '_')}"
            
            # ファイルの更新時間を取得
            file_path = self.mod_path / design_path
            file_mtime = file_path.stat().st_mtime if file_path.exists() else time.time()
            
            # キャッシュデータを準備
            cache_data = self._load_cache_data()
            cache_data[cache_key] = {
                'data': design_data,
                'file_path': str(design_path),
                'file_mtime': file_mtime,
                'cached_at': time.time(),
                'data_type': 'design'
            }
            
            # 保存
            self._save_cache_data(cache_data)
            
            logger.debug(f"設計キャッシュ保存完了: {design_path}")
            
        except Exception as e:
            logger.error(f"設計キャッシュ保存エラー ({design_file_path}): {e}")
    
    def load_resolved_design_cache(self, design_id: str) -> Optional[Dict[str, Any]]:
        """
        解決済み設計データ（船体・装備情報含む）のキャッシュを読み込み
        
        Args:
            design_id: 設計ID
            
        Returns:
            キャッシュされた解決済み設計データ、またはNone
        """
        try:
            cache_data = self._load_cache_data()
            cache_key = f"{self.mod_id}_resolved_designs"
            
            if cache_key in cache_data:
                resolved_data = cache_data[cache_key].get('data', {})
                if design_id in resolved_data:
                    logger.debug(f"解決済み設計キャッシュヒット: {design_id}")
                    return resolved_data[design_id]
            
            return None
            
        except Exception as e:
            logger.warning(f"解決済み設計キャッシュ読み込みエラー ({design_id}): {e}")
            return None
    
    def save_resolved_design_cache(self, design_id: str, resolved_data: Dict[str, Any]) -> None:
        """
        解決済み設計データをキャッシュに保存
        
        Args:
            design_id: 設計ID
            resolved_data: 解決済み設計データ
        """
        try:
            cache_data = self._load_cache_data()
            cache_key = f"{self.mod_id}_resolved_designs"
            
            # 既存の解決済みキャッシュを取得
            if cache_key not in cache_data:
                cache_data[cache_key] = {
                    'data': {},
                    'cached_at': time.time(),
                    'data_type': 'resolved_designs'
                }
            
            cache_data[cache_key]['data'][design_id] = resolved_data
            cache_data[cache_key]['cached_at'] = time.time()
            
            # 保存
            self._save_cache_data(cache_data)
            
            logger.debug(f"解決済み設計キャッシュ保存完了: {design_id}")
            
        except Exception as e:
            logger.error(f"解決済み設計キャッシュ保存エラー ({design_id}): {e}")
    
    def load_design_stats_cache(self, design_id: str) -> Optional[Dict[str, Any]]:
        """
        設計統計データのキャッシュを読み込み
        
        Args:
            design_id: 設計ID
            
        Returns:
            キャッシュされた統計データ、またはNone
        """
        try:
            cache_data = self._load_cache_data()
            cache_key = f"{self.mod_id}_design_stats"
            
            if cache_key in cache_data:
                stats_data = cache_data[cache_key].get('data', {})
                if design_id in stats_data:
                    logger.debug(f"設計統計キャッシュヒット: {design_id}")
                    return stats_data[design_id]
            
            return None
            
        except Exception as e:
            logger.warning(f"設計統計キャッシュ読み込みエラー ({design_id}): {e}")
            return None
    
    def save_design_stats_cache(self, design_id: str, stats_data: Dict[str, Any]) -> None:
        """
        設計統計データをキャッシュに保存
        
        Args:
            design_id: 設計ID
            stats_data: 統計データ
        """
        try:
            cache_data = self._load_cache_data()
            cache_key = f"{self.mod_id}_design_stats"
            
            # 既存の統計キャッシュを取得
            if cache_key not in cache_data:
                cache_data[cache_key] = {
                    'data': {},
                    'cached_at': time.time(),
                    'data_type': 'design_stats'
                }
            
            cache_data[cache_key]['data'][design_id] = stats_data
            cache_data[cache_key]['cached_at'] = time.time()
            
            # 保存
            self._save_cache_data(cache_data)
            
            logger.debug(f"設計統計キャッシュ保存完了: {design_id}")
            
        except Exception as e:
            logger.error(f"設計統計キャッシュ保存エラー ({design_id}): {e}")
    
    def clear_design_cache(self, design_id: Optional[str] = None) -> None:
        """
        設計関連キャッシュをクリア
        
        Args:
            design_id: 特定の設計IDのみクリア（省略時は全設計データ）
        """
        try:
            cache_data = self._load_cache_data()
            keys_to_remove = []
            
            if design_id:
                # 特定設計のキャッシュをクリア
                design_cache_prefix = f"{self.mod_id}_design_"
                resolved_key = f"{self.mod_id}_resolved_designs"
                stats_key = f"{self.mod_id}_design_stats"
                
                # 個別設計ファイルキャッシュ
                for key in cache_data.keys():
                    if key.startswith(design_cache_prefix):
                        cached_data = cache_data[key]
                        if cached_data.get('data', {}).get('id') == design_id:
                            keys_to_remove.append(key)
                
                # 解決済み設計キャッシュから削除
                cache_modified = False
                if resolved_key in cache_data:
                    resolved_data = cache_data[resolved_key].get('data', {})
                    if design_id in resolved_data:
                        del resolved_data[design_id]
                        cache_modified = True
                
                # 統計キャッシュから削除
                if stats_key in cache_data:
                    stats_data = cache_data[stats_key].get('data', {})
                    if design_id in stats_data:
                        del stats_data[design_id]
                        cache_modified = True
                
            else:
                # 全設計キャッシュをクリア
                design_related_prefixes = [
                    f"{self.mod_id}_design_",
                    f"{self.mod_id}_resolved_designs",
                    f"{self.mod_id}_design_stats"
                ]
                
                for key in cache_data.keys():
                    for prefix in design_related_prefixes:
                        if key.startswith(prefix):
                            keys_to_remove.append(key)
                            break
            
            # キーを削除
            for key in keys_to_remove:
                if key in cache_data:
                    del cache_data[key]
            
            # 変更を保存
            if keys_to_remove or cache_modified:
                self._save_cache_data(cache_data)
                total_removed = len(keys_to_remove) + (1 if cache_modified else 0)
                logger.info(f"設計キャッシュクリア完了: {total_removed}個のエントリを削除")
            
        except Exception as e:
            logger.error(f"設計キャッシュクリアエラー: {e}")