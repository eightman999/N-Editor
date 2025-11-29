# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: test_efficiency_factors効率係数テスト
"""効率係数値オブジェクトのユニットテスト

EngineEfficiencyFactors, EngineRangeFactors, ReductionFactorLimitsの
動作を検証するテストスイート。
"""

import unittest
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from domain.value_objects.efficiency_factors import (
    EngineEfficiencyFactors,
    EngineRangeFactors,
    ReductionFactorLimits,
    DEFAULT_EFFICIENCY_FACTORS,
    DEFAULT_RANGE_FACTORS,
    DEFAULT_REDUCTION_LIMITS
)


class TestEngineEfficiencyFactors(unittest.TestCase):
    """EngineEfficiencyFactorsのテストケース"""

    def setUp(self):
        """テストの前準備"""
        self.factors = EngineEfficiencyFactors()

    def test_default_values(self):
        """デフォルト値が正しく設定されているか"""
        self.assertEqual(self.factors.coal, 1.25)
        self.assertEqual(self.factors.heavy_oil, 1.0)
        self.assertEqual(self.factors.diesel, 0.77)
        self.assertEqual(self.factors.gas_turbine, 1.11)
        self.assertEqual(self.factors.nuclear, 0.1)

    def test_get_factor_coal(self):
        """石炭機関の効率係数取得"""
        factor = self.factors.get_factor('Coal')
        self.assertEqual(factor, 1.25)

    def test_get_factor_heavy_oil(self):
        """重油機関の効率係数取得"""
        factor = self.factors.get_factor('HeavyOil')
        self.assertEqual(factor, 1.0)

    def test_get_factor_diesel(self):
        """ディーゼル機関の効率係数取得"""
        factor = self.factors.get_factor('Diesel')
        self.assertEqual(factor, 0.77)

    def test_get_factor_nuclear(self):
        """原子炉の効率係数取得"""
        factor = self.factors.get_factor('Nuclear')
        self.assertEqual(factor, 0.1)

    def test_get_factor_unknown(self):
        """未知の機関種別の場合は標準値を返す"""
        factor = self.factors.get_factor('Unknown')
        self.assertEqual(factor, 1.0)  # 標準値（heavy_oil）

    def test_get_all_factors(self):
        """全ての効率係数を取得"""
        all_factors = self.factors.get_all_factors()

        self.assertIsInstance(all_factors, dict)
        self.assertEqual(len(all_factors), 8)  # 8種類の機関
        self.assertIn('Coal', all_factors)
        self.assertIn('Diesel', all_factors)
        self.assertIn('Nuclear', all_factors)

    def test_is_valid_engine_type(self):
        """有効な機関種別の判定"""
        self.assertTrue(self.factors.is_valid_engine_type('Coal'))
        self.assertTrue(self.factors.is_valid_engine_type('Diesel'))
        self.assertFalse(self.factors.is_valid_engine_type('Unknown'))
        self.assertFalse(self.factors.is_valid_engine_type(''))

    def test_immutability(self):
        """イミュータブル性の確認（変更不可）"""
        with self.assertRaises(Exception):  # FrozenInstanceError
            self.factors.coal = 2.0

    def test_default_instance(self):
        """デフォルトインスタンスが使用可能"""
        self.assertIsNotNone(DEFAULT_EFFICIENCY_FACTORS)
        self.assertEqual(DEFAULT_EFFICIENCY_FACTORS.diesel, 0.77)


class TestEngineRangeFactors(unittest.TestCase):
    """EngineRangeFactorsのテストケース"""

    def setUp(self):
        """テストの前準備"""
        self.factors = EngineRangeFactors()

    def test_default_values(self):
        """デフォルト値が正しく設定されているか"""
        self.assertEqual(self.factors.coal, 0.8)
        self.assertEqual(self.factors.heavy_oil, 1.0)
        self.assertEqual(self.factors.diesel, 1.3)
        self.assertEqual(self.factors.nuclear, 10.0)

    def test_get_factor_diesel(self):
        """ディーゼル機関の航続距離係数取得"""
        factor = self.factors.get_factor('Diesel')
        self.assertEqual(factor, 1.3)

    def test_get_factor_nuclear(self):
        """原子炉の航続距離係数取得（超長距離）"""
        factor = self.factors.get_factor('Nuclear')
        self.assertEqual(factor, 10.0)

    def test_get_factor_unknown(self):
        """未知の機関種別の場合は標準値を返す"""
        factor = self.factors.get_factor('Unknown')
        self.assertEqual(factor, 1.0)

    def test_diesel_better_than_coal(self):
        """ディーゼルが石炭より航続距離が長いことを確認"""
        diesel_factor = self.factors.get_factor('Diesel')
        coal_factor = self.factors.get_factor('Coal')
        self.assertGreater(diesel_factor, coal_factor)

    def test_default_instance(self):
        """デフォルトインスタンスが使用可能"""
        self.assertIsNotNone(DEFAULT_RANGE_FACTORS)
        self.assertEqual(DEFAULT_RANGE_FACTORS.diesel, 1.3)


