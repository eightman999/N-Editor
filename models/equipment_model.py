# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: equipment_modelデータモデル
import os
import json
import yaml
import time
import logging
import csv
from typing import Dict, List, Any, Optional, Union

# ロガーの設定
logger = logging.getLogger(__name__)


class EquipmentModel:
    """装備データモデル"""

    def __init__(self, data_dir: str = None, cache_manager=None):
        """
        初期化

        Args:
            data_dir: データディレクトリのパス（必須）
            cache_manager: キャッシュマネージャーのインスタンス
        """
        if data_dir is None:
            raise ValueError("data_dir parameter is required for CSV-based equipment data")
        self.data_dir = data_dir

        # データディレクトリが存在しない場合は作成
        os.makedirs(self.data_dir, exist_ok=True)

        # キャッシュマネージャー
        self.cache_manager = cache_manager

        # 装備テンプレート（装備種別など）
        self.equipment_templates = self._load_equipment_templates()
        
        # IDプレフィックスから装備タイプへの逆引きマップを作成
        self.prefix_to_type_map = self._create_prefix_to_type_map()

        # キャッシュ（ID -> 装備データ）
        self.equipment_cache = {}

    def _create_prefix_to_type_map(self) -> Dict[str, str]:
        """IDプレフィックスから装備タイプ名へのマッピングを作成"""
        prefix_map = {}
        if hasattr(self, 'equipment_templates'):
            for equipment_type, template in self.equipment_templates.items():
                if 'id_prefix' in template:
                    prefix_map[template['id_prefix']] = equipment_type
        return prefix_map

    def _load_equipment_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        装備テンプレートの読み込み（キャッシュ対応）

        Returns:
            Dict[str, Dict[str, Any]]: 装備テンプレート辞書
        """
        start_time = time.time()
        
        # アプリのルートディレクトリを取得
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        yaml_template_file = os.path.join(root_dir, 'equipments_templates.yml')
        
        # キャッシュから読み込み試行
        if self.cache_manager and os.path.exists(yaml_template_file):
            cached_data = self.cache_manager.load("equipment_templates", yaml_template_file)
            if cached_data is not None:
                duration = time.time() - start_time
                logger.debug(f"装備テンプレートをキャッシュから読み込み: {len(cached_data)}種類, 時間: {duration:.3f}秒")
                return cached_data

        templates = {}

        try:
            # まず equipments_templates.yml を読み込む
            if os.path.exists(yaml_template_file):
                logger.info(f"装備テンプレートファイルを読み込み中: {yaml_template_file}")
                try:
                    with open(yaml_template_file, 'r', encoding='utf-8') as f:
                        yaml_data = yaml.safe_load(f)

                    # YAMLデータを解析して装備テンプレートを構築
                    self._parse_yaml_templates(yaml_data, templates)
                    logger.info(f"YAMLテンプレートから {len(templates)} 種類の装備テンプレートを読み込みました")

                except Exception as e:
                    logger.error(f"YAMLテンプレートファイルの読み込みエラー: {e}")

            # 次に paste.txt もチェック（互換性のため）
            paste_template_file = os.path.join(root_dir, 'paste.txt')

            # ユーザーのドキュメントディレクトリ内のpaste.txtも検索
            if not os.path.exists(paste_template_file):
                import platform
                from pathlib import Path

                if platform.system() == "Windows":
                    docs_dir = os.path.join(Path.home(), "Documents", "NavalDesignSystem")
                elif platform.system() == "Darwin":
                    docs_dir = os.path.join(Path.home(), "Library", "Application Support", "NavalDesignSystem")
                else:
                    docs_dir = os.path.join(Path.home(), ".local", "share", "navaldesignsystem")

                paste_template_file = os.path.join(docs_dir, 'paste.txt')

            if os.path.exists(paste_template_file):
                print(f"追加テンプレートファイルを読み込み中: {paste_template_file}")
                try:
                    with open(paste_template_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # YAMLライクな形式をパースする簡易実装（既存の互換性のため）
                    self._parse_paste_templates(content, templates)
                    print(f"paste.txtから追加テンプレートを読み込みました")

                except Exception as e:
                    print(f"paste.txtテンプレートファイルの読み込みエラー: {e}")

            if not templates:
                logger.warning("警告: 装備テンプレートファイルが見つからないか、読み込みに失敗しました")

            # キャッシュに保存
            if templates and self.cache_manager:
                self.cache_manager.save("equipment_templates", yaml_template_file, templates)

        except Exception as e:
            logger.error(f"装備テンプレート読み込みエラー: {e}")

        duration = time.time() - start_time
        logger.info(f"装備テンプレート読み込み完了: {len(templates)}種類, 時間: {duration:.3f}秒")
        
        return templates

    def _parse_yaml_templates(self, yaml_data: dict, templates: dict):
        """YAMLデータから装備テンプレートを解析"""
        try:
            # 各カテゴリーを処理
            for category_name, category_data in yaml_data.items():
                if isinstance(category_data, dict):
                    # カテゴリー内の各装備タイプを処理
                    for equipment_name, equipment_data in category_data.items():
                        if isinstance(equipment_data, dict) and 'id_prefix' in equipment_data:
                            # 表示名を取得（存在する場合）
                            display_name = equipment_data.get('display_name', equipment_name)

                            # テンプレートデータを構築
                            template_entry = {
                                'category': category_name,
                                'display_name': display_name,
                                'id_prefix': equipment_data['id_prefix'],
                                'common_elements': equipment_data.get('common_elements', {}),
                                'specific_elements': equipment_data.get('specific_elements', {})
                            }

                            # 装備名をキーとして保存
                            templates[equipment_name] = template_entry

                            # 表示名でもアクセス可能にする（異なる場合）
                            if display_name != equipment_name:
                                templates[display_name] = template_entry

                            print(
                                f"装備テンプレートを追加: {equipment_name} ({display_name}) - プレフィックス: {equipment_data['id_prefix']}")

        except Exception as e:
            print(f"YAMLテンプレート解析エラー: {e}")

    def _parse_paste_templates(self, content: str, templates: dict):
        """paste.txtの内容を解析（既存の互換性のため）"""
        try:
            current_type = None

            for line in content.split('\n'):
                if line.strip() and not line.startswith('#'):
                    if ':' in line and not line.startswith(' '):
                        # トップレベルの定義（装備タイプ）
                        current_type = line.split(':')[0].strip()
                        if current_type not in templates:
                            templates[current_type] = {'common_elements': {}, 'specific_elements': {}}
                    elif 'id_prefix:' in line and current_type:
                        prefix = line.split('id_prefix:')[1].strip()
                        templates[current_type]['id_prefix'] = prefix
                        print(f"paste.txtから装備テンプレートを追加: {current_type} - プレフィックス: {prefix}")
                    elif 'common_elements:' in line or 'specific_elements:' in line:
                        # セクション定義は無視（パース簡易化のため）
                        pass

        except Exception as e:
            print(f"paste.txtテンプレート解析エラー: {e}")

    def get_equipment_types(self) -> List[str]:
        """
        利用可能な装備タイプの一覧を取得

        Returns:
            List[str]: 装備タイプのリスト
        """
        return list(self.equipment_templates.keys())

    def get_equipment_categories(self) -> Dict[str, List[str]]:
        """
        装備カテゴリー別の装備タイプ一覧を取得

        Returns:
            Dict[str, List[str]]: カテゴリー名をキーとした装備タイプのリスト
        """
        categories = {}
        for equipment_type, template in self.equipment_templates.items():
            category = template.get('category', 'その他')
            if category not in categories:
                categories[category] = []
            categories[category].append(equipment_type)
        return categories

    def get_equipment_display_name(self, equipment_type: str) -> str:
        """
        装備タイプの表示名を取得

        Args:
            equipment_type: 装備タイプ

        Returns:
            str: 表示名
        """
        if equipment_type in self.equipment_templates:
            return self.equipment_templates[equipment_type].get('display_name', equipment_type)
        return equipment_type

    def get_prefix_for_type(self, equipment_type: str) -> str:
        """
        装備タイプからIDプレフィックスを取得

        Args:
            equipment_type: 装備タイプ

        Returns:
            str: IDプレフィックス
        """
        if equipment_type in self.equipment_templates:
            return self.equipment_templates[equipment_type].get('id_prefix', '')
        return ''

    def get_template_elements(self, equipment_type: str) -> Dict[str, Any]:
        """
        装備タイプのテンプレート要素を取得

        Args:
            equipment_type: 装備タイプ

        Returns:
            Dict[str, Any]: テンプレート要素（common_elements, specific_elements）
        """
        if equipment_type in self.equipment_templates:
            template = self.equipment_templates[equipment_type]
            return {
                'common_elements': template.get('common_elements', {}),
                'specific_elements': template.get('specific_elements', {})
            }
        return {'common_elements': {}, 'specific_elements': {}}

    def save_equipment(self, equipment_data: Dict[str, Any]) -> bool:
        """
        装備データの保存（CSVベースでは未実装）
        """
        logger.error("CSVをマスターデータとしているため、個別の装備保存は現在サポートされていません。")
        raise NotImplementedError("Saving individual equipment is not supported when using CSV as the master data.")

    def load_equipment(self, equipment_id: str) -> Optional[Dict[str, Any]]:
        """
        装備データの読み込み

        Args:
            equipment_id: 装備ID

        Returns:
            Optional[Dict[str, Any]]: 装備データ辞書（存在しない場合はNone）
        """
        # メモリキャッシュにあれば返す
        if equipment_id in self.equipment_cache:
            return self.equipment_cache[equipment_id]

        # キャッシュにない場合は全データをロードして探す
        self.get_all_equipment() # これで全データがロードされ、キャッシュされる
        
        return self.equipment_cache.get(equipment_id)

    def get_all_equipment(self, equipment_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        全装備データまたは指定タイプの装備データを取得（キャッシュ対応）

        Args:
            equipment_type: 装備タイプ（指定しない場合は全装備）

        Returns:
            List[Dict[str, Any]]: 装備データリスト
        """
        start_time = time.time()
        
        # キャッシュキーを生成 (CSVベースなので、ディレクトリの最終更新時刻なども考慮するとより堅牢)
        cache_key = f"{self.data_dir}:all_csv"
        
        # キャッシュから読み込み試行
        if self.cache_manager:
            cached_data = self.cache_manager.load("equipment_all_csv", cache_key)
            if cached_data is not None:
                # メモリキャッシュも更新
                for equipment_data in cached_data:
                    equipment_id = equipment_data.get('common', {}).get('ID', '')
                    if equipment_id:
                        self.equipment_cache[equipment_id] = equipment_data
                
                duration = time.time() - start_time
                logger.debug(f"全装備データをキャッシュから読み込み: {len(cached_data)}件, 時間: {duration:.3f}秒")
                
                if equipment_type:
                    display_name = self.get_equipment_display_name(equipment_type)
                    return [eq for eq in cached_data if eq.get("equipment_type") == display_name]
                return cached_data

        # キャッシュがない場合、CSVから全データをロード
        all_equipments = self._load_all_equipments_from_csv()
        
        # ファイルキャッシュに保存
        if all_equipments and self.cache_manager:
            self.cache_manager.save("equipment_all_csv", cache_key, all_equipments)
            
        duration = time.time() - start_time
        logger.info(f"全装備データをCSVから読み込み完了: {len(all_equipments)}件, 時間: {duration:.3f}秒")

        if equipment_type:
            display_name = self.get_equipment_display_name(equipment_type)
            return [eq for eq in all_equipments if eq.get("equipment_type") == display_name]

        return all_equipments

    def delete_equipment(self, equipment_id: str) -> bool:
        """
        装備データの削除（CSVベースでは未実装）
        """
        logger.error("CSVをマスターデータとしているため、個別の装備削除は現在サポートされていません。")
        raise NotImplementedError("Deleting individual equipment is not supported when using CSV as the master data.")

    def get_next_id(self, equipment_type: str) -> str:
        """
        指定装備タイプの次のIDを生成（CSVベースでは未実装）
        """
        logger.error("CSVをマスターデータとしているため、IDの自動採番は現在サポートされていません。")
        raise NotImplementedError("Automatic ID generation is not supported when using CSV as the master data.")

    def get_equipment_type_mapping(self) -> Dict[str, str]:
        """
        装備タイプのキー名→表示名マッピングを取得

        Returns:
            Dict[str, str]: キー名をキー、表示名を値とする辞書
        """
        mapping = {}
        processed = set()

        for key, template in self.equipment_templates.items():
            if 'display_name' in template:
                display_name = template['display_name']
                # 表示名が別のキーとして登録されている場合は、元のキーを優先
                if key != display_name and key not in processed:
                    mapping[key] = display_name
                    processed.add(key)
                    processed.add(display_name)
                elif key == display_name and key not in processed:
                    mapping[key] = display_name
                    processed.add(key)

        return mapping

    def _load_all_equipments_from_csv(self) -> List[Dict[str, Any]]:
        """
        data/equipments 内の全CSVファイルから装備データを読み込み、JSONライクな構造に変換する
        """
        all_equipments = []
        
        # テンプレートからcommonとspecificのフィールドリストを作成
        common_fields = set(['名前', 'ID', '重量', '人員', '開発年', '開発国'])
        # resourcesはネストされているので特別扱い
        resource_fields = set(['必要資源_鉄', '必要資源_クロム', '必要資源_アルミ', '必要資源_タングステン', '必要資源_ゴム'])

        for file in os.listdir(self.data_dir):
            if file.endswith('.csv'):
                file_path = os.path.join(self.data_dir, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            equipment_id = row.get('ID')
                            if not equipment_id:
                                continue

                            # IDプレフィックスから装備タイプを特定
                            prefix = ''.join([c for c in equipment_id if c.isalpha()])
                            equipment_type = self.prefix_to_type_map.get(prefix, 'その他')
                            display_name = self.get_equipment_display_name(equipment_type)

                            equipment_data = {
                                "equipment_type": display_name,
                                "common": {},
                                "specific": {}
                            }

                            for key, value in row.items():
                                # 空文字列は適切なデフォルト値に変換
                                if value == '' or value is None:
                                    value = 0 if key in ['重量', '人員', '開発年'] or key.startswith('必要資源_') else value
                                
                                # 数値変換を試みる
                                try:
                                    if isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit():
                                        if '.' in value:
                                            value = float(value)
                                        else:
                                            value = int(value)
                                except (ValueError, TypeError):
                                    pass # 変換できない場合は文字列のまま

                                if key in common_fields:
                                    equipment_data["common"][key] = value
                                elif key in resource_fields:
                                    # "必要資源_"プレフィックスを除去してネスト構造作成
                                    resource_name = key.replace('必要資源_', '')
                                    if "必要資源" not in equipment_data["common"]:
                                        equipment_data["common"]["必要資源"] = {}
                                    equipment_data["common"]["必要資源"][resource_name] = value
                                else:
                                    equipment_data["specific"][key] = value

                            all_equipments.append(equipment_data)
                            # メモリキャッシュにも保存
                            self.equipment_cache[equipment_id] = equipment_data

                except Exception as e:
                    logger.error(f"CSV装備データ読み込みエラー ({file_path}): {e}")
        
        return all_equipments