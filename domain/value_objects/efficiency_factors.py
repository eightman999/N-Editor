# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: efficiency_factors効率係数値オブジェクト
"""機関効率係数の値オブジェクト

機関種別ごとの燃料消費効率係数を定義します。
イミュータブルな値オブジェクトとして実装されています。
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class EngineEfficiencyFactors:
    """機関効率係数（イミュータブル）

    各機関種別の燃料消費効率を表す係数。
    値が大きいほど燃料消費が多い（効率が悪い）。

    Attributes:
        coal: 石炭機関の効率係数（1.25 = 燃料消費25%増）
        heavy_oil: 重油機関の効率係数（1.0 = 標準）
        diesel: ディーゼル機関の効率係数（0.77 = 燃料消費23%減）
        gas_turbine: ガスタービン機関の効率係数
        coal_heavy_oil: 石炭重油混燃機関の効率係数
        diesel_gas: ディーゼルガス混燃機関の効率係数
        battery: バッテリー機関の効率係数
        nuclear: 原子炉の効率係数（0.1 = 超高効率）
    """

    coal: float = 1.25              # 石炭（燃料消費多）
    heavy_oil: float = 1.0          # 重油（標準）
    diesel: float = 0.77            # ディーゼル（効率良）
    gas_turbine: float = 1.11       # ガスタービン（やや消費多）
    coal_heavy_oil: float = 1.05    # 石炭重油混燃
    diesel_gas: float = 0.83        # ディーゼルガス混燃
    battery: float = 1.67           # バッテリー（容量制約）
    nuclear: float = 0.1            # 原子炉（超高効率）

    def get_factor(self, engine_type: str) -> float:
        """機関種別から効率係数を取得

        Args:
            engine_type: 機関種別文字列
                       （例: "Coal", "HeavyOil", "Diesel"）

        Returns:
            float: 効率係数（該当なしの場合は標準値1.0）
        """
        mapping = {
            'Coal': self.coal,
            'HeavyOil': self.heavy_oil,
            'Diesel': self.diesel,
            'GasTurbine': self.gas_turbine,
            'CoalHeavyOil': self.coal_heavy_oil,
            'DieselGas': self.diesel_gas,
            'Battery': self.battery,
            'Nuclear': self.nuclear
        }
        return mapping.get(engine_type, self.heavy_oil)

    def get_all_factors(self) -> Dict[str, float]:
        """全ての効率係数を辞書で取得

        Returns:
            Dict[str, float]: 機関種別と効率係数のマッピング
        """
        return {
            'Coal': self.coal,
            'HeavyOil': self.heavy_oil,
            'Diesel': self.diesel,
            'GasTurbine': self.gas_turbine,
            'CoalHeavyOil': self.coal_heavy_oil,
            'DieselGas': self.diesel_gas,
            'Battery': self.battery,
            'Nuclear': self.nuclear
        }

    def is_valid_engine_type(self, engine_type: str) -> bool:
        """機関種別が有効かチェック

        Args:
            engine_type: 機関種別文字列

        Returns:
            bool: 有効な機関種別の場合True
        """
        return engine_type in self.get_all_factors()


@dataclass(frozen=True)
class EngineRangeFactors:
    """機関種別ごとの航続距離効率係数（イミュータブル）

    各機関種別の航続距離に対する影響を表す係数。
    値が大きいほど航続距離が長くなる。

    Attributes:
        coal: 石炭機関の航続距離係数
        heavy_oil: 重油機関の航続距離係数
        diesel: ディーゼル機関の航続距離係数
        gas_turbine: ガスタービン機関の航続距離係数
        coal_heavy_oil: 石炭重油混燃機関の航続距離係数
        diesel_gas: ディーゼルガス混燃機関の航続距離係数
        battery: バッテリー機関の航続距離係数
        nuclear: 原子炉の航続距離係数
    """

    coal: float = 0.8               # 石炭（航続距離短）
    heavy_oil: float = 1.0          # 重油（標準）
    diesel: float = 1.3             # ディーゼル（航続距離長）
    gas_turbine: float = 0.9        # ガスタービン（やや短）
    coal_heavy_oil: float = 0.95    # 石炭重油混燃
    diesel_gas: float = 1.2         # ディーゼルガス混燃
    battery: float = 0.6            # バッテリー（航続距離短）
    nuclear: float = 10.0           # 原子炉（超長距離）

    def get_factor(self, engine_type: str) -> float:
        """機関種別から航続距離係数を取得

        Args:
            engine_type: 機関種別文字列

        Returns:
            float: 航続距離係数（該当なしの場合は標準値1.0）
        """
        mapping = {
            'Coal': self.coal,
            'HeavyOil': self.heavy_oil,
            'Diesel': self.diesel,
            'GasTurbine': self.gas_turbine,
            'CoalHeavyOil': self.coal_heavy_oil,
            'DieselGas': self.diesel_gas,
            'Battery': self.battery,
            'Nuclear': self.nuclear
        }
        return mapping.get(engine_type, self.heavy_oil)


@dataclass(frozen=True)
class ReductionFactorLimits:
    """性能軽減係数の限界値（イミュータブル）

    船体サイズ・重量による装備コスト軽減の限界値を定義します。

    Attributes:
        max_area: 軽減効果が最大になる船体面積 (m²)
        max_displacement: 軽減効果が最大になる排水量 (ton)
        max_size_reduction: サイズによる最大軽減率
        max_weight_reduction: 重量による最大軽減率
        total_max_reduction: 総合的な最大軽減率
    """

    max_area: float = 25000.0           # 25,000 m² (超大型戦艦クラス)
    max_displacement: float = 50000.0   # 50,000 ton (大和型クラス)
    max_size_reduction: float = 0.3     # 最大30%軽減
    max_weight_reduction: float = 0.2   # 最大20%軽減
    total_max_reduction: float = 0.5    # 総合最大50%軽減

    def is_within_limits(self, area: float, displacement: float) -> bool:
        """指定された値が限界値内かチェック

        Args:
            area: 船体面積 (m²)
            displacement: 排水量 (ton)

        Returns:
            bool: 両方とも限界値以下の場合True
        """
        return area <= self.max_area and displacement <= self.max_displacement


# デフォルトインスタンス（シングルトンとして使用可能）
DEFAULT_EFFICIENCY_FACTORS = EngineEfficiencyFactors()
DEFAULT_RANGE_FACTORS = EngineRangeFactors()
DEFAULT_REDUCTION_LIMITS = ReductionFactorLimits()
