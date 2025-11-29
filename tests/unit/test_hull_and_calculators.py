# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: test_hull_and_calculators船体・計算機統合テスト
"""船体エンティティと計算機の統合ユニットテスト

Hull, HullPerformanceCalculator, EquipmentEffectCalculatorの
動作を検証するテストスイート。
"""

import unittest
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from domain.entities.hull import Hull, create_test_hull
from domain.calculators.hull_calculator import HullPerformanceCalculator
from domain.calculators.equipment_calculator import (
    EquipmentEffectCalculator,
    Equipment,
    create_test_equipment
)


class TestHullEntity(unittest.TestCase):
    """船体エンティティのテストケース"""

    def setUp(self):
        """テストの前準備"""
        self.hull = create_test_hull()

    def test_hull_creation(self):
        """船体エンティティの作成"""
        self.assertEqual(self.hull.id, "TEST_HULL_001")
        self.assertEqual(self.hull.name, "テスト艦級")
        self.assertEqual(self.hull.archetype, "DD")
        self.assertEqual(self.hull.weight, 2000.0)

    def test_hull_validation(self):
        """船体の妥当性検証"""
        self.assertTrue(self.hull.validate())

    def test_hull_invalid_id(self):
        """無効なIDでの作成"""
        with self.assertRaises(ValueError):
            Hull(id="", name="テスト")

    def test_hull_area_calculation(self):
        """船体面積の計算"""
        area = self.hull.get_hull_area()
        expected = 100.0 * 10.0  # length × width
        self.assertEqual(area, expected)

    def test_hull_displacement(self):
        """排水量の取得"""
        displacement = self.hull.get_displacement()
        self.assertEqual(displacement, 2000.0)

    def test_armor_average(self):
        """平均装甲厚の計算"""
        avg = self.hull.get_armor_average()
        expected = (50.0 + 20.0) / 2  # (armor_max + armor_min) / 2
        self.assertEqual(avg, expected)

    def test_is_large_ship(self):
        """大型艦判定"""
        self.assertFalse(self.hull.is_large_ship())  # 2000ton

        battleship = create_test_hull(weight=40000.0)
        self.assertTrue(battleship.is_large_ship())

    def test_is_fast_ship(self):
        """高速艦判定"""
        self.assertTrue(self.hull.is_fast_ship())  # 35kt

        slow_ship = create_test_hull(max_speed=20.0)
        self.assertFalse(slow_ship.is_fast_ship())

    def test_ship_class_category(self):
        """艦級カテゴリの判定"""
        self.assertEqual(self.hull.get_ship_class_category(), "中型艦")

        small = create_test_hull(weight=1000.0)
        self.assertEqual(small.get_ship_class_category(), "小型艦")

        large = create_test_hull(weight=25000.0)
        self.assertEqual(large.get_ship_class_category(), "大型艦")

        super_large = create_test_hull(weight=50000.0)
        self.assertEqual(super_large.get_ship_class_category(), "超大型艦")

    def test_to_dict(self):
        """辞書への変換"""
        data = self.hull.to_dict()
        self.assertIsInstance(data, dict)
        self.assertEqual(data['id'], "TEST_HULL_001")
        self.assertEqual(data['weight'], 2000.0)

    def test_from_dict(self):
        """辞書からの生成"""
        data = self.hull.to_dict()
        hull2 = Hull.from_dict(data)
        self.assertEqual(hull2.id, self.hull.id)
        self.assertEqual(hull2.weight, self.hull.weight)

    def test_clone(self):
        """複製"""
        hull2 = self.hull.clone()
        self.assertEqual(hull2.id, self.hull.id)
        self.assertIsNot(hull2, self.hull)  # 別のインスタンス

    def test_equality(self):
        """等価性比較"""
        hull2 = Hull.from_dict(self.hull.to_dict())
        self.assertEqual(self.hull, hull2)  # IDが同じなので等価

        hull3 = create_test_hull(id="DIFFERENT_ID")
        self.assertNotEqual(self.hull, hull3)  # IDが異なるので不等


class TestHullPerformanceCalculator(unittest.TestCase):
    """船体性能計算機のテストケース"""

    def setUp(self):
        """テストの前準備"""
        self.calculator = HullPerformanceCalculator()
        self.hull = create_test_hull()

    def test_basic_calculation(self):
        """基本的な性能計算"""
        result = self.calculator.calculate(self.hull)

        self.assertEqual(result['max_speed'], 35.0)
        self.assertEqual(result['cruise_speed'], 18.0)
        self.assertEqual(result['naval_range'], 5000.0)

    def test_fuel_capacity_reverse_calculation(self):
        """燃料容量の逆算"""
        # 燃料容量0の船体を作成
        hull = create_test_hull(fuel_capacity=0.0)
        engine_data = {
            'engine_type': 'HeavyOil',
            'power': 50000.0
        }

        result = self.calculator.calculate(hull, engine_data)

        # 燃料容量が逆算されているか
        self.assertGreater(result['fuel_capacity'], 0)
        # 期待値: (5000 * 18 * 1.0) / 100 = 900
        self.assertAlmostEqual(result['fuel_capacity'], 900.0, places=1)

    def test_diesel_engine_efficiency(self):
        """ディーゼル機関の効率計算"""
        hull = create_test_hull(fuel_capacity=0.0)
        engine_data = {
            'engine_type': 'Diesel',
            'power': 50000.0
        }

        result = self.calculator.calculate(hull, engine_data)

        # ディーゼルは効率が良いので燃料容量が少ない
        # 期待値: (5000 * 18 * 0.77) / 100 = 693
        self.assertAlmostEqual(result['fuel_capacity'], 693.0, places=1)

    def test_nuclear_engine_efficiency(self):
        """原子炉の超高効率"""
        hull = create_test_hull(fuel_capacity=0.0)
        engine_data = {
            'engine_type': 'Nuclear',
            'power': 100000.0
        }

        result = self.calculator.calculate(hull, engine_data)

        # 原子炉は超効率（0.1）
        # 期待値: (5000 * 18 * 0.1) / 100 = 90
        self.assertAlmostEqual(result['fuel_capacity'], 90.0, places=1)

    def test_display_speed_calculation(self):
        """表示速度の計算"""
        result = self.calculator.calculate(self.hull)

        # 航続距離と巡航速度から計算
        # (5000/100 + 18) / 2 = (50 + 18) / 2 = 34
        expected = (5000.0 / 100.0 + 18.0) / 2.0
        self.assertAlmostEqual(result['display_speed'], expected, places=1)

    def test_validation(self):
        """入力検証"""
        self.assertTrue(self.calculator.validate(self.hull))

        # 無効な船体
        invalid_hull = create_test_hull(weight=-100.0)
        self.assertFalse(self.calculator.validate(invalid_hull))

    def test_fuel_consumption(self):
        """燃料消費量の計算"""
        consumption = self.calculator.calculate_fuel_consumption(
            self.hull, 'HeavyOil', cruising=True
        )
        self.assertGreater(consumption, 0)

    def test_operational_range(self):
        """運用航続距離の計算"""
        operational_range = self.calculator.calculate_operational_range(
            self.hull, 'HeavyOil'
        )
        self.assertGreater(operational_range, 0)


