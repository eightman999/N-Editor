# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: csv_to_hull_converter CSV船体コンバーター
"""CSVから船体エンティティへのコンバーター

CSVフォーマットの船体データをHullエンティティに変換します。
レガシーシステムとの互換性を保ちつつ、新しいドメインモデルに対応します。
"""

from typing import Dict, List, Any, Optional
import csv
import re
import logging
from domain.entities.hull import Hull

logger = logging.getLogger(__name__)


class CSVToHullConverter:
    """CSV船体データコンバーター

    CSVファイルまたはCSV行データをHullエンティティに変換します。
    レガシーフォーマットからの移行をサポートします。
    """

    # 船殻構造のマッピング（数値ID → 文字列表現）
    HULL_STRUCTURE_MAPPING = {
        0: 'なし',
        1: '中世型',
        2: '近代型',
        3: 'WWI型',
        4: '戦間期型',
        5: 'WWII型',
        6: '戦後前期型',
        7: '現代型'
    }

    # 装甲種別のマッピング（数値ID → 文字列表現）
    ARMOR_TYPE_MAPPING = {
        0: 'なし',
        1.0: '装甲なし',
        1.35: '軽装甲',
        1.4: '標準装甲',
        1.5: '重装甲',
        1.8: '特殊装甲',
        2.0: '複合装甲'
    }

    # 艦種表示名マッピング（短縮形 → 完全表示）
    SHIP_TYPE_MAPPING = {
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

        # 小型艦艇
        "PC": "PC - 哨戒艇、駆潜艇",
        "PT": "PT - 高速魚雷艇",
        "FF": "FF - フリゲート",
        "K": "K - コルベット",
        "PF": "PF - 哨戒フリゲート",
        "PG": "PG - 砲艦",
        "TB": "TB - 魚雷艇",

        # 駆逐艦系
        "D": "D - 水雷駆逐艦",
        "DB": "DB - 通報艦",
        "DD": "DD - 駆逐艦",
        "DDE": "DDE - 対潜護衛駆逐艦",
        "DDG": "DDG - ミサイル駆逐艦",
        "DE": "DE - 護衛駆逐艦",
        "DL": "DL - 嚮導駆逐艦",
        "DDH": "DDH - ヘリコプター搭載護衛艦",

        # 潜水艦系
        "CSS": "CSS - 沿岸潜水艦",
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
        "CAG": "CAG - ミサイル重巡洋艦",
        "CLG": "CLG - ミサイル軽巡洋艦",
        "CGN": "CGN - 原子力ミサイル巡洋艦",

        # 戦艦系
        "BB": "BB - 戦艦",
        "BBG": "BBG - ミサイル戦艦",
        "BC": "BC - 巡洋戦艦",
        "BM": "BM - モニター艦",

        # 補助艦艇
        "AO": "AO - 給油艦",
        "AS": "AS - 潜水母艦",
        "AR": "AR - 工作艦",
        "AD": "AD - 駆逐艦母艦",
        "AP": "AP - 輸送艦",
    }

    def __init__(self, id_generator=None):
        """初期化

        Args:
            id_generator: ID生成関数（オプション）
        """
        self.id_generator = id_generator or self._default_id_generator
        self._id_counter = 0

    def _default_id_generator(self, prefix: str = 'HULL') -> str:
        """デフォルトID生成関数

        Args:
            prefix: IDプレフィックス

        Returns:
            str: 生成されたID
        """
        self._id_counter += 1
        return f"{prefix}_{self._id_counter:06d}"

    def convert_row(self, row: Dict[str, str]) -> Optional[Hull]:
        """CSV行データをHullエンティティに変換

        Args:
            row: CSVの行データ（辞書形式）

        Returns:
            Optional[Hull]: 変換されたHullエンティティ（変換失敗時はNone）
        """
        try:
            # CSVフィールドからHullフィールドへのマッピング
            field_mapping = {
                '艦級名': 'name',
                'システム名称': 'id',
                'weight': 'weight',
                'length': 'length',
                'width': 'width',
                'speed': 'max_speed',
                'cruise_speed': 'cruise_speed',
                'range': 'naval_range',
                'fuel_capacity': 'fuel_capacity',
                'armor_max': 'armor_max',
                'armor_min': 'armor_min',
                '船殻構造': 'hull_structure_id',
                '装甲種別': 'armor_type_id',
                'crew': 'crew',
                'year': 'year',
                'country': 'country',
                'archetype': 'archetype',
                'TYPE': 'type_display'
            }

            # 基本データの抽出
            hull_data = {}
            for csv_field, hull_field in field_mapping.items():
                if csv_field in row:
                    hull_data[hull_field] = row[csv_field]

            # IDの生成または検証
            hull_id = hull_data.get('id', '')
            if not hull_id or hull_id == '-':
                # IDがない場合は生成
                hull_id = self.id_generator('HULL')
                hull_data['id'] = hull_id

            # 名前の検証（必須）
            hull_name = hull_data.get('name', '')
            if not hull_name or hull_name == '-':
                # 名前がない場合はIDを使用
                hull_data['name'] = hull_id

            # 数値フィールドの変換
            numeric_fields = {
                'weight': 0.0,
                'length': 0.0,
                'width': 0.0,
                'max_speed': 0.0,
                'cruise_speed': 0.0,
                'naval_range': 0.0,
                'fuel_capacity': 0.0,
                'armor_max': 0.0,
                'armor_min': 0.0,
                'crew': 0,
                'year': 1936,
                'hull_structure_id': 5,  # デフォルトはWWII型
                'armor_type_id': 1.4  # デフォルトは標準装甲
            }

            for field, default_value in numeric_fields.items():
                if field in hull_data:
                    hull_data[field] = self._convert_numeric(
                        hull_data[field],
                        default_value
                    )
                else:
                    hull_data[field] = default_value

            # 船殻構造の変換（ID → 文字列）
            hull_structure_id = hull_data.get('hull_structure_id', 0)
            hull_data['hull_structure'] = self.HULL_STRUCTURE_MAPPING.get(
                int(hull_structure_id),
                'WWII型'
            )

            # 装甲種別の変換（ID → 文字列）
            armor_type_id = hull_data.get('armor_type_id', 1.4)
            # 浮動小数点の精度問題に対処するため、最も近いキーを検索
            hull_data['armor_type'] = self._find_closest_armor_type(armor_type_id)

            # 艦種表示名の変換
            if 'type_display' in hull_data:
                hull_data['type_display'] = self._convert_ship_type(
                    hull_data['type_display']
                )

            # archetypeの変換
            if 'archetype' in hull_data:
                hull_data['archetype'] = self._convert_ship_type(
                    hull_data['archetype']
                )

            # 不要なフィールドを削除
            hull_data.pop('hull_structure_id', None)
            hull_data.pop('armor_type_id', None)

            # Hullエンティティを生成
            hull = Hull(**hull_data)

            # バリデーション
            if not hull.validate():
                logger.warning(f"Invalid hull data: {hull_id}")
                return None

            logger.debug(f"Converted hull: {hull_id}")
            return hull

        except Exception as e:
            logger.error(f"Failed to convert CSV row: {e}")
            return None

    def _convert_numeric(self, value: Any, default: Any) -> Any:
        """数値変換（エラー耐性）

        Args:
            value: 変換する値
            default: デフォルト値

        Returns:
            Any: 変換された数値またはデフォルト値
        """
        try:
            # 特殊値の処理
            if value in ['', '#REF!', 'NULL', '-', None]:
                return default

            # 数値型の判定
            if isinstance(default, int):
                return int(float(value))
            else:
                return float(value)

        except (ValueError, TypeError):
            return default

    def _find_closest_armor_type(self, armor_id: float) -> str:
        """装甲種別IDから最も近い装甲タイプを検索

        浮動小数点の精度問題に対処するため、最も近いキーを検索します。

        Args:
            armor_id: 装甲種別ID

        Returns:
            str: 装甲種別名
        """
        # 完全一致を優先
        if armor_id in self.ARMOR_TYPE_MAPPING:
            return self.ARMOR_TYPE_MAPPING[armor_id]

        # 最も近いキーを検索（0.01の誤差範囲内）
        for key, value in self.ARMOR_TYPE_MAPPING.items():
            if abs(key - armor_id) < 0.01:
                return value

        # デフォルト値
        return '標準装甲'

    def _convert_ship_type(self, ship_type: str) -> str:
        """艦種コードを完全表示に変換

        Args:
            ship_type: 艦種コード（短縮形）

        Returns:
            str: 完全表示の艦種名
        """
        if not ship_type:
            return ''

        # 先頭の1〜5文字のアルファベットを抽出
        type_code_match = re.match(r'^([A-Za-z]{1,5})', ship_type)
        if type_code_match:
            type_code = type_code_match.group(1).upper()
            # マッピングを確認
            if type_code in self.SHIP_TYPE_MAPPING:
                return self.SHIP_TYPE_MAPPING[type_code]

        # マッピングになければそのまま返す
        return ship_type

    def convert_csv_file(self, csv_file_path: str, encoding: str = 'utf-8') -> List[Hull]:
        """CSVファイルから船体リストを読み込み

        Args:
            csv_file_path: CSVファイルパス
            encoding: ファイルエンコーディング

        Returns:
            List[Hull]: 船体エンティティのリスト
        """
        hulls = []

        try:
            with open(csv_file_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)

                for row in reader:
                    hull = self.convert_row(row)
                    if hull:
                        hulls.append(hull)

            logger.info(f"Loaded {len(hulls)} hulls from {csv_file_path}")

        except Exception as e:
            logger.error(f"Failed to load CSV file {csv_file_path}: {e}")

        return hulls

    def export_to_csv(self, hulls: List[Hull], csv_file_path: str, encoding: str = 'utf-8'):
        """船体リストをCSVファイルに出力

        Args:
            hulls: 船体エンティティのリスト
            csv_file_path: 出力CSVファイルパス
            encoding: ファイルエンコーディング
        """
        if not hulls:
            logger.warning("No hulls to export")
            return

        try:
            # フィールド名のマッピング（逆変換）
            field_names = [
                'システム名称', '艦級名', 'weight', 'length', 'width',
                'speed', 'cruise_speed', 'range', 'fuel_capacity',
                'armor_max', 'armor_min', '船殻構造', '装甲種別',
                'crew', 'year', 'country', 'archetype', 'TYPE'
            ]

            with open(csv_file_path, 'w', encoding=encoding, newline='') as f:
                writer = csv.DictWriter(f, fieldnames=field_names)
                writer.writeheader()

                for hull in hulls:
                    # Hull → CSV行データに変換
                    row = {
                        'システム名称': hull.id,
                        '艦級名': hull.name,
                        'weight': hull.weight,
                        'length': hull.length,
                        'width': hull.width,
                        'speed': hull.max_speed,
                        'cruise_speed': hull.cruise_speed,
                        'range': hull.naval_range,
                        'fuel_capacity': hull.fuel_capacity,
                        'armor_max': hull.armor_max,
                        'armor_min': hull.armor_min,
                        '船殻構造': hull.hull_structure,
                        '装甲種別': hull.armor_type,
                        'crew': hull.crew,
                        'year': hull.year,
                        'country': hull.country,
                        'archetype': hull.archetype,
                        'TYPE': hull.type_display
                    }
                    writer.writerow(row)

            logger.info(f"Exported {len(hulls)} hulls to {csv_file_path}")

        except Exception as e:
            logger.error(f"Failed to export CSV file {csv_file_path}: {e}")
