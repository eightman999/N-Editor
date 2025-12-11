# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: hull_model_facade レガシーHullModel互換ファサード
"""レガシーHullModelと互換性のあるファサード

新システムを使用しながら、レガシーHullModelと同じ
インターフェースを提供するファサードです。
"""

from typing import Dict, List, Any, Optional
import logging

from domain.services.hull_performance_service import HullPerformanceService
from infrastructure.repositories.hull_repository import HullRepository
from infrastructure.adapters.legacy_hull_adapter import LegacyHullAdapter

logger = logging.getLogger(__name__)


class HullModelFacade:
    """レガシーHullModel互換のファサード

    新システム（HullPerformanceService）を使用しながら、
    レガシーHullModelと同じインターフェースを提供します。

    これにより、既存のコードベースを変更せずに
    新システムに移行できます。
    """

    def __init__(self, data_dir: str = None, cache_manager=None):
        """初期化

        Args:
            data_dir: データディレクトリパス
            cache_manager: キャッシュマネージャー（レガシー互換）
        """
        # 新システムの初期化
        self.repository = HullRepository(data_dir, cache_manager)
        self.service = HullPerformanceService(self.repository)

        # レガシー互換のために保持
        self.data_dir = data_dir or self.repository.data_dir
        self.cache_manager = cache_manager
        self.hull_cache = {}  # レガシーキャッシュ（使用されないが互換性のため）

        logger.info(f"HullModelFacade initialized with data_dir: {self.data_dir}")

    def load_hull(self, hull_id: str) -> Optional[Dict[str, Any]]:
        """船体データを読み込み（レガシー互換）

        Args:
            hull_id: 船体ID

        Returns:
            Optional[Dict[str, Any]]: レガシー形式の船体データ
        """
        try:
            hull = self.service.get_hull(hull_id)
            legacy_data = LegacyHullAdapter.to_legacy(hull)
            return legacy_data
        except Exception as e:
            logger.warning(f"Failed to load hull {hull_id}: {e}")
            return None

    def save_hull(self, hull_data: Dict[str, Any]) -> bool:
        """船体データを保存（レガシー互換）

        Args:
            hull_data: レガシー形式の船体データ

        Returns:
            bool: 保存成功
        """
        try:
            hull = LegacyHullAdapter.from_legacy(hull_data)
            return self.service.save_hull(hull)
        except Exception as e:
            logger.error(f"Failed to save hull: {e}")
            return False

    def get_all_hulls(self, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """全船体を取得（レガシー互換）

        Args:
            filter_dict: フィルタ条件

        Returns:
            List[Dict[str, Any]]: レガシー形式の船体データリスト
        """
        try:
            hulls = self.service.get_all_hulls(filter_dict)
            return LegacyHullAdapter.batch_to_legacy(hulls)
        except Exception as e:
            logger.error(f"Failed to get all hulls: {e}")
            return []

    def calculate_hull_performance(
        self,
        hull_data: Dict[str, Any],
        engine_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """船体性能を計算（レガシー互換）

        Args:
            hull_data: レガシー形式の船体データ
            engine_data: 機関データ

        Returns:
            Dict[str, Any]: レガシー形式の性能データ
        """
        try:
            # レガシーデータを新形式に変換
            hull = LegacyHullAdapter.from_legacy(hull_data)

            # 一時的に保存（計算に必要）
            hull_id = hull.id
            self.service.save_hull(hull)

            # 性能計算
            performance = self.service.calculate_hull_performance(hull_id, engine_data)

            # レガシー形式に変換
            legacy_performance = LegacyHullAdapter.convert_performance_to_legacy(performance)

            # 元の船体データに性能データをマージ
            result = hull_data.copy()
            result.update(legacy_performance)

            return result

        except Exception as e:
            logger.error(f"Failed to calculate hull performance: {e}")
            # エラー時は元のデータを返す
            return hull_data.copy()

    def import_from_csv(self, csv_file_path: str, encoding: str = 'utf-8') -> int:
        """CSVから船体をインポート（レガシー互換）

        Args:
            csv_file_path: CSVファイルパス
            encoding: エンコーディング

        Returns:
            int: インポートされた船体数
        """
        return self.service.import_from_csv(csv_file_path, encoding)

    def export_to_csv(
        self,
        csv_file_path: str,
        filter_dict: Optional[Dict[str, Any]] = None,
        encoding: str = 'utf-8'
    ) -> int:
        """船体をCSVにエクスポート（レガシー互換）

        Args:
            csv_file_path: 出力CSVファイルパス
            filter_dict: フィルタ条件
            encoding: エンコーディング

        Returns:
            int: エクスポートされた船体数
        """
        return self.service.export_to_csv(csv_file_path, filter_dict, encoding)

    def delete_hull(self, hull_id: str) -> bool:
        """船体を削除（レガシー互換）

        Args:
            hull_id: 船体ID

        Returns:
            bool: 削除成功
        """
        return self.service.delete_hull(hull_id)

    def hull_exists(self, hull_id: str) -> bool:
        """船体の存在確認（レガシー互換）

        Args:
            hull_id: 船体ID

        Returns:
            bool: 存在する場合True
        """
        return self.service.hull_exists(hull_id)

    def get_statistics(self, filter_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """統計情報を取得（新機能）

        Args:
            filter_dict: フィルタ条件

        Returns:
            Dict[str, Any]: 統計情報
        """
        return self.service.get_statistics(filter_dict)

    def batch_calculate_performance(
        self,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, float]]:
        """バッチ性能計算（新機能）

        Args:
            filter_dict: フィルタ条件

        Returns:
            Dict[str, Dict[str, float]]: 船体ID → 性能データ
        """
        results = self.service.batch_calculate_performance(filter_dict)

        # レガシー形式に変換
        legacy_results = {}
        for hull_id, performance in results.items():
            legacy_results[hull_id] = LegacyHullAdapter.convert_performance_to_legacy(performance)

        return legacy_results

    def clear_cache(self):
        """キャッシュをクリア"""
        self.service.clear_cache()
        self.hull_cache.clear()

    def get_cache_info(self) -> Dict[str, Any]:
        """キャッシュ情報を取得

        Returns:
            Dict[str, Any]: キャッシュ情報
        """
        return self.service.get_cache_info()
