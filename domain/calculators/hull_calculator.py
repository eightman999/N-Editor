# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: hull_calculator船体性能計算機
"""船体性能計算機

船体と機関を組み合わせた性能を計算する計算機。
"""

from typing import Dict, Any, Optional
from .base import PerformanceCalculator
from ..entities.hull import Hull
from ..value_objects.efficiency_factors import (
    EngineEfficiencyFactors,
    DEFAULT_EFFICIENCY_FACTORS
)


class HullPerformanceCalculator(PerformanceCalculator):
    """船体性能計算機

    船体の基本性能と機関データを組み合わせて、
    実際の性能値（速度、航続距離、燃料容量等）を計算します。

    Attributes:
        efficiency_factors: 機関効率係数
    """

    def __init__(self, efficiency_factors: Optional[EngineEfficiencyFactors] = None):
        """初期化

        Args:
            efficiency_factors: 機関効率係数（省略時はデフォルト値）
        """
        self.efficiency_factors = efficiency_factors or DEFAULT_EFFICIENCY_FACTORS

    def calculate(self, hull: Hull, engine_data: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """船体+機関の統合性能を計算

        Args:
            hull: 船体エンティティ
            engine_data: 機関データ（オプション）
                {
                    'engine_type': 'HeavyOil',  # 機関種別
                    'power': 50000.0,           # 出力 (hp)
                    'fuel_capacity': 0.0        # 燃料容量 (ton)
                }

        Returns:
            Dict[str, float]: 計算された性能データ
                {
                    'max_speed': 最大速度,
                    'cruise_speed': 巡航速度,
                    'naval_range': 航続距離,
                    'fuel_capacity': 燃料容量,
                    'display_speed': 表示用速度
                }

        Raises:
            ValueError: 入力データが不正な場合
        """
        if not self.validate(hull):
            raise ValueError(f"船体データが不正です: {hull.id}")

        # 基本性能を取得
        performance = {
            'max_speed': hull.max_speed,
            'cruise_speed': hull.cruise_speed,
            'naval_range': hull.naval_range,
            'fuel_capacity': hull.fuel_capacity
        }

        # 機関データがある場合は効果を適用
        if engine_data:
            performance = self._apply_engine_effects(performance, engine_data, hull)

        # 表示速度の計算
        performance['display_speed'] = self._calculate_display_speed(performance)

        return performance

    def _apply_engine_effects(
        self,
        base_performance: Dict[str, float],
        engine_data: Dict[str, Any],
        hull: Hull
    ) -> Dict[str, float]:
        """機関による性能影響を適用

        Args:
            base_performance: 基本性能
            engine_data: 機関データ
            hull: 船体エンティティ

        Returns:
            Dict[str, float]: 機関効果適用後の性能
        """
        result = base_performance.copy()

        # 機関データから値を取得
        engine_type = engine_data.get('engine_type', 'HeavyOil')
        engine_power = engine_data.get('power', 0.0)
        fuel_capacity = engine_data.get('fuel_capacity', result['fuel_capacity'])

        # 燃料容量が0の場合は航続距離と巡航速度から逆算
        if fuel_capacity == 0.0 and result['naval_range'] > 0 and result['cruise_speed'] > 0:
            efficiency_factor = self.efficiency_factors.get_factor(engine_type)
            fuel_capacity = (
                result['naval_range'] *
                result['cruise_speed'] *
                efficiency_factor
            ) / 100.0

            result['fuel_capacity'] = fuel_capacity

        return result

    def _calculate_display_speed(self, performance: Dict[str, float]) -> float:
        """表示用速度を計算

        航続距離と巡航速度から表示用の速度を計算します。

        Args:
            performance: 性能データ

        Returns:
            float: 表示用速度
        """
        naval_range = performance.get('naval_range', 0.0)
        cruise_speed = performance.get('cruise_speed', 0.0)
        max_speed = performance.get('max_speed', 0.0)

        if naval_range > 0 and cruise_speed > 0:
            # 航続距離を適切にスケールして速度単位に合わせる
            range_speed_component = naval_range / 100.0
            display_speed = (range_speed_component + cruise_speed) / 2.0
        else:
            display_speed = max_speed

        return display_speed

    def validate(self, hull: Hull) -> bool:
        """入力データの妥当性を検証

        Args:
            hull: 船体エンティティ

        Returns:
            bool: データが妥当な場合True
        """
        # 船体エンティティ自体の検証
        if not hull.validate():
            return False

        # 性能計算に必要な値のチェック
        if hull.max_speed < 0:
            return False
        if hull.naval_range < 0:
            return False
        if hull.weight <= 0:
            return False

        return True

    def get_dependencies(self) -> list:
        """依存する他の計算機のリスト

        Returns:
            list: 依存する計算機のクラス名リスト（なし）
        """
        return []

    def calculate_fuel_consumption(
        self,
        hull: Hull,
        engine_type: str = 'HeavyOil',
        cruising: bool = True
    ) -> float:
        """燃料消費量を計算

        Args:
            hull: 船体エンティティ
            engine_type: 機関種別
            cruising: 巡航速度での計算かどうか

        Returns:
            float: 燃料消費量 (ton/hour)
        """
        efficiency_factor = self.efficiency_factors.get_factor(engine_type)

        if cruising:
            # 巡航速度での消費
            base_consumption = hull.cruise_speed * hull.weight / 100000.0
        else:
            # 最大速度での消費
            base_consumption = hull.max_speed * hull.weight / 100000.0

        return base_consumption * efficiency_factor

    def calculate_operational_range(
        self,
        hull: Hull,
        engine_type: str = 'HeavyOil',
        fuel_load: Optional[float] = None
    ) -> float:
        """運用航続距離を計算

        Args:
            hull: 船体エンティティ
            engine_type: 機関種別
            fuel_load: 燃料搭載量 (ton)（省略時は満載）

        Returns:
            float: 運用航続距離 (nautical miles)
        """
        if fuel_load is None:
            fuel_load = hull.fuel_capacity

        if fuel_load <= 0 or hull.cruise_speed <= 0:
            return 0.0

        # 燃料消費率を計算
        consumption_rate = self.calculate_fuel_consumption(
            hull, engine_type, cruising=True
        )

        if consumption_rate <= 0:
            return hull.naval_range  # デフォルト値を返す

        # 航続時間を計算
        endurance_hours = fuel_load / consumption_rate

        # 航続距離を計算
        operational_range = hull.cruise_speed * endurance_hours

        return operational_range
