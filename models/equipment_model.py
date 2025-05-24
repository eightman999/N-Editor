import os
import json
import yaml
from typing import Dict, List, Any, Optional, Union


class EquipmentModel:
    """装備データモデル"""

    def __init__(self, data_dir: str = None):
        """
        初期化

        Args:
            data_dir: データディレクトリのパス（デフォルトは'../data/equipments'）
        """
        if data_dir is None:
            # デフォルトのデータディレクトリを設定
            self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'equipments')
        else:
            self.data_dir = data_dir

        # データディレクトリが存在しない場合は作成
        os.makedirs(self.data_dir, exist_ok=True)

        # 装備テンプレート（装備種別など）
        self.equipment_templates = self._load_equipment_templates()

        # キャッシュ（ID -> 装備データ）
        self.equipment_cache = {}

    def _load_equipment_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        装備テンプレートの読み込み

        Returns:
            Dict[str, Dict[str, Any]]: 装備テンプレート辞書
        """
        templates = {}

        try:
            # アプリのルートディレクトリを取得
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            # まず equipments_templates.yml を読み込む
            yaml_template_file = os.path.join(root_dir, 'equipments_templates.yml')

            if os.path.exists(yaml_template_file):
                print(f"装備テンプレートファイルを読み込み中: {yaml_template_file}")
                try:
                    with open(yaml_template_file, 'r', encoding='utf-8') as f:
                        yaml_data = yaml.safe_load(f)

                    # YAMLデータを解析して装備テンプレートを構築
                    self._parse_yaml_templates(yaml_data, templates)
                    print(f"YAMLテンプレートから {len(templates)} 種類の装備テンプレートを読み込みました")

                except Exception as e:
                    print(f"YAMLテンプレートファイルの読み込みエラー: {e}")

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
                print("警告: 装備テンプレートファイルが見つからないか、読み込みに失敗しました")

        except Exception as e:
            print(f"装備テンプレート読み込みエラー: {e}")

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
        装備データの保存

        Args:
            equipment_data: 装備データ辞書

        Returns:
            bool: 保存成功時True
        """
        try:
            equipment_type = equipment_data.get('equipment_type', '')
            equipment_id = equipment_data.get('common', {}).get('ID', '')

            if not equipment_type or not equipment_id:
                return False

            # IDプレフィックスの取得
            id_prefix = self.get_prefix_for_type(equipment_type)
            if not id_prefix:
                return False

            # 保存ディレクトリの作成
            save_dir = os.path.join(self.data_dir, id_prefix)
            os.makedirs(save_dir, exist_ok=True)

            # ファイル名は装備IDを使用
            file_path = os.path.join(save_dir, f"{equipment_id}.json")

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(equipment_data, f, ensure_ascii=False, indent=2)

            # キャッシュを更新
            self.equipment_cache[equipment_id] = equipment_data

            return True

        except Exception as e:
            print(f"装備データ保存エラー: {e}")
            return False

    def load_equipment(self, equipment_id: str) -> Optional[Dict[str, Any]]:
        """
        装備データの読み込み

        Args:
            equipment_id: 装備ID

        Returns:
            Optional[Dict[str, Any]]: 装備データ辞書（存在しない場合はNone）
        """
        # キャッシュにあれば返す
        if equipment_id in self.equipment_cache:
            return self.equipment_cache[equipment_id]

        # キャッシュにない場合はファイルから読み込み
        for type_dir in os.listdir(self.data_dir):
            dir_path = os.path.join(self.data_dir, type_dir)
            if not os.path.isdir(dir_path):
                continue

            file_path = os.path.join(dir_path, f"{equipment_id}.json")
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # キャッシュに保存
                    self.equipment_cache[equipment_id] = data
                    return data

                except Exception as e:
                    print(f"装備データ読み込みエラー: {e}")
                    return None

        return None

    def get_all_equipment(self, equipment_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        全装備データまたは指定タイプの装備データを取得

        Args:
            equipment_type: 装備タイプ（指定しない場合は全装備）

        Returns:
            List[Dict[str, Any]]: 装備データリスト
        """
        result = []

        if equipment_type:
            # 特定タイプの装備のみ
            id_prefix = self.get_prefix_for_type(equipment_type)
            if id_prefix:
                type_dir = os.path.join(self.data_dir, id_prefix)
                if os.path.exists(type_dir) and os.path.isdir(type_dir):
                    for file_name in os.listdir(type_dir):
                        if file_name.endswith('.json'):
                            file_path = os.path.join(type_dir, file_name)
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    data = json.load(f)

                                # キャッシュに保存
                                equipment_id = data.get('common', {}).get('ID', '')
                                if equipment_id:
                                    self.equipment_cache[equipment_id] = data

                                result.append(data)
                            except Exception as e:
                                print(f"装備データ読み込みエラー: {e}")
        else:
            # 全装備
            for type_dir in os.listdir(self.data_dir):
                dir_path = os.path.join(self.data_dir, type_dir)
                if not os.path.isdir(dir_path):
                    continue

                for file_name in os.listdir(dir_path):
                    if file_name.endswith('.json'):
                        file_path = os.path.join(dir_path, file_name)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)

                            # キャッシュに保存
                            equipment_id = data.get('common', {}).get('ID', '')
                            if equipment_id:
                                self.equipment_cache[equipment_id] = data

                            result.append(data)
                        except Exception as e:
                            print(f"装備データ読み込みエラー: {e}")

        return result

    def delete_equipment(self, equipment_id: str) -> bool:
        """
        装備データの削除

        Args:
            equipment_id: 装備ID

        Returns:
            bool: 削除成功時True
        """
        # 装備データがどのタイプか検索
        for type_dir in os.listdir(self.data_dir):
            dir_path = os.path.join(self.data_dir, type_dir)
            if not os.path.isdir(dir_path):
                continue

            file_path = os.path.join(dir_path, f"{equipment_id}.json")
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)

                    # キャッシュから削除
                    if equipment_id in self.equipment_cache:
                        del self.equipment_cache[equipment_id]

                    return True

                except Exception as e:
                    print(f"装備データ削除エラー: {e}")
                    return False

        return False

    def get_next_id(self, equipment_type: str) -> str:
        """
        指定装備タイプの次のIDを生成

        Args:
            equipment_type: 装備タイプ

        Returns:
            str: 次のID
        """
        id_prefix = self.get_prefix_for_type(equipment_type)
        if not id_prefix:
            return ""

        # プレフィックスディレクトリの装備を取得
        type_dir = os.path.join(self.data_dir, id_prefix)
        if not os.path.exists(type_dir):
            os.makedirs(type_dir, exist_ok=True)
            return f"{id_prefix}001"  # 最初の装備ID

        # 既存のIDから最大値を取得
        max_number = 0
        for file_name in os.listdir(type_dir):
            if file_name.endswith('.json'):
                try:
                    # ファイル名（拡張子なし）＝装備ID
                    equipment_id = file_name[:-5]
                    # プレフィックス部分を取り除いて数値部分を取得
                    if equipment_id.startswith(id_prefix):
                        number_part = equipment_id[len(id_prefix):]
                        if number_part.isdigit():
                            number = int(number_part)
                            max_number = max(max_number, number)
                except Exception:
                    pass

        # 次の番号を生成
        next_number = max_number + 1
        return f"{id_prefix}{next_number:03d}"