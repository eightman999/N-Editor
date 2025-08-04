# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: stats_calculatorユーティリティ
"""モジュール性能計算エンジン

このモジュールは、設計されたモジュール構成に基づいて
艦船の総合性能を計算する機能を提供します。
"""

from typing import Dict, Any, List, Optional
import json
import os
import logging
import math


class StatsCalculator:
    """モジュール性能を基にした統計計算エンジン
    
    設計データ内のモジュール、アップグレード、船体情報を統合して
    艦船の総合性能を計算します。
    """
    
    def __init__(self, app_controller=None):
        """性能計算エンジンを初期化
        
        Args:
            app_controller: アプリケーションコントローラー（データ取得用）
        """
        self.app_controller = app_controller
        self.logger = logging.getLogger('StatsCalculator')
        
        # キャッシュ
        self.module_stats_cache = {}
        self.hull_stats_cache = {}
        self.upgrade_effects_cache = {}
        
        # 性能計算ルール
        self.stat_rules = self._initialize_stat_rules()

    
    # --- 軽減係数に関する定数 ---
    # サイズ軽減率が最大になる船体面積 (m^2)
    MAX_AREA_FOR_REDUCTION = 25000
    # 重量軽減率が最大になる推定排水量 (ton)
    MAX_DISPLACEMENT_FOR_REDUCTION = 50000
    # サイズによる最大軽減率
    MAX_SIZE_REDUCTION_RATIO = 0.3
    # 重量による最大軽減率
    MAX_WEIGHT_REDUCTION_RATIO = 0.2
    # 総合的な最大軽減率
    TOTAL_MAX_REDUCTION_RATIO = 0.5

    # --- 排水量推定に関する定数 ---
    # 喫水と全幅の比率のデフォルト値
    DEFAULT_DRAFT_TO_BEAM_RATIO = 0.35
    # 方形係数のデフォルト値
    DEFAULT_BLOCK_COEFFICIENT = 0.6
    # 軍艦補正係数
    MILITARY_SHIP_COEFFICIENT = 1.5
    
    def calculate_design_stats(self, design_data: Dict[str, Any]) -> Dict[str, Any]:
        """設計の総合性能を計算

        Args:
            design_data (Dict[str, Any]): 設計データ

        Returns:
            Dict[str, Any]: 計算された総合性能
        """
        try:
            self.logger.debug(f"性能計算開始: {design_data.get('design_name', 'Unknown')}")

            # 各要素の性能を取得
            hull_stats = self._get_hull_base_stats(design_data.get('hull_id'))
            module_stats = self._calculate_module_stats(design_data.get('modules', {}), hull_stats)
            upgrade_stats = self._calculate_upgrade_stats(design_data.get('upgrades', {}))

            # 統合計算
            total_stats = self._combine_stats(hull_stats, module_stats, upgrade_stats)

            # 派生統計を計算
            derived_stats = self._calculate_derived_stats(total_stats)
            total_stats.update(derived_stats)

            self.logger.debug(f"性能計算完了: {len(total_stats)}個の統計を計算")
            return total_stats

        except Exception as e:
            self.logger.error(f"性能計算エラー: {e}")
            return {}
    
    def _get_hull_base_stats(self, hull_id: str) -> Dict[str, Any]:
        """船体の基本性能を取得
        
        Args:
            hull_id (str): 船体ID
            
        Returns:
            Dict[str, Any]: 船体の基本性能
        """
        if not hull_id:
            return {}
        
        # キャッシュチェック
        if hull_id in self.hull_stats_cache:
            return self.hull_stats_cache[hull_id].copy()
        
        hull_stats = {}
        
        if self.app_controller:
            try:
                hull_data = self.app_controller.load_hull(hull_id)
                if hull_data:
                    hull_stats = hull_data.get('base_stats', {})
            except Exception as e:
                self.logger.warning(f"船体データ取得エラー ({hull_id}): {e}")
        
        # デフォルト値の設定
        if not hull_stats:
            hull_stats = self._get_default_hull_stats(hull_id)
        
        # キャッシュに保存
        self.hull_stats_cache[hull_id] = hull_stats.copy()
        
        return hull_stats
    
    def _calculate_module_stats(self, modules: Dict[str, str], hull_stats: Dict[str, Any] = None) -> Dict[str, Any]:
        """モジュール性能の合計を計算
        
        Args:
            modules (Dict[str, str]): スロットIDとモジュールIDのマッピング
            hull_stats (Dict[str, Any]): 船体統計（軽減計算用）
            
        Returns:
            Dict[str, Any]: モジュール性能の合計
        """
        total_stats = {}
        
        for slot_id, module_id in modules.items():
            if not module_id or module_id == 'empty':
                continue
            
            module_stats = self._get_module_stats(module_id)
            
            # --- 船体サイズ/重量に応じた軽減ロジック（仮実装） ---
            if hull_stats:
                reduction_factor = self._calculate_reduction_factor(hull_stats)
                if 'build_cost_ic' in module_stats:
                    module_stats = module_stats.copy()  # 元のキャッシュを変更しないため
                    module_stats['build_cost_ic'] *= (1 - reduction_factor)
                if 'naval_speed' in module_stats and module_stats['naval_speed'] < 0:
                    if 'naval_speed' not in module_stats or module_stats == self._get_module_stats(module_id):
                        module_stats = module_stats.copy()
                    module_stats['naval_speed'] *= (1 - reduction_factor)
            # ----------------------------------------------------
            
            total_stats = self._add_stats(total_stats, module_stats)
        
        return total_stats
    
    def _calculate_reduction_factor(self, hull_stats: Dict[str, Any]) -> float:
        """船体サイズ/重量に基づく装備コスト・速度低下の軽減係数を計算
        
        Args:
            hull_stats (Dict[str, Any]): 船体統計
            
        Returns:
            float: 軽減係数（0.0-0.5の範囲）
        """
        try:
            # 船体の物理的サイズを取得（全長・全幅）
            length = hull_stats.get('length', 0)
            width = hull_stats.get('width', 0)
            
            if length > 0 and width > 0:
                # 全長・全幅から船体面積を計算（メートル単位想定）
                hull_area = length * width
                
                # 船体面積に基づくサイズ軽減（指数減衰関数）
                # 駆逐艦: 約100m x 10m = 1,000㎡
                # 戦艦: 約250m x 35m = 8,750㎡
                k_size = 1 / (self.MAX_AREA_FOR_REDUCTION * 0.8)  # 減衰係数
                size_reduction = self.MAX_SIZE_REDUCTION_RATIO * (1 - math.exp(-k_size * hull_area))
                
            else:
                # 全長・全幅データがない場合はフォールバック計算
                base_cost = hull_stats.get('build_cost_ic', 0)
                base_strength = hull_stats.get('max_strength', 0)
                hull_area = (base_cost * 0.7 + base_strength * 3.0)
                k_size = 1 / (10000 * 0.8)  # フォールバック用減衰係数
                size_reduction = self.MAX_SIZE_REDUCTION_RATIO * (1 - math.exp(-k_size * hull_area))
            
            # 排水量を取得（weightが排水量）
            displacement = hull_stats.get('weight', 0)
            
            if displacement <= 0:
                # weightがない場合は全長・全幅から推定
                if length > 0 and width > 0:
                    # 簡易推定式: L × B × 喫水係数 × 方形係数
                    draft = width * self.DEFAULT_DRAFT_TO_BEAM_RATIO
                    displacement = length * width * draft * self.DEFAULT_BLOCK_COEFFICIENT * self.MILITARY_SHIP_COEFFICIENT
                else:
                    # 最終フォールバック: コストと強度から推定
                    base_cost = hull_stats.get('build_cost_ic', 0)
                    base_strength = hull_stats.get('max_strength', 0)
                    displacement = base_cost * 3.5 + base_strength * 75
            
            # 軽減係数の計算（大型船ほど装備の相対的影響が小さくなる）
            # 最大軽減率: 50%（大型戦艦クラス）
            # 最小軽減率: 0%（駆逐艦クラス）
            
            # 重量ベースの軽減（指数減衰関数）
            k_weight = 1 / (self.MAX_DISPLACEMENT_FOR_REDUCTION * 0.8)  # 減衰係数
            weight_reduction = self.MAX_WEIGHT_REDUCTION_RATIO * (1 - math.exp(-k_weight * displacement))
            
            # 総合軽減係数（飽和関数で組み合わせ）
            # 2つの軽減率を独立に適用し、相乗効果を考慮
            combined_reduction = size_reduction + weight_reduction - (size_reduction * weight_reduction)
            
            return combined_reduction
            
        except Exception as e:
            self.logger.warning(f"軽減係数計算エラー: {e}")
            return 0.0
    
    def _get_module_stats(self, module_id: str) -> Dict[str, Any]:
        """モジュールの性能データを取得
        
        Args:
            module_id (str): モジュールID
            
        Returns:
            Dict[str, Any]: モジュールの性能データ
        """
        if module_id in self.module_stats_cache:
            return self.module_stats_cache[module_id].copy()
        
        module_stats = {}
        
        if self.app_controller:
            try:
                module_data = self.app_controller.get_equipment_data(module_id)
                if module_data:
                    module_stats = module_data.get('stats', {})
            except Exception as e:
                self.logger.warning(f"モジュールデータ取得エラー ({module_id}): {e}")
        
        # デフォルト値の設定
        if not module_stats:
            module_stats = self._get_default_module_stats(module_id)
        
        # キャッシュに保存
        self.module_stats_cache[module_id] = module_stats.copy()
        
        return module_stats
    
    def _calculate_upgrade_stats(self, upgrades: Dict[str, int]) -> Dict[str, Any]:
        """アップグレードによる性能修正を計算
        
        Args:
            upgrades (Dict[str, int]): アップグレードタイプとレベルのマッピング
            
        Returns:
            Dict[str, Any]: アップグレードによる性能修正
        """
        upgrade_effects = {}
        
        for upgrade_type, level in upgrades.items():
            if level <= 0:
                continue
            
            effects = self._get_upgrade_effects(upgrade_type, level)
            upgrade_effects = self._add_stats(upgrade_effects, effects)
        
        return upgrade_effects
    
    def _get_upgrade_effects(self, upgrade_type: str, level: int) -> Dict[str, Any]:
        """アップグレードの効果を取得
        
        Args:
            upgrade_type (str): アップグレードタイプ
            level (int): アップグレードレベル
            
        Returns:
            Dict[str, Any]: アップグレード効果
        """
        cache_key = f"{upgrade_type}_{level}"
        if cache_key in self.upgrade_effects_cache:
            return self.upgrade_effects_cache[cache_key].copy()
        
        effects = {}
        
        # アップグレード効果の計算ルール
        upgrade_rules = {
            'ship_mtg_naval_range_upgrade': {
                'naval_range': level * 50
            },
            'ship_mtg_carrier_engine_upgrade': {
                'naval_speed': level * 0.5
            },
            'ship_mtg_armor_upgrade': {
                'armor_value': level * 2
            },
            'ship_mtg_deck_space_upgrade': {
                'carrier_size': level * 2
            },
            'ship_mtg_anti_air_upgrade': {
                'anti_air_attack': level * 5
            },
            'ship_mtg_fire_control_upgrade': {
                'lg_attack': level * 3,
                'torpedo_attack': level * 2
            }
        }
        
        if upgrade_type in upgrade_rules:
            effects = upgrade_rules[upgrade_type].copy()
        else:
            self.logger.warning(f"未知のアップグレードタイプ: {upgrade_type}")
        
        # キャッシュに保存
        self.upgrade_effects_cache[cache_key] = effects.copy()
        
        return effects
    
    def _add_stats(self, stats1: Dict[str, Any], stats2: Dict[str, Any]) -> Dict[str, Any]:
        """2つの性能辞書を加算
        
        Args:
            stats1 (Dict[str, Any]): 基準となる性能辞書
            stats2 (Dict[str, Any]): 追加する性能辞書
            
        Returns:
            Dict[str, Any]: 加算結果
        """
        result = stats1.copy()
        
        for key, value in stats2.items():
            if isinstance(value, (int, float)):
                result[key] = result.get(key, 0) + value
            elif isinstance(value, str):
                # 文字列の場合は上書き
                result[key] = value
            elif isinstance(value, dict):
                # 辞書の場合は再帰的に加算
                if key in result and isinstance(result[key], dict):
                    result[key] = self._add_stats(result[key], value)
                else:
                    result[key] = value.copy()
            else:
                result[key] = value
        
        return result
    
    def _combine_stats(self, hull_stats: Dict[str, Any], 
                      module_stats: Dict[str, Any], 
                      upgrade_stats: Dict[str, Any]) -> Dict[str, Any]:
        """船体・モジュール・アップグレード性能を統合
        
        Args:
            hull_stats (Dict[str, Any]): 船体基本性能
            module_stats (Dict[str, Any]): モジュール性能
            upgrade_stats (Dict[str, Any]): アップグレード性能
            
        Returns:
            Dict[str, Any]: 統合された性能
        """
        combined = hull_stats.copy()
        combined = self._add_stats(combined, module_stats)
        combined = self._add_stats(combined, upgrade_stats)
        
        # 性能値の範囲チェックと調整
        combined = self._apply_stat_limits(combined)
        
        return combined
    
    def _calculate_derived_stats(self, base_stats: Dict[str, Any]) -> Dict[str, Any]:
        """派生統計を計算
        
        Args:
            base_stats (Dict[str, Any]): 基本性能データ
            
        Returns:
            Dict[str, Any]: 派生統計
        """
        derived = {}
        
        # 戦闘力評価の計算
        lg_attack = base_stats.get('lg_attack', 0)
        torpedo_attack = base_stats.get('torpedo_attack', 0)
        anti_air_attack = base_stats.get('anti_air_attack', 0)
        
        derived['total_attack'] = lg_attack + torpedo_attack + anti_air_attack
        
        # 生存性評価の計算
        armor_value = base_stats.get('armor_value', 0)
        max_strength = base_stats.get('max_strength', 0)
        derived['survivability'] = armor_value + (max_strength / 10)
        
        # 戦略的価値の計算
        naval_range = base_stats.get('naval_range', 0)
        naval_speed = base_stats.get('naval_speed', 0)
        derived['strategic_value'] = (naval_range / 100) + (naval_speed * 2)
        
        # コスト効率の計算
        build_cost_ic = base_stats.get('build_cost_ic', 1)
        if build_cost_ic > 0:
            derived['cost_efficiency'] = derived['total_attack'] / build_cost_ic
        
        return derived
    
    def _apply_stat_limits(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """性能値の範囲制限を適用
        
        Args:
            stats (Dict[str, Any]): 制限前の性能データ
            
        Returns:
            Dict[str, Any]: 制限後の性能データ
        """
        limited_stats = stats.copy()
        
        # 性能制限ルール
        stat_limits = {
            'naval_speed': {'min': 0, 'max': 50},
            'armor_value': {'min': 0, 'max': 100},
            'anti_air_attack': {'min': 0, 'max': 500},
            'carrier_size': {'min': 0, 'max': 200},
            'reliability': {'min': 0.0, 'max': 1.0}
        }
        
        for stat_name, limits in stat_limits.items():
            if stat_name in limited_stats:
                value = limited_stats[stat_name]
                if isinstance(value, (int, float)):
                    min_val = limits.get('min', float('-inf'))
                    max_val = limits.get('max', float('inf'))
                    limited_stats[stat_name] = max(min_val, min(max_val, value))
        
        return limited_stats
    
    def _get_default_hull_stats(self, hull_id: str) -> Dict[str, Any]:
        """デフォルト船体性能を取得
        
        Args:
            hull_id (str): 船体ID
            
        Returns:
            Dict[str, Any]: デフォルト船体性能
        """
        # 船体IDから艦種を推定
        hull_type = self._infer_hull_type(hull_id)
        
        default_stats = {
            'destroyer': {
                'lg_attack': 10,
                'torpedo_attack': 30,
                'anti_air_attack': 15,
                'armor_value': 5,
                'naval_speed': 35,
                'naval_range': 2000,
                'max_strength': 50,
                'build_cost_ic': 250,
                'manpower': 500
            },
            'light_cruiser': {
                'lg_attack': 25,
                'torpedo_attack': 20,
                'anti_air_attack': 25,
                'armor_value': 15,
                'naval_speed': 30,
                'naval_range': 3000,
                'max_strength': 100,
                'build_cost_ic': 500,
                'manpower': 1000
            },
            'heavy_cruiser': {
                'lg_attack': 40,
                'torpedo_attack': 15,
                'anti_air_attack': 20,
                'armor_value': 25,
                'naval_speed': 28,
                'naval_range': 3500,
                'max_strength': 150,
                'build_cost_ic': 800,
                'manpower': 1500
            },
            'battleship': {
                'lg_attack': 80,
                'torpedo_attack': 0,
                'anti_air_attack': 30,
                'armor_value': 50,
                'naval_speed': 25,
                'naval_range': 4000,
                'max_strength': 300,
                'build_cost_ic': 2000,
                'manpower': 3000
            },
            'carrier': {
                'lg_attack': 0,
                'torpedo_attack': 0,
                'anti_air_attack': 40,
                'armor_value': 15,
                'naval_speed': 25,
                'naval_range': 4000,
                'max_strength': 200,
                'carrier_size': 50,
                'build_cost_ic': 1500,
                'manpower': 2000
            },
            'submarine': {
                'lg_attack': 5,
                'torpedo_attack': 50,
                'anti_air_attack': 0,
                'armor_value': 2,
                'naval_speed': 20,
                'naval_range': 3000,
                'max_strength': 30,
                'build_cost_ic': 300,
                'manpower': 300
            }
        }
        
        return default_stats.get(hull_type, default_stats['destroyer']).copy()
    
    def _get_default_module_stats(self, module_id: str) -> Dict[str, Any]:
        """デフォルトモジュール性能を取得
        
        Args:
            module_id (str): モジュールID
            
        Returns:
            Dict[str, Any]: デフォルトモジュール性能
        """
        # モジュールIDからタイプを推定して基本性能を返す
        module_lower = module_id.lower()
        
        if 'gun' in module_lower or 'battery' in module_lower:
            return {'lg_attack': 15}
        elif 'torpedo' in module_lower:
            return {'torpedo_attack': 20}
        elif 'anti_air' in module_lower:
            return {'anti_air_attack': 10}
        elif 'armor' in module_lower:
            return {'armor_value': 10}
        elif 'engine' in module_lower:
            return {'naval_speed': 2}
        elif 'radar' in module_lower:
            return {'lg_attack': 5, 'anti_air_attack': 5}
        else:
            return {}
    
    def _infer_hull_type(self, hull_id: str) -> str:
        """船体IDから艦種を推定
        
        Args:
            hull_id (str): 船体ID
            
        Returns:
            str: 推定された艦種
        """
        hull_lower = hull_id.lower()
        
        if 'destroyer' in hull_lower:
            return 'destroyer'
        elif 'light_cruiser' in hull_lower:
            return 'light_cruiser'
        elif 'heavy_cruiser' in hull_lower:
            return 'heavy_cruiser'
        elif 'battle_cruiser' in hull_lower:
            return 'battle_cruiser'
        elif 'battleship' in hull_lower:
            return 'battleship'
        elif 'carrier' in hull_lower:
            return 'carrier'
        elif 'submarine' in hull_lower:
            return 'submarine'
        else:
            return 'destroyer'  # デフォルト
    
    def _initialize_stat_rules(self) -> Dict[str, Any]:
        """性能計算ルールを初期化
        
        Returns:
            Dict[str, Any]: 性能計算ルール
        """
        return {
            'additive_stats': [
                'lg_attack', 'torpedo_attack', 'anti_air_attack',
                'armor_value', 'naval_speed', 'naval_range',
                'max_strength', 'carrier_size', 'build_cost_ic', 'manpower'
            ],
            'multiplicative_stats': [
                'reliability', 'fuel_consumption'
            ],
            'override_stats': [
                'year', 'type', 'sprite'
            ]
        }
    
    def clear_cache(self):
        """キャッシュをクリア"""
        self.module_stats_cache.clear()
        self.hull_stats_cache.clear()
        self.upgrade_effects_cache.clear()
        self.logger.info("性能計算キャッシュをクリアしました")
    
    def get_cache_info(self) -> Dict[str, int]:
        """キャッシュ情報を取得
        
        Returns:
            Dict[str, int]: キャッシュサイズ情報
        """
        return {
            'module_stats_cache': len(self.module_stats_cache),
            'hull_stats_cache': len(self.hull_stats_cache),
            'upgrade_effects_cache': len(self.upgrade_effects_cache)
        }

    
    def calculate_equipment_stats(self, equipment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        装備データからHOI4用の性能値を計算・変換する
        
        Args:
            equipment_data: 装備データ
            
        Returns:
            Dict[str, Any]: HOI4形式の性能値（add_stats, multiply_stats, add_average_stats構造）
        """
        common = equipment_data.get('common', {})
        specific = equipment_data.get('specific', {})
        equipment_type = equipment_data.get('equipment_type', 'その他')
        
        # HOI4の新しい構造に合わせた出力
        hoi4_stats = {
            'add_stats': {},
            'multiply_stats': {},
            'add_average_stats': {}
        }
        
        # 装備タイプからHOI4カテゴリを取得
        hoi4_category = self._get_hoi4_equipment_category(equipment_type)
        
        # カテゴリ別の性能値変換ロジック
        category_converters = {
            'ship_light_battery': self._convert_light_battery_new,
            'ship_medium_battery': self._convert_medium_battery_new,
            'ship_heavy_battery': self._convert_heavy_battery_new,
            'ship_anti_air_battery': self._convert_aa_battery_new,
            'ship_torpedo': self._convert_torpedo_new,
            'ship_engine': self._convert_engine_new,
            'ship_sonar': self._convert_sonar_new,
            'ship_radar': self._convert_radar_new,
            'ship_fire_control_system': self._convert_fire_control_new,
            'ship_airplane': self._convert_airplane_new,
            'ship_depth_charge': self._convert_depth_charge_new,
            'ship_armor': self._convert_armor_new,
            'ship_extra': self._convert_extra_new
        }
        
        converter = category_converters.get(hoi4_category)
        if converter:
            converted_stats = converter(common, specific)
            # 各セクションにデータをマージ
            for section in ['add_stats', 'multiply_stats', 'add_average_stats']:
                if section in converted_stats:
                    hoi4_stats[section].update(converted_stats[section])
        
        # 空のセクションは削除
        hoi4_stats = {k: v for k, v in hoi4_stats.items() if v}
        
        return hoi4_stats

    def _get_hoi4_equipment_category(self, equipment_type: str) -> str:
        """装備タイプをHOI4の装備カテゴリにマッピング"""
        category_mapping = {
            # 砲系装備
            '小口径砲': 'ship_light_battery',
            '中口径砲': 'ship_medium_battery', 
            '大口径砲': 'ship_heavy_battery',
            '超大口径砲': 'ship_heavy_battery',
            '対空砲': 'ship_anti_air_battery',
            
            # 魚雷・ミサイル系
            '魚雷': 'ship_torpedo',
            '潜水艦魚雷': 'ship_torpedo',
            '対艦ミサイル': 'ship_torpedo',  # HOI4では魚雷カテゴリとして扱う
            '対空ミサイル': 'ship_anti_air_battery',
            
            # 機関系
            '主機': 'ship_engine',
            '補機': 'ship_engine',
            
            # 電子装備
            'ソナー': 'ship_sonar',
            '大型ソナー': 'ship_sonar', 
            '小型電探': 'ship_radar',
            '大型電探': 'ship_radar',
            '火器管制/測距儀': 'ship_fire_control_system',
            
            # 航空装備
            '水上機': 'ship_airplane',
            '艦上偵察機': 'ship_airplane',
            '回転翼機': 'ship_airplane',
            '対潜哨戒機': 'ship_airplane',
            '大型飛行艇': 'ship_airplane',
            
            # 対潜装備
            '爆雷投射機': 'ship_depth_charge',
            '爆雷': 'ship_depth_charge',
            '対潜迫撃砲': 'ship_depth_charge',
            
            # その他
            'ハンガー': 'ship_extra',
            '中型バルジ': 'ship_armor',
            '大型バルジ': 'ship_armor',
            'その他': 'ship_extra'
        }
        
        return category_mapping.get(equipment_type, 'ship_extra')

    def _convert_resource_keys(self, resources: Dict[str, Any]) -> Dict[str, Any]:
        """日本語リソース名をHOI4英語名に変換"""
        resource_mapping = {
            '鉄': 'steel',
            'クロム': 'chromium', 
            'アルミ': 'aluminium',
            'タングステン': 'tungsten',
            'ゴム': 'rubber'
        }
        
        converted = {}
        for resource_jp, amount in resources.items():
            if amount > 0:
                resource_en = resource_mapping.get(resource_jp, resource_jp.lower())
                converted[resource_en] = amount
        
        return converted

    def _convert_light_battery(self, specific: Dict[str, Any]) -> Dict[str, Any]:
        """小口径砲の性能値を変換"""
        stats = {}
        if '威力' in specific:
            stats['light_attack'] = specific['威力']
        if '対空威力' in specific:
            stats['anti_air_attack'] = specific['対空威力']
        if '射程' in specific:
            # 射程は信頼性に変換（長射程 = 高信頼性）
            range_val = specific['射程']
            stats['reliability'] = min(0.95, 0.7 + (range_val / 15000))
        if '発射速度' in specific:
            # 発射速度は攻撃力にボーナス
            fire_rate = specific['発射速度']
            if 'light_attack' in stats:
                stats['light_attack'] *= (1 + fire_rate / 100)
        return stats

    def _convert_medium_battery(self, specific: Dict[str, Any]) -> Dict[str, Any]:
        """中口径砲の性能値を変換"""
        stats = {}
        if '威力' in specific:
            power = specific['威力']
            stats['light_attack'] = power * 0.8
            stats['heavy_attack'] = power * 0.6
        if '対空威力' in specific:
            stats['anti_air_attack'] = specific['対空威力']
        if '射程' in specific:
            range_val = specific['射程']
            stats['reliability'] = min(0.95, 0.75 + (range_val / 20000))
        return stats

    def _convert_heavy_battery(self, specific: Dict[str, Any]) -> Dict[str, Any]:
        """大口径砲の性能値を変換"""
        stats = {}
        if '威力' in specific:
            stats['heavy_attack'] = specific['威力']
        if '対空威力' in specific:
            stats['anti_air_attack'] = specific['対空威力'] * 0.5  # 対空には不向き
        if '射程' in specific:
            range_val = specific['射程']
            stats['reliability'] = min(0.95, 0.8 + (range_val / 25000))
        if '貫通力' in specific:
            stats['ap_attack'] = specific['貫通力']
        return stats

    def _convert_aa_battery(self, specific: Dict[str, Any]) -> Dict[str, Any]:
        """対空砲の性能値を変換"""
        stats = {}
        if '威力' in specific:
            stats['anti_air_attack'] = specific['威力']
        if '対艦威力' in specific:
            stats['light_attack'] = specific['対艦威力'] * 0.3  # 対艦には不向き
        if '射程' in specific:
            range_val = specific['射程']
            stats['reliability'] = min(0.95, 0.75 + (range_val / 12000))
        return stats

    def _convert_torpedo(self, specific: Dict[str, Any]) -> Dict[str, Any]:
        """魚雷の性能値を変換"""
        stats = {}
        if '威力' in specific:
            stats['torpedo_attack'] = specific['威力']
        if '射程' in specific:
            range_val = specific['射程']
            stats['reliability'] = min(0.95, 0.7 + (range_val / 30000))
        if '速度' in specific:
            # 魚雷速度は命中率に影響
            speed = specific['速度']
            if 'torpedo_attack' in stats:
                stats['torpedo_attack'] *= (1 + speed / 200)
        return stats

    def _convert_engine(self, specific: Dict[str, Any]) -> Dict[str, Any]:
        """機関の性能値を変換"""
        stats = {}
        if '出力' in specific:
            stats['naval_speed'] = specific['出力'] / 1000  # 出力を速度に変換
        if '燃費' in specific:
            stats['fuel_consumption'] = specific['燃費']
        if '信頼性' in specific:
            stats['reliability'] = min(0.95, specific['信頼性'] / 100)
        return stats

    def _convert_sonar(self, specific: Dict[str, Any]) -> Dict[str, Any]:
        """ソナーの性能値を変換"""
        stats = {}
        if '探知距離' in specific:
            detection_range = specific['探知距離']
            stats['sub_detection'] = detection_range / 100
        if '精度' in specific:
            stats['reliability'] = min(0.95, specific['精度'] / 100)
        return stats

    def _convert_radar(self, specific: Dict[str, Any]) -> Dict[str, Any]:
        """レーダーの性能値を変換"""
        stats = {}
        if '探知距離' in specific:
            detection_range = specific['探知距離']
            stats['surface_detection'] = detection_range / 100
        if '精度' in specific:
            stats['reliability'] = min(0.95, specific['精度'] / 100)
        return stats

    def _convert_fire_control(self, specific: Dict[str, Any]) -> Dict[str, Any]:
        """火器管制システムの性能値を変換"""
        stats = {}
        if '精度向上' in specific:
            accuracy = specific['精度向上']
            stats['light_attack_modifier'] = accuracy / 100
            stats['heavy_attack_modifier'] = accuracy / 100
        if '射程延長' in specific:
            range_ext = specific['射程延長']
            stats['reliability'] = min(0.95, 0.8 + (range_ext / 100))
        return stats

    def _convert_airplane(self, specific: Dict[str, Any]) -> Dict[str, Any]:
        """航空機の性能値を変換"""
        stats = {}
        if '偵察能力' in specific:
            recon = specific['偵察能力']
            stats['surface_detection'] = recon / 50
            stats['sub_detection'] = recon / 100
        if '攻撃力' in specific:
            stats['naval_strike_attack'] = specific['攻撃力']
        return stats

    def _convert_depth_charge(self, specific: Dict[str, Any]) -> Dict[str, Any]:
        """対潜兵器の性能値を変換"""
        stats = {}
        if '威力' in specific:
            stats['sub_attack'] = specific['威力']
        if '射程' in specific:
            range_val = specific['射程']
            stats['reliability'] = min(0.95, 0.7 + (range_val / 5000))
        return stats

    def _convert_armor(self, specific: Dict[str, Any]) -> Dict[str, Any]:
        """装甲の性能値を変換"""
        stats = {}
        if '装甲値' in specific:
            stats['armor_value'] = specific['装甲値']
        if '重量軽減' in specific:
            weight_reduction = specific['重量軽減']
            stats['build_cost_ic_modifier'] = -weight_reduction / 100
        return stats

    def _convert_extra(self, specific: Dict[str, Any]) -> Dict[str, Any]:
        """その他装備の性能値を変換"""
        stats = {}
        # 汎用的な変換ロジック
        if '効果' in specific:
            stats['modifier_value'] = specific['効果']
        return stats

    # === 新しいHOI4形式対応の変換メソッド ===
    
    def _convert_light_battery_new(self, common: Dict[str, Any], specific: Dict[str, Any]) -> Dict[str, Any]:
        """小口径砲の性能値を新HOI4形式に変換"""
        result = {
            'add_stats': {},
            'multiply_stats': {},
            'add_average_stats': {}
        }
        
        # 威力 -> lg_attack
        if '威力' in specific:
            result['add_stats']['lg_attack'] = specific['威力'] / 10.0
        
        # 重量 -> build_cost_ic
        if '重量' in common:
            result['add_stats']['build_cost_ic'] = common['重量']
        
        # 速度低下 -> naval_speed (負の値)
        if '重量' in common:
            weight = common['重量']
            speed_penalty = -(weight / 5000.0)  # 重量5000で-1.0の速度低下
            result['multiply_stats']['naval_speed'] = speed_penalty
        
        # 装甲貫通力
        if '威力' in specific:
            result['add_average_stats']['lg_armor_piercing'] = specific['威力'] / 4.0
        
        # 耐久力への貢献
        if '重量' in common:
            result['add_average_stats']['max_strength'] = common['重量'] / 20.0
        
        return result
    
    def _convert_medium_battery_new(self, common: Dict[str, Any], specific: Dict[str, Any]) -> Dict[str, Any]:
        """中口径砲の性能値を新HOI4形式に変換"""
        result = {
            'add_stats': {},
            'multiply_stats': {},
            'add_average_stats': {}
        }
        
        if '威力' in specific:
            power = specific['威力']
            result['add_stats']['lg_attack'] = power / 8.0
            result['add_stats']['hg_attack'] = power / 15.0
        
        if '重量' in common:
            result['add_stats']['build_cost_ic'] = common['重量']
            speed_penalty = -(common['重量'] / 4000.0)
            result['multiply_stats']['naval_speed'] = speed_penalty
            result['add_average_stats']['max_strength'] = common['重量'] / 15.0
        
        if '威力' in specific:
            result['add_average_stats']['lg_armor_piercing'] = specific['威力'] / 3.0
            result['add_average_stats']['hg_armor_piercing'] = specific['威力'] / 6.0
        
        return result
    
    def _convert_heavy_battery_new(self, common: Dict[str, Any], specific: Dict[str, Any]) -> Dict[str, Any]:
        """大口径砲の性能値を新HOI4形式に変換"""
        result = {
            'add_stats': {},
            'multiply_stats': {},
            'add_average_stats': {}
        }
        
        if '威力' in specific:
            result['add_stats']['hg_attack'] = specific['威力'] / 12.0
        
        if '重量' in common:
            result['add_stats']['build_cost_ic'] = common['重量']
            speed_penalty = -(common['重量'] / 3000.0)
            result['multiply_stats']['naval_speed'] = speed_penalty
            result['add_average_stats']['max_strength'] = common['重量'] / 10.0
        
        if '威力' in specific:
            result['add_average_stats']['hg_armor_piercing'] = specific['威力'] / 2.0
        
        return result
    
    def _convert_aa_battery_new(self, common: Dict[str, Any], specific: Dict[str, Any]) -> Dict[str, Any]:
        """対空砲の性能値を新HOI4形式に変換"""
        result = {
            'add_stats': {},
            'multiply_stats': {},
            'add_average_stats': {}
        }
        
        if '威力' in specific:
            result['add_stats']['anti_air_attack'] = specific['威力'] / 8.0
        
        if '重量' in common:
            result['add_stats']['build_cost_ic'] = common['重量']
            speed_penalty = -(common['重量'] / 6000.0)
            result['multiply_stats']['naval_speed'] = speed_penalty
            result['add_average_stats']['max_strength'] = common['重量'] / 25.0
        
        return result
    
    def _convert_torpedo_new(self, common: Dict[str, Any], specific: Dict[str, Any]) -> Dict[str, Any]:
        """魚雷の性能値を新HOI4形式に変換"""
        result = {
            'add_stats': {},
            'multiply_stats': {},
            'add_average_stats': {}
        }
        
        if '威力' in specific:
            result['add_stats']['torpedo_attack'] = specific['威力'] / 8.0
        
        if '重量' in common:
            result['add_stats']['build_cost_ic'] = common['重量']
            speed_penalty = -(common['重量'] / 7000.0)
            result['multiply_stats']['naval_speed'] = speed_penalty
            result['add_average_stats']['max_strength'] = common['重量'] / 30.0
        
        return result
    
    def _convert_engine_new(self, common: Dict[str, Any], specific: Dict[str, Any]) -> Dict[str, Any]:
        """機関の性能値を新HOI4形式に変換"""
        result = {
            'add_stats': {},
            'multiply_stats': {},
            'add_average_stats': {}
        }
        
        if '出力' in specific:
            power = specific['出力']
            result['add_stats']['naval_speed'] = power / 2000.0
        
        if '重量' in common:
            result['add_stats']['build_cost_ic'] = common['重量']
        
        if '燃費' in specific:
            result['multiply_stats']['fuel_consumption'] = specific['燃費'] / 100.0
        
        return result
    
    def _convert_sonar_new(self, common: Dict[str, Any], specific: Dict[str, Any]) -> Dict[str, Any]:
        """ソナーの性能値を新HOI4形式に変換"""
        result = {
            'add_stats': {},
            'multiply_stats': {},
            'add_average_stats': {}
        }
        
        if '探知距離' in specific:
            result['add_stats']['sub_detection'] = specific['探知距離'] / 200.0
        
        if '重量' in common:
            result['add_stats']['build_cost_ic'] = common['重量']
            speed_penalty = -(common['重量'] / 10000.0)
            result['multiply_stats']['naval_speed'] = speed_penalty
        
        return result
    
    def _convert_radar_new(self, common: Dict[str, Any], specific: Dict[str, Any]) -> Dict[str, Any]:
        """レーダーの性能値を新HOI4形式に変換"""
        result = {
            'add_stats': {},
            'multiply_stats': {},
            'add_average_stats': {}
        }
        
        if '探知距離' in specific:
            result['add_stats']['surface_detection'] = specific['探知距離'] / 150.0
        
        if '重量' in common:
            result['add_stats']['build_cost_ic'] = common['重量']
            speed_penalty = -(common['重量'] / 8000.0)
            result['multiply_stats']['naval_speed'] = speed_penalty
        
        return result
    
    def _convert_fire_control_new(self, common: Dict[str, Any], specific: Dict[str, Any]) -> Dict[str, Any]:
        """火器管制システムの性能値を新HOI4形式に変換"""
        result = {
            'add_stats': {},
            'multiply_stats': {},
            'add_average_stats': {}
        }
        
        if '精度向上' in specific:
            accuracy = specific['精度向上']
            result['multiply_stats']['lg_attack'] = accuracy / 200.0
            result['multiply_stats']['hg_attack'] = accuracy / 200.0
        
        if '重量' in common:
            result['add_stats']['build_cost_ic'] = common['重量']
        
        return result
    
    def _convert_airplane_new(self, common: Dict[str, Any], specific: Dict[str, Any]) -> Dict[str, Any]:
        """航空機の性能値を新HOI4形式に変換"""
        result = {
            'add_stats': {},
            'multiply_stats': {},
            'add_average_stats': {}
        }
        
        if '偵察能力' in specific:
            recon = specific['偵察能力']
            result['add_stats']['surface_detection'] = recon / 80.0
            result['add_stats']['sub_detection'] = recon / 160.0
        
        if '重量' in common:
            result['add_stats']['build_cost_ic'] = common['重量']
        
        return result
    
    def _convert_depth_charge_new(self, common: Dict[str, Any], specific: Dict[str, Any]) -> Dict[str, Any]:
        """対潜兵器の性能値を新HOI4形式に変換"""
        result = {
            'add_stats': {},
            'multiply_stats': {},
            'add_average_stats': {}
        }
        
        if '威力' in specific:
            result['add_stats']['sub_attack'] = specific['威力'] / 10.0
        
        if '重量' in common:
            result['add_stats']['build_cost_ic'] = common['重量']
            speed_penalty = -(common['重量'] / 8000.0)
            result['multiply_stats']['naval_speed'] = speed_penalty
        
        return result
    
    def _convert_armor_new(self, common: Dict[str, Any], specific: Dict[str, Any]) -> Dict[str, Any]:
        """装甲の性能値を新HOI4形式に変換"""
        result = {
            'add_stats': {},
            'multiply_stats': {},
            'add_average_stats': {}
        }
        
        if '装甲値' in specific:
            result['add_stats']['armor_value'] = specific['装甲値'] / 10.0
        
        if '重量' in common:
            result['add_stats']['build_cost_ic'] = common['重量']
            speed_penalty = -(common['重量'] / 5000.0)
            result['multiply_stats']['naval_speed'] = speed_penalty
            result['add_average_stats']['max_strength'] = common['重量'] / 8.0
        
        return result
    
    def _convert_extra_new(self, common: Dict[str, Any], specific: Dict[str, Any]) -> Dict[str, Any]:
        """その他装備の性能値を新HOI4形式に変換"""
        result = {
            'add_stats': {},
            'multiply_stats': {},
            'add_average_stats': {}
        }
        
        if '重量' in common:
            result['add_stats']['build_cost_ic'] = common['重量']
        
        if '効果' in specific:
            result['add_stats']['modifier_value'] = specific['効果']
        
        return result
