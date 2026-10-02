# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: test_equipment_persistence データ永続化テスト
"""unique_equipments.csv の保存・削除の堅牢性に関するユニットテスト

書き込み/シリアライズ/置換の失敗時に既存データとキャッシュが
失われないこと、および正常系の insert/update/delete が
既存のCSV形式(UTF-8/ヘッダー/動的列)を維持することを検証する。
"""

import csv
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from models.equipment_model import EquipmentModel


def _make_equipment(equipment_id, name='テスト装備', **specific):
    """テスト用の装備データ辞書を生成する"""
    return {
        'common': {
            'ID': equipment_id,
            '名前': name,
            '重量': 10,
            '人員': 5,
            '開発年': 1940,
        },
        'specific': specific,
        'equipment_type': 'その他',
    }


class _FailingStr:
    """str() 呼び出しで例外を発生させるテスト用オブジェクト"""
    def __str__(self):
        raise ValueError("シリアライズ失敗(テスト用)")


class TestEquipmentCsvPersistence(unittest.TestCase):
    """save_equipment/delete_equipment の永続化テスト"""

    def setUp(self):
        """テストの前準備: 一時ディレクトリにモデルを構築

        実ユーザーのHOMEや設定には一切触れないようHOMEを偽装し、
        テンプレート読み込みもスタブ化してリポジトリ外ファイルへの
        依存を遮断する。
        """
        self.test_dir = tempfile.mkdtemp()
        self.fake_home = os.path.join(self.test_dir, 'home')
        os.makedirs(self.fake_home, exist_ok=True)
        self._home_patcher = mock.patch.dict(os.environ, {'HOME': self.fake_home})
        self._home_patcher.start()
        self._templates_patcher = mock.patch.object(
            EquipmentModel, '_load_equipment_templates', return_value={})
        self._templates_patcher.start()
        self.data_dir = os.path.join(self.test_dir, 'data')
        self.model = EquipmentModel(data_dir=self.data_dir)
        self.csv_path = self.model.unique_equipment_file
        self.user_data_dir = os.path.dirname(self.csv_path)

    def tearDown(self):
        """テストの後処理"""
        self._templates_patcher.stop()
        self._home_patcher.stop()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _read_rows(self):
        with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
            return list(csv.DictReader(f))

    def _raw_bytes(self):
        with open(self.csv_path, 'rb') as f:
            return f.read()

    def _leftover_tmp_files(self):
        return [f for f in os.listdir(self.user_data_dir) if f.endswith('.tmp')]

    def _seed_csv(self):
        """2件の装備を書き込んだCSVを作成して元のバイト列を返す"""
        self.assertTrue(self.model.save_equipment(_make_equipment('EQ0001', name='装備甲')))
        self.assertTrue(self.model.save_equipment(_make_equipment('EQ0002', name='装備乙')))
        return self._raw_bytes()

    # --- 正常系 ---

    def test_save_insert_creates_csv_with_header(self):
        self.assertTrue(self.model.save_equipment(_make_equipment('EQ0001')))
        self.assertTrue(os.path.exists(self.csv_path))
        with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
        self.assertIn('ID', header)
        rows = self._read_rows()
        self.assertEqual(1, len(rows))
        self.assertEqual('EQ0001', rows[0]['ID'])
        self.assertEqual('テスト装備', rows[0]['名前'])

    def test_save_update_keeps_other_rows(self):
        self._seed_csv()
        updated = _make_equipment('EQ0001', name='改修装備')
        self.assertTrue(self.model.save_equipment(updated))
        rows = self._read_rows()
        self.assertEqual(2, len(rows))
        by_id = {r['ID']: r for r in rows}
        self.assertEqual('改修装備', by_id['EQ0001']['名前'])
        self.assertEqual('装備乙', by_id['EQ0002']['名前'])

    def test_save_extends_header_for_new_columns(self):
        self._seed_csv()
        extra = _make_equipment('EQ0003', 追加能力='対空強化')
        self.assertTrue(self.model.save_equipment(extra))
        rows = self._read_rows()
        self.assertIn('追加能力', rows[0])
        self.assertEqual('対空強化', rows[2]['追加能力'])
        # 既存レコードの値が失われていないこと
        self.assertEqual('装備甲', rows[0]['名前'])

    def test_save_preserves_japanese_commas_and_newlines(self):
        data = _make_equipment('EQ0001', name='艦載,対空"砲"')
        data['specific']['説明'] = '一行目\n二行目,カンマ入り'
        self.assertTrue(self.model.save_equipment(data))
        rows = self._read_rows()
        self.assertEqual('艦載,対空"砲"', rows[0]['名前'])
        self.assertEqual('一行目\n二行目,カンマ入り', rows[0]['説明'])

    def test_delete_removes_only_target_row(self):
        self._seed_csv()
        self.assertTrue(self.model.save_equipment(_make_equipment('EQ0003')))
        self.assertTrue(self.model.delete_equipment('EQ0002'))
        rows = self._read_rows()
        self.assertEqual(2, len(rows))
        self.assertEqual({'EQ0001', 'EQ0003'}, {r['ID'] for r in rows})
        self.assertFalse(os.path.exists(self.csv_path) is False)

    def test_delete_missing_id_returns_false_and_keeps_bytes(self):
        original = self._seed_csv()
        self.assertFalse(self.model.delete_equipment('NO_SUCH'))
        self.assertEqual(original, self._raw_bytes())

    def test_delete_without_file_returns_false(self):
        self.assertFalse(self.model.delete_equipment('EQ0001'))

    def test_save_without_id_returns_false(self):
        self.assertFalse(self.model.save_equipment({'common': {'名前': 'IDなし'}}))

    # --- 失敗時のデータ保全 ---

    def test_save_writerows_failure_preserves_file_and_cache(self):
        original = self._seed_csv()
        original_cached = dict(self.model.equipment_cache)
        with mock.patch.object(csv.DictWriter, 'writerows', side_effect=OSError('disk full')):
            self.assertFalse(self.model.save_equipment(_make_equipment('EQ0003')))
        self.assertEqual(original, self._raw_bytes())
        self.assertEqual([], self._leftover_tmp_files())
        self.assertEqual(original_cached, self.model.equipment_cache)
        self.assertNotIn('EQ0003', self.model.equipment_cache)

    def test_save_serialization_failure_preserves_file(self):
        original = self._seed_csv()
        bad = _make_equipment('EQ0009', 壊れる=_FailingStr())
        self.assertFalse(self.model.save_equipment(bad))
        self.assertEqual(original, self._raw_bytes())
        self.assertEqual([], self._leftover_tmp_files())
        rows = self._read_rows()
        self.assertEqual(2, len(rows))

    def test_save_replace_failure_preserves_file(self):
        original = self._seed_csv()
        with mock.patch('os.replace', side_effect=OSError('rename failed')):
            self.assertFalse(self.model.save_equipment(_make_equipment('EQ0001', name='更新不可')))
        self.assertEqual(original, self._raw_bytes())
        self.assertEqual([], self._leftover_tmp_files())

    def test_save_failure_on_new_file_leaves_no_partial_file(self):
        with mock.patch.object(csv.DictWriter, 'writerows', side_effect=OSError('disk full')):
            self.assertFalse(self.model.save_equipment(_make_equipment('EQ0001')))
        # 初回保存の失敗では対象ファイル自体を残さないこと
        self.assertFalse(os.path.exists(self.csv_path))
        self.assertEqual([], self._leftover_tmp_files())

    def test_delete_writerows_failure_preserves_file_and_cache(self):
        original = self._seed_csv()
        original_cached = dict(self.model.equipment_cache)
        with mock.patch.object(csv.DictWriter, 'writerows', side_effect=OSError('disk full')):
            self.assertFalse(self.model.delete_equipment('EQ0001'))
        self.assertEqual(original, self._raw_bytes())
        self.assertEqual([], self._leftover_tmp_files())
        self.assertEqual(original_cached, self.model.equipment_cache)

    def test_delete_replace_failure_preserves_file(self):
        original = self._seed_csv()
        with mock.patch('os.replace', side_effect=OSError('rename failed')):
            self.assertFalse(self.model.delete_equipment('EQ0001'))
        self.assertEqual(original, self._raw_bytes())
        self.assertEqual([], self._leftover_tmp_files())


if __name__ == '__main__':
    unittest.main()
