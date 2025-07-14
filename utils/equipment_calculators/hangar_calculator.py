# -*- coding: utf-8 -*-
"""
ハンガー装備専用ステータス計算

航空機格納庫装備のステータス計算を行うクラス
"""

from typing import Dict, Any, Optional
from .base_calculator import BaseEquipmentCalculator


class HangarCalculator(BaseEquipmentCalculator):
    """ハンガー装備用ステータス計算機"""
    
    def __init__(self):
        super().__init__()
        self.equipment_type = "hangar"
        
    def _calculate_category_stats(self, equipment_data: Dict[str, Any], hull_data: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        ハンガー装備のカテゴリー固有ステータス計算
        
        Args:
            equipment_data (dict): 装備データ
            hull_data (dict, optional): 船体データ
            
        Returns:
            dict: カテゴリー固有ステータス
        """
        stats = {}
        
        # ハンガーサイズによる艦載機容量計算
        carrier_size = self._calculate_carrier_size(equipment_data)
        stats['carrier_size'] = carrier_size
        
        # ICコスト計算
        stats['build_cost_ic'] = self._calculate_ic_cost(equipment_data, stats)
        
        return stats
    
    def _calculate_carrier_size(self, equipment_data: Dict[str, Any]) -> float:
        """
        ハンガーの艦載機容量を計算
        
        Args:
            equipment_data (dict): 装備データ
            
        Returns:
            float: 艦載機容量
        """
        # 基本容量
        base_capacity = equipment_data.get('carrier_size', 0.0)
        
        # 重量ベースの容量計算（大型ハンガーの場合）
        weight = equipment_data.get('weight', 0.0)
        is_large = equipment_data.get('specific_elements', {}).get('is_large', False)
        
        if is_large:
            # 大型ハンガーは重量あたりの容量が高い
            weight_bonus = weight * 0.02  # 1トンあたり0.02機
        else:
            # 通常ハンガーは効率が低い
            weight_bonus = weight * 0.01  # 1トンあたり0.01機
            
        total_capacity = base_capacity + weight_bonus
        
        return max(0.0, total_capacity)
    
    def _calculate_hangar_adjustments(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        """
        ハンガー装備による調整値計算
        
        Args:
            equipment_data (dict): 装備データ
            
        Returns:
            dict: 調整値
        """
        adjustments = {}
        
        # ハンガーサイズに基づく燃料消費増加
        carrier_size = equipment_data.get('carrier_size', 0.0)
        fuel_consumption_increase = carrier_size * 0.5  # 1機あたり0.5の燃料消費増加
        adjustments['fuel_consumption'] = fuel_consumption_increase
        
        # 艦載機運用による視認性増加
        visibility_increase = carrier_size * 0.1  # 1機あたり0.1の視認性増加
        adjustments['surface_visibility'] = visibility_increase
        
        # 航空管制による探知能力向上
        detection_bonus = carrier_size * 0.05  # 1機あたり0.05の探知力増加
        adjustments['surface_detection'] = detection_bonus
        
        return adjustments
    
    def _calculate_large_hangar_bonus(self, equipment_data: Dict[str, Any], current_stats: Dict[str, float]) -> Dict[str, float]:
        """
        大型ハンガーの特別ボーナス計算
        
        Args:
            equipment_data (dict): 装備データ
            current_stats (dict): 現在のステータス
            
        Returns:
            dict: 大型ハンガーボーナス
        """
        bonus = {}
        
        # 大型ハンガーは効率的な航空機運用が可能
        carrier_size = current_stats.get('carrier_size', 0.0)
        
        # 追加の探知能力
        bonus['surface_detection'] = carrier_size * 0.03  # 追加で1機あたり0.03
        
        # 航続距離向上（航空機による偵察範囲拡大）
        bonus['naval_range'] = carrier_size * 2.0  # 1機あたり2海里
        
        return bonus
    
    def _calculate_ic_cost(self, equipment_data: Dict[str, Any], calculated_stats: Dict[str, float]) -> float:
        """
        ハンガー装備のICコスト計算
        
        Args:
            equipment_data (dict): 装備データ
            calculated_stats (dict): 計算済みステータス
            
        Returns:
            float: ICコスト
        """
        try:
            # 基本パラメータ
            weight = calculated_stats.get('equipment_weight', 0.0)
            crew = calculated_stats.get('manpower', 0.0)
            carrier_size = calculated_stats.get('carrier_size', 0.0)
            
            # 開発年度による調整
            dev_year = equipment_data.get('year', 1936)
            year_factor = max(0.1, (1950 - dev_year) / 20.0)
            
            # ハンガー特有のコスト計算
            # 重量とクルーのベースコスト
            base_cost = weight * 0.15 + crew * 0.08
            
            # 艦載機容量によるコスト（格納庫構造の複雑さ）
            capacity_cost = carrier_size * 2.0  # 1機容量あたり2.0のコスト
            
            # 大型ハンガーのコスト増加
            is_large = equipment_data.get('specific_elements', {}).get('is_large', False)
            size_multiplier = 1.5 if is_large else 1.0
            
            # 最終コスト計算
            total_cost = (base_cost + capacity_cost) * year_factor * size_multiplier
            
            return max(0.5, total_cost)  # 最低コスト保証
            
        except Exception as e:
            print(f"ハンガーICコスト計算エラー: {e}")
            return 2.0  # ハンガーのデフォルト値（高め）