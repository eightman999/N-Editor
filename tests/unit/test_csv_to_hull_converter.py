# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: test_csv_to_hull_converter CSVコンバーターテスト
"""CSVから船体エンティティへのコンバーターのユニットテスト

CSVToHullConverterの動作を検証するテストスイート。
"""

import unittest
import sys
import os
import tempfile
import csv

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from converters.csv_to_hull_converter import CSVToHullConverter
from domain.entities.hull import Hull


class TestCSVToHullConverter(unittest.TestCase):
    """CSVToHullConverterのテストケース"""

    def setUp(self):
        """テストの前準備"""
        self.converter = CSVToHullConverter()

    def test_basic_conversion(self):
        """基本的なCSV行の変換"""
        row = {
            'システム名称': 'TEST_001',
            '艦級名': 'テスト艦',
            'weight': '2000',
            'length': '100',
            'width': '10',
            'speed': '35',
            'cruise_speed': '18',
            'range': '5000',
            'fuel_capacity': '500',
            'armor_max': '50',
            'armor_min': '20',
            '船殻構造': '5',
            '装甲種別': '1.4',
            'crew': '200',
            'year': '1942',
            'country': 'JPN',
            'archetype': 'DD',
            'TYPE': 'DD'
        }

        hull = self.converter.convert_row(row)

        self.assertIsNotNone(hull)
        self.assertEqual(hull.id, 'TEST_001')
        self.assertEqual(hull.name, 'テスト艦')
        self.assertEqual(hull.weight, 2000.0)
        self.assertEqual(hull.max_speed, 35.0)
        self.assertEqual(hull.hull_structure, 'WWII型')
        self.assertEqual(hull.armor_type, '標準装甲')

    def test_missing_id_generation(self):
        """IDが欠落している場合の自動生成"""
        row = {
            '艦級名': 'テスト艦',
            'weight': '1000'
        }

        hull = self.converter.convert_row(row)

        self.assertIsNotNone(hull)
        self.assertTrue(hull.id.startswith('HULL_'))
        self.assertEqual(hull.name, 'テスト艦')

    def test_missing_name_uses_id(self):
        """名前が欠落している場合はIDを使用"""
        row = {
            'システム名称': 'TEST_ID',
            'weight': '1000'
        }

        hull = self.converter.convert_row(row)

        self.assertIsNotNone(hull)
        self.assertEqual(hull.id, 'TEST_ID')
        self.assertEqual(hull.name, 'TEST_ID')

    def test_numeric_field_error_handling(self):
        """数値フィールドのエラー処理"""
        row = {
            '艦級名': 'テスト艦',
            'weight': '#REF!',  # エラー値
            'length': '',  # 空文字
            'width': 'invalid',  # 無効な値
            'speed': '35'
        }

        hull = self.converter.convert_row(row)

        self.assertIsNotNone(hull)
        self.assertEqual(hull.weight, 0.0)  # デフォルト値
        self.assertEqual(hull.length, 0.0)  # デフォルト値
        self.assertEqual(hull.width, 0.0)  # デフォルト値
        self.assertEqual(hull.max_speed, 35.0)  # 正常な値

    def test_hull_structure_mapping(self):
        """船殻構造のマッピング"""
        test_cases = [
            ('0', 'なし'),
            ('1', '中世型'),
            ('2', '近代型'),
            ('3', 'WWI型'),
            ('4', '戦間期型'),
            ('5', 'WWII型'),
            ('6', '戦後前期型'),
            ('7', '現代型'),
            ('99', 'WWII型')  # 不明な値はデフォルト
        ]

        for structure_id, expected_structure in test_cases:
            row = {
                '艦級名': 'テスト',
                '船殻構造': structure_id
            }
            hull = self.converter.convert_row(row)
            self.assertEqual(
                hull.hull_structure,
                expected_structure,
                f"Structure ID {structure_id} should map to {expected_structure}"
            )

    def test_armor_type_mapping(self):
        """装甲種別のマッピング"""
        test_cases = [
            ('0', 'なし'),
            ('1.0', '装甲なし'),
            ('1.35', '軽装甲'),
            ('1.4', '標準装甲'),
            ('1.5', '重装甲'),
            ('1.8', '特殊装甲'),
            ('2.0', '複合装甲'),
            ('999', '標準装甲')  # 不明な値はデフォルト
        ]

        for armor_id, expected_armor in test_cases:
            row = {
                '艦級名': 'テスト',
                '装甲種別': armor_id
            }
            hull = self.converter.convert_row(row)
            self.assertEqual(
                hull.armor_type,
                expected_armor,
                f"Armor ID {armor_id} should map to {expected_armor}"
            )

    def test_ship_type_conversion(self):
        """艦種コードの変換"""
        test_cases = [
            ('DD', 'DD - 駆逐艦'),
            ('CA', 'CA - 重巡・一等巡洋艦'),
            ('BB', 'BB - 戦艦'),
            ('CV', 'CV - 航空母艦'),
            ('SS', 'SS - 航洋型潜水艦'),
            ('UNKNOWN', 'UNKNOWN')  # 不明なコードはそのまま
        ]

        for ship_code, expected_type in test_cases:
            row = {
                '艦級名': 'テスト',
                'archetype': ship_code
            }
            hull = self.converter.convert_row(row)
            self.assertEqual(
                hull.archetype,
                expected_type,
                f"Ship code {ship_code} should convert to {expected_type}"
            )

    def test_csv_file_import(self):
        """CSVファイルからのインポート"""
        # 一時CSVファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.csv') as f:
            csv_path = f.name
            writer = csv.DictWriter(f, fieldnames=[
                'システム名称', '艦級名', 'weight', 'length', 'width',
                'speed', 'cruise_speed', 'range', 'fuel_capacity',
                'armor_max', 'armor_min', '船殻構造', '装甲種別',
                'crew', 'year', 'country', 'archetype', 'TYPE'
            ])
            writer.writeheader()

            # 3隻分のデータ
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

            writer.writerow({
                'システム名称': 'YAMATO',
                '艦級名': '大和型',
                'weight': '72000',
                'speed': '27',
                'archetype': 'BB',
                'country': 'JPN',
                'year': '1941',
                '船殻構造': '5',
                '装甲種別': '2.0',
                'length': '263',
                'width': '38.9',
                'cruise_speed': '16',
                'range': '7200',
                'fuel_capacity': '6300',
                'armor_max': '410',
                'armor_min': '200',
                'crew': '2500',
                'TYPE': 'BB'
            })

            writer.writerow({
                'システム名称': 'INVALID',
                '艦級名': '',  # 無効データ
                'weight': '#REF!',
                'speed': '',
                'archetype': '',
                'country': '',
                'year': '',
                '船殻構造': '',
                '装甲種別': '',
                'length': '',
                'width': '',
                'cruise_speed': '',
                'range': '',
                'fuel_capacity': '',
                'armor_max': '',
                'armor_min': '',
                'crew': '',
                'TYPE': ''
            })

        try:
            # CSVファイル読み込み
            hulls = self.converter.convert_csv_file(csv_path)

            # 3隻読み込まれるはず（INVALIDもIDで名前が設定されるため有効）
            self.assertEqual(len(hulls), 3)

            # 吹雪型の検証
            fubuki = next(h for h in hulls if h.id == 'FUBUKI')
            self.assertEqual(fubuki.name, '吹雪型')
            self.assertEqual(fubuki.weight, 2000.0)
            self.assertEqual(fubuki.max_speed, 38.0)
            self.assertEqual(fubuki.hull_structure, '戦間期型')

            # 大和型の検証
            yamato = next(h for h in hulls if h.id == 'YAMATO')
            self.assertEqual(yamato.name, '大和型')
            self.assertEqual(yamato.weight, 72000.0)
            self.assertEqual(yamato.armor_type, '複合装甲')

        finally:
            # 一時ファイル削除
            os.unlink(csv_path)

    def test_csv_file_export(self):
        """CSVファイルへのエクスポート"""
        # テスト用船体データ
        hulls = [
            Hull(
                id='TEST_001',
                name='テスト艦1',
                weight=2000.0,
                length=100.0,
                width=10.0,
                max_speed=35.0,
                cruise_speed=18.0,
                naval_range=5000.0,
                fuel_capacity=500.0,
                armor_max=50.0,
                armor_min=20.0,
                hull_structure='WWII型',
                armor_type='標準装甲',
                crew=200,
                year=1942,
                country='JPN',
                archetype='DD - 駆逐艦',
                type_display='DD - 駆逐艦'
            ),
            Hull(
                id='TEST_002',
                name='テスト艦2',
                weight=10000.0,
                length=150.0,
                width=15.0,
                max_speed=32.0,
                cruise_speed=16.0,
                naval_range=8000.0,
                fuel_capacity=1200.0,
                armor_max=100.0,
                armor_min=50.0,
                hull_structure='戦間期型',
                armor_type='重装甲',
                crew=500,
                year=1936,
                country='USA',
                archetype='CA - 重巡・一等巡洋艦',
                type_display='CA - 重巡・一等巡洋艦'
            )
        ]

        # 一時CSVファイルに出力
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.csv') as f:
            csv_path = f.name

        try:
            # エクスポート
            self.converter.export_to_csv(hulls, csv_path)

            # 読み込んで検証
            reimported_hulls = self.converter.convert_csv_file(csv_path)

            self.assertEqual(len(reimported_hulls), 2)

            # データの整合性確認
            test1 = next(h for h in reimported_hulls if h.id == 'TEST_001')
            self.assertEqual(test1.name, 'テスト艦1')
            self.assertEqual(test1.weight, 2000.0)
            self.assertEqual(test1.max_speed, 35.0)

            test2 = next(h for h in reimported_hulls if h.id == 'TEST_002')
            self.assertEqual(test2.name, 'テスト艦2')
            self.assertEqual(test2.weight, 10000.0)

        finally:
            # 一時ファイル削除
            os.unlink(csv_path)

    def test_custom_id_generator(self):
        """カスタムID生成関数の使用"""
        def custom_generator(prefix):
            return f"CUSTOM_{prefix}_999"

        converter = CSVToHullConverter(id_generator=custom_generator)

        row = {
            '艦級名': 'テスト艦',
            'weight': '1000'
        }

        hull = converter.convert_row(row)

        self.assertIsNotNone(hull)
        self.assertEqual(hull.id, 'CUSTOM_HULL_999')

    def test_validation_failure(self):
        """バリデーション失敗の処理"""
        # 無効なデータ（年代が範囲外）
        row = {
            '艦級名': 'テスト艦',
            'year': '999'  # 無効な年（1800未満）
        }

        hull = self.converter.convert_row(row)

        # バリデーションエラーでNoneが返る
        self.assertIsNone(hull)

    def test_empty_csv_file(self):
        """空のCSVファイルの処理"""
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.csv') as f:
            csv_path = f.name
            f.write('システム名称,艦級名\n')  # ヘッダーのみ

        try:
            hulls = self.converter.convert_csv_file(csv_path)
            self.assertEqual(len(hulls), 0)

        finally:
            os.unlink(csv_path)


