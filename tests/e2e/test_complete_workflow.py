# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: test_complete_workflow エンドツーエンドテスト
"""完全なワークフローのエンドツーエンドテスト

CSVインポートから性能計算、エクスポートまでの
完全なワークフローを検証します。
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
from infrastructure.repositories.hull_repository import HullRepository


class TestCompleteWorkflow(unittest.TestCase):
    """完全なワークフローのテスト"""

    def setUp(self):
        """テストの前準備"""
        # 一時ディレクトリを作成
        self.test_dir = tempfile.mkdtemp()
        self.repository = HullRepository(self.test_dir)
        self.service = HullPerformanceService(self.repository)

        # テスト用CSVファイルパス
        self.import_csv_path = os.path.join(self.test_dir, 'import_hulls.csv')
        self.export_csv_path = os.path.join(self.test_dir, 'export_hulls.csv')

    def tearDown(self):
        """テストの後処理"""
        # 一時ディレクトリを削除
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_test_csv(self):
        """テスト用CSVファイルを作成"""
        with open(self.import_csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'システム名称', '艦級名', 'weight', 'length', 'width',
                'speed', 'cruise_speed', 'range', 'fuel_capacity',
                'armor_max', 'armor_min', '船殻構造', '装甲種別',
                'crew', 'year', 'country', 'archetype', 'TYPE'
            ])
            writer.writeheader()

            # 吹雪型駆逐艦
            writer.writerow({
                'システム名称': 'FUBUKI',
                '艦級名': '吹雪型',
                'weight': '2000',
                'speed': '38',
                'cruise_speed': '18',
                'range': '5000',
                'fuel_capacity': '500',
                'archetype': 'DD',
                'country': 'JPN',
                'year': '1928',
                '船殻構造': '4',  # 戦間期型
                '装甲種別': '1.0',  # 装甲なし
                'length': '118',
                'width': '10.4',
                'armor_max': '50',
                'armor_min': '20',
                'crew': '219',
                'TYPE': 'DD'
            })

            # 大和型戦艦
            writer.writerow({
                'システム名称': 'YAMATO',
                '艦級名': '大和型',
                'weight': '72000',
                'speed': '27',
                'cruise_speed': '16',
                'range': '7200',
                'fuel_capacity': '6300',
                'archetype': 'BB',
                'country': 'JPN',
                'year': '1941',
                '船殻構造': '5',  # WWII型
                '装甲種別': '2.0',  # 複合装甲
                'length': '263',
                'width': '38.9',
                'armor_max': '410',
                'armor_min': '200',
                'crew': '2500',
                'TYPE': 'BB'
            })

            # フレッチャー級駆逐艦
            writer.writerow({
                'システム名称': 'FLETCHER',
                '艦級名': 'フレッチャー級',
                'weight': '2500',
                'speed': '36.5',
                'cruise_speed': '15',
                'range': '6000',
                'fuel_capacity': '492',
                'archetype': 'DD',
                'country': 'USA',
                'year': '1942',
                '船殻構造': '5',  # WWII型
                '装甲種別': '1.0',  # 装甲なし
                'length': '114.7',
                'width': '12.1',
                'armor_max': '50',
                'armor_min': '25',
                'crew': '273',
                'TYPE': 'DD'
            })

    def test_complete_workflow_csv_to_performance(self):
        """完全なワークフロー: CSV → インポート → 性能計算 → エクスポート"""

        # Step 1: テストCSVを作成
        self._create_test_csv()

        # Step 2: CSVからインポート
        imported_count = self.service.import_from_csv(self.import_csv_path)
        self.assertEqual(imported_count, 3, "3隻の船体がインポートされるべき")

        # Step 3: インポートされた船体を確認
        all_hulls = self.service.get_all_hulls()
        self.assertEqual(len(all_hulls), 3)

        # Step 4: 各船体の性能を計算
        # 4-1: 吹雪型の性能計算
        fubuki_performance = self.service.calculate_hull_performance('FUBUKI')
        self.assertEqual(fubuki_performance['max_speed'], 38.0)
        self.assertEqual(fubuki_performance['cruise_speed'], 18.0)
        self.assertEqual(fubuki_performance['naval_range'], 5000.0)

        # 4-2: 大和型の性能計算（機関データ付き）
        yamato_engine = {
            'engine_type': 'HeavyOil',
            'power': 150000
        }
        yamato_performance = self.service.calculate_hull_performance('YAMATO', yamato_engine)
        self.assertEqual(yamato_performance['max_speed'], 27.0)
        self.assertIn('display_speed', yamato_performance)

        # Step 5: 装備効果の計算
        equipment_list = [
            {'id': 'MAIN_GUN_1', 'weight': 200.0, 'type': '主砲'},
            {'id': 'SECONDARY_GUN_1', 'weight': 50.0, 'type': '副砲'},
            {'id': 'TORPEDO_1', 'weight': 100.0, 'type': '魚雷'}
        ]

        fubuki_with_equipment = self.service.calculate_equipment_effect('FUBUKI', equipment_list)
        self.assertIn('new_speed', fubuki_with_equipment)
        self.assertLess(
            fubuki_with_equipment['new_speed'],
            38.0,
            "装備により速度が低下するべき"
        )

        # Step 6: 完全な性能計算（船体 + 機関 + 装備）
        fletcher_engine = {
            'engine_type': 'Diesel',
            'power': 60000
        }
        fletcher_equipment = [
            {'id': 'GUN_1', 'weight': 100.0, 'type': '主砲'}
        ]

        fletcher_complete = self.service.calculate_complete_performance(
            'FLETCHER',
            fletcher_engine,
            fletcher_equipment
        )

        self.assertIn('max_speed', fletcher_complete)
        self.assertIn('fuel_capacity', fletcher_complete)
        self.assertIn('equipment_effect', fletcher_complete)
        self.assertIn('final_speed', fletcher_complete)

        # Step 7: バッチ性能計算
        batch_results = self.service.batch_calculate_performance()
        self.assertEqual(len(batch_results), 3)
        self.assertIn('FUBUKI', batch_results)
        self.assertIn('YAMATO', batch_results)
        self.assertIn('FLETCHER', batch_results)

        # Step 8: 統計情報の取得
        stats = self.service.get_statistics()
        self.assertEqual(stats['count'], 3)
        self.assertGreater(stats['avg_weight'], 0)
        self.assertGreater(stats['avg_speed'], 0)

        # Step 9: CSVにエクスポート
        exported_count = self.service.export_to_csv(self.export_csv_path)
        self.assertEqual(exported_count, 3, "3隻の船体がエクスポートされるべき")

        # Step 10: エクスポートされたCSVを検証
        with open(self.export_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            exported_hulls = list(reader)
            self.assertEqual(len(exported_hulls), 3)

    def test_workflow_with_filter(self):
        """フィルタ条件を使ったワークフロー"""

        # CSVからインポート
        self._create_test_csv()
        self.service.import_from_csv(self.import_csv_path)

        # 日本艦のみ取得
        jpn_hulls = self.service.get_all_hulls({'country': 'JPN'})
        self.assertEqual(len(jpn_hulls), 2, "日本艦は2隻")

        # アメリカ艦のみ取得
        usa_hulls = self.service.get_all_hulls({'country': 'USA'})
        self.assertEqual(len(usa_hulls), 1, "アメリカ艦は1隻")

        # 駆逐艦のみ取得
        destroyers = self.service.get_all_hulls({'archetype': 'DD - 駆逐艦'})
        self.assertEqual(len(destroyers), 2, "駆逐艦は2隻")

        # 日本艦の統計
        jpn_stats = self.service.get_statistics({'country': 'JPN'})
        self.assertEqual(jpn_stats['count'], 2)

        # 日本艦のみエクスポート
        jpn_export_path = os.path.join(self.test_dir, 'jpn_export.csv')
        jpn_exported = self.service.export_to_csv(jpn_export_path, {'country': 'JPN'})
        self.assertEqual(jpn_exported, 2)

    def test_workflow_with_cache(self):
        """キャッシュ機能を使ったワークフロー"""

        # CSVからインポート
        self._create_test_csv()
        self.service.import_from_csv(self.import_csv_path)

        # インポート時にキャッシュされるため、一度クリア
        self.service.clear_cache()

        # 初回アクセス（キャッシュなし）
        hull1 = self.service.get_hull('FUBUKI')
        self.assertEqual(hull1.id, 'FUBUKI')

        # キャッシュ情報を確認
        cache_info = self.service.get_cache_info()
        self.assertEqual(cache_info['memory_cache_size'], 1, "1隻がキャッシュされている")

        # 2回目のアクセス（キャッシュから）
        hull2 = self.service.get_hull('FUBUKI')
        self.assertIs(hull1, hull2, "同じオブジェクトがキャッシュから返される")

        # 複数アクセス
        self.service.get_hull('YAMATO')
        self.service.get_hull('FLETCHER')

        cache_info = self.service.get_cache_info()
        self.assertEqual(cache_info['memory_cache_size'], 3, "3隻がキャッシュされている")

        # キャッシュクリア
        self.service.clear_cache()

        cache_info = self.service.get_cache_info()
        self.assertEqual(cache_info['memory_cache_size'], 0, "キャッシュがクリアされた")

    def test_workflow_error_handling(self):
        """エラーハンドリングのワークフロー"""

        # CSVからインポート
        self._create_test_csv()
        self.service.import_from_csv(self.import_csv_path)

        # 存在しない船体へのアクセス
        from domain.services.base_service import NotFoundError
        with self.assertRaises(NotFoundError):
            self.service.get_hull('NONEXISTENT')

        # 無効な船体の保存
        from domain.entities.hull import create_test_hull
        from domain.services.base_service import ValidationError

        invalid_hull = create_test_hull(year=999)  # 無効な年代
        with self.assertRaises(ValidationError):
            self.service.save_hull(invalid_hull)

        # 存在しない船体の性能計算
        with self.assertRaises(NotFoundError):
            self.service.calculate_hull_performance('NONEXISTENT')

    def test_real_world_scenario(self):
        """実世界シナリオ: 艦隊編成と性能評価"""

        # シナリオ: プレイヤーが日本艦隊を編成し、各艦の性能を評価する

        # Step 1: マスターデータ（CSV）をインポート
        self._create_test_csv()
        self.service.import_from_csv(self.import_csv_path)

        # Step 2: 日本艦のみを抽出
        jpn_fleet = self.service.get_all_hulls({'country': 'JPN'})
        self.assertEqual(len(jpn_fleet), 2)

        # Step 3: 各艦の基本性能を計算
        fleet_performance = {}
        for hull in jpn_fleet:
            performance = self.service.calculate_hull_performance(hull.id)
            fleet_performance[hull.id] = performance

        # 吹雪型は速い
        self.assertGreater(
            fleet_performance['FUBUKI']['max_speed'],
            fleet_performance['YAMATO']['max_speed']
        )

        # Step 4: 装備を装着して実戦性能を評価
        # 吹雪型に主砲と魚雷を装備
        fubuki_equipment = [
            {'id': 'MAIN_GUN', 'weight': 150.0, 'type': '12.7cm連装砲'},
            {'id': 'TORPEDO', 'weight': 200.0, 'type': '61cm三連装魚雷'}
        ]

        fubuki_combat_perf = self.service.calculate_complete_performance(
            'FUBUKI',
            equipment_list=fubuki_equipment
        )

        # 装備により速度低下を確認
        self.assertLess(
            fubuki_combat_perf['final_speed'],
            fubuki_combat_perf['max_speed']
        )

        # Step 5: 艦隊統計を取得
        fleet_stats = self.service.get_statistics({'country': 'JPN'})

        self.assertEqual(fleet_stats['count'], 2)
        self.assertGreater(fleet_stats['avg_weight'], 0)
        self.assertGreater(fleet_stats['max_weight'], fleet_stats['min_weight'])

        # Step 6: 結果をエクスポート（MOD配布用）
        export_path = os.path.join(self.test_dir, 'jpn_fleet_export.csv')
        exported = self.service.export_to_csv(export_path, {'country': 'JPN'})

        self.assertEqual(exported, 2)
        self.assertTrue(os.path.exists(export_path))


if __name__ == '__main__':
    unittest.main()
