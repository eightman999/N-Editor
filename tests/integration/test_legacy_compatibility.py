# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: test_legacy_compatibility レガシー互換性テスト
"""レガシーシステムとの互換性テスト

アダプター、ファサード、マイグレーションヘルパーの
動作を検証します。
"""

import unittest
import sys
import os
import tempfile
import shutil
import csv

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from infrastructure.adapters.legacy_hull_adapter import LegacyHullAdapter
from infrastructure.adapters.hull_model_facade import HullModelFacade
from infrastructure.migration.migration_helper import MigrationHelper
from domain.entities.hull import create_test_hull


class TestLegacyHullAdapter(unittest.TestCase):
    """LegacyHullAdapterのテスト"""

    def test_from_legacy_basic(self):
        """レガシーデータからHullへの基本変換"""
        legacy_data = {
            'id': 'TEST_001',
            'name': 'テスト艦',
            'weight': 2000.0,
            'speed': 35.0,
            'cruise_speed': 18.0,
            'range': 5000.0,
            'country': 'JPN'
        }

        hull = LegacyHullAdapter.from_legacy(legacy_data)

        self.assertEqual(hull.id, 'TEST_001')
        self.assertEqual(hull.name, 'テスト艦')
        self.assertEqual(hull.weight, 2000.0)
        self.assertEqual(hull.max_speed, 35.0)
        self.assertEqual(hull.cruise_speed, 18.0)
        self.assertEqual(hull.naval_range, 5000.0)
        self.assertEqual(hull.country, 'JPN')

    def test_from_legacy_field_mapping(self):
        """フィールドマッピングの検証"""
        legacy_data = {
            'id': 'TEST',
            'name': 'Test',
            'speed': 30.0,  # → max_speed
            'range': 4000.0,  # → naval_range
        }

        hull = LegacyHullAdapter.from_legacy(legacy_data)

        self.assertEqual(hull.max_speed, 30.0)
        self.assertEqual(hull.naval_range, 4000.0)

    def test_to_legacy_basic(self):
        """Hullからレガシーデータへの基本変換"""
        hull = create_test_hull(
            id='TEST_001',
            name='テスト艦',
            weight=2000.0,
            max_speed=35.0
        )

        legacy_data = LegacyHullAdapter.to_legacy(hull)

        self.assertEqual(legacy_data['id'], 'TEST_001')
        self.assertEqual(legacy_data['name'], 'テスト艦')
        self.assertEqual(legacy_data['weight'], 2000.0)
        self.assertEqual(legacy_data['speed'], 35.0)
        self.assertIn('slots', legacy_data)

    def test_round_trip_conversion(self):
        """双方向変換の検証"""
        # レガシー → Hull → レガシー
        original_legacy = {
            'id': 'TEST',
            'name': 'Test Hull',
            'weight': 3000.0,
            'speed': 32.0,
            'cruise_speed': 16.0,
            'range': 6000.0,
            'country': 'USA'
        }

        hull = LegacyHullAdapter.from_legacy(original_legacy)
        converted_legacy = LegacyHullAdapter.to_legacy(hull)

        # 主要フィールドが保持されているか
        self.assertEqual(converted_legacy['id'], original_legacy['id'])
        self.assertEqual(converted_legacy['name'], original_legacy['name'])
        self.assertEqual(converted_legacy['weight'], original_legacy['weight'])
        self.assertEqual(converted_legacy['speed'], original_legacy['speed'])

    def test_batch_from_legacy(self):
        """バッチ変換（レガシー→Hull）"""
        legacy_list = [
            {'id': 'TEST_001', 'name': 'Hull 1', 'weight': 1000.0},
            {'id': 'TEST_002', 'name': 'Hull 2', 'weight': 2000.0},
            {'id': 'TEST_003', 'name': 'Hull 3', 'weight': 3000.0},
        ]

        hulls = LegacyHullAdapter.batch_from_legacy(legacy_list)

        self.assertEqual(len(hulls), 3)
        self.assertEqual(hulls[0].id, 'TEST_001')
        self.assertEqual(hulls[1].weight, 2000.0)
        self.assertEqual(hulls[2].name, 'Hull 3')

    def test_batch_to_legacy(self):
        """バッチ変換（Hull→レガシー）"""
        hulls = [
            create_test_hull(id='TEST_001', weight=1000.0),
            create_test_hull(id='TEST_002', weight=2000.0),
            create_test_hull(id='TEST_003', weight=3000.0),
        ]

        legacy_list = LegacyHullAdapter.batch_to_legacy(hulls)

        self.assertEqual(len(legacy_list), 3)
        self.assertEqual(legacy_list[0]['id'], 'TEST_001')
        self.assertEqual(legacy_list[1]['weight'], 2000.0)
        self.assertEqual(legacy_list[2]['id'], 'TEST_003')


