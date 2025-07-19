# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: gun_calculator計算ユーティリティ
# -*- coding: utf-8 -*-
"""
砲系統装備専用ステータス計算

各種艦砲装備のステータス計算を行うクラス
"""

from typing import Dict, Any, Optional
import math
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

        # HOI4艦砲統計計算（新方式）
        hoi4_stats = self._calculate_hoi4_artillery_stats(equipment_data)
        stats.update(hoi4_stats)

        # 砲数による調整
        stats.update(self._calculate_gun_count_adjustments(equipment_data))

        return stats

    def _calculate_hoi4_artillery_stats(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        """HOI4艦砲統計計算（新方式）"""
        stats = {}
        
        # パラメータ取得
        shell_weight = equipment_data.get('specific_elements', {}).get('shell_weight_kg', 0.0)
        if not shell_weight:
            shell_weight = equipment_data.get('specific_elements', {}).get('shell_weight_g', 0.0) / 1000.0
        
        initial_velocity = equipment_data.get('specific_elements', {}).get('initial_velocity_mps', 0.0)
        rate_of_fire = equipment_data.get('specific_elements', {}).get('rate_of_fire_rpm', 1)
        
        caliber = equipment_data.get('specific_elements', {}).get('caliber_cm', 0.0)
        if not caliber:
            caliber = equipment_data.get('specific_elements', {}).get('caliber_mm', 0.0) / 10.0
        
        year = equipment_data.get('year', 1900)
        
        # calculate_hoi4_artillery_stats関数の実装
        attack, piercing, cost = self.calculate_hoi4_artillery_stats(
            shell_weight, initial_velocity, rate_of_fire, caliber, year
        )
        
        # 口径に応じた攻撃力・貫通力の配分
        if caliber >= 30.0:
            stats['lg_attack'] = attack * 1.2
            stats['hg_attack'] = attack * 0.3
            stats['lg_armor_piercing'] = piercing
        elif caliber >= 15.0:
            stats['lg_attack'] = attack * 0.8
            stats['hg_attack'] = attack * 0.8
            stats['hg_armor_piercing'] = piercing
        elif caliber >= 7.5:
            stats['lg_attack'] = attack * 0.4
            stats['hg_attack'] = attack * 1.0
            stats['lg_armor_piercing'] = piercing * 0.5
            stats['hg_armor_piercing'] = piercing
        else:
            stats['anti_air_attack'] = attack * 1.5
            stats['hg_attack'] = attack * 0.6
            stats['hg_armor_piercing'] = piercing
        
        stats['build_cost_ic'] = cost
        
        return stats

    def calculate_hoi4_artillery_stats(self, W, V, R, D, year):
        """HOI4艦砲統計計算関数"""
        # 調整係数（最新版）
        alpha = 0.005   # 攻撃力
        beta = 0.134    # 貫徹力
        gamma = 0.98    # コスト（全体2.8倍）
        delta = 0.02    # 年代補正（強め）

        # 攻撃力（J→毎秒換算）
        E = 0.5 * W * (V ** 2)
        attack = alpha * E * (R / 60) / 10000

        # 貫徹力（KC鋼換算）
        piercing = beta * D * V / 100

        # コスト（開発年を加味）
        base_cost = (W ** 0.5) * (D ** 1.2) + (R ** 0.3)
        year_adjust = 1 + delta * (year - 1900)
        cost = gamma * base_cost * year_adjust

        return round(attack, 2), round(piercing, 2), round(cost, 2)

    def _calculate_gun_attack_power(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        attack_stats = {}

        caliber = equipment_data.get('specific_elements', {}).get('caliber_cm', 0.0)
        if not caliber:
            caliber = equipment_data.get('specific_elements', {}).get('caliber_mm', 0.0) / 10.0

        shell_weight = equipment_data.get('specific_elements', {}).get('shell_weight_kg', 0.0)
        if not shell_weight:
            shell_weight = equipment_data.get('specific_elements', {}).get('shell_weight_g', 0.0) / 1000.0

        initial_velocity = equipment_data.get('specific_elements', {}).get('initial_velocity_mps', 0.0)
        barrel_count = equipment_data.get('specific_elements', {}).get('barrel_count', 1)
        rate_of_fire = equipment_data.get('specific_elements', {}).get('rate_of_fire_rpm', 1)

        if shell_weight > 0 and initial_velocity > 0:
            energy = 0.5 * shell_weight * (initial_velocity ** 2)
            base_attack = 0.005 * energy * (rate_of_fire / 60) / 10000
        else:
            base_attack = caliber * barrel_count * 0.5

        if caliber >= 30.0:
            attack_stats['lg_attack'] = base_attack * 1.2
            attack_stats['hg_attack'] = base_attack * 0.3
        elif caliber >= 15.0:
            attack_stats['lg_attack'] = base_attack * 0.8
            attack_stats['hg_attack'] = base_attack * 0.8
        elif caliber >= 7.5:
            attack_stats['lg_attack'] = base_attack * 0.4
            attack_stats['hg_attack'] = base_attack * 1.0
        else:
            attack_stats['anti_air_attack'] = base_attack * 1.5
            attack_stats['hg_attack'] = base_attack * 0.6

        return attack_stats

    def _calculate_armor_piercing(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        piercing_stats = {}

        caliber = equipment_data.get('specific_elements', {}).get('caliber_cm', 0.0)
        if not caliber:
            caliber = equipment_data.get('specific_elements', {}).get('caliber_mm', 0.0) / 10.0

        initial_velocity = equipment_data.get('specific_elements', {}).get('initial_velocity_mps', 0.0)

        piercing = 0.134 * caliber * initial_velocity / 100

        if caliber >= 30.0:
            piercing_stats['lg_armor_piercing'] = piercing
        elif caliber >= 15.0:
            piercing_stats['hg_armor_piercing'] = piercing
        else:
            piercing_stats['lg_armor_piercing'] = piercing * 0.5
            piercing_stats['hg_armor_piercing'] = piercing

        return piercing_stats

    def _calculate_gun_count_adjustments(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        adjustments = {}

        turret_count = equipment_data.get('specific_elements', {}).get('turret_count', 1)
        barrel_count = equipment_data.get('specific_elements', {}).get('barrel_count', 1)

        total_guns = turret_count * barrel_count
        if total_guns > 1:
            weight_increase = (total_guns - 1) * 0.1
            crew_increase = (total_guns - 1) * 0.05

            base_weight = equipment_data.get('weight', 0.0)
            base_crew = equipment_data.get('personnel', 0.0)

            adjustments['equipment_weight'] = base_weight * (1 + weight_increase)
            adjustments['manpower'] = base_crew * (1 + crew_increase)
        else:
            adjustments['equipment_weight'] = equipment_data.get('weight', 0.0)
            adjustments['manpower'] = equipment_data.get('personnel', 0.0)

        return adjustments

    def _calculate_ic_cost_new(self, equipment_data: Dict[str, Any], calculated_stats: Dict[str, float]) -> float:
        try:
            shell_weight = equipment_data.get('specific_elements', {}).get('shell_weight_kg', 0.0)
            if not shell_weight:
                shell_weight = equipment_data.get('specific_elements', {}).get('shell_weight_g', 0.0) / 1000.0

            initial_velocity = equipment_data.get('specific_elements', {}).get('initial_velocity_mps', 0.0)
            rate_of_fire = equipment_data.get('specific_elements', {}).get('rate_of_fire_rpm', 1)
            caliber = equipment_data.get('specific_elements', {}).get('caliber_cm', 0.0)
            if not caliber:
                caliber = equipment_data.get('specific_elements', {}).get('caliber_mm', 0.0) / 10.0
            year = equipment_data.get('year', 1900)

            gamma = 0.98
            delta = 0.02

            base = (shell_weight ** 0.5) * (caliber ** 1.2) + (rate_of_fire ** 0.3)
            year_factor = 1 + delta * (year - 1900)

            cost = gamma * base * year_factor

            return round(cost, 2)
        except Exception as e:
            print(f"新ICコスト計算エラー: {e}")
            return 1.5
