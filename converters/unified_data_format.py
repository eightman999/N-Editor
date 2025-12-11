# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: unified_data_format統一データフォーマット
"""統一データフォーマット定義

新システムで使用する標準的なデータ構造を定義します。
CSV、JSON、HOI4形式など、異なるフォーマット間の変換を容易にします。
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
import json


@dataclass
class UnifiedHullData:
    """統一船体データ形式

    全てのデータソース（CSV、JSON、HOI4等）から変換可能な
    標準的な船体データ構造。

    Attributes:
        id: 船体の一意識別子
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
        hull_structure: 船殻構造（例: "WWII型"）
        armor_type: 装甲種別（例: "標準装甲"）
        crew: 乗員数
        year: 開発年
        country: 国家コード（例: "JPN", "USA"）
        archetype: 艦種（例: "DD", "CA", "BB"）
        type_display: 艦種表示名（例: "DD - 駆逐艦"）
        source_format: データソース識別子
    """

    # 必須フィールド
    id: str
    name: str

    # 物理特性
    weight: float = 0.0              # 排水量 (ton)
    length: float = 0.0              # 全長 (m)
    width: float = 0.0               # 全幅 (m)

    # 性能特性
    max_speed: float = 0.0           # 最大速度 (knots)
    cruise_speed: float = 0.0        # 巡航速度 (knots)
    naval_range: float = 0.0         # 航続距離 (nm)
    fuel_capacity: float = 0.0       # 燃料容量 (ton)

    # 防御特性
    armor_max: float = 0.0           # 最大装甲 (mm)
    armor_min: float = 0.0           # 最小装甲 (mm)
    hull_structure: str = ""         # 船殻構造
    armor_type: str = ""             # 装甲種別

    # 運用特性
    crew: int = 0                    # 乗員数
    year: int = 1936                 # 開発年

    # 分類
    country: str = ""                # 国家
    archetype: str = ""              # 艦種コード
    type_display: str = ""           # 艦種表示名

    # メタデータ
    source_format: str = "unified"   # データソース

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedHullData':
        """辞書から生成"""
        # dataclassのフィールド名と一致するキーのみ抽出
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)

    def to_json(self) -> str:
        """JSON文字列に変換"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'UnifiedHullData':
        """JSON文字列から生成"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def to_legacy_format(self) -> Dict[str, Any]:
        """旧HullModel形式に変換

        既存のHullModelと互換性のある辞書形式に変換します。
        """
        return {
            'id': self.id,
            'name': self.name,
            'weight': self.weight,
            'length': self.length,
            'width': self.width,
            'speed': self.max_speed,
            'cruise_speed': self.cruise_speed,
            'range': self.naval_range,
            'fuel_capacity': self.fuel_capacity,
            'armor_max': self.armor_max,
            'armor_min': self.armor_min,
            'hull_structure': self.hull_structure,
            'armor_type': self.armor_type,
            'crew': self.crew,
            'year': self.year,
            'country': self.country,
            'archetype': self.archetype,
            'type': self.type_display,
            # 性能計算用フィールド
            'max_speed': self.max_speed,
            'naval_range': self.naval_range,
        }

    @classmethod
    def from_legacy_format(cls, legacy_data: Dict[str, Any]) -> 'UnifiedHullData':
        """旧HullModel形式から生成

        既存のHullModelの辞書形式から統一フォーマットに変換します。
        """
        return cls(
            id=legacy_data.get('id', ''),
            name=legacy_data.get('name', ''),
            weight=float(legacy_data.get('weight', 0)),
            length=float(legacy_data.get('length', 0)),
            width=float(legacy_data.get('width', 0)),
            max_speed=float(legacy_data.get('speed', legacy_data.get('max_speed', 0))),
            cruise_speed=float(legacy_data.get('cruise_speed', 0)),
            naval_range=float(legacy_data.get('range', legacy_data.get('naval_range', 0))),
            fuel_capacity=float(legacy_data.get('fuel_capacity', 0)),
            armor_max=float(legacy_data.get('armor_max', 0)),
            armor_min=float(legacy_data.get('armor_min', 0)),
            hull_structure=legacy_data.get('hull_structure', ''),
            armor_type=legacy_data.get('armor_type', ''),
            crew=int(legacy_data.get('crew', 0)),
            year=int(legacy_data.get('year', 1936)),
            country=legacy_data.get('country', ''),
            archetype=legacy_data.get('archetype', ''),
            type_display=legacy_data.get('type', ''),
            source_format='legacy'
        )

    def validate(self) -> bool:
        """データの妥当性を検証

        Returns:
            bool: データが妥当な場合True
        """
        # 必須フィールドのチェック
        if not self.id or not self.name:
            return False

        # 数値フィールドの範囲チェック
        if self.weight < 0:
            return False
        if self.max_speed < 0 or self.max_speed > 100:  # 100ノット以上は非現実的
            return False
        if self.year < 1800 or self.year > 2100:  # 年代の妥当性
            return False

        return True


@dataclass
class UnifiedEquipmentData:
    """統一装備データ形式

    Attributes:
        id: 装備の一意識別子
        name: 装備名
        equipment_type: 装備種別（例: "小口径砲", "機関"）
        weight: 重量 (ton)
        crew: 必要人員数
        year: 開発年
        country: 国家コード
    """

    id: str
    name: str
    equipment_type: str = ""
    weight: float = 0.0
    crew: int = 0
    year: int = 1936
    country: str = ""

    # 性能データ（装備種別により異なる）
    specific_stats: Dict[str, Any] = field(default_factory=dict)

    # メタデータ
    source_format: str = "unified"

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedEquipmentData':
        """辞書から生成"""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)

    def to_legacy_format(self) -> Dict[str, Any]:
        """旧EquipmentModel形式に変換"""
        return {
            'id': self.id,
            'common': {
                'ID': self.id,
                '名前': self.name,
                '重量': self.weight,
                '人員': self.crew,
            },
            'equipment_type': self.equipment_type,
            'specific_elements': self.specific_stats,
            'year': self.year,
            'country': self.country,
        }

    @classmethod
    def from_legacy_format(cls, legacy_data: Dict[str, Any]) -> 'UnifiedEquipmentData':
        """旧EquipmentModel形式から生成"""
        common = legacy_data.get('common', {})
        return cls(
            id=common.get('ID', legacy_data.get('id', '')),
            name=common.get('名前', legacy_data.get('name', '')),
            equipment_type=legacy_data.get('equipment_type', ''),
            weight=float(common.get('重量', legacy_data.get('weight', 0))),
            crew=int(common.get('人員', legacy_data.get('crew', 0))),
            year=int(legacy_data.get('year', 1936)),
            country=legacy_data.get('country', ''),
            specific_stats=legacy_data.get('specific_elements', {}),
            source_format='legacy'
        )


@dataclass
class UnifiedPerformanceData:
    """統一性能データ形式

    計算結果を表す標準的なデータ構造。

    Attributes:
        max_speed: 最大速度 (knots)
        cruise_speed: 巡航速度 (knots)
        naval_range: 航続距離 (nm)
        fuel_capacity: 燃料容量 (ton)
        display_speed: 表示用速度（UI表示用）
    """

    max_speed: float = 0.0
    cruise_speed: float = 0.0
    naval_range: float = 0.0
    fuel_capacity: float = 0.0
    display_speed: float = 0.0

    # 追加性能値（オプション）
    additional_stats: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        result = asdict(self)
        # additional_statsを展開
        if self.additional_stats:
            result.update(self.additional_stats)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedPerformanceData':
        """辞書から生成"""
        # 既知のフィールド
        known_fields = {'max_speed', 'cruise_speed', 'naval_range',
                       'fuel_capacity', 'display_speed'}

        base_data = {k: v for k, v in data.items() if k in known_fields}
        additional = {k: v for k, v in data.items()
                     if k not in known_fields and isinstance(v, (int, float))}

        return cls(**base_data, additional_stats=additional)
