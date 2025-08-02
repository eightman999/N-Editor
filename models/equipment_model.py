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

        # ユーザーデータディレクトリの設定
        self.user_data_dir = os.path.join(os.path.dirname(self.data_dir), 'user_data')
        os.makedirs(self.user_data_dir, exist_ok=True)
        self.unique_equipment_file = os.path.join(self.user_data_dir, 'unique_equipments.csv')

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
        装備データをunique_equipments.csvに保存
        
        Args:
            equipment_data: 保存する装備データ
            
        Returns:
            bool: 保存成功時True、失敗時False
        """
        equipment_id = equipment_data.get('common', {}).get('ID')
        if not equipment_id:
            logger.error("保存する装備データにIDがありません。")
            return False

        try:
            # データをフラットな辞書に変換
            flat_data = {}
            
            # commonデータを展開
            if 'common' in equipment_data:
                for key, value in equipment_data['common'].items():
                    if key == '必要資源' and isinstance(value, dict):
                        # ネストされた必要資源を展開
                        for resource, resource_value in value.items():
                            flat_data[f'必要資源_{resource}'] = resource_value
                    else:
                        flat_data[key] = value
            
            # specificデータを展開
            if 'specific' in equipment_data:
                flat_data.update(equipment_data['specific'])
            
            # equipment_typeも追加
            if 'equipment_type' in equipment_data:
                flat_data['equipment_type'] = equipment_data['equipment_type']

            # unique.csvを読み込んで更新または追記
            rows = []
            header = []
            updated = False
            
            if os.path.exists(self.unique_equipment_file):
                with open(self.unique_equipment_file, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    header = next(reader, [])
                    if header:
                        f.seek(0)  # ファイルポインタを先頭に戻す
                        dict_reader = csv.DictReader(f)
                        for row in dict_reader:
                            if row.get('ID') == equipment_id:
                                # データを更新
                                updated_row = dict(row)
                                updated_row.update(flat_data)
                                rows.append(updated_row)
                                updated = True
                            else:
                                rows.append(row)
            
            # 新規データの場合は追記
            if not updated:
                rows.append(flat_data)

            # ヘッダーを決定（既存ヘッダー + 新しいキー）
            if not header:
                header = list(flat_data.keys())
            else:
                for key in flat_data.keys():
                    if key not in header:
                        header.append(key)

            # ファイルに書き込み
            with open(self.unique_equipment_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=header)
                writer.writeheader()
                writer.writerows(rows)

            # メモリキャッシュとファイルキャッシュを更新
            self.equipment_cache[equipment_id] = equipment_data
            if self.cache_manager:
                self.cache_manager.invalidate("equipment_all_csv")  # キャッシュを無効化

            logger.info(f"装備 {equipment_id} を unique_equipments.csv に保存しました。")
            return True

        except Exception as e:
            logger.error(f"ユニーク装備の保存中にエラーが発生しました: {e}")
            return False

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
        装備データをunique_equipments.csvから削除
        
        Args:
            equipment_id: 削除する装備ID
            
        Returns:
            bool: 削除成功時True、失敗時False
        """
        if not equipment_id:
            logger.error("削除する装備IDが指定されていません。")
            return False

        try:
            # unique.csvが存在しない場合は削除対象なし
            if not os.path.exists(self.unique_equipment_file):
                logger.warning(f"装備 {equipment_id} はユニークファイルに存在しません。")
                return False

            rows = []
            header = []
            deleted = False
            
            with open(self.unique_equipment_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, [])
                if header:
                    f.seek(0)  # ファイルポインタを先頭に戻す
                    dict_reader = csv.DictReader(f)
                    for row in dict_reader:
                        if row.get('ID') == equipment_id:
                            # この行は削除対象のため追加しない
                            deleted = True
                            logger.info(f"装備 {equipment_id} を削除しました")
                        else:
                            rows.append(row)

            if not deleted:
                logger.warning(f"装備 {equipment_id} はユニークファイルに存在しません。")
                return False

            # ファイルに書き戻し
            with open(self.unique_equipment_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=header)
                writer.writeheader()
                writer.writerows(rows)

            # メモリキャッシュからも削除
            if equipment_id in self.equipment_cache:
                del self.equipment_cache[equipment_id]
            
            # ファイルキャッシュを無効化
            if self.cache_manager:
                self.cache_manager.invalidate("equipment_all_csv")

            logger.info(f"装備 {equipment_id} を unique_equipments.csv から削除しました。")
            return True

        except Exception as e:
            logger.error(f"ユニーク装備の削除中にエラーが発生しました: {e}")
            return False

    def get_next_id(self, equipment_type: str) -> str:
        """
        指定装備タイプの次のIDを生成
        マスターとユニークの両方のデータを参照して、最大IDに基づいて次のIDを生成
        
        Args:
            equipment_type: 装備タイプ
            
        Returns:
            str: 次のID
        """
        if not equipment_type:
            logger.error("装備タイプが指定されていません。")
            return ""

        try:
            # 装備タイプに対応するプレフィックスを取得
            prefix = self.get_prefix_for_type(equipment_type)
            if not prefix:
                logger.error(f"装備タイプ {equipment_type} のプレフィックスが見つかりません。")
                return ""

            # 全装備データを取得
            all_equipments = self.get_all_equipment()
            
            # 該当プレフィックスの装備IDを検索
            max_id_num = 0
            for equipment in all_equipments:
                equipment_id = equipment.get('common', {}).get('ID', '')
                if equipment_id.startswith(prefix):
                    # IDから数値部分を抽出
                    numeric_part = ''.join([c for c in equipment_id if c.isdigit()])
                    if numeric_part:
                        try:
                            current_num = int(numeric_part)
                            max_id_num = max(max_id_num, current_num)
                        except ValueError:
                            continue

            # 次のIDを生成（プレフィックス + 数値）
            next_id_num = max_id_num + 1
            next_id = f"{prefix}{next_id_num:04d}"  # 4桁0埋め

            logger.info(f"装備タイプ {equipment_type} の次のIDを生成: {next_id}")
            return next_id

        except Exception as e:
            logger.error(f"次のID生成中にエラーが発生しました: {e}")
            return ""

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
        data/equipments 内の全CSVファイルからマスター装備データを読み込み、
        その後unique_equipments.csvからユーザー作成装備データを読み込んで統合し、
        JSON ライクな構造に変換する
        """
        equipments_map = {}  # IDをキーとする辞書で管理
        
        # テンプレートからcommonとspecificのフィールドリストを作成
        common_fields = set(['名前', 'ID', '重量', '人員', '開発年', '開発国'])
        # resourcesはネストされているので特別扱い
        resource_fields = set(['必要資源_鉄', '必要資源_クロム', '必要資源_アルミ', '必要資源_タングステン', '必要資源_ゴム'])

        # 1. マスターCSVファイルの読み込み
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

                            # マスターデータをマップに追加
                            equipments_map[equipment_id] = equipment_data

                except Exception as e:
                    logger.error(f"CSV装備データ読み込みエラー ({file_path}): {e}")
        
        # 2. ユニーク装備データの読み込み（存在する場合）
        if os.path.exists(self.unique_equipment_file):
            try:
                with open(self.unique_equipment_file, 'r', encoding='utf-8') as f:
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

                        # ユニークデータでマスターデータを上書き（または新規追加）
                        equipments_map[equipment_id] = equipment_data
                        logger.info(f"ユニーク装備 {equipment_id} をロードしました")

            except Exception as e:
                logger.error(f"ユニークCSV装備データ読み込みエラー ({self.unique_equipment_file}): {e}")

        # 辞書の値をリストに変換
        all_equipments = list(equipments_map.values())
        
        # メモリキャッシュに保存
        for eq in all_equipments:
            equipment_id = eq.get('common', {}).get('ID')
            if equipment_id:
                self.equipment_cache[equipment_id] = eq
        
        return all_equipments