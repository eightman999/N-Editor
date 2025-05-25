import os
import json
import csv
import re
import time
from typing import Dict, List, Any, Optional, Union

from tools.japanese_tools import convert_name


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

        # 艦種の種別データベース
        self.ship_type_mapping = {
            # 掃海艦艇
            "AM": "AM - 掃海艇",
            "CMC": "CMC - 沿岸敷設艇",
            "MCM": "MCM - 掃海艦",
            "MCS": "MCS - 掃海母艦",

            # 空母系
            "AV": "AV - 水上機母艦",
            "CV": "CV - 航空母艦",
            "CVE": "CVE - 護衛空母",
            "CVL": "CVL - 軽空母",
            "CVS": "CVS - 対潜空母",
            "SV": "SV - 飛行艇母艦",

            # 揚陸艦艇
            "LCSL": "LCSL - 上陸支援艇",

            # 小型艦艇（哨戒・砲艦など）
            "PC": "PC - 哨戒艇、駆潜艇",
            "PT": "PT - 高速魚雷艇",
            "FF": "FF - フリゲート",
            "K": "K - コルベット",
            "MB": "MB - ミサイル艇",
            "PF": "PF - 哨戒フリゲート",
            "PG": "PG - 砲艦",
            "TB": "TB - 魚雷艇",

            # 駆逐艦系
            "D": "D - 水雷駆逐艦",
            "DB": "DB - 通報艦",
            "DD": "DD - 駆逐艦",
            "DDE": "DDE - 対潜護衛駆逐艦",
            "DDG": "DDG - ミサイル駆逐艦",
            "DDR": "DDR - レーダーピケット駆逐艦",
            "DE": "DE - 護衛駆逐艦",
            "DL": "DL - 嚮導駆逐艦",
            "DM": "DM - 敷設駆逐艦",
            "DMS": "DMS - 掃海駆逐艦",
            "DDH": "DDH - ヘリコプター搭載護衛艦",

            # 潜水艦系
            "CSS": "CSS - 沿岸潜水艦",
            "MSM": "MSM - 特殊潜航艇",
            "SC": "SC - 巡洋潜水艦",
            "SCV": "SCV - 潜水空母",
            "SF": "SF - 艦隊型潜水艦",
            "SM": "SM - 敷設型潜水艦",
            "SS": "SS - 航洋型潜水艦",

            # 巡洋艦系
            "ACR": "ACR - 装甲巡洋艦",
            "C": "C - 防護巡洋艦",
            "CA": "CA - 重巡・一等巡洋艦",
            "CL": "CL - 軽巡洋艦/二等巡洋艦",
            "CB": "CB - 大型巡洋艦",
            "CF": "CF - 航空巡洋艦",
            "CG": "CG - ミサイル巡洋艦",
            "CM": "CM - 敷設巡洋艦",
            "CS": "CS - 偵察巡洋艦",
            "HTC": "HTC - 重雷装巡洋艦",
            "TC": "TC - 水雷巡洋艦",
            "TCL": "TCL - 練習巡洋艦",


            # 戦艦系
            "B": "B - 前弩級戦艦",
            "BB": "BB - 戦艦",
            "BBG": "BBG - ミサイル戦艦",
            "BC": "BC - 巡洋戦艦",
            "BF": "BF - 航空戦艦",
            "BM": "BM - モニター艦",
            "FBB": "FBB - 高速戦艦",
            "PB": "PB - ポケット戦艦",
            "SB": "SB - 超戦艦",
            "CDB": "CDB - 海防戦艦",

            # その他装甲艦
            "IC": "IC - 装甲艦",
            # 特設・巡視船・その他艦艇
            "AAA": "AAA - 特設防空艦",
            "AAG": "AAG - 特設防空警備艦",
            "AAM": "AAM - 特設掃海艇",
            "AAS": "AAS - 特設駆潜艇",
            "AAV": "AAV - 特設水上機母艦",
            "AC": "AC - 特設巡洋艦",
            "AG": "AG - 特設砲艦",
            "AMS": "AMS - 特設敷設艦",
            "APC": "APC - 特設監視艇",
            "APS": "APS - 特設哨戒艦",
            "CAM": "CAM - CAMシップ",
            "MAC": "MAC - 特設空母",
            "APB": "APB - 航行可能な宿泊艦",
            "PL": "PL - 大型巡視船",
            "PLH": "PLH - ヘリ搭載型",
            "PM": "PM - 中型巡視船",
            "WHEC": "WHEC - 長距離カッター"
        }
        self.ship_archetype_mapping = {
            # 戦艦
            "BB": "BB - 一等戦艦",
            "BC": "BC - 二等戦艦",
            "BF": "BF - 航空戦艦",
            "CDB": "CDB - 海防戦艦",

            # 巡洋艦
            "CB": "CB - 大型巡洋艦",
            "CA": "CA - 一等巡洋艦",
            "CL": "CL - 二等巡洋艦",
            "CF": "CF - 航空巡洋艦",

            # 特設巡洋艦
            "MC": "MC - 特設巡洋艦",

            # 駆逐艦
            "DD": "DD - 一等駆逐艦",
            "DE": "DE - 二等駆逐艦",

            # フリゲート・コルベット
            "FF": "FF - フリゲート艦",
            "K": "K - コルベット艦",

            # 補助艦艇
            "FAV": "FAV - 一等補助艦",
            "SAV": "SAV - 二等補助艦",
            "TAV": "TAV - 二等補助艦",

            # 小型戦闘艦
            "CC": "CC - 戦闘艇",

            # 空母
            "AV": "AV - 水上機母艦",
            "CV": "CV - 一等航空母艦",
            "CVL": "CVL - 二等航空母艦",

            # 潜水艦
            "FS": "FS - 一等潜水艦",
            "SS": "SS - 二等潜水艦",
            "SCV": "SCV - 潜水空母"
        }

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
                # IDが指定されていない場合は生成
                name = hull_data.get('name', '')
                country = hull_data.get('country', '')
                ship_type = hull_data.get('type', '')

                if name and (country or ship_type):
                    hull_id = self.convert_name(name, country, ship_type)
                    hull_data['id'] = hull_id
                else:
                    # 必要な情報がない場合はデフォルトIDを生成
                    hull_id = self.get_next_id('HULL')
                    hull_data['id'] = hull_id

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
                            # 数値部分を抽出（最後の連続する数字）
                            match = re.search(r'(\d+)$', hull_id)
                            if match:
                                number = int(match.group(1))
                                max_number = max(max_number, number)
                    except Exception:
                        pass

        # 次の番号を生成
        next_number = max_number + 1
        return f"{prefix}{next_number:03d}"

    def convert_name(self, name: str, country: str, ship_type: str) -> str:
        """
        名前、国、艦種からIDを生成

        Args:
            name: 艦級名
            country: 国コード
            ship_type: 艦種

        Returns:
            str: 生成されたID
        """
        # 特殊文字を除去し、英数字のみに変換
        name_part = re.sub(r'[^a-zA-Z0-9]', '', name.replace(' ', '_'))

        # 国コードを大文字に変換
        country_part = country.upper() if country else ""

        # 艦種からプレフィックスを抽出 (例: "CV - 航空母艦" -> "CV")
        type_prefix = ""
        if ship_type:
            # 最初の5文字までのアルファベットを抽出
            alpha_part = re.match(r'^([A-Za-z]{1,5})', ship_type)
            if alpha_part:
                type_prefix = alpha_part.group(1).upper()

            # マッピングを確認
            for key in self.ship_type_mapping:
                if ship_type.startswith(key):
                    type_prefix = key
                    break

        # IDの構築 (例: "USH_USA_CV_Enterprise")
        id_parts = ["USH"]  # 共通プレフィックス "Universal Ship Hull"

        if country_part:
            id_parts.append(country_part)

        if type_prefix:
            id_parts.append(type_prefix)

        if name_part:
            id_parts.append(name_part)
        else:
            # 名前部分がない場合は一意のIDを追加
            id_parts.append(f"HULL{int(time.time())%10000}")

        return "_".join(id_parts)

    def import_from_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """
        CSVから船体データをインポート（全行の連続的な読み込み）

        Args:
            file_path: CSVファイルのパス

        Returns:
            List[Dict[str, Any]]: インポートされた船体データのリスト
        """
        imported_hulls = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                # 全行を処理
                for row_number, row in enumerate(reader, start=1):
                    try:
                        # 各行のデータをパース
                        hull_data = self._convert_csv_row_to_hull_data(row)

                        if hull_data:
                            # IDが未設定または自動生成が必要な場合は新しいIDを生成
                            if not hull_data.get('id') or hull_data.get('id') == '-':
                                name = hull_data.get('name', '')
                                country = hull_data.get('country', '')
                                ship_type = hull_data.get('type', '')

                                if name and (country or ship_type):
                                    hull_data['id'] = self.convert_name(name, country, ship_type)
                                else:
                                    hull_data['id'] = self.get_next_id('HULL')

                            # 既存データの確認
                            existing_hull = self.load_hull(hull_data['id'])
                            if existing_hull:
                                print(f"警告: 行 {row_number} - 既存の船体ID '{hull_data['id']}' が上書きされます")

                            # 船体データを保存
                            if self.save_hull(hull_data):
                                print(f"行 {row_number} - 船体データ '{hull_data.get('name', '')}' (ID: {hull_data['id']}) を保存しました")
                                imported_hulls.append(hull_data)
                            else:
                                print(f"エラー: 行 {row_number} - 船体データの保存に失敗しました")
                        else:
                            print(f"エラー: 行 {row_number} - 無効または不完全な船体データ")

                    except Exception as e:
                        print(f"エラー: 行 {row_number} - 処理中にエラーが発生しました: {e}")
                        # 個別の行のエラーで処理を中断せず、次の行に進む
                        continue

            print(f"CSVのインポートが完了しました。合計: {len(imported_hulls)}件の船体データをインポートしました。")
            return imported_hulls

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
        # IDの処理
        if not hull_data.get('id') or hull_data.get('id') == '-':
            name = hull_data.get('name', '')
            country = hull_data.get('country', '')
            ship_type = hull_data.get('type', '')

            if name and (country or ship_type):
                hull_data['id'] = convert_name(name, country, ship_type)
            else:
                hull_data['id'] = self.get_next_id('HULL')
        # 艦種（type）の処理 - 短い艦種コードから完全な記述に変換
        if 'type' in hull_data:
            ship_type = hull_data['type']
            # 先頭の1〜5文字のアルファベットを抽出
            type_code_match = re.match(r'^([A-Za-z]{1,5})', ship_type)
            if type_code_match:
                type_code = type_code_match.group(1).upper()
                # マッピングを確認
                if type_code in self.ship_type_mapping:
                    hull_data['type'] = self.ship_type_mapping[type_code]
        # 艦種（archetype）の処理 - 短い艦種コードから完全な記述に変換
        if 'archetype' in hull_data:
            ship_type = hull_data['archetype']
            # 先頭の1〜5文字のアルファベットを抽出
            type_code_match = re.match(r'^([A-Za-z]{1,5})', ship_type)
            if type_code_match:
                type_code = type_code_match.group(1).upper()
                # マッピングを確認
                if type_code in self.ship_archetype_mapping:
                    hull_data['archetype'] = self.ship_archetype_mapping[type_code]




        # nameが必須、ない場合はidを使用
        if not hull_data.get('name'):
            if hull_data.get('id'):
                hull_data['name'] = hull_data['id']
            else:
                # 必須データがない場合はNoneを返す
                return None

        # 数値型フィールドの変換
        numeric_fields = ['weight', 'length', 'width', 'power', 'speed', 'range',
                          'cruise_speed', 'fuel_capacity', 'armor_max', 'armor_min',
                          'crew', 'year', 'hull_structure_id', 'armor_type_id']

        for field in numeric_fields:
            if field in hull_data:
                try:
                    # '#REF!'などの特殊値を処理
                    if hull_data[field] in ['', '#REF!', 'NULL', '-']:
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
            else:
                slots[slot] = ' '  # デフォルトは有効

        hull_data['slots'] = slots

        return hull_data