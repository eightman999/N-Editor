# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: legacy_hull_adapter レガシーシステムアダプター
"""レガシーHullModelとの互換性アダプター

新しいHullエンティティとレガシーのHullModel辞書形式を
相互変換するアダプターです。
"""

from typing import Dict, Any, Optional
import logging

from domain.entities.hull import Hull

logger = logging.getLogger(__name__)


class LegacyHullAdapter:
    """レガシーHullModel形式とHullエンティティの変換アダプター

    旧システムの辞書形式と新システムのHullエンティティを
    相互変換します。これにより、段階的な移行が可能になります。
    """

    # レガシーフィールドから新フィールドへのマッピング
    LEGACY_TO_NEW_MAPPING = {
        'id': 'id',
        'name': 'name',
        'weight': 'weight',
        'length': 'length',
        'width': 'width',
        'speed': 'max_speed',
        'max_speed': 'max_speed',
        'cruise_speed': 'cruise_speed',
        'range': 'naval_range',
        'naval_range': 'naval_range',
        'fuel_capacity': 'fuel_capacity',
        'armor_max': 'armor_max',
        'armor_min': 'armor_min',
        'hull_structure': 'hull_structure',
        'armor_type': 'armor_type',
        'crew': 'crew',
        'year': 'year',
        'country': 'country',
        'archetype': 'archetype',
        'type': 'type_display',
        'class': 'ship_class',
    }

    # 新フィールドからレガシーフィールドへのマッピング
    NEW_TO_LEGACY_MAPPING = {
        'id': 'id',
        'name': 'name',
        'weight': 'weight',
        'length': 'length',
        'width': 'width',
        'max_speed': 'speed',
        'cruise_speed': 'cruise_speed',
        'naval_range': 'range',
        'fuel_capacity': 'fuel_capacity',
        'armor_max': 'armor_max',
        'armor_min': 'armor_min',
        'hull_structure': 'hull_structure',
        'armor_type': 'armor_type',
        'crew': 'crew',
        'year': 'year',
        'country': 'country',
        'archetype': 'archetype',
        'type_display': 'type',
        'ship_class': 'class',
    }

    @classmethod
    def from_legacy(cls, legacy_data: Dict[str, Any]) -> Hull:
        """レガシー辞書形式から新Hullエンティティに変換

        Args:
            legacy_data: レガシーHullModel形式のデータ

        Returns:
            Hull: 新しいHullエンティティ

        Raises:
            ValueError: 必須フィールドが欠落している場合
        """
        hull_data = {}

        # フィールドマッピング
        for legacy_field, new_field in cls.LEGACY_TO_NEW_MAPPING.items():
            if legacy_field in legacy_data:
                hull_data[new_field] = legacy_data[legacy_field]

        # 必須フィールドの検証
        if 'id' not in hull_data:
            raise ValueError("Missing required field: id")
        if 'name' not in hull_data:
            hull_data['name'] = hull_data['id']

        # デフォルト値の設定
        hull_data.setdefault('weight', 0.0)
        hull_data.setdefault('max_speed', 0.0)
        hull_data.setdefault('cruise_speed', 0.0)
        hull_data.setdefault('naval_range', 0.0)
        hull_data.setdefault('fuel_capacity', 0.0)
        hull_data.setdefault('hull_structure', 'WWII型')
        hull_data.setdefault('armor_type', '標準装甲')
        hull_data.setdefault('year', 1936)

        # Hullエンティティを作成
        try:
            hull = Hull(**hull_data)
            logger.debug(f"Converted legacy data to Hull: {hull.id}")
            return hull
        except Exception as e:
            logger.error(f"Failed to convert legacy data: {e}")
            raise ValueError(f"Invalid hull data: {e}") from e

    @classmethod
    def to_legacy(cls, hull: Hull) -> Dict[str, Any]:
        """新Hullエンティティからレガシー辞書形式に変換

        Args:
            hull: 新しいHullエンティティ

        Returns:
            Dict[str, Any]: レガシーHullModel形式のデータ
        """
        legacy_data = {}

        # Hullエンティティから辞書に変換
        hull_dict = hull.to_dict()

        # フィールドマッピング
        for new_field, legacy_field in cls.NEW_TO_LEGACY_MAPPING.items():
            if new_field in hull_dict:
                legacy_data[legacy_field] = hull_dict[new_field]

        # レガシーシステムで期待される追加フィールド
        legacy_data['max_speed'] = hull.max_speed  # speedとmax_speedの両方
        legacy_data['naval_range'] = hull.naval_range  # rangeとnaval_rangeの両方

        # スロット情報（レガシー互換のため空で提供）
        if 'slots' not in legacy_data:
            legacy_data['slots'] = {
                'PA': ' ',
                'SA': ' ',
                'PSA': ' ',
                'SSA': ' ',
                'PLA': ' ',
                'SLA': ' '
            }

        logger.debug(f"Converted Hull to legacy data: {hull.id}")
        return legacy_data

    @classmethod
    def convert_performance_to_legacy(
        cls,
        performance: Dict[str, float]
    ) -> Dict[str, float]:
        """新システムの性能データをレガシー形式に変換

        Args:
            performance: 新システムの性能データ

        Returns:
            Dict[str, float]: レガシー形式の性能データ
        """
        legacy_performance = {}

        # フィールドマッピング
        mapping = {
            'max_speed': 'speed',
            'cruise_speed': 'cruise_speed',
            'naval_range': 'range',
            'fuel_capacity': 'fuel_capacity',
            'display_speed': 'display_speed',
            'fuel_consumption': 'fuel_consumption',
            'operational_range': 'operational_range'
        }

        for new_field, legacy_field in mapping.items():
            if new_field in performance:
                legacy_performance[legacy_field] = performance[new_field]

        # レガシーシステムで期待される両方の名前
        if 'max_speed' in performance:
            legacy_performance['max_speed'] = performance['max_speed']

        if 'naval_range' in performance:
            legacy_performance['naval_range'] = performance['naval_range']

        return legacy_performance

    @classmethod
    def convert_equipment_to_legacy(
        cls,
        equipment_effect: Dict[str, Any]
    ) -> Dict[str, Any]:
        """新システムの装備効果データをレガシー形式に変換

        Args:
            equipment_effect: 新システムの装備効果データ

        Returns:
            Dict[str, Any]: レガシー形式の装備効果データ
        """
        legacy_effect = {}

        # フィールドマッピング
        mapping = {
            'new_speed': 'new_speed',
            'new_cruise_speed': 'new_cruise_speed',
            'new_range': 'new_range',
            'speed_penalty': 'speed_penalty',
            'cruise_penalty': 'cruise_penalty',
            'range_penalty': 'range_penalty',
            'weight_ratio': 'weight_ratio',
            'armor_factor': 'armor_factor',
            'size_factor': 'size_factor',
            'total_equipment_weight': 'total_equipment_weight'
        }

        for new_field, legacy_field in mapping.items():
            if new_field in equipment_effect:
                legacy_effect[legacy_field] = equipment_effect[new_field]

        return legacy_effect

    @classmethod
    def batch_from_legacy(cls, legacy_data_list: list[Dict[str, Any]]) -> list[Hull]:
        """複数のレガシーデータを一括変換

        Args:
            legacy_data_list: レガシーデータのリスト

        Returns:
            list[Hull]: Hullエンティティのリスト
        """
        hulls = []
        for legacy_data in legacy_data_list:
            try:
                hull = cls.from_legacy(legacy_data)
                hulls.append(hull)
            except Exception as e:
                logger.warning(f"Failed to convert legacy data: {e}")

        logger.info(f"Converted {len(hulls)}/{len(legacy_data_list)} legacy entries")
        return hulls

    @classmethod
    def batch_to_legacy(cls, hulls: list[Hull]) -> list[Dict[str, Any]]:
        """複数のHullエンティティを一括変換

        Args:
            hulls: Hullエンティティのリスト

        Returns:
            list[Dict[str, Any]]: レガシーデータのリスト
        """
        legacy_data_list = []
        for hull in hulls:
            try:
                legacy_data = cls.to_legacy(hull)
                legacy_data_list.append(legacy_data)
            except Exception as e:
                logger.warning(f"Failed to convert Hull {hull.id}: {e}")

        logger.info(f"Converted {len(legacy_data_list)}/{len(hulls)} hulls to legacy format")
        return legacy_data_list
