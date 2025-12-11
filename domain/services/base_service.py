# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: base_service サービス基底クラス
"""サービス層の基底クラス

ドメインサービスの共通インターフェースと基底実装を提供します。
サービス層はドメインロジックとインフラストラクチャ層を繋ぎ、
ユースケースを実装します。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """サービス層のエラー基底クラス"""
    pass


class ValidationError(ServiceError):
    """バリデーションエラー"""
    pass


class NotFoundError(ServiceError):
    """リソースが見つからないエラー"""
    pass


class DomainService(ABC):
    """ドメインサービスの抽象基底クラス

    サービス層は以下の責務を持ちます:
    - ユースケースの実装
    - リポジトリと計算機の調整
    - トランザクション管理
    - エラーハンドリング
    """

    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def validate_input(self, input_data: Any) -> bool:
        """入力データの検証

        Args:
            input_data: 検証するデータ

        Returns:
            bool: 検証結果

        Raises:
            ValidationError: 検証失敗時
        """
        pass

    def _log_operation(self, operation: str, details: Optional[Dict[str, Any]] = None):
        """操作のログ記録

        Args:
            operation: 操作名
            details: 詳細情報（オプション）
        """
        if details:
            self.logger.info(f"{operation}: {details}")
        else:
            self.logger.info(operation)

    def _handle_error(self, error: Exception, context: str) -> None:
        """エラーハンドリング

        Args:
            error: 発生したエラー
            context: エラーのコンテキスト

        Raises:
            ServiceError: 再スロー
        """
        self.logger.error(f"Error in {context}: {str(error)}")
        if isinstance(error, ServiceError):
            raise
        else:
            raise ServiceError(f"Service error in {context}: {str(error)}") from error