class TestEquipmentEffectCalculator(unittest.TestCase):
    """装備影響計算機のテストケース"""

    def setUp(self):
        """テストの前準備"""
        self.calculator = EquipmentEffectCalculator()
        self.hull = create_test_hull()

    def test_no_equipment(self):
        """装備なしの場合"""
        result = self.calculator.calculate(self.hull, [])

        # 装備はないが、装甲とサイズによる基本ペナルティがある
        # 装備重量0でもarmor_factorとsize_factorは計算される
        self.assertLessEqual(result['new_speed'], self.hull.max_speed)
        self.assertLessEqual(result['new_cruise_speed'], self.hull.cruise_speed)
        self.assertLessEqual(result['new_range'], self.hull.naval_range)

        # 装備重量比率は0であることを確認
        self.assertEqual(result['weight_ratio'], 0.0)

    def test_light_equipment(self):
        """軽装備の場合"""
        equipments = [
            create_test_equipment(weight=50.0),
            create_test_equipment(weight=50.0)
        ]

        result = self.calculator.calculate(self.hull, equipments)

        # 軽微なペナルティ
        self.assertLess(result['new_speed'], self.hull.max_speed)
        self.assertGreater(result['new_speed'], self.hull.max_speed * 0.9)

    def test_heavy_equipment(self):
        """重装備の場合"""
        equipments = [
            create_test_equipment(weight=500.0),  # 重い装備
            create_test_equipment(weight=500.0)
        ]

        result = self.calculator.calculate(self.hull, equipments)

        # 顕著なペナルティ
        self.assertLess(result['new_speed'], self.hull.max_speed)
        self.assertLess(result['new_cruise_speed'], self.hull.cruise_speed)
        self.assertLess(result['new_range'], self.hull.naval_range)

    def test_penalty_details(self):
        """ペナルティの詳細情報"""
        equipments = [create_test_equipment(weight=200.0)]
        result = self.calculator.calculate(self.hull, equipments)

        # ペナルティ情報が含まれているか
        self.assertIn('speed_penalty', result)
        self.assertIn('cruise_penalty', result)
        self.assertIn('range_penalty', result)
        self.assertIn('weight_ratio', result)

    def test_validation(self):
        """入力検証"""
        self.assertTrue(self.calculator.validate(self.hull))

        # 重量0の船体は無効
        invalid_hull = create_test_hull(weight=0.0)
        self.assertFalse(self.calculator.validate(invalid_hull))

    def test_equipment_limit_estimation(self):
        """装備可能重量の推定"""
        max_weight = self.calculator.estimate_equipment_limit(
            self.hull, max_penalty_ratio=0.1
        )

        self.assertGreater(max_weight, 0)
        # 船体重量の一定割合以下
        self.assertLess(max_weight, self.hull.weight)


class TestIntegration(unittest.TestCase):
    """統合テスト"""

    def test_complete_workflow(self):
        """完全なワークフロー"""
        # 1. 船体作成
        hull = create_test_hull(
            id="IJN_FUBUKI",
            name="吹雪型駆逐艦",
            weight=2000.0,
            max_speed=38.0,
            cruise_speed=18.0,
            naval_range=5000.0,
            fuel_capacity=0.0
        )

        # 2. 船体性能計算
        hull_calc = HullPerformanceCalculator()
        engine_data = {'engine_type': 'HeavyOil', 'power': 50000.0}
        base_performance = hull_calc.calculate(hull, engine_data)

        self.assertGreater(base_performance['fuel_capacity'], 0)

        # 3. 装備影響計算
        equipment_calc = EquipmentEffectCalculator()
        equipments = [
            Equipment(id="GUN_01", name="12.7cm砲", weight=20.0),
            Equipment(id="GUN_02", name="12.7cm砲", weight=20.0),
            Equipment(id="TORPEDO", name="魚雷発射管", weight=30.0)
        ]

        equipment_effect = equipment_calc.calculate(hull, equipments)

        # 装備により性能が低下していることを確認
        self.assertLess(equipment_effect['new_speed'], hull.max_speed)
        self.assertGreater(equipment_effect['new_speed'], 0)


if __name__ == '__main__':
    unittest.main()