class TestHullModelFacade(unittest.TestCase):
    """HullModelFacadeのテスト"""

    def setUp(self):
        """テストの前準備"""
        self.test_dir = tempfile.mkdtemp()
        self.facade = HullModelFacade(self.test_dir)

    def tearDown(self):
        """テストの後処理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_save_and_load_hull(self):
        """船体の保存と読み込み（レガシーインターフェース）"""
        legacy_data = {
            'id': 'TEST_001',
            'name': 'テスト艦',
            'weight': 2000.0,
            'speed': 35.0,
            'country': 'JPN'
        }

        # 保存
        result = self.facade.save_hull(legacy_data)
        self.assertTrue(result)

        # 読み込み
        loaded = self.facade.load_hull('TEST_001')
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded['id'], 'TEST_001')
        self.assertEqual(loaded['name'], 'テスト艦')

    def test_get_all_hulls(self):
        """全船体の取得（レガシーインターフェース）"""
        # 複数保存
        for i in range(3):
            self.facade.save_hull({
                'id': f'TEST_{i:03d}',
                'name': f'Ship {i}',
                'weight': 1000.0 * (i + 1)
            })

        # 全取得
        all_hulls = self.facade.get_all_hulls()
        self.assertEqual(len(all_hulls), 3)

    def test_calculate_hull_performance(self):
        """性能計算（レガシーインターフェース）"""
        hull_data = {
            'id': 'PERF_TEST',
            'name': 'Performance Test',
            'weight': 2000.0,
            'speed': 35.0,
            'cruise_speed': 18.0,
            'range': 5000.0,
            'fuel_capacity': 500.0
        }

        # 性能計算
        result = self.facade.calculate_hull_performance(hull_data)

        self.assertIn('speed', result)
        self.assertIn('range', result)
        self.assertEqual(result['speed'], 35.0)

    def test_import_export_csv(self):
        """CSV入出力（レガシーインターフェース）"""
        # テストCSV作成
        csv_path = os.path.join(self.test_dir, 'test.csv')

        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['システム名称', '艦級名', 'weight', 'speed'])
            writer.writeheader()
            writer.writerow({
                'システム名称': 'CSV_001',
                '艦級名': 'CSV Ship',
                'weight': '1000',
                'speed': '30'
            })

        # インポート
        count = self.facade.import_from_csv(csv_path)
        self.assertEqual(count, 1)

        # エクスポート
        export_path = os.path.join(self.test_dir, 'export.csv')
        exported = self.facade.export_to_csv(export_path)
        self.assertEqual(exported, 1)
        self.assertTrue(os.path.exists(export_path))

    def test_new_features_available(self):
        """新機能が使用可能か"""
        # テストデータ保存
        for i in range(3):
            self.facade.save_hull({
                'id': f'TEST_{i}',
                'name': f'Ship {i}',
                'weight': 1000.0 * (i + 1),
                'speed': 30.0 + i,
                'country': 'JPN'
            })

        # 統計情報（新機能）
        stats = self.facade.get_statistics()
        self.assertEqual(stats['count'], 3)
        self.assertGreater(stats['avg_weight'], 0)

        # バッチ計算（新機能）
        batch_results = self.facade.batch_calculate_performance()
        self.assertEqual(len(batch_results), 3)


class TestMigrationHelper(unittest.TestCase):
    """MigrationHelperのテスト"""

    def setUp(self):
        """テストの前準備"""
        self.test_dir = tempfile.mkdtemp()
        self.helper = MigrationHelper(self.test_dir)

    def tearDown(self):
        """テストの後処理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_migrate_from_legacy_dict(self):
        """レガシー辞書からのマイグレーション"""
        legacy_list = [
            {'id': 'MIG_001', 'name': 'Ship 1', 'weight': 1000.0},
            {'id': 'MIG_002', 'name': 'Ship 2', 'weight': 2000.0},
            {'id': 'MIG_003', 'name': 'Ship 3', 'weight': 3000.0},
        ]

        report = self.helper.migrate_from_legacy_dict(legacy_list)

        self.assertEqual(report.total_count, 3)
        self.assertEqual(report.success_count, 3)
        self.assertEqual(report.failed_count, 0)

    def test_migrate_with_overwrite(self):
        """上書きマイグレーション"""
        legacy_data = [
            {'id': 'MIG_001', 'name': 'Original', 'weight': 1000.0},
        ]

        # 1回目
        report1 = self.helper.migrate_from_legacy_dict(legacy_data)
        self.assertEqual(report1.success_count, 1)

        # 2回目（上書きなし）
        report2 = self.helper.migrate_from_legacy_dict(legacy_data, overwrite=False)
        self.assertEqual(report2.skipped_count, 1)

        # 3回目（上書きあり）
        updated_data = [
            {'id': 'MIG_001', 'name': 'Updated', 'weight': 2000.0},
        ]
        report3 = self.helper.migrate_from_legacy_dict(updated_data, overwrite=True)
        self.assertEqual(report3.success_count, 1)

        # 確認
        hull = self.helper.service.get_hull('MIG_001')
        self.assertEqual(hull.name, 'Updated')
        self.assertEqual(hull.weight, 2000.0)

    def test_migrate_from_csv(self):
        """CSVからのマイグレーション"""
        # テストCSV作成
        csv_path = os.path.join(self.test_dir, 'migration.csv')

        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['システム名称', '艦級名', 'weight'])
            writer.writeheader()
            for i in range(5):
                writer.writerow({
                    'システム名称': f'CSV_MIG_{i}',
                    '艦級名': f'CSV Ship {i}',
                    'weight': str(1000 * (i + 1))
                })

        report = self.helper.migrate_from_csv(csv_path)

        self.assertEqual(report.total_count, 5)
        self.assertEqual(report.success_count, 5)

    def test_verify_migration(self):
        """マイグレーション検証"""
        legacy_list = [
            {'id': 'VER_001', 'name': 'Ship 1', 'weight': 1000.0, 'speed': 30.0, 'country': 'JPN'},
            {'id': 'VER_002', 'name': 'Ship 2', 'weight': 2000.0, 'speed': 32.0, 'country': 'USA'},
        ]

        # マイグレーション
        self.helper.migrate_from_legacy_dict(legacy_list)

        # 検証
        match_count, mismatch_ids = self.helper.verify_migration(legacy_list)

        self.assertEqual(match_count, 2)
        self.assertEqual(len(mismatch_ids), 0)

    def test_generate_migration_plan(self):
        """マイグレーション計画の生成"""
        legacy_list = [
            {'id': 'PLAN_001', 'name': 'Ship 1', 'country': 'JPN', 'archetype': 'DD', 'year': 1942},
            {'id': 'PLAN_002', 'name': 'Ship 2', 'country': 'USA', 'archetype': 'BB', 'year': 1944},
            {'id': 'PLAN_003', 'name': 'Ship 3', 'country': 'JPN', 'archetype': 'DD', 'year': 1943},
        ]

        plan = self.helper.generate_migration_plan(legacy_list)

        self.assertEqual(plan['total_count'], 3)
        self.assertEqual(plan['new_count'], 3)
        self.assertEqual(plan['update_count'], 0)
        self.assertEqual(plan['by_country']['JPN'], 2)
        self.assertEqual(plan['by_country']['USA'], 1)
        self.assertEqual(plan['by_archetype']['DD'], 2)
        self.assertEqual(plan['by_archetype']['BB'], 1)

    def test_export_migration_report(self):
        """マイグレーションレポートのエクスポート"""
        legacy_list = [
            {'id': 'REP_001', 'name': 'Ship 1', 'weight': 1000.0},
        ]

        report = self.helper.migrate_from_legacy_dict(legacy_list)

        # レポート出力
        report_path = os.path.join(self.test_dir, 'report.json')
        self.helper.export_migration_report(report, report_path)

        self.assertTrue(os.path.exists(report_path))

        # レポート内容確認
        import json
        with open(report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)

        self.assertEqual(report_data['total_count'], 1)
        self.assertEqual(report_data['success_count'], 1)


if __name__ == '__main__':
    unittest.main()
