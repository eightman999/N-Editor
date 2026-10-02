# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: test_design_persistence 設計データ永続化テスト
"""設計JSONの保存/読込/一覧/削除のディレクトリ一貫性と原子的保存のテスト

PyQt5等のGUI依存が無い環境でも実コードを検証するため、
controllers/app_controller.py をAST解析して対象メソッドのみを
抽出・実行し、協力オブジェクト(船体/装備/同期/キャッシュ)はスタブ化する。
"""

import ast
import json
import logging
import os
import shutil
import sys
import tempfile
import time
import types
import unittest
from typing import Any, Dict, List, Optional
from unittest import mock

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from utils.path_utils import get_data_dir
from utils.file_utils import atomic_write_text

_CONTROLLER_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'controllers', 'app_controller.py'))

# 抽出対象のメソッド名（get_all_designsは2回定義されるため最後の定義=実効定義を採用）
_METHOD_NAMES = (
    '_get_design_dirs',
    'save_design',
    'load_design',
    'get_all_designs',
    'delete_design',
    'load_design_from_file',
    'get_nation_designs',
)


def _load_controller_namespace():
    """app_controller.py から対象メソッドの実コードをASTで抽出して実行する"""
    with open(_CONTROLLER_PATH, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())

    cls = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == 'AppController'
    )
    selected = {}
    for node in cls.body:
        if isinstance(node, ast.FunctionDef) and node.name in _METHOD_NAMES:
            selected[node.name] = node  # 同名は後勝ち（実効定義）

    namespace = {
        'os': os,
        'json': json,
        'time': time,
        'logger': logging.getLogger(__name__),
        'get_data_dir': get_data_dir,
        'atomic_write_text': atomic_write_text,
        'List': List,
        'Dict': Dict,
        'Any': Any,
        'Optional': Optional,
    }
    for node in selected.values():
        module = ast.Module(body=[node], type_ignores=[])
        exec(compile(module, _CONTROLLER_PATH, 'exec'), namespace)
    return namespace


def _make_controller(namespace, design_dir, data_dir):
    """抽出した実メソッドを持つスタブコントローラを生成する"""
    controller_class = type('StubbedAppController', (), {
        name: namespace[name] for name in _METHOD_NAMES if name in namespace
    })
    controller = controller_class()
    controller.app_settings = types.SimpleNamespace(
        design_dir=design_dir,
        data_dir=data_dir,
    )
    controller.equipment_model = mock.Mock()
    controller.equipment_model.save_equipment.return_value = True
    controller.sync_manager = mock.Mock()
    controller.mod_cache_manager = None
    controller.load_hull = lambda hull_id: {'id': hull_id, 'name': 'hull'}
    controller._regenerate_equipment_for_hull = lambda eid, hull: (None, None)
    return controller


def _design_payload(design_id='D1', name='テスト設計', country='JPN'):
    return {
        'id': design_id,
        'design_name': name,
        'hull_id': 'H1',
        'country': country,
        'main_slots': {},
        'internal_slots': [],
    }


def _write_legacy_design(legacy_dir, design_id, name='レガシー設計'):
    """旧Documents配下にヘッダー付き設計ファイルを直接作成する"""
    os.makedirs(legacy_dir, exist_ok=True)
    file_path = os.path.join(legacy_dir, f'{design_id}.json')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('@config.design\n')
        json.dump(_design_payload(design_id, name), f, ensure_ascii=False, indent=2)
    return file_path


