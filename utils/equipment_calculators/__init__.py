# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: equipment_calculatorsパッケージの初期化モジュール
# -*- coding: utf-8 -*-
"""
装備カテゴリー別ステータス計算モジュール

各装備カテゴリーに特化したステータス計算を提供する
"""

from .base_calculator import BaseEquipmentCalculator
from .hangar_calculator import HangarCalculator
from .gun_calculator import GunCalculator
from .torpedo_calculator import TorpedoCalculator
from .engine_calculator import EngineCalculator
from .armor_calculator import ArmorCalculator


class DefaultEquipmentCalculator(BaseEquipmentCalculator):
    """デフォルト装備計算機（特定の計算機が定義されていない装備用）"""
    
    def __init__(self):
        super().__init__()
        self.equipment_type = "default"
        
    def _calculate_category_stats(self, equipment_data, hull_data=None):
        """デフォルトのカテゴリー固有ステータス計算（基本ステータスのみ）"""
        return {}

# カテゴリー名とCalculatorクラスのマッピング
CALCULATOR_REGISTRY = {
    'hangar': HangarCalculator,
    'ハンガー': HangarCalculator,
    '格納庫': HangarCalculator,
    
    '小口径砲': GunCalculator,
    '中口径砲': GunCalculator,
    '大口径砲': GunCalculator,
    '超大口径砲': GunCalculator,
    '対空砲': GunCalculator,
    
    '魚雷': TorpedoCalculator,
    '潜水艦魚雷': TorpedoCalculator,
    
    '機関': EngineCalculator,
    
    '増設バルジ(中型艦)': ArmorCalculator,
    '増設バルジ(大型艦)': ArmorCalculator,
}

def get_calculator(equipment_type: str) -> BaseEquipmentCalculator:
    """
    装備タイプに対応する計算機を取得
    
    Args:
        equipment_type (str): 装備タイプ
        
    Returns:
        BaseEquipmentCalculator: 対応する計算機
    """
    calculator_class = CALCULATOR_REGISTRY.get(equipment_type, DefaultEquipmentCalculator)
    return calculator_class()

__all__ = [
    'BaseEquipmentCalculator',
    'DefaultEquipmentCalculator',
    'HangarCalculator',
    'GunCalculator', 
    'TorpedoCalculator',
    'EngineCalculator',
    'ArmorCalculator',
    'get_calculator',
    'CALCULATOR_REGISTRY'
]