# -*- coding: utf-8 -*-
"""
砲系統装備専用ステータス計算

各種艦砲装備のステータス計算を行うクラス
"""

from typing import Dict, Any, Optional
from .base_calculator import BaseEquipmentCalculator


class GunCalculator(BaseEquipmentCalculator):
    """砲系統装備用ステータス計算機"""
    
    def __init__(self):
        super().__init__()
        self.equipment_type = "gun"
        
    def _calculate_category_stats(self, equipment_data: Dict[str, Any], hull_data: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        砲装備のカテゴリー固有ステータス計算
        
        Args:
            equipment_data (dict): 装備データ
            hull_data (dict, optional): 船体データ
            
        Returns:
            dict: カテゴリー固有ステータス
        """
        stats = {}
        
        # 砲の攻撃力計算
        stats.update(self._calculate_gun_attack_power(equipment_data))
        
        # 装甲貫通力計算
        stats.update(self._calculate_armor_piercing(equipment_data))
        
        # 砲数による調整
        stats.update(self._calculate_gun_count_adjustments(equipment_data))
        
        return stats
    
    def _calculate_gun_attack_power(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        """
        砲の攻撃力を計算
        
        Args:
            equipment_data (dict): 装備データ
            
        Returns:
            dict: 攻撃力ステータス
        """
        attack_stats = {}
        
        # 口径による分類
        caliber = equipment_data.get('specific_elements', {}).get('caliber_cm', 0.0)
        if not caliber:
            caliber = equipment_data.get('specific_elements', {}).get('caliber_mm', 0.0) / 10.0
        
        # 砲弾重量と初速
        shell_weight = equipment_data.get('specific_elements', {}).get('shell_weight_kg', 0.0)
        if not shell_weight:
            shell_weight = equipment_data.get('specific_elements', {}).get('shell_weight_g', 0.0) / 1000.0
        
        initial_velocity = equipment_data.get('specific_elements', {}).get('initial_velocity_mps', 0.0)
        barrel_count = equipment_data.get('specific_elements', {}).get('barrel_count', 1)
        
        # 運動エネルギーベースの攻撃力計算
        if shell_weight > 0 and initial_velocity > 0:
            kinetic_energy = 0.5 * shell_weight * (initial_velocity ** 2) / 1000000  # MJ単位
            base_attack = kinetic_energy * barrel_count * 0.1  # 適切なスケーリング
        else:
            base_attack = caliber * barrel_count * 0.5  # フォールバック計算
        
        # 口径による攻撃力分類
        if caliber >= 30.0:  # 大口径砲（30cm以上）
            attack_stats['lg_attack'] = base_attack * 1.2
            attack_stats['hg_attack'] = base_attack * 0.3
        elif caliber >= 15.0:  # 中口径砲（15-30cm）
            attack_stats['lg_attack'] = base_attack * 0.8
            attack_stats['hg_attack'] = base_attack * 0.8
        elif caliber >= 7.5:  # 小口径砲（7.5-15cm）
            attack_stats['lg_attack'] = base_attack * 0.4
            attack_stats['hg_attack'] = base_attack * 1.0
        else:  # 対空砲等（7.5cm未満）
            attack_stats['anti_air_attack'] = base_attack * 1.5
            attack_stats['hg_attack'] = base_attack * 0.6
        
        return attack_stats
    
    def _calculate_armor_piercing(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        """
        装甲貫通力を計算
        
        Args:
            equipment_data (dict): 装備データ
            
        Returns:
            dict: 装甲貫通力ステータス
        """
        piercing_stats = {}
        
        # 口径と砲弾重量から貫通力を計算
        caliber = equipment_data.get('specific_elements', {}).get('caliber_cm', 0.0)
        if not caliber:
            caliber = equipment_data.get('specific_elements', {}).get('caliber_mm', 0.0) / 10.0
        
        shell_weight = equipment_data.get('specific_elements', {}).get('shell_weight_kg', 0.0)
        if not shell_weight:
            shell_weight = equipment_data.get('specific_elements', {}).get('shell_weight_g', 0.0) / 1000.0
        
        initial_velocity = equipment_data.get('specific_elements', {}).get('initial_velocity_mps', 0.0)
        
        # 貫通力計算（口径と運動エネルギーベース）
        if shell_weight > 0 and initial_velocity > 0:
            penetration_factor = (shell_weight * initial_velocity) / 1000.0
        else:
            penetration_factor = caliber * 10.0  # フォールバック
        
        # 口径による貫通力分類
        if caliber >= 30.0:  # 大口径砲
            piercing_stats['lg_armor_piercing'] = penetration_factor * 0.08
            piercing_stats['hg_armor_piercing'] = penetration_factor * 0.02
        elif caliber >= 15.0:  # 中口径砲
            piercing_stats['lg_armor_piercing'] = penetration_factor * 0.05
            piercing_stats['hg_armor_piercing'] = penetration_factor * 0.05
        else:  # 小口径砲
            piercing_stats['lg_armor_piercing'] = penetration_factor * 0.02
            piercing_stats['hg_armor_piercing'] = penetration_factor * 0.08
        
        return piercing_stats
    
    def _calculate_gun_count_adjustments(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        """
        砲数による調整値計算
        
        Args:
            equipment_data (dict): 装備データ
            
        Returns:
            dict: 調整値
        """
        adjustments = {}
        
        turret_count = equipment_data.get('specific_elements', {}).get('turret_count', 1)
        barrel_count = equipment_data.get('specific_elements', {}).get('barrel_count', 1)
        
        # 多砲塔による重量とクルー増加
        total_guns = turret_count * barrel_count
        if total_guns > 1:
            weight_increase = (total_guns - 1) * 0.1  # 砲1門あたり10%重量増加
            crew_increase = (total_guns - 1) * 0.05    # 砲1門あたり5%クルー増加
            
            # 基本重量とクルーに乗算
            base_weight = equipment_data.get('weight', 0.0)
            base_crew = equipment_data.get('personnel', 0.0)
            
            adjustments['equipment_weight'] = base_weight * weight_increase
            adjustments['manpower'] = base_crew * crew_increase
        
        return adjustments
    
    def _calculate_ic_cost(self, equipment_data: Dict[str, Any], calculated_stats: Dict[str, float]) -> float:
        """
        砲装備のICコスト計算
        
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
            
            # 砲特有のパラメータ
            caliber = equipment_data.get('specific_elements', {}).get('caliber_cm', 0.0)
            if not caliber:
                caliber = equipment_data.get('specific_elements', {}).get('caliber_mm', 0.0) / 10.0
            
            turret_count = equipment_data.get('specific_elements', {}).get('turret_count', 1)
            barrel_count = equipment_data.get('specific_elements', {}).get('barrel_count', 1)
            
            # 開発年度による調整
            dev_year = equipment_data.get('year', 1936)
            year_factor = max(0.1, (1950 - dev_year) / 20.0)
            
            # 砲特有のコスト計算
            base_cost = weight * 0.12 + crew * 0.06
            
            # 口径によるコスト増加
            caliber_cost = caliber * 0.5  # 1cmあたり0.5のコスト
            
            # 砲数によるコスト増加
            gun_complexity = (turret_count * barrel_count) ** 1.2  # 非線形増加
            
            # 最終コスト計算
            total_cost = (base_cost + caliber_cost) * gun_complexity * year_factor
            
            return max(0.3, total_cost)  # 最低コスト保証
            
        except Exception as e:
            print(f"砲ICコスト計算エラー: {e}")
            return 1.5  # 砲のデフォルト値