# -*- coding: utf-8 -*-
"""
装甲系統装備専用ステータス計算

バルジ等の装甲装備のステータス計算を行うクラス
"""

from typing import Dict, Any, Optional
from .base_calculator import BaseEquipmentCalculator


class ArmorCalculator(BaseEquipmentCalculator):
    """装甲系統装備用ステータス計算機"""
    
    def __init__(self):
        super().__init__()
        self.equipment_type = "armor"
        
    def _calculate_category_stats(self, equipment_data: Dict[str, Any], hull_data: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        装甲装備のカテゴリー固有ステータス計算
        
        Args:
            equipment_data (dict): 装備データ
            hull_data (dict, optional): 船体データ
            
        Returns:
            dict: カテゴリー固有ステータス
        """
        stats = {}
        
        # 装甲防御力計算
        stats.update(self._calculate_armor_protection(equipment_data))
        
        # 重量による速度低下計算
        stats.update(self._calculate_weight_penalty(equipment_data, hull_data))
        
        # 視認性への影響計算
        stats.update(self._calculate_visibility_effect(equipment_data))
        
        # 耐久力向上計算
        stats.update(self._calculate_durability_bonus(equipment_data))
        
        return stats
    
    def _calculate_armor_protection(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        """
        装甲による防御力を計算
        
        Args:
            equipment_data (dict): 装備データ
            
        Returns:
            dict: 防御力ステータス
        """
        protection_stats = {}
        
        # 装甲厚
        armor_thickness = equipment_data.get('specific_elements', {}).get('available_armor', 0.0)
        if not armor_thickness:
            # フォールバック：重量から装甲厚を推定
            weight = equipment_data.get('weight', 0.0)
            armor_thickness = weight * 0.1  # 1トンあたり0.1mmと仮定
        
        # 装甲重量
        armor_weight = equipment_data.get('weight', 0.0)
        
        # 装甲タイプによる効果分類
        equipment_name = equipment_data.get('name', '').lower()
        
        if 'バルジ' in equipment_name or 'bulge' in equipment_name:
            # バルジ装甲：主に魚雷防御
            protection_stats.update(self._calculate_bulge_protection(armor_thickness, armor_weight))
        else:
            # 一般装甲：総合防御
            protection_stats.update(self._calculate_general_armor_protection(armor_thickness, armor_weight))
        
        return protection_stats
    
    def _calculate_bulge_protection(self, armor_thickness: float, armor_weight: float) -> Dict[str, float]:
        """
        バルジ装甲の防御効果を計算
        
        Args:
            armor_thickness (float): 装甲厚
            armor_weight (float): 装甲重量
            
        Returns:
            dict: バルジ防御ステータス
        """
        bulge_stats = {}
        
        # 魚雷防御効果（主効果）
        torpedo_protection = armor_thickness * 0.02 + armor_weight * 0.001
        
        # 軽度の砲弾防御効果
        shell_protection = torpedo_protection * 0.3
        
        # 耐久力向上（構造強化）
        durability_bonus = armor_weight * 0.05
        
        # ステータス設定（HOI4の防御ステータスに相当するものがないので、耐久力で代用）
        bulge_stats['max_strength'] = durability_bonus + torpedo_protection
        
        # わずかな装甲貫通抵抗
        bulge_stats['lg_armor_piercing'] = -shell_protection * 0.1  # 被ダメージ軽減として負の値
        bulge_stats['hg_armor_piercing'] = -shell_protection * 0.1
        
        return bulge_stats
    
    def _calculate_general_armor_protection(self, armor_thickness: float, armor_weight: float) -> Dict[str, float]:
        """
        一般装甲の防御効果を計算
        
        Args:
            armor_thickness (float): 装甲厚
            armor_weight (float): 装甲重量
            
        Returns:
            dict: 一般装甲防御ステータス
        """
        armor_stats = {}
        
        # 砲弾防御効果
        shell_protection = armor_thickness * 0.015 + armor_weight * 0.001
        
        # 耐久力向上
        durability_bonus = armor_weight * 0.08
        
        # ステータス設定
        armor_stats['max_strength'] = durability_bonus + shell_protection
        
        # 装甲貫通抵抗
        armor_stats['lg_armor_piercing'] = -shell_protection * 0.15
        armor_stats['hg_armor_piercing'] = -shell_protection * 0.1
        
        return armor_stats
    
    def _calculate_weight_penalty(self, equipment_data: Dict[str, Any], hull_data: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """
        装甲重量による速度低下を計算
        
        Args:
            equipment_data (dict): 装備データ
            hull_data (dict, optional): 船体データ
            
        Returns:
            dict: 速度ペナルティ
        """
        penalty_stats = {}
        
        armor_weight = equipment_data.get('weight', 0.0)
        
        # 船体重量による相対的な影響計算
        if hull_data:
            hull_weight = hull_data.get('weight', 10000.0)
        else:
            hull_weight = 10000.0  # デフォルト値
        
        # 重量比による速度低下
        weight_ratio = armor_weight / hull_weight if hull_weight > 0 else 0
        speed_penalty = weight_ratio * 20.0  # 重量比に応じた速度低下
        
        # 最大ペナルティ制限
        speed_penalty = min(speed_penalty, 5.0)  # 最大5ノットの速度低下
        
        penalty_stats['naval_speed'] = -speed_penalty
        
        return penalty_stats
    
    def _calculate_visibility_effect(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        """
        装甲による視認性への影響を計算
        
        Args:
            equipment_data (dict): 装備データ
            
        Returns:
            dict: 視認性効果
        """
        visibility_stats = {}
        
        armor_weight = equipment_data.get('weight', 0.0)
        
        # 重装甲による視認性増加（艦影が大きくなる）
        visibility_increase = armor_weight * 0.0001  # 重量による視認性増加
        
        # バルジの場合は特に視認性が増加
        equipment_name = equipment_data.get('name', '').lower()
        if 'バルジ' in equipment_name or 'bulge' in equipment_name:
            visibility_increase *= 1.5  # バルジは艦幅を増すため
        
        visibility_stats['surface_visibility'] = visibility_increase
        
        return visibility_stats
    
    def _calculate_durability_bonus(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        """
        装甲による耐久力向上を計算
        
        Args:
            equipment_data (dict): 装備データ
            
        Returns:
            dict: 耐久力ボーナス
        """
        durability_stats = {}
        
        armor_weight = equipment_data.get('weight', 0.0)
        armor_thickness = equipment_data.get('specific_elements', {}).get('available_armor', 0.0)
        
        # 装甲による構造強化効果
        structural_bonus = armor_weight * 0.02
        
        # 装甲厚による防護効果
        if armor_thickness > 0:
            thickness_bonus = armor_thickness * 0.1
        else:
            thickness_bonus = 0.0
        
        # 信頼性向上（装甲による保護）
        reliability_bonus = min(0.1, armor_weight * 0.0001)  # 最大0.1の信頼性向上
        
        durability_stats['max_strength'] = structural_bonus + thickness_bonus
        durability_stats['reliability'] = reliability_bonus
        
        return durability_stats
    
    def _calculate_ic_cost(self, equipment_data: Dict[str, Any], calculated_stats: Dict[str, float]) -> float:
        """
        装甲装備のICコスト計算
        
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
            armor_thickness = equipment_data.get('specific_elements', {}).get('available_armor', 0.0)
            
            # 開発年度による調整
            dev_year = equipment_data.get('year', 1936)
            year_factor = max(0.1, (1950 - dev_year) / 20.0)
            
            # 装甲特有のコスト計算
            base_cost = weight * 0.05 + crew * 0.02  # 装甲は重量あたりのコストが低い
            
            # 装甲厚によるコスト増加（厚い装甲は加工が困難）
            thickness_cost = armor_thickness * 0.01 if armor_thickness > 0 else 0
            
            # 装甲材質によるコスト（現時点では一律）
            material_multiplier = 1.0
            
            # バルジの場合は構造複雑性によるコスト増加
            equipment_name = equipment_data.get('name', '').lower()
            if 'バルジ' in equipment_name or 'bulge' in equipment_name:
                complexity_multiplier = 1.3  # バルジは複雑な構造
            else:
                complexity_multiplier = 1.0
            
            # 最終コスト計算
            total_cost = (base_cost + thickness_cost) * material_multiplier * complexity_multiplier * year_factor
            
            return max(0.1, total_cost)  # 最低コスト保証
            
        except Exception as e:
            print(f"装甲ICコスト計算エラー: {e}")
            return 0.8  # 装甲のデフォルト値