class TestDesignDirectoryConsistency(unittest.TestCase):
    """save/load/list/delete が設定ディレクトリで一貫し、旧パスをフォールバック参照すること"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        # 偽HOME: get_data_dir('designs') は <HOME>/Documents/NavalDesignSystem/designs を指す
        self.fake_home = os.path.join(self.test_dir, 'home')
        os.makedirs(self.fake_home, exist_ok=True)
        self._home_patcher = mock.patch.dict(os.environ, {'HOME': self.fake_home})
        self._home_patcher.start()
        # 設定された(正規の)設計ディレクトリ（Linuxの .local/share 相当）
        self.design_dir = os.path.join(self.test_dir, 'share', 'navaldesignsystem', 'designs')
        # data_dir は design_dir と別系統にし、data_dir/designs への誤参照を検出可能にする
        self.data_dir = os.path.join(self.test_dir, 'other_data')
        self.legacy_dir = get_data_dir('designs')  # Documents側（makedirsされる）
        self.namespace = _load_controller_namespace()
        self.controller = _make_controller(self.namespace, self.design_dir, self.data_dir)

    def tearDown(self):
        self._home_patcher.stop()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _leftover_tmp_files(self, directory):
        if not os.path.exists(directory):
            return []
        return [f for f in os.listdir(directory) if f.endswith('.tmp')]

    # --- 保存先の一貫性 ---

    def test_save_writes_to_configured_design_dir(self):
        self.assertTrue(self.controller.save_design(_design_payload('D1')))
        saved_path = os.path.join(self.design_dir, 'D1.json')
        self.assertTrue(os.path.exists(saved_path))
        # 旧Documents配下には書き込まれないこと
        self.assertFalse(os.path.exists(os.path.join(self.legacy_dir, 'D1.json')))
        # @config.design ヘッダーが維持されていること
        with open(saved_path, 'r', encoding='utf-8') as f:
            self.assertEqual('@config.design', f.readline().strip())
            data = json.loads(f.read())
        self.assertEqual('D1', data['id'])
        self.assertEqual('テスト設計', data['design_name'])

    def test_save_then_load_roundtrip(self):
        self.assertTrue(self.controller.save_design(_design_payload('D1')))
        loaded = self.controller.load_design('D1')
        self.assertIsNotNone(loaded)
        self.assertEqual('D1', loaded['id'])
        self.assertEqual('テスト設計', loaded['design_name'])

    def test_get_all_designs_lists_saved_design(self):
        self.assertTrue(self.controller.save_design(_design_payload('D1')))
        designs = self.controller.get_all_designs()
        ids = [d.get('id') for d in designs]
        self.assertIn('D1', ids)

    def test_delete_removes_saved_design(self):
        self.assertTrue(self.controller.save_design(_design_payload('D1')))
        self.assertTrue(self.controller.delete_design('D1'))
        self.assertIsNone(self.controller.load_design('D1'))
        self.assertNotIn('D1', [d.get('id') for d in self.controller.get_all_designs()])

    # --- 旧Documentsディレクトリのフォールバック ---

    def test_load_falls_back_to_legacy_dir(self):
        _write_legacy_design(self.legacy_dir, 'LEG1')
        loaded = self.controller.load_design('LEG1')
        self.assertIsNotNone(loaded)
        self.assertEqual('LEG1', loaded['id'])

    def test_get_all_designs_includes_legacy_only_files(self):
        _write_legacy_design(self.legacy_dir, 'LEG1')
        self.assertTrue(self.controller.save_design(_design_payload('D1')))
        ids = [d.get('id') for d in self.controller.get_all_designs()]
        self.assertIn('D1', ids)
        self.assertIn('LEG1', ids)

    def test_configured_dir_wins_on_name_conflict(self):
        _write_legacy_design(self.legacy_dir, 'D1', name='旧コピー')
        self.assertTrue(self.controller.save_design(_design_payload('D1', name='新コピー')))
        loaded = self.controller.load_design('D1')
        self.assertEqual('新コピー', loaded['design_name'])
        designs = self.controller.get_all_designs()
        d1_entries = [d for d in designs if d.get('id') == 'D1']
        self.assertEqual(1, len(d1_entries))
        self.assertEqual('新コピー', d1_entries[0]['design_name'])

    def test_delete_removes_legacy_only_file(self):
        _write_legacy_design(self.legacy_dir, 'LEG1')
        self.assertTrue(self.controller.delete_design('LEG1'))
        self.assertFalse(os.path.exists(os.path.join(self.legacy_dir, 'LEG1.json')))

    def test_delete_refuses_on_duplicate_conflict(self):
        # 同名設計が設定ディレクトリと旧ディレクトリの両方にある場合は
        # 部分的な削除による復活を防ぐため、どちらも削除せず拒否する
        _write_legacy_design(self.legacy_dir, 'D1')
        self.assertTrue(self.controller.save_design(_design_payload('D1')))
        self.assertFalse(self.controller.delete_design('D1'))
        self.assertTrue(os.path.exists(os.path.join(self.design_dir, 'D1.json')))
        self.assertTrue(os.path.exists(os.path.join(self.legacy_dir, 'D1.json')))
        # 拒否後も設定ディレクトリ側が有効なまま読み込めること
        self.assertEqual('テスト設計', self.controller.load_design('D1')['design_name'])

    def test_delete_failure_preserves_single_file(self):
        self.assertTrue(self.controller.save_design(_design_payload('D1')))
        saved_path = os.path.join(self.design_dir, 'D1.json')
        with open(saved_path, 'rb') as f:
            original = f.read()
        with mock.patch('os.remove', side_effect=PermissionError('denied')):
            self.assertFalse(self.controller.delete_design('D1'))
        with open(saved_path, 'rb') as f:
            self.assertEqual(original, f.read())

    def test_load_missing_returns_none(self):
        self.assertIsNone(self.controller.load_design('NOPE'))

    def test_delete_missing_returns_false(self):
        self.assertFalse(self.controller.delete_design('NOPE'))

    # --- 原子的保存 ---

    def test_save_replace_failure_preserves_existing_file(self):
        self.assertTrue(self.controller.save_design(_design_payload('D1', name='初回')))
        saved_path = os.path.join(self.design_dir, 'D1.json')
        with open(saved_path, 'rb') as f:
            original = f.read()
        with mock.patch('os.replace', side_effect=OSError('rename failed')):
            self.assertFalse(self.controller.save_design(_design_payload('D1', name='更新不可')))
        with open(saved_path, 'rb') as f:
            self.assertEqual(original, f.read())
        self.assertEqual([], self._leftover_tmp_files(self.design_dir))

    def test_save_dump_failure_leaves_no_partial_file(self):
        with mock.patch('json.dump', side_effect=TypeError('serialization failed')):
            self.assertFalse(self.controller.save_design(_design_payload('D1')))
        # 初回保存の失敗では対象ファイル自体を残さないこと
        self.assertFalse(os.path.exists(os.path.join(self.design_dir, 'D1.json')))
        self.assertEqual([], self._leftover_tmp_files(self.design_dir))

    # --- 国家別設計の取得 ---

    def test_get_nation_designs_reads_saved_headered_files(self):
        # design_dir が data_dir/designs と異なる構成でも保存済み設計を取得できること
        self.assertTrue(self.controller.save_design(_design_payload('D1', country='JPN')))
        self.assertTrue(self.controller.save_design(_design_payload('D2', country='USA')))
        nation_designs = self.controller.get_nation_designs('JPN')
        ids = [d.get('id') for d in nation_designs]
        self.assertIn('D1', ids)
        self.assertNotIn('D2', ids)
        entry = next(d for d in nation_designs if d.get('id') == 'D1')
        self.assertEqual('テスト設計', entry['design_name'])

    def test_get_nation_designs_falls_back_to_legacy_dir(self):
        _write_legacy_design(self.legacy_dir, 'LEG1')
        nation_designs = self.controller.get_nation_designs('JPN')
        self.assertIn('LEG1', [d.get('id') for d in nation_designs])

    def test_get_data_dir_create_false_makes_no_directories(self):
        probe = os.path.join(self.fake_home, 'Documents', 'NavalDesignSystem', 'probe_type')
        if os.path.exists(probe):
            shutil.rmtree(probe)
        result = get_data_dir('probe_type', create=False)
        self.assertEqual(probe, result)
        self.assertFalse(os.path.exists(probe))


if __name__ == '__main__':
    unittest.main()