class TestShipTypeMappings(unittest.TestCase):
    """艦種マッピングのテストケース"""

    def setUp(self):
        """テストの前準備"""
        self.converter = CSVToHullConverter()

    def test_destroyer_types(self):
        """駆逐艦系の変換"""
        test_cases = [
            ('D', 'D - 水雷駆逐艦'),
            ('DD', 'DD - 駆逐艦'),
            ('DDG', 'DDG - ミサイル駆逐艦'),
            ('DE', 'DE - 護衛駆逐艦'),
        ]

        for code, expected in test_cases:
            result = self.converter._convert_ship_type(code)
            self.assertEqual(result, expected)

    def test_cruiser_types(self):
        """巡洋艦系の変換"""
        test_cases = [
            ('CA', 'CA - 重巡・一等巡洋艦'),
            ('CL', 'CL - 軽巡洋艦/二等巡洋艦'),
            ('CB', 'CB - 大型巡洋艦'),
        ]

        for code, expected in test_cases:
            result = self.converter._convert_ship_type(code)
            self.assertEqual(result, expected)

    def test_battleship_types(self):
        """戦艦系の変換"""
        test_cases = [
            ('BB', 'BB - 戦艦'),
            ('BC', 'BC - 巡洋戦艦'),
        ]

        for code, expected in test_cases:
            result = self.converter._convert_ship_type(code)
            self.assertEqual(result, expected)

    def test_carrier_types(self):
        """空母系の変換"""
        test_cases = [
            ('CV', 'CV - 航空母艦'),
            ('CVL', 'CVL - 軽空母'),
            ('CVE', 'CVE - 護衛空母'),
        ]

        for code, expected in test_cases:
            result = self.converter._convert_ship_type(code)
            self.assertEqual(result, expected)

    def test_submarine_types(self):
        """潜水艦系の変換"""
        test_cases = [
            ('SS', 'SS - 航洋型潜水艦'),
            ('SC', 'SC - 巡洋潜水艦'),
            ('SCV', 'SCV - 潜水空母'),
        ]

        for code, expected in test_cases:
            result = self.converter._convert_ship_type(code)
            self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
