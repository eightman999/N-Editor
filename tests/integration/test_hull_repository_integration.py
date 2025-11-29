# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: test_hull_repository_integration リポジトリ統合テスト
"""HullRepositoryとCSVコンバーターの統合テスト

リポジトリパターン、CSVコンバーター、キャッシュマネージャーが
正しく統合されていることを検証します。
"""

import unittest
import sys
import os
import tempfile
import shutil
import csv

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from infrastructure.repositories.hull_repository import HullRepository
from converters.csv_to_hull_converter import CSVToHullConverter
from domain.entities.hull import Hull, create_test_hull


class TestHullRepositoryIntegration(unittest.TestCase):
    """HullRepositoryの統合テストケース"""

    def setUp(self):
        """テストの前準備"""
        # 一時ディレクトリを作成
        self.test_dir = tempfile.mkdtemp()
        self.repository = HullRepository(self.test_dir)
        self.converter = CSVToHullConverter()

    def tearDown(self):
        """テストの後処理"""
        # 一時ディレクトリを削除
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_save_and_find_by_id(self):
        """船体の保存と取得"""
        hull = create_test_hull(
            id='TEST_001',
            name='テスト駆逐艦',
            weight=2000.0
        )

        # 保存
        result = self.repository.save(hull)
        self.assertTrue(result)

        # 取得
        loaded_hull = self.repository.find_by_id('TEST_001')
        self.assertIsNotNone(loaded_hull)
        self.assertEqual(loaded_hull.id, 'TEST_001')
        self.assertEqual(loaded_hull.name, 'テスト駆逐艦')
        self.assertEqual(loaded_hull.weight, 2000.0)

    def test_find_by_id_not_found(self):
        """存在しない船体の検索"""
        hull = self.repository.find_by_id('NONEXISTENT')
        self.assertIsNone(hull)

    def test_find_all(self):
        """全船体の取得"""
        # 複数の船体を保存
        hulls_to_save = [
            create_test_hull(id='DD_001', archetype='DD', country='JPN'),
            create_test_hull(id='DD_002', archetype='DD', country='USA'),
            create_test_hull(id='CA_001', archetype='CA', country='JPN'),
        ]

        for hull in hulls_to_save:
            self.repository.save(hull)

        # 全船体を取得
        all_hulls = self.repository.find_all()
        self.assertEqual(len(all_hulls), 3)

    def test_find_all_with_filter(self):
        """フィルタ条件での船体取得"""
        # 複数の船体を保存
        hulls_to_save = [
            create_test_hull(id='DD_JPN_001', archetype='DD', country='JPN'),
            create_test_hull(id='DD_JPN_002', archetype='DD', country='JPN'),
            create_test_hull(id='DD_USA_001', archetype='DD', country='USA'),
            create_test_hull(id='CA_JPN_001', archetype='CA', country='JPN'),
        ]

        for hull in hulls_to_save:
            self.repository.save(hull)

        # 日本の駆逐艦のみを取得
        jpn_destroyers = self.repository.find_all({
            'country': 'JPN',
            'archetype': 'DD'
        })

        self.assertEqual(len(jpn_destroyers), 2)
        for hull in jpn_destroyers:
            self.assertEqual(hull.country, 'JPN')
            self.assertEqual(hull.archetype, 'DD')

    def test_delete(self):
        """船体の削除"""
        hull = create_test_hull(id='DELETE_TEST')
        self.repository.save(hull)

        # 存在を確認
        self.assertTrue(self.repository.exists('DELETE_TEST'))

        # 削除
        result = self.repository.delete('DELETE_TEST')
        self.assertTrue(result)

        # 削除後は存在しない
        self.assertFalse(self.repository.exists('DELETE_TEST'))

    def test_delete_nonexistent(self):
        """存在しない船体の削除"""
        result = self.repository.delete('NONEXISTENT')
        self.assertFalse(result)

    def test_memory_cache(self):
        """メモリキャッシュの動作確認"""
        hull = create_test_hull(id='CACHE_TEST')
        self.repository.save(hull)

        # 1回目の読み込み（ファイルから）
        hull1 = self.repository.find_by_id('CACHE_TEST')

        # 2回目の読み込み（キャッシュから）
        hull2 = self.repository.find_by_id('CACHE_TEST')

        # 同じオブジェクトが返される（メモリキャッシュ）
        self.assertIs(hull1, hull2)

    def test_clear_cache(self):
        """キャッシュのクリア"""
        hull = create_test_hull(id='CACHE_CLEAR_TEST')
        self.repository.save(hull)

        # キャッシュに読み込み
        self.repository.find_by_id('CACHE_CLEAR_TEST')

        # キャッシュ情報を確認
        cache_info = self.repository.get_cache_info()
        self.assertEqual(cache_info['memory_cache_size'], 1)

        # キャッシュをクリア
        self.repository.clear_cache()

        # キャッシュがクリアされている
        cache_info = self.repository.get_cache_info()
        self.assertEqual(cache_info['memory_cache_size'], 0)

    def test_count(self):
        """エンティティ数のカウント"""
        # 3隻保存
        for i in range(3):
            hull = create_test_hull(id=f'COUNT_TEST_{i}')
            self.repository.save(hull)

        # カウント
        count = self.repository.count()
        self.assertEqual(count, 3)

    def test_count_with_filter(self):
        """フィルタ条件でのカウント"""
        hulls_to_save = [
            create_test_hull(id='DD_001', archetype='DD', country='JPN'),
            create_test_hull(id='DD_002', archetype='DD', country='JPN'),
            create_test_hull(id='CA_001', archetype='CA', country='JPN'),
        ]

        for hull in hulls_to_save:
            self.repository.save(hull)

        # 駆逐艦のみカウント
        dd_count = self.repository.count({'archetype': 'DD'})
        self.assertEqual(dd_count, 2)


