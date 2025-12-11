# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: test_hull_performance_service サービス層テスト
"""HullPerformanceServiceのユニットテスト

サービス層の動作を検証するテストスイート。
"""

import unittest
import sys
import os
import tempfile
import shutil
import csv

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from domain.services.hull_performance_service import HullPerformanceService
from domain.services.base_service import ValidationError, NotFoundError
from infrastructure.repositories.hull_repository import HullRepository
from domain.entities.hull import Hull, create_test_hull


class TestHullPerformanceService(unittest.TestCase):
    """HullPerformanceServiceのテストケース"""

    def setUp(self):
        """テストの前準備"""
        # 一時ディレクトリを作成
        self.test_dir = tempfile.mkdtemp()
        self.repository = HullRepository(self.test_dir)
        self.service = HullPerformanceService(self.repository)

    def tearDown(self):
        """テストの後処理"""
        # 一時ディレクトリを削除
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    # ========== 船体管理テスト ==========

    def test_save_and_get_hull(self):
        """船体の保存と取得"""
        hull = create_test_hull(id='TEST_001', name='テスト艦')

        # 保存
        result = self.service.save_hull(hull)
        self.assertTrue(result)

        # 取得
        retrieved = self.service.get_hull('TEST_001')
        self.assertEqual(retrieved.id, 'TEST_001')
        self.assertEqual(retrieved.name, 'テスト艦')

    def test_get_nonexistent_hull_raises_error(self):
        """存在しない船体の取得でエラー"""
        with self.assertRaises(NotFoundError):
            self.service.get_hull('NONEXISTENT')

    def test_save_invalid_hull_raises_error(self):
        """無効な船体の保存でエラー"""
        # 無効な年代
        invalid_hull = create_test_hull(year=999)

        with self.assertRaises(ValidationError):
            self.service.save_hull(invalid_hull)

    def test_get_all_hulls(self):
        """全船体の取得"""
        # 3隻保存
        for i in range(3):
            hull = create_test_hull(id=f'TEST_{i}')
            self.service.save_hull(hull)

        # 全取得
        hulls = self.service.get_all_hulls()
        self.assertEqual(len(hulls), 3)

    def test_get_all_hulls_with_filter(self):
        """フィルタ条件での船体取得"""
        # 異なる国の船体を保存
        hulls_to_save = [
            create_test_hull(id='JPN_001', country='JPN'),
            create_test_hull(id='JPN_002', country='JPN'),
            create_test_hull(id='USA_001', country='USA'),
        ]

        for hull in hulls_to_save:
            self.service.save_hull(hull)

        # 日本艦のみ取得
        jpn_hulls = self.service.get_all_hulls({'country': 'JPN'})
        self.assertEqual(len(jpn_hulls), 2)
        for hull in jpn_hulls:
            self.assertEqual(hull.country, 'JPN')

    def test_delete_hull(self):
        """船体の削除"""
        hull = create_test_hull(id='DELETE_TEST')
        self.service.save_hull(hull)

        # 削除
        result = self.service.delete_hull('DELETE_TEST')
        self.assertTrue(result)

        # 存在しない
        self.assertFalse(self.service.hull_exists('DELETE_TEST'))

    def test_hull_exists(self):
        """船体の存在確認"""
        hull = create_test_hull(id='EXISTS_TEST')

        # 保存前は存在しない
        self.assertFalse(self.service.hull_exists('EXISTS_TEST'))

        # 保存後は存在する
        self.service.save_hull(hull)
        self.assertTrue(self.service.hull_exists('EXISTS_TEST'))

    # ========== 性能計算テスト ==========

    def test_calculate_hull_performance_basic(self):
        """基本的な船体性能計算"""
        hull = create_test_hull(
            id='PERF_TEST',
            max_speed=35.0,
            cruise_speed=18.0,
            naval_range=5000.0,
            fuel_capacity=500.0
        )
        self.service.save_hull(hull)

        # 性能計算
        performance = self.service.calculate_hull_performance('PERF_TEST')

        self.assertIn('max_speed', performance)
        self.assertEqual(performance['max_speed'], 35.0)
        self.assertEqual(performance['cruise_speed'], 18.0)
        self.assertEqual(performance['naval_range'], 5000.0)

    def test_calculate_hull_performance_with_engine(self):
        """機関データ付き性能計算"""
        hull = create_test_hull(
            id='ENGINE_TEST',
            max_speed=35.0,
            cruise_speed=18.0,
            naval_range=5000.0,
            fuel_capacity=0.0  # 燃料容量は逆算
        )
        self.service.save_hull(hull)

        # 機関データ
        engine_data = {
            'engine_type': 'Diesel',
            'power': 50000
        }

        # 性能計算
        performance = self.service.calculate_hull_performance('ENGINE_TEST', engine_data)

        self.assertIn('fuel_capacity', performance)
        self.assertGreater(performance['fuel_capacity'], 0.0)
        self.assertIn('display_speed', performance)

    def test_calculate_equipment_effect(self):
        """装備効果計算"""
        hull = create_test_hull(
            id='EQUIP_TEST',
            max_speed=35.0,
            weight=2000.0,
            length=100.0,
            width=10.0
        )
        self.service.save_hull(hull)

        # 装備データ
        equipment = [
            {'weight': 100.0, 'type': 'main_gun'},
            {'weight': 50.0, 'type': 'secondary_gun'}
        ]

        # 装備効果計算
        result = self.service.calculate_equipment_effect('EQUIP_TEST', equipment)

        self.assertIn('new_speed', result)
        self.assertIn('speed_penalty', result)
        self.assertIn('total_equipment_weight', result)

    def test_calculate_complete_performance(self):
        """完全な性能計算（船体+機関+装備）"""
        hull = create_test_hull(
            id='COMPLETE_TEST',
            max_speed=35.0,
            cruise_speed=18.0,
            naval_range=5000.0,
            weight=2000.0
        )
        self.service.save_hull(hull)

        # 機関データ
        engine_data = {
            'engine_type': 'Diesel',
            'power': 50000
        }

        # 装備データ
        equipment = [
            {'weight': 100.0, 'type': 'main_gun'}
        ]

        # 完全計算
        performance = self.service.calculate_complete_performance(
            'COMPLETE_TEST',
            engine_data,
            equipment
        )

        # 船体性能
        self.assertIn('max_speed', performance)
        self.assertIn('fuel_capacity', performance)

        # 装備効果
        self.assertIn('equipment_effect', performance)
        self.assertIn('final_speed', performance)

    def test_calculate_performance_for_nonexistent_hull(self):
        """存在しない船体の性能計算でエラー"""
        with self.assertRaises(NotFoundError):
            self.service.calculate_hull_performance('NONEXISTENT')

    # ========== CSV操作テスト ==========

    def test_import_from_csv(self):
        """CSVからのインポート"""
        # テストCSVファイルを作成
        csv_path = os.path.join(self.test_dir, 'test_import.csv')

        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'システム名称', '艦級名', 'weight', 'speed'
            ])
            writer.writeheader()

            writer.writerow({
                'システム名称': 'IMPORT_001',
                '艦級名': 'インポート艦1',
                'weight': '1000',
                'speed': '30'
            })

            writer.writerow({
                'システム名称': 'IMPORT_002',
                '艦級名': 'インポート艦2',
                'weight': '2000',
                'speed': '32'
            })

        # インポート
        count = self.service.import_from_csv(csv_path)

        self.assertEqual(count, 2)
        self.assertTrue(self.service.hull_exists('IMPORT_001'))
        self.assertTrue(self.service.hull_exists('IMPORT_002'))

    def test_export_to_csv(self):
        """CSVへのエクスポート"""
        # テスト船体を保存
        hulls = [
            create_test_hull(id='EXPORT_001', name='エクスポート1'),
            create_test_hull(id='EXPORT_002', name='エクスポート2'),
        ]

        for hull in hulls:
            self.service.save_hull(hull)

        # エクスポート
        csv_path = os.path.join(self.test_dir, 'test_export.csv')
        count = self.service.export_to_csv(csv_path)

        self.assertEqual(count, 2)
        self.assertTrue(os.path.exists(csv_path))

        # CSVファイルの内容確認
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            self.assertEqual(len(rows), 2)

    def test_export_to_csv_with_filter(self):
        """フィルタ条件付きCSVエクスポート"""
        # 異なる国の船体を保存
        hulls = [
            create_test_hull(id='JPN_001', country='JPN'),
            create_test_hull(id='JPN_002', country='JPN'),
            create_test_hull(id='USA_001', country='USA'),
        ]

        for hull in hulls:
            self.service.save_hull(hull)

        # 日本艦のみエクスポート
        csv_path = os.path.join(self.test_dir, 'test_export_filtered.csv')
        count = self.service.export_to_csv(csv_path, {'country': 'JPN'})

        self.assertEqual(count, 2)

    # ========== バッチ操作テスト ==========

    def test_batch_calculate_performance(self):
        """バッチ性能計算"""
        # 複数の船体を保存
        hulls = [
            create_test_hull(id='BATCH_001', max_speed=30.0),
            create_test_hull(id='BATCH_002', max_speed=35.0),
            create_test_hull(id='BATCH_003', max_speed=40.0),
        ]

        for hull in hulls:
            self.service.save_hull(hull)

        # バッチ計算
        results = self.service.batch_calculate_performance()

        self.assertEqual(len(results), 3)
        self.assertIn('BATCH_001', results)
        self.assertIn('BATCH_002', results)
        self.assertIn('BATCH_003', results)

        # 各結果に性能データが含まれる
        for hull_id, performance in results.items():
            self.assertIn('max_speed', performance)

    def test_batch_calculate_performance_with_filter(self):
        """フィルタ条件付きバッチ計算"""
        # 異なる国の船体を保存
        hulls = [
            create_test_hull(id='JPN_001', country='JPN'),
            create_test_hull(id='JPN_002', country='JPN'),
            create_test_hull(id='USA_001', country='USA'),
        ]

        for hull in hulls:
            self.service.save_hull(hull)

        # 日本艦のみ計算
        results = self.service.batch_calculate_performance({'country': 'JPN'})

        self.assertEqual(len(results), 2)
        self.assertIn('JPN_001', results)
        self.assertIn('JPN_002', results)
        self.assertNotIn('USA_001', results)

    def test_get_statistics(self):
        """統計情報取得"""
        # テスト船体を保存
        hulls = [
            create_test_hull(id='STAT_001', weight=1000.0, max_speed=30.0, naval_range=4000.0),
            create_test_hull(id='STAT_002', weight=2000.0, max_speed=35.0, naval_range=5000.0),
            create_test_hull(id='STAT_003', weight=3000.0, max_speed=40.0, naval_range=6000.0),
        ]

        for hull in hulls:
            self.service.save_hull(hull)

        # 統計取得
        stats = self.service.get_statistics()

        self.assertEqual(stats['count'], 3)
        self.assertEqual(stats['avg_weight'], 2000.0)
        self.assertEqual(stats['avg_speed'], 35.0)
        self.assertEqual(stats['avg_range'], 5000.0)
        self.assertEqual(stats['max_weight'], 3000.0)
        self.assertEqual(stats['min_weight'], 1000.0)

    def test_get_statistics_empty(self):
        """空の統計情報"""
        stats = self.service.get_statistics()

        self.assertEqual(stats['count'], 0)
        self.assertEqual(stats['avg_weight'], 0.0)

    def test_get_statistics_with_filter(self):
        """フィルタ条件付き統計"""
        # 異なる国の船体を保存
        hulls = [
            create_test_hull(id='JPN_001', country='JPN', weight=1000.0),
            create_test_hull(id='JPN_002', country='JPN', weight=2000.0),
            create_test_hull(id='USA_001', country='USA', weight=5000.0),
        ]

        for hull in hulls:
            self.service.save_hull(hull)

        # 日本艦の統計のみ
        stats = self.service.get_statistics({'country': 'JPN'})

        self.assertEqual(stats['count'], 2)
        self.assertEqual(stats['avg_weight'], 1500.0)

    # ========== キャッシュ管理テスト ==========

    def test_clear_cache(self):
        """キャッシュのクリア"""
        hull = create_test_hull(id='CACHE_TEST')
        self.service.save_hull(hull)

        # キャッシュに読み込み
        self.service.get_hull('CACHE_TEST')

        # キャッシュ情報確認
        cache_info = self.service.get_cache_info()
        self.assertGreater(cache_info['memory_cache_size'], 0)

        # キャッシュクリア
        self.service.clear_cache()

        # キャッシュが空
        cache_info = self.service.get_cache_info()
        self.assertEqual(cache_info['memory_cache_size'], 0)

    def test_get_cache_info(self):
        """キャッシュ情報の取得"""
        cache_info = self.service.get_cache_info()

        self.assertIn('memory_cache_size', cache_info)
        self.assertIsInstance(cache_info['memory_cache_size'], int)


class TestServiceValidation(unittest.TestCase):
    """サービス層のバリデーションテスト"""

    def setUp(self):
        """テストの前準備"""
        self.test_dir = tempfile.mkdtemp()
        self.repository = HullRepository(self.test_dir)
        self.service = HullPerformanceService(self.repository)

    def tearDown(self):
        """テストの後処理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_validate_hull_entity(self):
        """Hullエンティティの検証"""
        valid_hull = create_test_hull()
        result = self.service.validate_input(valid_hull)
        self.assertTrue(result)

    def test_validate_dict_input(self):
        """辞書形式入力の検証"""
        valid_dict = {'id': 'TEST', 'name': 'テスト'}
        result = self.service.validate_input(valid_dict)
        self.assertTrue(result)

    def test_validate_dict_missing_field(self):
        """必須フィールド欠落でエラー"""
        invalid_dict = {'id': 'TEST'}  # nameがない

        with self.assertRaises(ValidationError):
            self.service.validate_input(invalid_dict)

    def test_validate_invalid_type(self):
        """無効な型でエラー"""
        with self.assertRaises(ValidationError):
            self.service.validate_input("invalid_string")


if __name__ == '__main__':
    unittest.main()
