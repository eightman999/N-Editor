# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: engine_calculator計算ユーティリティ
# -*- coding: utf-8 -*-
"""
機関装備専用ステータス計算

エンジン・機関装備のステータス計算を行うクラス
"""

from typing import Dict, Any, Optional
from .base_calculator import BaseEquipmentCalculator


class EngineCalculator(BaseEquipmentCalculator):
    """機関装備用ステータス計算機"""
    
    def __init__(self):
        super().__init__()
        self.equipment_type = "engine"
        
    def _calculate_category_stats(self, equipment_data: Dict[str, Any], hull_data: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        機関装備のカテゴリー固有ステータス計算
        
        Args:
            equipment_data (dict): 装備データ
            hull_data (dict, optional): 船体データ
            
        Returns:
            dict: カテゴリー固有ステータス
        """
        stats = {}
        
        # 速度向上計算
        stats.update(self._calculate_speed_bonus(equipment_data, hull_data))
        
        # 燃料消費計算
        stats.update(self._calculate_fuel_consumption(equipment_data))
        
        # 航続距離計算
        stats.update(self._calculate_range_bonus(equipment_data))
        
        # 信頼性計算
        stats.update(self._calculate_reliability(equipment_data))
        
        return stats
    
    def _calculate_speed_bonus(self, equipment_data: Dict[str, Any], hull_data: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """
        機関による速度向上を計算
        
        Args:
            equipment_data (dict): 装備データ
            hull_data (dict, optional): 船体データ
            
        Returns:
            dict: 速度ボーナス
        """
        speed_stats = {}
        
        # 機関出力
        specific_elements = equipment_data.get('specific_elements', {})
        engine_power = specific_elements.get('power', equipment_data.get('power', 0.0))
        
        # フォールバック：重量ベースで推定
        if engine_power == 0.0:
            engine_weight = equipment_data.get('weight', 0.0)
            engine_power = engine_weight * 10.0  # 1トンあたり10馬力と仮定
        
        # 船体重量による効率計算
        if hull_data:
            hull_weight = hull_data.get('weight', 10000.0)  # デフォルト10,000トン
        else:
            hull_weight = 10000.0
        
        # 馬力重量比による速度計算
        power_to_weight_ratio = engine_power / hull_weight if hull_weight > 0 else 0
        
        # 速度ボーナス（非線形計算）
        speed_bonus = power_to_weight_ratio * 5.0  # 適切なスケーリング
        
        # 最大速度制限（物理的限界）
        max_speed_bonus = 15.0  # 最大15ノットのボーナス
        speed_bonus = min(speed_bonus, max_speed_bonus)
        
        speed_stats['naval_speed'] = speed_bonus
        
        return speed_stats
    
    def _calculate_fuel_consumption(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        """
        燃料消費量を計算
        
        Args:
            equipment_data (dict): 装備データ
            
        Returns:
            dict: 燃料消費ステータス
        """
        consumption_stats = {}
        
        specific_elements = equipment_data.get('specific_elements', {})

        # 機関出力から燃料消費を計算
        engine_power = specific_elements.get('power', equipment_data.get('power', 0.0))
        fuel_capacity = specific_elements.get('fuel_capacity', equipment_data.get('fuel_capacity', 0.0))
        engine_type = specific_elements.get('engine_type', equipment_data.get('engine_type', 'HeavyOil'))
        
        # 機関種別による効率係数
        efficiency_factors = {
            'Coal': 0.8,           # 石炭
            'HeavyOil': 1.0,       # 重油
            'Diesel': 1.2,         # ディーゼル
            'GasTurbine': 1.1,     # ガスタービン
            'CoalHeavyOil': 0.9,   # 石炭重油混燃
            'DieselGas': 1.15,     # ディーゼルガス混燃
            'Battery': 2.0,        # バッテリー（効率高）
            'Nuclear': 5.0         # 原子炉（超高効率）
        }
        
        efficiency_factor = efficiency_factors.get(engine_type, 1.0)
        
        # 基本燃料消費（馬力ベース）
        base_consumption = engine_power * 0.003 / efficiency_factor
        
        # フォールバック：重量ベース
        if engine_power == 0.0:
            engine_weight = equipment_data.get('weight', 0.0)
            crew = equipment_data.get('personnel', 0.0)
            base_consumption = (engine_weight * 0.02 + crew * 0.1) / efficiency_factor
        
        # 開発年度による効率性
        dev_year = specific_elements.get('year', equipment_data.get('year', 1936))
        year_efficiency = max(0.5, 1.0 - (dev_year - 1936) / 100.0)
        
        fuel_consumption = base_consumption * year_efficiency
        consumption_stats['fuel_consumption'] = fuel_consumption
        
        return consumption_stats
    
    def _calculate_range_bonus(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        """
        航続距離ボーナスを計算（船体モデル側で主計算を行うため、効率係数のみ適用）
        
        Args:
            equipment_data (dict): 装備データ
            
        Returns:
            dict: 航続距離ボーナス
        """
        range_stats = {}
        
        specific_elements = equipment_data.get('specific_elements', {})
        engine_type = specific_elements.get('engine_type', equipment_data.get('engine_type', 'HeavyOil'))
        
        # 機関種別による航続距離効率係数
        range_factors = {
            'Coal': 0.8,           # 石炭（効率低）
            'HeavyOil': 1.0,       # 重油（標準）
            'Diesel': 1.3,         # ディーゼル（高効率）
            'GasTurbine': 0.9,     # ガスタービン（やや低効率）
            'CoalHeavyOil': 0.95,  # 石炭重油混燃
            'DieselGas': 1.2,      # ディーゼルガス混燃
            'Battery': 0.6,        # バッテリー（航続距離短）
            'Nuclear': 10.0        # 原子炉（超長距離）
        }
        
        range_factor = range_factors.get(engine_type, 1.0)
        
        # 開発年度による技術進歩
        dev_year = specific_elements.get('year', equipment_data.get('year', 1936))
        tech_factor = 1.0 + max(0, (dev_year - 1936) * 0.01)  # 1年あたり1%の改善
        
        # クルー数による運用効率
        crew = equipment_data.get('personnel', 0.0)
        crew_factor = 1.0 + min(crew * 0.001, 0.1)  # 最大10%の効率向上
        
        # 基本値（船体側で計算された値に係数を適用）
        base_range = equipment_data.get('naval_range', 0.0)
        
        # 最終航続距離係数
        total_factor = range_factor * tech_factor * crew_factor
        range_stats['naval_range'] = base_range * total_factor
        
        return range_stats
    
    def _calculate_reliability(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        """
        機関の信頼性を計算
        
        Args:
            equipment_data (dict): 装備データ
            
        Returns:
            dict: 信頼性ステータス
        """
        reliability_stats = {}
        
        # 基本信頼性
        base_reliability = equipment_data.get('reliability', equipment_data.get('specific_elements', {}).get('reliability', 0.0))
        
        # 開発年度による信頼性（技術成熟度）
        dev_year = equipment_data.get('year', 1936)
        maturity_factor = min(1.0, (dev_year - 1920) / 30.0)  # 1920年から1950年で成熟
        
        # クルー数による整備品質
        crew = equipment_data.get('personnel', 0.0)
        maintenance_factor = min(crew * 0.01, 0.5)  # 最大0.5の信頼性向上
        
        # 重量による堅牢性（重い機関は頑丈）
        weight = equipment_data.get('weight', 0.0)
        robustness_factor = min(weight * 0.0001, 0.3)  # 最大0.3の信頼性向上
        
        total_reliability = base_reliability + maturity_factor + maintenance_factor + robustness_factor
        
        # 信頼性は1.0が上限
        reliability_stats['reliability'] = min(total_reliability, 1.0)
        
        return reliability_stats
    
    def _calculate_ic_cost(self, equipment_data: Dict[str, Any], calculated_stats: Dict[str, float]) -> float:
        """
        機関装備のICコスト計算
        
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
            speed_bonus = calculated_stats.get('naval_speed', 0.0)
            range_bonus = calculated_stats.get('naval_range', 0.0)
            
            # 開発年度による調整
            dev_year = equipment_data.get('year', 1936)
            year_factor = max(0.1, (1950 - dev_year) / 20.0)
            
            # 機関特有のコスト計算
            base_cost = weight * 0.08 + crew * 0.04
            
            # 性能によるコスト増加
            performance_cost = speed_bonus * 0.2 + range_bonus * 0.01
            
            # 高性能機関のコスト増加（非線形）
            if speed_bonus > 10.0:
                performance_multiplier = 1.0 + (speed_bonus - 10.0) / 20.0
            else:
                performance_multiplier = 1.0
            
            # 最終コスト計算
            total_cost = (base_cost + performance_cost) * performance_multiplier * year_factor
            
            return max(0.2, total_cost)  # 最低コスト保証
            
        except Exception as e:
            print(f"機関ICコスト計算エラー: {e}")
            return 1.0  # 機関のデフォルト値