class TestCSVIntegration(unittest.TestCase):
    """CSVコンバーターとリポジトリの統合テスト"""

    def setUp(self):
        """テストの前準備"""
        self.test_dir = tempfile.mkdtemp()
        self.repository = HullRepository(self.test_dir)
        self.converter = CSVToHullConverter()
        self.csv_path = os.path.join(self.test_dir, 'test_hulls.csv')

    def tearDown(self):
        """テストの後処理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_csv_import_and_repository_save(self):
        """CSVインポートとリポジトリ保存の統合"""
        # テストCSVファイルを作成
        with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'システム名称', '艦級名', 'weight', 'length', 'width',
                'speed', 'cruise_speed', 'range', 'fuel_capacity',
                'armor_max', 'armor_min', '船殻構造', '装甲種別',
                'crew', 'year', 'country', 'archetype', 'TYPE'
            ])
            writer.writeheader()

            writer.writerow({
                'システム名称': 'FUBUKI',
                '艦級名': '吹雪型',
                'weight': '2000',
                'speed': '38',
                'archetype': 'DD',
                'country': 'JPN',
                'year': '1928',
                '船殻構造': '4',
                '装甲種別': '1.0',
                'length': '118',
                'width': '10.4',
                'cruise_speed': '18',
                'range': '5000',
                'fuel_capacity': '500',
                'armor_max': '50',
                'armor_min': '20',
                'crew': '219',
                'TYPE': 'DD'
            })

        # CSVから読み込み
        hulls = self.converter.convert_csv_file(self.csv_path)
        self.assertEqual(len(hulls), 1)

        # リポジトリに保存
        for hull in hulls:
            self.repository.save(hull)

        # リポジトリから取得して確認
        fubuki = self.repository.find_by_id('FUBUKI')
        self.assertIsNotNone(fubuki)
        self.assertEqual(fubuki.name, '吹雪型')
        self.assertEqual(fubuki.weight, 2000.0)
        self.assertEqual(fubuki.max_speed, 38.0)
        self.assertEqual(fubuki.hull_structure, '戦間期型')
        self.assertEqual(fubuki.armor_type, '装甲なし')

    def test_repository_export_and_reimport(self):
        """リポジトリエクスポートと再インポート"""
        # テスト船体を作成してリポジトリに保存
        original_hulls = [
            create_test_hull(id='EXPORT_001', name='エクスポート1', weight=2000.0),
            create_test_hull(id='EXPORT_002', name='エクスポート2', weight=3000.0),
        ]

        for hull in original_hulls:
            self.repository.save(hull)

        # リポジトリから全船体を取得してCSVにエクスポート
        all_hulls = self.repository.find_all()
        self.converter.export_to_csv(all_hulls, self.csv_path)

        # 新しいリポジトリを作成
        new_repo_dir = tempfile.mkdtemp()
        new_repository = HullRepository(new_repo_dir)

        try:
            # CSVから再インポート
            reimported_hulls = self.converter.convert_csv_file(self.csv_path)

            # 新しいリポジトリに保存
            for hull in reimported_hulls:
                new_repository.save(hull)

            # データの整合性確認
            hull1 = new_repository.find_by_id('EXPORT_001')
            self.assertIsNotNone(hull1)
            self.assertEqual(hull1.name, 'エクスポート1')
            self.assertEqual(hull1.weight, 2000.0)

            hull2 = new_repository.find_by_id('EXPORT_002')
            self.assertIsNotNone(hull2)
            self.assertEqual(hull2.name, 'エクスポート2')
            self.assertEqual(hull2.weight, 3000.0)

        finally:
            # クリーンアップ
            shutil.rmtree(new_repo_dir)

    def test_bulk_import_performance(self):
        """大量データのインポートパフォーマンス"""
        # 100隻分のCSVデータを作成
        with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'システム名称', '艦級名', 'weight', 'speed', 'archetype'
            ])
            writer.writeheader()

            for i in range(100):
                writer.writerow({
                    'システム名称': f'BULK_{i:03d}',
                    '艦級名': f'バルク艦{i}',
                    'weight': str(1000 + i * 10),
                    'speed': str(30 + i % 10),
                    'archetype': 'DD'
                })

        # インポート
        import time
        start_time = time.time()

        hulls = self.converter.convert_csv_file(self.csv_path)
        for hull in hulls:
            self.repository.save(hull)

        duration = time.time() - start_time

        # 100隻すべて保存されている
        self.assertEqual(len(hulls), 100)
        self.assertEqual(self.repository.count(), 100)

        # パフォーマンスチェック（1秒以内で完了すること）
        self.assertLess(duration, 1.0, f"Bulk import took {duration:.3f}s")


if __name__ == '__main__':
    unittest.main()