class TestReductionFactorLimits(unittest.TestCase):
    """ReductionFactorLimitsのテストケース"""

    def setUp(self):
        """テストの前準備"""
        self.limits = ReductionFactorLimits()

    def test_default_values(self):
        """デフォルト値が正しく設定されているか"""
        self.assertEqual(self.limits.max_area, 25000.0)
        self.assertEqual(self.limits.max_displacement, 50000.0)
        self.assertEqual(self.limits.max_size_reduction, 0.3)
        self.assertEqual(self.limits.max_weight_reduction, 0.2)
        self.assertEqual(self.limits.total_max_reduction, 0.5)

    def test_is_within_limits_small_ship(self):
        """小型艦（駆逐艦）が限界値内であることを確認"""
        area = 1000.0  # 100m × 10m = 1,000 m²
        displacement = 2000.0  # 2,000 ton

        self.assertTrue(self.limits.is_within_limits(area, displacement))

    def test_is_within_limits_battleship(self):
        """戦艦クラスが限界値内であることを確認"""
        area = 8000.0  # 250m × 32m = 8,000 m²
        displacement = 40000.0  # 40,000 ton

        self.assertTrue(self.limits.is_within_limits(area, displacement))

    def test_is_within_limits_超戦艦(self):
        """超戦艦（大和型）が限界値ギリギリ"""
        area = 24999.0
        displacement = 49999.0

        self.assertTrue(self.limits.is_within_limits(area, displacement))

    def test_exceeds_area_limit(self):
        """面積が限界値を超える場合"""
        area = 30000.0  # 限界値超過
        displacement = 40000.0

        self.assertFalse(self.limits.is_within_limits(area, displacement))

    def test_exceeds_displacement_limit(self):
        """排水量が限界値を超える場合"""
        area = 20000.0
        displacement = 60000.0  # 限界値超過

        self.assertFalse(self.limits.is_within_limits(area, displacement))

    def test_reduction_limits_sanity(self):
        """軽減率の妥当性チェック"""
        # 総合軽減率が個別軽減率の合計を超えないこと
        self.assertLessEqual(
            self.limits.max_size_reduction + self.limits.max_weight_reduction,
            self.limits.total_max_reduction + 0.1  # 若干のマージン
        )

        # 軽減率が0-1の範囲内
        self.assertGreaterEqual(self.limits.max_size_reduction, 0)
        self.assertLessEqual(self.limits.max_size_reduction, 1)
        self.assertGreaterEqual(self.limits.total_max_reduction, 0)
        self.assertLessEqual(self.limits.total_max_reduction, 1)

    def test_default_instance(self):
        """デフォルトインスタンスが使用可能"""
        self.assertIsNotNone(DEFAULT_REDUCTION_LIMITS)
        self.assertEqual(DEFAULT_REDUCTION_LIMITS.max_area, 25000.0)


class TestEfficiencyFactorsIntegration(unittest.TestCase):
    """効率係数間の整合性テスト"""

    def test_diesel_is_most_efficient(self):
        """ディーゼルが最も燃費効率が良いことを確認"""
        eff = EngineEfficiencyFactors()

        diesel_factor = eff.get_factor('Diesel')
        coal_factor = eff.get_factor('Coal')
        heavy_oil_factor = eff.get_factor('HeavyOil')

        # ディーゼルの効率係数が最も小さい（=燃費が良い）
        self.assertLess(diesel_factor, coal_factor)
        self.assertLess(diesel_factor, heavy_oil_factor)

    def test_nuclear_is_best_range(self):
        """原子炉が最も航続距離が長いことを確認"""
        range_factors = EngineRangeFactors()

        nuclear_range = range_factors.get_factor('Nuclear')

        # 全ての機関種別より長距離
        for engine_type in ['Coal', 'HeavyOil', 'Diesel', 'GasTurbine']:
            other_range = range_factors.get_factor(engine_type)
            self.assertGreater(nuclear_range, other_range)

    def test_consistency_between_efficiency_and_range(self):
        """効率と航続距離の一貫性確認"""
        eff = EngineEfficiencyFactors()
        rng = EngineRangeFactors()

        # ディーゼル：効率良い → 航続距離長い
        diesel_eff = eff.get_factor('Diesel')
        diesel_rng = rng.get_factor('Diesel')
        heavy_oil_eff = eff.get_factor('HeavyOil')
        heavy_oil_rng = rng.get_factor('HeavyOil')

        # ディーゼルは重油より効率が良く、航続距離も長い
        self.assertLess(diesel_eff, heavy_oil_eff)
        self.assertGreater(diesel_rng, heavy_oil_rng)


if __name__ == '__main__':
    unittest.main()
