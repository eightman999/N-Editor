# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: hull船体エンティティ
"""船体エンティティ

船体データとビジネスロジックをカプセル化するドメインエンティティ。
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import json


@dataclass
class Hull:
    """船体エンティティ

    船体の物理特性、性能特性、防御特性を持つドメインオブジェクト。
    エンティティとして一意のIDを持ち、ライフサイクルを管理します。

    Attributes:
        id: 船体の一意識別子（エンティティID）
        name: 艦級名
        weight: 排水量 (ton)
        length: 全長 (m)
        width: 全幅 (m)
        max_speed: 最大速度 (knots)
        cruise_speed: 巡航速度 (knots)
        naval_range: 航続距離 (nautical miles)
        fuel_capacity: 燃料容量 (ton)
        armor_max: 最大装甲厚 (mm)
        armor_min: 最小装甲厚 (mm)
        hull_structure: 船殻構造
        armor_type: 装甲種別
        crew: 乗員数
        year: 開発年
        country: 国家コード
        archetype: 艦種コード
        type_display: 艦種表示名
    """

    # エンティティID（必須）
    id: str
    name: str

    # 物理特性
    weight: float = 0.0
    length: float = 0.0
    width: float = 0.0

    # 性能特性
    max_speed: float = 0.0
    cruise_speed: float = 0.0
    naval_range: float = 0.0
    fuel_capacity: float = 0.0

    # 防御特性
    armor_max: float = 0.0
    armor_min: float = 0.0
    hull_structure: str = ""
    armor_type: str = ""

    # 運用特性
    crew: int = 0
    year: int = 1936

    # 分類
    country: str = ""
    archetype: str = ""
    type_display: str = ""

    # エンティティメタデータ
    _version: int = field(default=1, init=False, repr=False)
    _created_at: Optional[str] = field(default=None, init=False, repr=False)
    _updated_at: Optional[str] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        """エンティティ初期化後の処理"""
        # IDと名前の必須チェック
        if not self.id:
            raise ValueError("船体IDは必須です")
        if not self.name:
            raise ValueError("艦級名は必須です")

    def get_hull_area(self) -> float:
        """船体面積を計算

        Returns:
            float: 船体面積 (m²)
        """
        return self.length * self.width if self.length > 0 and self.width > 0 else 0.0

    def get_displacement(self) -> float:
        """排水量を取得

        Returns:
            float: 排水量 (ton)
        """
        return self.weight

    def get_armor_average(self) -> float:
        """平均装甲厚を計算

        Returns:
            float: 平均装甲厚 (mm)
        """
        if self.armor_max > 0 and self.armor_min >= 0:
            return (self.armor_max + self.armor_min) / 2
        return max(self.armor_max, self.armor_min)

    def is_large_ship(self, threshold: float = 10000.0) -> bool:
        """大型艦判定

        Args:
            threshold: 大型艦の排水量閾値 (ton)

        Returns:
            bool: 排水量が閾値以上の場合True
        """
        return self.weight >= threshold

    def is_fast_ship(self, threshold: float = 30.0) -> bool:
        """高速艦判定

        Args:
            threshold: 高速艦の速度閾値 (knots)

        Returns:
            bool: 最大速度が閾値以上の場合True
        """
        return self.max_speed >= threshold

    def get_ship_class_category(self) -> str:
        """艦級カテゴリを取得

        排水量に基づいて艦級カテゴリを返します。

        Returns:
            str: 艦級カテゴリ（"小型艦", "中型艦", "大型艦", "超大型艦"）
        """
        if self.weight < 2000:
            return "小型艦"
        elif self.weight < 10000:
            return "中型艦"
        elif self.weight < 30000:
            return "大型艦"
        else:
            return "超大型艦"

    def validate(self) -> bool:
        """エンティティの妥当性を検証

        Returns:
            bool: エンティティが妥当な場合True
        """
        # 必須フィールドチェック
        if not self.id or not self.name:
            return False

        # 物理的制約チェック
        if self.weight < 0:
            return False
        if self.length < 0 or self.width < 0:
            return False

        # 性能値の範囲チェック
        if self.max_speed < 0 or self.max_speed > 100:
            return False
        if self.cruise_speed < 0 or self.cruise_speed > self.max_speed:
            return False
        if self.naval_range < 0:
            return False

        # 年代の妥当性チェック
        if self.year < 1800 or self.year > 2100:
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換

        Returns:
            Dict[str, Any]: 船体データの辞書
        """
        return {
            'id': self.id,
            'name': self.name,
            'weight': self.weight,
            'length': self.length,
            'width': self.width,
            'max_speed': self.max_speed,
            'cruise_speed': self.cruise_speed,
            'naval_range': self.naval_range,
            'fuel_capacity': self.fuel_capacity,
            'armor_max': self.armor_max,
            'armor_min': self.armor_min,
            'hull_structure': self.hull_structure,
            'armor_type': self.armor_type,
            'crew': self.crew,
            'year': self.year,
            'country': self.country,
            'archetype': self.archetype,
            'type_display': self.type_display,
            '_version': self._version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Hull':
        """辞書から船体エンティティを生成

        Args:
            data: 船体データの辞書

        Returns:
            Hull: 船体エンティティ
        """
        # メタデータフィールドを除外
        entity_data = {k: v for k, v in data.items() if not k.startswith('_')}
        return cls(**entity_data)

    def to_json(self) -> str:
        """JSON文字列に変換

        Returns:
            str: JSON文字列
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'Hull':
        """JSON文字列から船体エンティティを生成

        Args:
            json_str: JSON文字列

        Returns:
            Hull: 船体エンティティ
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    def clone(self) -> 'Hull':
        """船体エンティティを複製

        Returns:
            Hull: 複製された船体エンティティ
        """
        return Hull.from_dict(self.to_dict())

    def __eq__(self, other: Any) -> bool:
        """等価性比較（エンティティIDで判定）

        Args:
            other: 比較対象

        Returns:
            bool: IDが同じ場合True
        """
        if not isinstance(other, Hull):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """ハッシュ値（エンティティIDベース）

        Returns:
            int: ハッシュ値
        """
        return hash(self.id)

    def __repr__(self) -> str:
        """文字列表現

        Returns:
            str: 船体の文字列表現
        """
        return (f"Hull(id='{self.id}', name='{self.name}', "
                f"archetype='{self.archetype}', weight={self.weight}t, "
                f"speed={self.max_speed}kt)")


# ファクトリー関数
def create_test_hull(
    id: str = "TEST_HULL_001",
    name: str = "テスト艦級",
    archetype: str = "DD",
    weight: float = 2000.0,
    max_speed: float = 35.0,
    **kwargs
) -> Hull:
    """テスト用の船体エンティティを生成

    Args:
        id: 船体ID
        name: 艦級名
        archetype: 艦種
        weight: 排水量
        max_speed: 最大速度
        **kwargs: その他のパラメータ

    Returns:
        Hull: テスト用船体エンティティ
    """
    default_data = {
        'id': id,
        'name': name,
        'weight': weight,
        'length': 100.0,
        'width': 10.0,
        'max_speed': max_speed,
        'cruise_speed': 18.0,
        'naval_range': 5000.0,
        'fuel_capacity': 500.0,
        'armor_max': 50.0,
        'armor_min': 20.0,
        'hull_structure': 'WWII型',
        'armor_type': '標準装甲',
        'crew': 200,
        'year': 1942,
        'country': 'JPN',
        'archetype': archetype,
        'type_display': f'{archetype} - 駆逐艦',
    }

    # kwargsで上書き
    default_data.update(kwargs)

    return Hull(**default_data)
