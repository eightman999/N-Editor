# -*- coding: utf-8 -*-
"""
装備ステータス計算の基底クラス

全ての装備カテゴリー計算機の基底となるクラス
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod


class BaseEquipmentCalculator(ABC):
    """装備ステータス計算の基底クラス"""
    
    def __init__(self):
        self.equipment_type = "base"
        
    def calculate_stats(self, equipment_data: Dict[str, Any], hull_data: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        装備のステータスを計算
        
        Args:
            equipment_data (dict): 装備データ
            hull_data (dict, optional): 船体データ
            
        Returns:
            dict: 計算されたステータス
        """
        stats = {
            'lg_attack': 0.0,
            'hg_attack': 0.0,
            'lg_armor_piercing': 0.0,
            'hg_armor_piercing': 0.0,
            'anti_air_attack': 0.0,
            'torpedo_attack': 0.0,
            'sub_attack': 0.0,
            'carrier_size': 0.0,
            'surface_detection': 0.0,
            'sub_detection': 0.0,
            'surface_visibility': 0.0,
            'sub_visibility': 0.0,
            'naval_speed': 0.0,
            'manpower': 0.0,
            'fuel_consumption': 0.0,
            'build_cost_ic': 0.0,
            'equipment_weight': 0.0,
            'reliability': 0.0,
            'naval_range': 0.0,
            'max_strength': 0.0,
            'shore_bombardment': 0.0
        }
        
        # 基本ステータスを取得
        stats.update(self._calculate_basic_stats(equipment_data))
        
        # カテゴリー固有の計算を実行
        stats.update(self._calculate_category_stats(equipment_data, hull_data))
        
        # ICコストを計算
        stats['build_cost_ic'] = self._calculate_ic_cost(equipment_data, stats)
        
        return stats
    
    def _calculate_basic_stats(self, equipment_data: Dict[str, Any]) -> Dict[str, float]:
        """
        基本ステータスを計算
        
        Args:
            equipment_data (dict): 装備データ
            
        Returns:
            dict: 基本ステータス
        """
        stats = {}
        
        # 装備データから直接ステータスを取得
        status_keys = [
            'lg_attack', 'hg_attack', 'lg_armor_piercing', 'hg_armor_piercing',
            'anti_air_attack', 'torpedo_attack', 'sub_attack', 'carrier_size',
            'surface_detection', 'sub_detection', 'surface_visibility', 'sub_visibility',
            'naval_speed', 'manpower', 'fuel_consumption', 'equipment_weight',
            'reliability', 'naval_range', 'max_strength', 'shore_bombardment'
        ]
        
        for key in status_keys:
            value = equipment_data.get(key, 0.0)
            if isinstance(value, (int, float)):
                stats[key] = float(value)
            else:
                stats[key] = 0.0
                
        return stats
    
    @abstractmethod 
    def _calculate_category_stats(self, equipment_data: Dict[str, Any], hull_data: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """
        カテゴリー固有のステータス計算
        
        Args:
            equipment_data (dict): 装備データ
            hull_data (dict, optional): 船体データ
            
        Returns:
            dict: カテゴリー固有ステータス
        """
        return {}
    
    def _calculate_ic_cost(self, equipment_data: Dict[str, Any], calculated_stats: Dict[str, float]) -> float:
        """
        ICコストを計算
        
        Args:
            equipment_data (dict): 装備データ
            calculated_stats (dict): 計算済みステータス
            
        Returns:
            float: ICコスト
        """
        try:
            # 重量と人員からベースコストを計算
            weight = calculated_stats.get('equipment_weight', 0.0)
            crew = calculated_stats.get('manpower', 0.0)
            
            # 開発年度による調整（逆補正：古い装備ほど安い）
            dev_year = equipment_data.get('year', 1936)
            year_factor = max(0.1, (1950 - dev_year) / 20.0)  # 1930年=1.0, 1950年=0.0
            
            # 基本コスト計算
            base_cost = (weight * 0.1 + crew * 0.05) * year_factor
            
            return max(0.1, base_cost)  # 最低コスト保証
            
        except Exception as e:
            print(f"ICコスト計算エラー: {e}")
            return 1.0  # デフォルト値
    
    def get_calculation_debug_info(self, equipment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        計算デバッグ情報を取得
        
        Args:
            equipment_data (dict): 装備データ
            
        Returns:
            dict: デバッグ情報
        """
        return {
            'calculator_type': self.__class__.__name__,
            'equipment_type': self.equipment_type,
            'equipment_id': equipment_data.get('common', {}).get('ID', 'Unknown'),
            'equipment_name': equipment_data.get('common', {}).get('名前', 'Unknown')
        }