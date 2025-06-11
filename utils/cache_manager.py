import os
import pickle
import time
import json
import logging
from typing import Optional, Any, Dict, List, Union
from utils.path_utils import get_user_documents_path

# ロガーの設定
logger = logging.getLogger(__name__)


class CacheManager:
    """
    MODデータのパース結果をキャッシュして、パフォーマンスを向上させるクラス
    """

    def __init__(self, mod_name: str):
        """
        CacheManagerを初期化

        Args:
            mod_name: MOD名（バニラの場合は '_vanilla_' を使用）
        """
        self.mod_name = mod_name

        # ベースキャッシュディレクトリパスを生成
        # 例: Documents/NavalDesignSystem/caches/MyMod/
        self.base_cache_dir = os.path.join(
            get_user_documents_path(),
            'caches',
            self.mod_name
        )
        
        # メタデータファイルのパス
        self.metadata_file = os.path.join(self.base_cache_dir, '_cache_metadata.json')

        logger.info(f"CacheManager初期化: MOD={mod_name}, キャッシュディレクトリ={self.base_cache_dir}")

    def _get_cache_file_path(self, file_type: str, original_file_path: str, country_tag: str = None) -> str:
        """
        対応するキャッシュファイルのフルパスを返す

        Args:
            file_type: ファイル種別 (states, naval_oob, designs, strategic_regions, country_colors, equipments など)
            original_file_path: パース対象の元ファイルのフルパス
            country_tag: 国家タグ（国別キャッシュが必要な場合）

        Returns:
            キャッシュファイルのフルパス
            例: .../Documents/NavalDesignSystem/caches/MyMod/naval_oob/USA/usa_naval_oob.txt.pkl
        """
        # 元ファイル名を取得
        original_filename = os.path.basename(original_file_path)

        # キャッシュファイル名を生成（元ファイル名 + .pkl）
        cache_filename = f"{original_filename}.pkl"

        # 国別キャッシュが必要なファイル種別の場合
        if file_type in ['naval_oob', 'designs'] and country_tag:
            cache_file_path = os.path.join(
                self.base_cache_dir,
                file_type,
                country_tag.upper(),  # 国家タグを大文字に統一
                cache_filename
            )
        else:
            # 通常のキャッシュパス
            cache_file_path = os.path.join(
                self.base_cache_dir,
                file_type,
                cache_filename
            )

        return cache_file_path

    def _load_metadata(self) -> Dict[str, Any]:
        """
        キャッシュメタデータを読み込む

        Returns:
            メタデータ辞書
        """
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"メタデータ読み込みエラー: {e}")
        
        return {}

    def _save_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        キャッシュメタデータを保存する

        Args:
            metadata: 保存するメタデータ辞書
        """
        try:
            # メタデータディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(self.metadata_file), exist_ok=True)
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"メタデータ保存エラー: {e}")

    def _get_cache_key(self, file_type: str, original_file_path: str, country_tag: str = None) -> str:
        """
        キャッシュキーを生成する

        Args:
            file_type: ファイル種別
            original_file_path: 元ファイルのフルパス
            country_tag: 国家タグ（国別キャッシュが必要な場合）

        Returns:
            キャッシュキー
        """
        if country_tag:
            return f"{file_type}:{original_file_path}:{country_tag}"
        return f"{file_type}:{original_file_path}"

    def _is_cache_valid(self, cache_key: str, original_file_path: str, cache_file_path: str) -> bool:
        """
        キャッシュが有効かどうかをチェックする（タイムスタンプベース、複数ファイル対応）

        Args:
            cache_key: キャッシュキー
            original_file_path: 元ファイルのパス（複数ファイルの場合は代表ファイルまたは結合パス）
            cache_file_path: キャッシュファイルのパス

        Returns:
            キャッシュが有効な場合True
        """
        try:
            # キャッシュファイルが存在しない場合は無効
            if not os.path.exists(cache_file_path):
                return False
            
            # メタデータを読み込む
            metadata = self._load_metadata()
            cache_info = metadata.get(cache_key)
            
            # 複数ファイル依存の場合（'+' で結合されたパス）
            if '+' in original_file_path:
                file_paths = original_file_path.split('+')
                
                # すべての依存ファイルが存在することを確認
                for file_path in file_paths:
                    if not os.path.exists(file_path):
                        logger.debug(f"依存ファイルが存在しない: {file_path}")
                        return False
                
                if cache_info:
                    # メタデータがある場合、各ファイルのタイムスタンプをチェック
                    multiple_file_mtimes = cache_info.get('multiple_file_mtimes', {})
                    for file_path in file_paths:
                        current_mtime = os.path.getmtime(file_path)
                        cached_mtime = multiple_file_mtimes.get(file_path, 0)
                        if abs(current_mtime - cached_mtime) >= 1.0:  # 1秒の誤差を許容
                            logger.debug(f"複数ファイル依存で更新検知: {file_path}, 現在={current_mtime}, キャッシュ={cached_mtime}")
                            return False
                    return True
                else:
                    # メタデータがない場合、最新ファイルのタイムスタンプと比較
                    newest_mtime = max(os.path.getmtime(fp) for fp in file_paths)
                    cache_mtime = os.path.getmtime(cache_file_path)
                    return cache_mtime >= newest_mtime
            
            else:
                # 単一ファイルの場合（従来の処理）
                if not os.path.exists(original_file_path):
                    return False
                
                if not cache_info:
                    # メタデータが存在しない場合、従来のタイムスタンプ比較にフォールバック
                    original_mtime = os.path.getmtime(original_file_path)
                    cache_mtime = os.path.getmtime(cache_file_path)
                    return cache_mtime >= original_mtime
                
                # メタデータに記録されたタイムスタンプと現在のファイルタイムスタンプを比較
                original_mtime = os.path.getmtime(original_file_path)
                cached_mtime = cache_info.get('original_mtime', 0)
                
                # 元ファイルが更新されていない場合はキャッシュが有効
                is_valid = abs(original_mtime - cached_mtime) < 1.0  # 1秒の誤差を許容
                
                logger.debug(f"キャッシュ有効性チェック: {cache_key}, 有効={is_valid}, 元ファイル={original_mtime}, キャッシュ={cached_mtime}")
                return is_valid
            
        except Exception as e:
            logger.warning(f"キャッシュ有効性チェックエラー ({cache_key}): {e}")
            return False

    def load(self, file_type: str, original_file_path: str, country_tag: str = None) -> Optional[Any]:
        """
        キャッシュからデータを読み込む（メタデータベースの有効性チェック付き）

        Args:
            file_type: ファイル種別
            original_file_path: 元ファイルのフルパス
            country_tag: 国家タグ（国別キャッシュが必要な場合）

        Returns:
            キャッシュされたデータ。キャッシュが存在しないか古い場合はNone
        """
        try:
            # キャッシュファイルパスとキーを取得
            cache_file_path = self._get_cache_file_path(file_type, original_file_path, country_tag)
            cache_key = self._get_cache_key(file_type, original_file_path, country_tag)

            # キャッシュの有効性をチェック
            if not self._is_cache_valid(cache_key, original_file_path, cache_file_path):
                logger.debug(f"キャッシュが無効または古い: {cache_key}")
                return None

            # キャッシュファイルからデータをデシリアライズして返す
            with open(cache_file_path, 'rb') as f:
                data = pickle.load(f)

            logger.debug(f"キャッシュからデータを読み込み成功: {cache_file_path}")
            return data

        except (FileNotFoundError, pickle.UnpicklingError, EOFError) as e:
            logger.warning(f"キャッシュ読み込みエラー ({original_file_path}): {e}")
            return None
        except Exception as e:
            logger.error(f"予期しないキャッシュ読み込みエラー ({original_file_path}): {e}")
            return None

    def save(self, file_type: str, original_file_path: str, data: Any, country_tag: str = None) -> None:
        """
        データをキャッシュに保存する（メタデータも同時に保存）

        Args:
            file_type: ファイル種別
            original_file_path: 元ファイルのフルパス
            data: 保存するデータ
            country_tag: 国家タグ（国別キャッシュが必要な場合）
        """
        try:
            # キャッシュファイルパスとキーを取得
            cache_file_path = self._get_cache_file_path(file_type, original_file_path, country_tag)
            cache_key = self._get_cache_key(file_type, original_file_path, country_tag)

            # 保存先ディレクトリが存在しない場合は作成
            cache_dir = os.path.dirname(cache_file_path)
            os.makedirs(cache_dir, exist_ok=True)

            # データをシリアライズして保存
            with open(cache_file_path, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

            # メタデータを更新（複数ファイル対応）
            metadata = self._load_metadata()
            cache_meta = {
                'file_type': file_type,
                'country_tag': country_tag,
                'created_at': time.time(),
                'original_file_path': original_file_path,
                'cache_file_path': cache_file_path,
                'cache_mtime': os.path.getmtime(cache_file_path)
            }
            
            # 複数ファイル依存の場合
            if '+' in original_file_path:
                file_paths = original_file_path.split('+')
                multiple_file_mtimes = {}
                
                for file_path in file_paths:
                    if os.path.exists(file_path):
                        multiple_file_mtimes[file_path] = os.path.getmtime(file_path)
                
                cache_meta['multiple_file_mtimes'] = multiple_file_mtimes
                cache_meta['is_multiple_file_cache'] = True
            else:
                # 単一ファイルの場合
                if os.path.exists(original_file_path):
                    cache_meta['original_mtime'] = os.path.getmtime(original_file_path)
            
            metadata[cache_key] = cache_meta
            self._save_metadata(metadata)

            logger.debug(f"キャッシュにデータを保存成功: {cache_file_path}")

        except Exception as e:
            logger.error(f"キャッシュ保存エラー ({original_file_path}): {e}")
            # エラーが発生してもアプリケーションを停止させない

    def clear_cache(self, file_type: Optional[str] = None) -> None:
        """
        キャッシュをクリアする（メタデータも同時にクリア）

        Args:
            file_type: 特定のファイル種別のキャッシュのみクリアする場合に指定。
                      Noneの場合は全てのキャッシュをクリア
        """
        try:
            if file_type is None:
                # 全キャッシュをクリア
                if os.path.exists(self.base_cache_dir):
                    import shutil
                    try:
                        # まず、すべてのファイルのパーミッションを変更
                        for root, dirs, files in os.walk(self.base_cache_dir):
                            for file in files:
                                try:
                                    os.chmod(os.path.join(root, file), 0o666)
                                except Exception as e:
                                    logger.warning(f"ファイルパーミッション変更エラー: {e}")
                            for dir in dirs:
                                try:
                                    os.chmod(os.path.join(root, dir), 0o777)
                                except Exception as e:
                                    logger.warning(f"ディレクトリパーミッション変更エラー: {e}")
                        
                        # ディレクトリを削除
                        shutil.rmtree(self.base_cache_dir)
                        os.makedirs(self.base_cache_dir, exist_ok=True)
                        logger.info(f"全キャッシュをクリアしました: {self.base_cache_dir}")
                    except Exception as e:
                        logger.error(f"キャッシュディレクトリの削除に失敗: {e}")
                        # 個別のファイルを削除
                        for root, dirs, files in os.walk(self.base_cache_dir):
                            for file in files:
                                try:
                                    os.chmod(os.path.join(root, file), 0o666)
                                    os.remove(os.path.join(root, file))
                                except Exception as e:
                                    logger.error(f"ファイル削除エラー: {e}")
            else:
                # 特定のファイル種別のキャッシュをクリア
                type_cache_dir = os.path.join(self.base_cache_dir, file_type)
                if os.path.exists(type_cache_dir):
                    try:
                        # まず、すべてのファイルのパーミッションを変更
                        for root, dirs, files in os.walk(type_cache_dir):
                            for file in files:
                                try:
                                    os.chmod(os.path.join(root, file), 0o666)
                                except Exception as e:
                                    logger.warning(f"ファイルパーミッション変更エラー: {e}")
                            for dir in dirs:
                                try:
                                    os.chmod(os.path.join(root, dir), 0o777)
                                except Exception as e:
                                    logger.warning(f"ディレクトリパーミッション変更エラー: {e}")
                        
                        # ディレクトリを削除
                        shutil.rmtree(type_cache_dir)
                        os.makedirs(type_cache_dir, exist_ok=True)
                        logger.info(f"{file_type} キャッシュをクリアしました: {type_cache_dir}")
                    except Exception as e:
                        logger.error(f"キャッシュディレクトリの削除に失敗: {e}")
                        # 個別のファイルを削除
                        for root, dirs, files in os.walk(type_cache_dir):
                            for file in files:
                                try:
                                    os.chmod(os.path.join(root, file), 0o666)
                                    os.remove(os.path.join(root, file))
                                except Exception as e:
                                    logger.error(f"ファイル削除エラー: {e}")
                
                # 特定ファイル種別のメタデータも削除
                metadata = self._load_metadata()
                keys_to_remove = [k for k in metadata.keys() if metadata[k].get('file_type') == file_type]
                for key in keys_to_remove:
                    del metadata[key]
                self._save_metadata(metadata)

        except Exception as e:
            logger.error(f"キャッシュクリアエラー: {e}")

    def get_cache_info(self) -> dict:
        """
        キャッシュの情報を取得する（メタデータ情報も含む）

        Returns:
            キャッシュ情報の辞書
        """
        info = {
            'mod_name': self.mod_name,
            'base_cache_dir': self.base_cache_dir,
            'cache_exists': os.path.exists(self.base_cache_dir),
            'metadata_exists': os.path.exists(self.metadata_file),
            'file_types': [],
            'metadata_entries': 0,
            'metadata_by_type': {}
        }

        try:
            # メタデータ情報を取得
            metadata = self._load_metadata()
            info['metadata_entries'] = len(metadata)
            
            # ファイル種別ごとのメタデータ情報を集計
            for cache_key, cache_meta in metadata.items():
                file_type = cache_meta.get('file_type', 'unknown')
                if file_type not in info['metadata_by_type']:
                    info['metadata_by_type'][file_type] = []
                info['metadata_by_type'][file_type].append({
                    'cache_key': cache_key,
                    'original_file': cache_meta.get('original_file_path', ''),
                    'created_at': cache_meta.get('created_at', 0),
                    'original_mtime': cache_meta.get('original_mtime', 0)
                })

            # 物理ファイルの情報を取得
            if os.path.exists(self.base_cache_dir):
                for item in os.listdir(self.base_cache_dir):
                    item_path = os.path.join(self.base_cache_dir, item)
                    if os.path.isdir(item_path) and not item.startswith('_'):  # メタデータファイルは除外
                        cache_files = []
                        try:
                            cache_files = [f for f in os.listdir(item_path) if f.endswith('.pkl')]
                        except:
                            pass
                        
                        metadata_count = len(info['metadata_by_type'].get(item, []))
                        info['file_types'].append({
                            'type': item,
                            'cache_count': len(cache_files),
                            'metadata_count': metadata_count,
                            'sync_status': 'synced' if len(cache_files) == metadata_count else 'mismatched'
                        })
        except Exception as e:
            logger.error(f"キャッシュ情報取得エラー: {e}")

        return info

    def cleanup_invalid_metadata(self) -> Dict[str, int]:
        """
        無効なメタデータエントリを削除する

        Returns:
            クリーンアップ結果の統計
        """
        stats = {
            'removed_entries': 0,
            'missing_cache_files': 0,
            'missing_original_files': 0,
            'total_entries': 0
        }

        try:
            metadata = self._load_metadata()
            stats['total_entries'] = len(metadata)
            
            keys_to_remove = []
            
            for cache_key, cache_meta in metadata.items():
                original_file = cache_meta.get('original_file_path')
                cache_file = cache_meta.get('cache_file_path')
                
                should_remove = False
                
                # 元ファイルが存在しない場合
                if original_file and not os.path.exists(original_file):
                    stats['missing_original_files'] += 1
                    should_remove = True
                
                # キャッシュファイルが存在しない場合
                if cache_file and not os.path.exists(cache_file):
                    stats['missing_cache_files'] += 1
                    should_remove = True
                
                if should_remove:
                    keys_to_remove.append(cache_key)
            
            # 無効エントリを削除
            for key in keys_to_remove:
                del metadata[key]
                stats['removed_entries'] += 1
            
            # メタデータを保存
            if stats['removed_entries'] > 0:
                self._save_metadata(metadata)
                logger.info(f"無効メタデータをクリーンアップ: {stats['removed_entries']}個のエントリを削除")

        except Exception as e:
            logger.error(f"メタデータクリーンアップエラー: {e}")

        return stats