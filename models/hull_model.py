import os
import json
from typing import Dict, List, Any, Optional, Union

class HullModel:
    """船体データモデル"""

    def __init__(self, data_dir: str = None):
        """
        初期化

        Args:
            data_dir: データディレクトリのパス（デフォルトは'../data/hulls'）
        """
        if data_dir is None:
            # デフォルトのデータディレクトリを設定
            self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'hulls')
        else:
            self.data_dir = data_dir

        # データディレクトリが存在しない場合は作成
        os.makedirs(self.data_dir, exist_ok=True)

        # キャッシュ（ID -> 船体データ）
        self.hull_cache = {}

    def save_hull(self, hull_data: Dict[str, Any]) -> bool:
        """
        船体データの保存

        Args:
            hull_data: 船体データ辞書

        Returns:
            bool: 保存成功時True
        """
        try:
            hull_id = hull_data.get('id', '')

            if not hull_id:
                return False

            # 保存ディレクトリの確認
            os.makedirs(self.data_dir, exist_ok=True)

            # ファイル名は船体IDを使用
            file_path = os.path.join(self.data_dir, f"{hull_id}.json")

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(hull_data, f, ensure_ascii=False, indent=2)

            # キャッシュを更新
            self.hull_cache[hull_id] = hull_data

            return True

        except Exception as e:
            print(f"船体データ保存エラー: {e}")
            return False

    def load_hull(self, hull_id: str) -> Optional[Dict[str, Any]]:
        """
        船体データの読み込み

        Args:
            hull_id: 船体ID

        Returns:
            Optional[Dict[str, Any]]: 船体データ辞書（存在しない場合はNone）
        """
        # キャッシュにあれば返す
        if hull_id in self.hull_cache:
            return self.hull_cache[hull_id]

        # キャッシュにない場合はファイルから読み込み
        file_path = os.path.join(self.data_dir, f"{hull_id}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # キャッシュに保存
                self.hull_cache[hull_id] = data
                return data

            except Exception as e:
                print(f"船体データ読み込みエラー: {e}")
                return None

        return None

    def get_all_hulls(self) -> List[Dict[str, Any]]:
        """
        全船体データを取得

        Returns:
            List[Dict[str, Any]]: 船体データリスト
        """
        result = []

        # 全船体
        if os.path.exists(self.data_dir):
            for file_name in os.listdir(self.data_dir):
                if file_name.endswith('.json'):
                    file_path = os.path.join(self.data_dir, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        # キャッシュに保存
                        hull_id = data.get('id', '')
                        if hull_id:
                            self.hull_cache[hull_id] = data

                        result.append(data)
                    except Exception as e:
                        print(f"船体データ読み込みエラー: {e}")

        return result

    def delete_hull(self, hull_id: str) -> bool:
        """
        船体データの削除

        Args:
            hull_id: 船体ID

        Returns:
            bool: 削除成功時True
        """
        file_path = os.path.join(self.data_dir, f"{hull_id}.json")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)

                # キャッシュから削除
                if hull_id in self.hull_cache:
                    del self.hull_cache[hull_id]

                return True

            except Exception as e:
                print(f"船体データ削除エラー: {e}")
                return False

        return False

    def get_next_id(self, prefix: str = "HULL") -> str:
        """
        次の船体IDを生成

        Args:
            prefix: IDのプレフィックス

        Returns:
            str: 次のID
        """
        # 既存のIDから最大値を取得
        max_number = 0

        if os.path.exists(self.data_dir):
            for file_name in os.listdir(self.data_dir):
                if file_name.endswith('.json'):
                    try:
                        # ファイル名（拡張子なし）＝船体ID
                        hull_id = file_name[:-5]
                        # プレフィックス部分を取り除いて数値部分を取得
                        if hull_id.startswith(prefix):
                            number_part = hull_id[len(prefix):]
                            if number_part.isdigit():
                                number = int(number_part)
                                max_number = max(max_number, number)
                    except Exception:
                        pass

        # 次の番号を生成
        next_number = max_number + 1
        return f"{prefix}{next_number:03d}"

    def import_from_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """
        CSVから船体データをインポート

        Args:
            file_path: CSVファイルのパス

        Returns:
            List[Dict[str, Any]]: インポートされた船体データのリスト
        """
        import csv

        imported_hulls = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    hull_data = self._convert_csv_row_to_hull_data(row)

                    if hull_data and 'id' in hull_data:
                        # 船体データを保存
                        if self.save_hull(hull_data):
                            imported_hulls.append(hull_data)

        except Exception as e:
            print(f"CSVインポートエラー: {e}")

        return imported_hulls

    def _convert_csv_row_to_hull_data(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        CSVの行データを船体データ形式に変換

        Args:
            row: CSVの行データ

        Returns:
            Optional[Dict[str, Any]]: 変換された船体データ（変換できない場合はNone）
        """
        hull_data = {}

        # CSVから読み込めるデータのマッピング
        field_mapping = {
            '艦級名': 'name',
            'システム名称': 'id',
            'weight': 'weight',
            'length': 'length',
            'width': 'width',
            'power': 'power',
            'speed': 'speed',
            'range': 'range',
            'cruise_speed': 'cruise_speed',
            'fuel_capacity': 'fuel_capacity',
            'armor_max': 'armor_max',
            'armor_min': 'armor_min',
            '船殻構造': 'hull_structure_id',
            '装甲種別': 'armor_type_id',
            'crew': 'crew',
            'country': 'country',
            '種別': 'class',
            'year': 'year',
            'archetype': 'archetype',
            'TYPE': 'type'
        }

        # 基本情報の変換
        for csv_field, data_field in field_mapping.items():
            if csv_field in row:
                hull_data[data_field] = row[csv_field]

        # IDが未設定の場合は新しいIDを生成
        if not hull_data.get('id') or hull_data.get('id') == '-':
            hull_data['id'] = self.get_next_id('HULL')

        # 数値型フィールドの変換
        numeric_fields = ['weight', 'length', 'width', 'power', 'speed', 'range',
                          'cruise_speed', 'fuel_capacity', 'armor_max', 'armor_min',
                          'crew', 'year', 'hull_structure_id', 'armor_type_id']

        for field in numeric_fields:
            if field in hull_data:
                try:
                    # '#REF!'などの特殊値を処理
                    if hull_data[field] in ['', '#REF!', 'NULL']:
                        hull_data[field] = 0
                    else:
                        hull_data[field] = float(hull_data[field])
                except ValueError:
                    hull_data[field] = 0

        # 船殻構造を数値IDから文字列表現に変換
        hull_structure_mapping = {
            0: 'なし',
            0.8: 'ライト',
            1.0: 'ミディアム',
            1.3: 'ヘビー',
            1.5: 'スーパーヘビー',
            1.75: 'ウルトラヘビー',
            2.0: 'マキシマムヘビー'
        }

        if 'hull_structure_id' in hull_data:
            hull_id = hull_data['hull_structure_id']
            hull_data['hull_structure'] = hull_structure_mapping.get(hull_id, 'ミディアム')

        # 装甲種別を数値IDから文字列表現に変換
        armor_type_mapping = {
            0: 'なし',
            1.0: '装甲なし',
            1.35: '軽装甲',
            1.4: '標準装甲',
            1.5: '重装甲',
            1.8: '特殊装甲',
            2.0: '複合装甲'
        }

        if 'armor_type_id' in hull_data:
            armor_id = hull_data['armor_type_id']
            hull_data['armor_type'] = armor_type_mapping.get(armor_id, '標準装甲')

        # スロット情報の処理
        slots = {}
        slot_fields = ['PA', 'SA', 'PSA', 'SSA', 'PLA', 'SLA']

        for slot in slot_fields:
            if slot in row:
                # スロット値のマッピング
                value = row[slot]
                if value == '':
                    slots[slot] = ' '  # 有効
                elif value == '-':
                    slots[slot] = '-'  # 無効
                elif value == '=':
                    slots[slot] = '='  # 有効化可能
                else:
                    slots[slot] = ' '  # デフォルトは有効

        hull_data['slots'] = slots

        return hull_data