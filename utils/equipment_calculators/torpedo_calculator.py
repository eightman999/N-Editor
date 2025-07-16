# -*- coding: utf-8 -*-
"""
魚雷系統装備専用ステータス計算

魚雷装備のステータス計算を行うクラス
"""

from typing import Dict, Any, Optional
from .base_calculator import BaseEquipmentCalculator


class TorpedoCalculator(BaseEquipmentCalculator):
    """魚雷系統装備用ステータス計算機"""
    
    def __init__(self):
        super().__init__()
        self.equipment_type = "torpedo"
        
    def _calculate_category_stats(self, equipment_data: Dict[str, Any], hull_data: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        魚雷装備のカテゴリー固有ステータス計算
        
        Args:
            equipment_data (dict): 装備データ
            hull_data (dict, optional): 船体データ
            
        Returns:
            dict: カテゴリー固有ステータス
        """
        stats = {}
        
        # 魚雷攻撃力計算
        stats.update(self._calculate_torpedo_attack(equipment_data))
        
        # 射程と速度による調整
        stats.update(self._calculate_range_speed_adjustments(equipment_data))
        
        # 発射管数による調整
        stats.update(self._calculate_launcher_adjustments(equipment_data))
        
        return stats
    
    def _calculate_torpedo_attack(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        """
        魚雷の攻撃力を計算
        
        Args:
            equipment_data (dict): 装備データ
            
        Returns:
            dict: 攻撃力ステータス
        """
        attack_stats = {}
        
        # 炸薬重量と発射管数
        explosive_weight = equipment_data.get('specific_elements', {}).get('explosive_weight_kg', 0.0)
        launcher_count = equipment_data.get('specific_elements', {}).get('launcher_count', 1)
        speed = equipment_data.get('specific_elements', {}).get('speed_kts', 0.0)
        
        # 基本攻撃力（炸薬重量ベース）
        base_attack = explosive_weight * launcher_count * 0.5
        
        # 速度による命中率調整（高速魚雷は命中率が上がるが威力は若干下がる）
        if speed > 0:
            speed_factor = min(1.2, 1.0 + (speed - 35) / 100.0)  # 35ノット基準
        else:
            speed_factor = 1.0
        
        # 魚雷攻撃力を設定
        attack_stats['torpedo_attack'] = base_attack * speed_factor
        
        # 潜水艦攻撃にも効果（対潜攻撃）
        attack_stats['sub_attack'] = base_attack * 0.3
        
        return attack_stats
    
    def _calculate_range_speed_adjustments(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        """
        射程と速度による調整値計算
        
        Args:
            equipment_data (dict): 装備データ
            
        Returns:
            dict: 調整値
        """
        adjustments = {}
        
        max_range = equipment_data.get('specific_elements', {}).get('max_range_m', 0.0)
        speed = equipment_data.get('specific_elements', {}).get('speed_kts', 0.0)
        
        # 長射程魚雷による戦術的優位
        if max_range > 10000:  # 10km以上の長射程
            range_bonus = (max_range - 10000) / 5000.0  # 5kmごとに+1
            adjustments['naval_range'] = range_bonus * 5.0  # 海域戦闘距離延長
        
        # 高速魚雷による機動性向上
        if speed > 40:  # 40ノット以上の高速
            speed_bonus = (speed - 40) / 10.0  # 10ノットごとに+1
            adjustments['naval_speed'] = speed_bonus * 0.5  # わずかな速度向上
        
        return adjustments
    
    def _calculate_launcher_adjustments(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        """
        発射管数による調整値計算
        
        Args:
            equipment_data (dict): 装備データ
            
        Returns:
            dict: 調整値
        """
        adjustments = {}
        
        launcher_count = equipment_data.get('specific_elements', {}).get('launcher_count', 1)
        
        # 多連装発射管による重量とクルー増加
        if launcher_count > 1:
            weight_multiplier = 1.0 + (launcher_count - 1) * 0.15  # 発射管1本あたり15%増加
            crew_multiplier = 1.0 + (launcher_count - 1) * 0.1    # 発射管1本あたり10%増加
            
            base_weight = equipment_data.get('weight', 0.0)
            base_crew = equipment_data.get('personnel', 0.0)
            
            adjustments['equipment_weight'] = base_weight * (weight_multiplier - 1.0)
            adjustments['manpower'] = base_crew * (crew_multiplier - 1.0)
        
        # 多連装による視認性増加（発射時の水柱等）
        if launcher_count > 2:
            visibility_increase = (launcher_count - 2) * 0.2
            adjustments['surface_visibility'] = visibility_increase
        
        return adjustments
    
    def _calculate_ic_cost(self, equipment_data: Dict[str, Any], calculated_stats: Dict[str, float]) -> float:
        """
        魚雷装備のICコスト計算
        
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
            
            # 魚雷特有のパラメータ
            explosive_weight = equipment_data.get('specific_elements', {}).get('explosive_weight_kg', 0.0)
            launcher_count = equipment_data.get('specific_elements', {}).get('launcher_count', 1)
            max_range = equipment_data.get('specific_elements', {}).get('max_range_m', 0.0)
            speed = equipment_data.get('specific_elements', {}).get('speed_kts', 0.0)
            
            # 開発年度による調整
            dev_year = equipment_data.get('year', 1936)
            year_factor = max(0.1, (1950 - dev_year) / 20.0)
            
            # 魚雷特有のコスト計算
            base_cost = weight * 0.1 + crew * 0.05
            
            # 炸薬量によるコスト（爆薬は高価）
            explosive_cost = explosive_weight * 0.3
            
            # 高性能魚雷（高速・長射程）のコスト増加
            performance_factor = 1.0
            if speed > 40:
                performance_factor += (speed - 40) / 100.0  # 高速化コスト
            if max_range > 10000:
                performance_factor += (max_range - 10000) / 50000.0  # 長射程化コスト
            
            # 発射管数によるコスト
            launcher_cost = launcher_count * 0.5
            
            # 最終コスト計算
            total_cost = (base_cost + explosive_cost + launcher_cost) * performance_factor * year_factor
            
            return max(0.4, total_cost)  # 最低コスト保証
            
        except Exception as e:
            print(f"魚雷ICコスト計算エラー: {e}")
            return 1.2  # 魚雷のデフォルト値