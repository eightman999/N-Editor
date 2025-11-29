# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: equipment_calculator装備影響計算機
"""装備影響計算機

装備の重量・装甲・サイズが船体性能に与える影響を計算する計算機。
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from .base import PerformanceCalculator
from ..entities.hull import Hull


@dataclass
class Equipment:
    """装備の簡易データクラス

    計算に必要な最小限の装備データを保持します。

    Attributes:
        id: 装備ID
        name: 装備名
        weight: 重量 (ton)
    """
    id: str
    name: str
    weight: float = 0.0


class EquipmentEffectCalculator(PerformanceCalculator):
    """装備影響計算機

    装備の重量が船体の速度と航続距離に与える影響を計算します。
    装甲とサイズ要素も考慮します。

    Attributes:
        weight_factor: 重量影響係数
        range_factor: 航続距離影響係数
    """

    def __init__(self, weight_factor: float = 0.2, range_factor: float = 0.1):
        """初期化

        Args:
            weight_factor: 重量影響係数（デフォルト: 0.2）
            range_factor: 航続距離影響係数（デフォルト: 0.1）
        """
        self.weight_factor = weight_factor
        self.range_factor = range_factor

    def calculate(
        self,
        hull: Hull,
        equipments: List[Equipment]
    ) -> Dict[str, float]:
        """装備による性能ペナルティを計算

        Args:
            hull: 船体エンティティ
            equipments: 装備リスト

        Returns:
            Dict[str, float]: ペナルティ適用後の性能
                {
                    'new_speed': 新しい最大速度,
                    'new_cruise_speed': 新しい巡航速度,
                    'new_range': 新しい航続距離,
                    'speed_penalty': 速度ペナルティ,
                    'cruise_penalty': 巡航速度ペナルティ,
                    'range_penalty': 航続距離ペナルティ
                }

        Raises:
            ValueError: 入力データが不正な場合
        """
        if not self.validate(hull):
            raise ValueError(f"船体データが不正です: {hull.id}")

        # 装備の総重量を計算
        total_equipment_weight = sum(e.weight for e in equipments)

        # 影響係数を計算
        weight_ratio = (total_equipment_weight / hull.weight
                       if hull.weight > 0 else 0.0)
        armor_factor = max(hull.armor_max, hull.armor_min) / 1000.0
        size_factor = hull.get_hull_area() / 10000.0

        # ペナルティを計算
        speed_penalty = self._calculate_speed_penalty(
            hull.max_speed, weight_ratio, armor_factor, size_factor
        )

        cruise_penalty = self._calculate_cruise_penalty(
            hull.cruise_speed, weight_ratio, armor_factor, size_factor
        )

        range_penalty = self._calculate_range_penalty(
            hull.naval_range, weight_ratio, armor_factor, size_factor
        )

        # 最終値を計算（負にならないように）
        new_speed = max(0.0, hull.max_speed - speed_penalty)
        new_cruise_speed = max(0.0, hull.cruise_speed - cruise_penalty)
        new_range = max(0.0, hull.naval_range - range_penalty)

        return {
            'new_speed': new_speed,
            'new_cruise_speed': new_cruise_speed,
            'new_range': new_range,
            'speed_penalty': speed_penalty,
            'cruise_penalty': cruise_penalty,
            'range_penalty': range_penalty,
            # デバッグ用情報
            'weight_ratio': weight_ratio,
            'armor_factor': armor_factor,
            'size_factor': size_factor,
            'total_equipment_weight': total_equipment_weight
        }

    def _calculate_speed_penalty(
        self,
        max_speed: float,
        weight_ratio: float,
        armor_factor: float,
        size_factor: float
    ) -> float:
        """速度ペナルティを計算

        Args:
            max_speed: 最大速度
            weight_ratio: 重量比率
            armor_factor: 装甲係数
            size_factor: サイズ係数

        Returns:
            float: 速度ペナルティ
        """
        penalty = max_speed * (
            weight_ratio * self.weight_factor +
            armor_factor +
            size_factor * 0.1
        )
        return penalty

    def _calculate_cruise_penalty(
        self,
        cruise_speed: float,
        weight_ratio: float,
        armor_factor: float,
        size_factor: float
    ) -> float:
        """巡航速度ペナルティを計算

        Args:
            cruise_speed: 巡航速度
            weight_ratio: 重量比率
            armor_factor: 装甲係数
            size_factor: サイズ係数

        Returns:
            float: 巡航速度ペナルティ
        """
        penalty = cruise_speed * (
            weight_ratio * self.weight_factor * 0.5 +
            armor_factor * 0.5 +
            size_factor * 0.05
        )
        return penalty

    def _calculate_range_penalty(
        self,
        naval_range: float,
        weight_ratio: float,
        armor_factor: float,
        size_factor: float
    ) -> float:
        """航続距離ペナルティを計算

        Args:
            naval_range: 航続距離
            weight_ratio: 重量比率
            armor_factor: 装甲係数
            size_factor: サイズ係数

        Returns:
            float: 航続距離ペナルティ
        """
        penalty = naval_range * (
            weight_ratio * self.range_factor +
            armor_factor * 0.5 +
            size_factor * 0.1
        )
        return penalty

    def validate(self, hull: Hull) -> bool:
        """入力データの妥当性を検証

        Args:
            hull: 船体エンティティ

        Returns:
            bool: データが妥当な場合True
        """
        # 船体エンティティの検証
        if not hull.validate():
            return False

        # 重量が正の値であることを確認
        if hull.weight <= 0:
            return False

        return True

    def get_dependencies(self) -> list:
        """依存する他の計算機のリスト

        Returns:
            list: 依存する計算機のクラス名リスト（なし）
        """
        return []

    def estimate_equipment_limit(self, hull: Hull, max_penalty_ratio: float = 0.2) -> float:
        """装備可能な最大重量を推定

        指定されたペナルティ比率を超えない装備重量の上限を計算します。

        Args:
            hull: 船体エンティティ
            max_penalty_ratio: 許容する最大ペナルティ比率（0.0-1.0）

        Returns:
            float: 装備可能な最大重量 (ton)
        """
        if hull.weight <= 0:
            return 0.0

        # 重量比率から装備重量を逆算
        # penalty_ratio ≈ weight_ratio * weight_factor
        # weight_ratio = equipment_weight / hull_weight
        # よって: equipment_weight = (penalty_ratio / weight_factor) * hull_weight

        if self.weight_factor <= 0:
            return hull.weight  # 無制限

        max_weight_ratio = max_penalty_ratio / self.weight_factor
        max_equipment_weight = max_weight_ratio * hull.weight

        return max_equipment_weight


# ヘルパー関数
def create_test_equipment(
    id: str = "TEST_EQUIPMENT_001",
    name: str = "テスト装備",
    weight: float = 100.0
) -> Equipment:
    """テスト用の装備を生成

    Args:
        id: 装備ID
        name: 装備名
        weight: 重量

    Returns:
        Equipment: テスト用装備
    """
    return Equipment(id=id, name=name, weight=weight)
