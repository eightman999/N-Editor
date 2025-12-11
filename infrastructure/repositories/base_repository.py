# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: base_repository基底リポジトリ
"""リポジトリパターンの基底インターフェース

データアクセス層の抽象化を提供します。
"""

from abc import ABC, abstractmethod
from typing import List, Optional, TypeVar, Generic, Dict, Any

# ジェネリック型変数（エンティティ型）
T = TypeVar('T')


class Repository(ABC, Generic[T]):
    """リポジトリの抽象基底クラス

    エンティティの永続化と取得を担当します。
    具体的なストレージ（JSON、CSV、データベース等）の詳細を隠蔽します。

    Type Parameters:
        T: 管理するエンティティの型
    """

    @abstractmethod
    def save(self, entity: T) -> bool:
        """エンティティを保存

        Args:
            entity: 保存するエンティティ

        Returns:
            bool: 保存成功時True

        Raises:
            RepositoryError: 保存に失敗した場合
        """
        pass

    @abstractmethod
    def find_by_id(self, entity_id: str) -> Optional[T]:
        """IDでエンティティを検索

        Args:
            entity_id: エンティティID

        Returns:
            Optional[T]: エンティティ（存在しない場合はNone）

        Raises:
            RepositoryError: 検索に失敗した場合
        """
        pass

    @abstractmethod
    def find_all(self, filter_criteria: Optional[Dict[str, Any]] = None) -> List[T]:
        """全エンティティを取得

        Args:
            filter_criteria: フィルタ条件（オプション）
                例: {'country': 'JPN', 'archetype': 'DD'}

        Returns:
            List[T]: エンティティリスト

        Raises:
            RepositoryError: 取得に失敗した場合
        """
        pass

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """エンティティを削除

        Args:
            entity_id: エンティティID

        Returns:
            bool: 削除成功時True

        Raises:
            RepositoryError: 削除に失敗した場合
        """
        pass

    def exists(self, entity_id: str) -> bool:
        """エンティティが存在するかチェック

        Args:
            entity_id: エンティティID

        Returns:
            bool: 存在する場合True
        """
        return self.find_by_id(entity_id) is not None

    def count(self, filter_criteria: Optional[Dict[str, Any]] = None) -> int:
        """エンティティ数をカウント

        Args:
            filter_criteria: フィルタ条件（オプション）

        Returns:
            int: エンティティ数
        """
        return len(self.find_all(filter_criteria))


class RepositoryError(Exception):
    """リポジトリ操作エラー

    データアクセス層で発生するエラーの基底クラス。
    """
    pass


class EntityNotFoundError(RepositoryError):
    """エンティティが見つからないエラー"""

    def __init__(self, entity_id: str, entity_type: str = "Entity"):
        self.entity_id = entity_id
        self.entity_type = entity_type
        super().__init__(f"{entity_type} not found: {entity_id}")


class DuplicateEntityError(RepositoryError):
    """重複エンティティエラー"""

    def __init__(self, entity_id: str, entity_type: str = "Entity"):
        self.entity_id = entity_id
        self.entity_type = entity_type
        super().__init__(f"Duplicate {entity_type}: {entity_id}")


class InvalidEntityError(RepositoryError):
    """無効なエンティティエラー"""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Invalid entity: {reason}")
