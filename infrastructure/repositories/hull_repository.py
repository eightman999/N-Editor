# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: hull_repository船体リポジトリ
"""船体リポジトリ

船体エンティティの永続化と取得を担当します。
"""

from typing import List, Optional, Dict, Any
import os
import json
import time
import logging
from .base_repository import Repository, RepositoryError, EntityNotFoundError
from domain.entities.hull import Hull

logger = logging.getLogger(__name__)


class HullRepository(Repository[Hull]):
    """船体リポジトリ（JSONファイルベース）

    船体エンティティをJSONファイルとして永続化します。
    キャッシュマネージャーと統合して高速なデータアクセスを実現します。

    Attributes:
        data_dir: データディレクトリのパス
        cache_manager: キャッシュマネージャー（オプション）
    """

    def __init__(self, data_dir: str, cache_manager=None):
        """初期化

        Args:
            data_dir: データディレクトリのパス
            cache_manager: キャッシュマネージャー（オプション）
        """
        self.data_dir = data_dir
        self.cache_manager = cache_manager
        os.makedirs(data_dir, exist_ok=True)

        # メモリキャッシュ
        self._memory_cache: Dict[str, Hull] = {}

    def save(self, hull: Hull) -> bool:
        """船体エンティティを保存

        Args:
            hull: 船体エンティティ

        Returns:
            bool: 保存成功時True

        Raises:
            RepositoryError: 保存に失敗した場合
        """
        try:
            # エンティティの妥当性検証
            if not hull.validate():
                raise RepositoryError(f"Invalid hull entity: {hull.id}")

            # JSONファイルとして保存
            file_path = self._get_file_path(hull.id)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(hull.to_dict(), f, ensure_ascii=False, indent=2)

            # メモリキャッシュを更新
            self._memory_cache[hull.id] = hull

            # 永続キャッシュを無効化（次回読み込み時に再キャッシュ）
            if self.cache_manager:
                self.cache_manager.invalidate(f"hull_{hull.id}")

            logger.debug(f"Saved hull: {hull.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save hull {hull.id}: {e}")
            raise RepositoryError(f"Failed to save hull: {e}")

    def find_by_id(self, hull_id: str) -> Optional[Hull]:
        """IDで船体を検索

        Args:
            hull_id: 船体ID

        Returns:
            Optional[Hull]: 船体エンティティ（存在しない場合はNone）

        Raises:
            RepositoryError: 検索に失敗した場合
        """
        try:
            # メモリキャッシュチェック
            if hull_id in self._memory_cache:
                return self._memory_cache[hull_id]

            # 永続キャッシュチェック
            if self.cache_manager:
                cache_key = f"hull_{hull_id}"
                cached_data = self.cache_manager.load(cache_key, self.data_dir)
                if cached_data is not None:
                    hull = Hull.from_dict(cached_data)
                    self._memory_cache[hull_id] = hull
                    logger.debug(f"Loaded hull from cache: {hull_id}")
                    return hull

            # ファイルから読み込み
            file_path = self._get_file_path(hull_id)
            if not os.path.exists(file_path):
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            hull = Hull.from_dict(data)

            # キャッシュに保存
            self._memory_cache[hull_id] = hull
            if self.cache_manager:
                self.cache_manager.save(f"hull_{hull_id}", self.data_dir, data)

            logger.debug(f"Loaded hull from file: {hull_id}")
            return hull

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for hull {hull_id}: {e}")
            raise RepositoryError(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Failed to load hull {hull_id}: {e}")
            raise RepositoryError(f"Failed to load hull: {e}")

    def find_all(self, filter_criteria: Optional[Dict[str, Any]] = None) -> List[Hull]:
        """全船体を取得

        Args:
            filter_criteria: フィルタ条件（オプション）
                例: {'country': 'JPN', 'archetype': 'DD'}

        Returns:
            List[Hull]: 船体エンティティのリスト

        Raises:
            RepositoryError: 取得に失敗した場合
        """
        start_time = time.time()

        try:
            hulls = []
            file_count = 0

            if not os.path.exists(self.data_dir):
                return hulls

            for file_name in os.listdir(self.data_dir):
                if file_name.endswith('.json'):
                    file_count += 1
                    hull_id = file_name[:-5]  # 拡張子を除去

                    hull = self.find_by_id(hull_id)
                    if hull and self._matches_filter(hull, filter_criteria):
                        hulls.append(hull)

            duration = time.time() - start_time
            logger.info(f"Loaded {len(hulls)} hulls from {file_count} files in {duration:.3f}s")

            return hulls

        except Exception as e:
            logger.error(f"Failed to load all hulls: {e}")
            raise RepositoryError(f"Failed to load all hulls: {e}")

    def delete(self, hull_id: str) -> bool:
        """船体を削除

        Args:
            hull_id: 船体ID

        Returns:
            bool: 削除成功時True

        Raises:
            RepositoryError: 削除に失敗した場合
        """
        try:
            file_path = self._get_file_path(hull_id)
            if not os.path.exists(file_path):
                return False

            os.remove(file_path)

            # キャッシュから削除
            if hull_id in self._memory_cache:
                del self._memory_cache[hull_id]

            if self.cache_manager:
                self.cache_manager.invalidate(f"hull_{hull_id}")

            logger.debug(f"Deleted hull: {hull_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete hull {hull_id}: {e}")
            raise RepositoryError(f"Failed to delete hull: {e}")

    def _get_file_path(self, hull_id: str) -> str:
        """船体IDからファイルパスを取得

        Args:
            hull_id: 船体ID

        Returns:
            str: ファイルパス
        """
        return os.path.join(self.data_dir, f"{hull_id}.json")

    def _matches_filter(self, hull: Hull, criteria: Optional[Dict[str, Any]]) -> bool:
        """フィルタ条件に一致するか判定

        Args:
            hull: 船体エンティティ
            criteria: フィルタ条件

        Returns:
            bool: 一致する場合True
        """
        if not criteria:
            return True

        for key, value in criteria.items():
            hull_value = getattr(hull, key, None)
            if hull_value != value:
                return False

        return True

    def clear_cache(self):
        """全キャッシュをクリア"""
        self._memory_cache.clear()
        logger.debug("Cleared hull repository cache")

    def get_cache_info(self) -> Dict[str, int]:
        """キャッシュ情報を取得

        Returns:
            Dict[str, int]: キャッシュサイズ情報
        """
        return {
            'memory_cache_size': len(self._memory_cache)
        }
