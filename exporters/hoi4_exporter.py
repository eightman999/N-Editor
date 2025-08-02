# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: hoi4_exporter形式のエクスポート機能
"""HOI4形式エクスポーター

このモジュールは、NavalDesignSystemの設計データを
Hearts of Iron IV（HOI4）のMODファイル形式でエクスポートする機能を提供します。
"""

import os
import json
from typing import Dict, Any, List, Optional
from .base_exporter import BaseExporter


class HOI4Exporter(BaseExporter):
    """HOI4形式でのエクスポーター
    
    設計データをcreate_equipment_variant形式で、
    船体データをequipments形式でエクスポートします。
    """
    
    def __init__(self, output_dir: str, country_tag: str = "GER"):
        """HOI4エクスポーターを初期化
        
        Args:
            output_dir (str): 出力ディレクトリパス
            country_tag (str): 国家タグ（3文字）
        """
        super().__init__(output_dir)
        self.country_tag = country_tag.upper()
        
        # 出力ファイルパス
        self.designs_file = os.path.join(output_dir, f"{self.country_tag}_designs.txt")
        self.hulls_file = os.path.join(output_dir, f"{self.country_tag}_hulls.txt")
        
        # 設定
        self.include_stats_comments = True
        self.include_upgrades = True
        self.file_encoding = 'utf-8'
        
        # 既に初期化済みかのフラグ
        self._files_initialized = False
        
        # 軽減後装備の重複防止用セット
        self.exported_reduced_equipments = set()
        
        # StatsCalculatorインスタンス
        from utils.stats_calculator import StatsCalculator
        self.stats_calculator = StatsCalculator()
    
    def export_design(self, design_data: Dict[str, Any]) -> bool:
        """設計データをcreate_equipment_variant形式でエクスポート
        
        Args:
            design_data (Dict[str, Any]): 設計データ
            
        Returns:
            bool: エクスポート成功時True、失敗時False
        """
        design_name = design_data.get('design_name', 'Unknown')
        
        try:
            self.log_export_start('design', design_name)
            
            # データ検証
            if not self.validate_design_data(design_data):
                self.log_export_error('design', design_name, "データ検証に失敗")
                return False
            
            # ファイル初期化（初回のみ）
            if not self._files_initialized:
                self.initialize_files()
            
            # 船体データを取得して軽減後装備を書き出し
            hull_id = design_data.get('hull_id')
            if hull_id and hasattr(self.stats_calculator, 'app_controller') and self.stats_calculator.app_controller:
                hull_stats = self.stats_calculator._get_hull_base_stats(hull_id)
                hull_type = self.stats_calculator._infer_hull_type(hull_id)
                
                # 各モジュールの軽減後装備を書き出し
                modules = design_data.get('modules', {})
                for slot_id, module_id in modules.items():
                    if module_id and module_id != 'empty':
                        # 元の装備データを取得
                        original_equipment = self.stats_calculator.app_controller.get_equipment_data(module_id)
                        if original_equipment:
                            # 軽減後装備IDを生成
                            reduced_id = self._generate_reduced_equipment_id(module_id, hull_type)
                            # 軽減後装備を書き出し
                            self._export_reduced_equipment(original_equipment, hull_stats, reduced_id)
            
            # create_equipment_variant ブロックの生成
            variant_block = self._generate_variant_block(design_data)
            
            # ファイルに書き込み
            self._append_to_file(self.designs_file, variant_block)
            
            self.log_export_success('design', design_name)
            return True
            
        except Exception as e:
            self.log_export_error('design', design_name, str(e))
            return False
    
    def export_hull(self, hull_data: Dict[str, Any]) -> bool:
        """船体データをequipments形式でエクスポート
        
        Args:
            hull_data (Dict[str, Any]): 船体データ
            
        Returns:
            bool: エクスポート成功時True、失敗時False
        """
        hull_name = hull_data.get('name', 'Unknown')
        
        try:
            self.log_export_start('hull', hull_name)
            
            # データ検証
            if not self.validate_hull_data(hull_data):
                self.log_export_error('hull', hull_name, "データ検証に失敗")
                return False
            
            # ファイル初期化（初回のみ）
            if not self._files_initialized:
                self.initialize_files()
            
            # equipments ブロックの生成
            equipment_block = self._generate_equipment_block(hull_data)
            
            # ファイルに書き込み
            self._append_to_file(self.hulls_file, equipment_block)
            
            self.log_export_success('hull', hull_name)
            return True
            
        except Exception as e:
            self.log_export_error('hull', hull_name, str(e))
            return False
    
    def _generate_variant_block(self, design_data: Dict[str, Any]) -> str:
        """create_equipment_variant ブロックを生成
        
        Args:
            design_data (Dict[str, Any]): 設計データ
            
        Returns:
            str: 生成されたブロックテキスト
        """
        design_name = design_data['design_name']
        hull_id = design_data['hull_id']
        modules = design_data.get('modules', {})
        upgrades = design_data.get('upgrades', {})
        
        lines = []
        lines.append("\tcreate_equipment_variant = {")
        lines.append(f'\t\tname = "{self._escape_string(design_name)}"')
        lines.append(f"\t\ttype = {hull_id}")
        
        # name_group があれば追加
        if 'name_group' in design_data and design_data['name_group']:
            lines.append(f"\t\tname_group = {design_data['name_group']}")
        
        # upgrades セクション
        if self.include_upgrades and upgrades:
            lines.append("\t\tupgrades = {")
            for upgrade_type, level in upgrades.items():
                lines.append(f"\t\t\t{upgrade_type} = {level}")
            lines.append("\t\t}")
        
        # modules セクション
        if modules:
            lines.append("\t\tmodules = {")
            for slot_id, module_id in modules.items():
                if module_id and module_id != 'empty':
                    hull_type = 'destroyer' if not hasattr(self.stats_calculator, '_infer_hull_type') else self.stats_calculator._infer_hull_type(hull_id)
                    reduced_id = self._generate_reduced_equipment_id(module_id, hull_type)
                    lines.append(f"\t\t\t{slot_id} = {reduced_id}")
            lines.append("\t\t}")
        
        lines.append("\t}")

        return "\n".join(lines)
    
    def _generate_equipment_block(self, hull_data: Dict[str, Any]) -> str:
        """equipments ブロックを生成
        
        Args:
            hull_data (Dict[str, Any]): 船体データ
            
        Returns:
            str: 生成されたブロックテキスト
        """
        hull_id = hull_data['hull_id']
        hull_name = hull_data['name']
        hull_type = hull_data['type']
        year = hull_data.get('year', 1940)
        slots = hull_data.get('slots', {})
        base_stats = hull_data.get('base_stats', {})
        
        # カスタム艦種は常にis_archetype=false（建造可能船体）
        is_archetype = False
        is_buildable = True
        
        # 船体タイプを標準HOI4アーキタイプにマッピング
        archetype_type = self._get_archetype_type(hull_type)
        
        lines = []
        lines.append(f"\t{hull_id} = {{")
        lines.append(f"\t\tyear = {year}")
        lines.append(f"\t\tis_archetype = {str(is_archetype).lower()}")
        lines.append(f"\t\tis_buildable = {str(is_buildable).lower()}")
        lines.append(f"\t\ttype = {archetype_type}")  # 標準アーキタイプタイプを使用
        lines.append(f"\t\tsprite = {hull_type}")      # スプライトは元の船体タイプ
        lines.append("\t\tgroup_by = archetype")
        lines.append("\t\tpriority = 1000")
        
        # interface_categoryの設定
        interface_category = self._get_interface_category(hull_type)
        lines.append(f"\t\tinterface_category = {interface_category}")
        
        # module_slots セクション
        if slots:
            lines.append("\t\tmodule_slots = {")
            for slot_id, slot_config in slots.items():
                lines.append(f"\t\t\t{slot_id} = {{")
                lines.append(f"\t\t\t\trequired = {str(slot_config.get('required', False)).lower()}")
                
                # ship_type_slotの場合は適切なカテゴリを設定
                categories = slot_config.get('categories', [])
                if slot_id == 'ship_type_slot':
                    # カスタム艦種のタイプに基づいてカテゴリを自動設定
                    categories = self._get_ship_type_categories(hull_type)
                    self.logger.info(f"船体タイプ {hull_type} に対してship_type_slotカテゴリを設定: {categories}")
                
                if categories:
                    lines.append("\t\t\t\tallowed_module_categories = {")
                    for category in categories:
                        lines.append(f"\t\t\t\t\t{category}")
                    lines.append("\t\t\t\t}")
                
                if 'gfx' in slot_config:
                    lines.append(f"\t\t\t\tgfx = {slot_config['gfx']}")
                    
                lines.append("\t\t\t}")
            lines.append("\t\t}")
        
        # default_modules セクション
        if slots:
            lines.append("\t\tdefault_modules = {")
            for slot_id, slot_config in slots.items():
                if slot_id == 'ship_type_slot':
                    # ship_type_slotに対して適切なデフォルトモジュールを設定
                    default_module = self._get_default_ship_type_module(hull_type)
                    self.logger.info(f"船体タイプ {hull_type} に対してship_type_slotデフォルトモジュールを設定: {default_module}")
                else:
                    default_module = slot_config.get('default_module', 'empty')
                lines.append(f"\t\t\t{slot_id} = {default_module}")
            lines.append("\t\t}")
        
        # 基本性能
        if base_stats:
            lines.append("")  # 空行を追加
            lines.append("\t\t# 基本性能")
            for stat_name, value in base_stats.items():
                lines.append(f"\t\t{stat_name} = {value}")
        
        lines.append("\t}")
        
        return "\n".join(lines)
    
    def _generate_stats_comment(self, stats: Dict[str, Any]) -> str:
        """性能コメントを生成
        
        Args:
            stats (Dict[str, Any]): 性能データ
            
        Returns:
            str: 生成されたコメント
        """
        stat_parts = []
        
        # 主要な性能値を選択してコメント化
        stat_mapping = {
            'lg_attack': '攻撃力',
            'torpedo_attack': '雷撃力',
            'anti_air_attack': '対空攻撃',
            'armor_value': '装甲',
            'naval_speed': '速度',
            'naval_range': '航続距離',
            'max_strength': '耐久力',
            'carrier_size': '航空機搭載数'
        }
        
        for stat_key, stat_display in stat_mapping.items():
            if stat_key in stats:
                value = stats[stat_key]
                if isinstance(value, (int, float)) and value != 0:
                    stat_parts.append(f"{stat_display}: {value}")
        
        if stat_parts:
            return f"# 性能: {', '.join(stat_parts)}"
        return ""
    
    def _get_interface_category(self, hull_type: str) -> str:
        """船体タイプからインターフェースカテゴリを取得
        
        Args:
            hull_type (str): 船体タイプ
            
        Returns:
            str: インターフェースカテゴリ
        """
        category_mapping = {
            'destroyer': 'interface_category_screen_ships',
            'light_cruiser': 'interface_category_screen_ships',
            'heavy_cruiser': 'interface_category_capital_ships',
            'battle_cruiser': 'interface_category_capital_ships',
            'battleship': 'interface_category_capital_ships',
            'carrier': 'interface_category_capital_ships',
            'submarine': 'interface_category_other_ships'
        }
        
        # カスタム船体タイプの場合のフォールバック
        if hull_type not in category_mapping:
            # DDG, FFG等のミサイル艦は駆逐艦カテゴリに分類
            if 'DDG' in hull_type.upper() or 'FFG' in hull_type.upper() or 'DD' in hull_type.upper():
                return 'interface_category_screen_ships'
            # CG, CA等の巡洋艦は主力艦カテゴリに分類
            elif 'CG' in hull_type.upper() or 'CA' in hull_type.upper() or 'CL' in hull_type.upper():
                return 'interface_category_capital_ships'
            # CV, CVN等の空母は主力艦カテゴリに分類
            elif 'CV' in hull_type.upper():
                return 'interface_category_capital_ships'
            # SS, SSN等の潜水艦はその他カテゴリに分類
            elif 'SS' in hull_type.upper():
                return 'interface_category_other_ships'
            # その他は主力艦として扱う
            else:
                self.logger.info(f"カスタム船体タイプ {hull_type} を主力艦カテゴリに分類")
                return 'interface_category_capital_ships'
        
        return category_mapping[hull_type]

    def _get_ship_type_categories(self, hull_type: str) -> List[str]:
        """船体タイプに基づいてship_type_slotのカテゴリを取得
        
        Args:
            hull_type (str): 船体タイプ
            
        Returns:
            List[str]: 適用可能なモジュールカテゴリのリスト
        """
        # 船体タイプに応じたカテゴリマッピング
        type_category_mapping = {
            # 駆逐艦系
            'destroyer': ['SRM_ESC'],
            'DDG': ['SRM_ESC', 'SRMs_CRS'],  # ミサイル駆逐艦
            'FFG': ['SRM_ESC'],  # フリゲート
            'DD': ['SRM_ESC'],   # 駆逐艦
            
            # 巡洋艦系
            'light_cruiser': ['SRMs_CRS'],
            'heavy_cruiser': ['SRMs_CRS'],
            'CL': ['SRMs_CRS'],  # 軽巡洋艦
            'CA': ['SRMs_CRS'],  # 重巡洋艦
            'CG': ['SRMs_CRS'],  # ミサイル巡洋艦
            
            # 戦艦系
            'battleship': ['SRM_CAP'],
            'battle_cruiser': ['SRM_CAP'],
            'BB': ['SRM_CAP'],   # 戦艦
            'BC': ['SRM_CAP'],   # 巡洋戦艦
            
            # 空母系
            'carrier': ['SRM_AIR'],
            'CV': ['SRM_AIR'],   # 空母
            'CVN': ['SRM_AIR'],  # 原子力空母
            'CVL': ['SRM_AIR'],  # 軽空母
            
            # 潜水艦系
            'submarine': ['SRM_SUB'],
            'SS': ['SRM_SUB'],   # 潜水艦
            'SSN': ['SRM_SUB'],  # 原子力潜水艦
            'SSK': ['SRM_SUB'],  # ディーゼル潜水艦
            
            # 補助艦艇系
            'AUX': ['SRM_AUX'],  # 補助艦艇
            'AS': ['SRM_AUX'],   # 潜水艦母艦
            'AR': ['SRM_AUX'],   # 修理艦
        }
        
        # 直接マッピングがある場合
        if hull_type in type_category_mapping:
            return type_category_mapping[hull_type]
        
        # パターンマッチング
        hull_upper = hull_type.upper()
        if any(pattern in hull_upper for pattern in ['DDG', 'FFG', 'DD']):
            return ['SRM_ESC', 'SRMs_CRS']
        elif any(pattern in hull_upper for pattern in ['CG', 'CA', 'CL']):
            return ['SRMs_CRS']
        elif any(pattern in hull_upper for pattern in ['CV']):
            return ['SRM_AIR']
        elif any(pattern in hull_upper for pattern in ['SS']):
            return ['SRM_SUB']
        elif any(pattern in hull_upper for pattern in ['BB', 'BC']):
            return ['SRM_CAP']
        else:
            # デフォルトは巡洋艦カテゴリ
            self.logger.warning(f"未知の船体タイプ {hull_type} - デフォルトカテゴリ SRMs_CRS を使用")
            return ['SRMs_CRS']

    def _get_default_ship_type_module(self, hull_type: str) -> str:
        """船体タイプに基づいてship_type_slotのデフォルトモジュールを取得
        
        Args:
            hull_type (str): 船体タイプ
            
        Returns:
            str: デフォルトモジュールID
        """
        # 船体タイプに応じたデフォルトモジュールマッピング
        default_module_mapping = {
            # 駆逐艦系 - 護衛任務
            'destroyer': 'SRM_FF',
            'DDG': 'SRM_MB',    # ミサイル駆逐艦
            'FFG': 'SRM_FF',    # フリゲート
            'DD': 'SRM_FF',     # 駆逐艦
            
            # 巡洋艦系 - 巡洋任務
            'light_cruiser': 'SRM_CL',
            'heavy_cruiser': 'SRM_CA',
            'CL': 'SRM_CL',     # 軽巡洋艦
            'CA': 'SRM_CA',     # 重巡洋艦
            'CG': 'SRM_CG',     # ミサイル巡洋艦
            
            # 戦艦系 - 主力艦任務
            'battleship': 'SRM_BB',
            'battle_cruiser': 'SRM_BC',
            'BB': 'SRM_BB',     # 戦艦
            'BC': 'SRM_BC',     # 巡洋戦艦
            
            # 空母系 - 航空任務
            'carrier': 'SRM_CV',
            'CV': 'SRM_CV',     # 空母
            'CVN': 'SRM_CVN',   # 原子力空母
            'CVL': 'SRM_CVL',   # 軽空母
            
            # 潜水艦系 - 潜水艦任務
            'submarine': 'SRM_SS',
            'SS': 'SRM_SS',     # 潜水艦
            'SSN': 'SRM_SSN',   # 原子力潜水艦
            'SSK': 'SRM_SS',    # ディーゼル潜水艦
            
            # 補助艦艇系
            'AUX': 'SRM_AUX',   # 補助艦艇
            'AS': 'SRM_AS',     # 潜水艦母艦
            'AR': 'SRM_AR',     # 修理艦
        }
        
        # 直接マッピングがある場合
        if hull_type in default_module_mapping:
            return default_module_mapping[hull_type]
        
        # パターンマッチング
        hull_upper = hull_type.upper()
        if 'DDG' in hull_upper:
            return 'SRM_MB'  # ミサイル駆逐艦
        elif any(pattern in hull_upper for pattern in ['FFG', 'DD']):
            return 'SRM_FF'  # フリゲート/駆逐艦
        elif 'CG' in hull_upper:
            return 'SRM_CG'  # ミサイル巡洋艦
        elif 'CA' in hull_upper:
            return 'SRM_CA'  # 重巡洋艦
        elif 'CL' in hull_upper:
            return 'SRM_CL'  # 軽巡洋艦
        elif 'CV' in hull_upper:
            return 'SRM_CV'  # 空母
        elif 'SS' in hull_upper:
            return 'SRM_SS'  # 潜水艦
        elif any(pattern in hull_upper for pattern in ['BB', 'BC']):
            return 'SRM_BB'  # 戦艦
        else:
            # デフォルトは汎用巡洋艦
            self.logger.warning(f"未知の船体タイプ {hull_type} - デフォルトモジュール SRM_C を使用")
            return 'SRM_C'

    def _get_archetype_type(self, hull_type: str) -> str:
        """船体タイプを標準HOI4アーキタイプにマッピング
        
        Args:
            hull_type (str): 船体タイプ
            
        Returns:
            str: 対応する標準アーキタイプタイプ
        """
        # 船体タイプ → 標準アーキタイプのマッピング表
        archetype_mapping = {
            # 戦艦系
            'BB': 'ship_hull_heavy',     # 戦艦
            'BC': 'ship_hull_heavy',     # 巡洋戦艦
            'BF': 'ship_hull_battle_carrier',  # 戦闘空母
            'CDB': 'ship_hull_heavy',    # 沿岸防御戦艦
            
            # 巡洋艦系
            'CB': 'ship_hull_cruiser',   # 巡洋戦艦
            'CA': 'ship_hull_cruiser',   # 重巡洋艦
            'CL': 'ship_hull_cruiser',   # 軽巡洋艦
            'MC': 'ship_hull_medium',    # 中型巡洋艦
            
            # 駆逐艦系
            'DD': 'ship_hull_light',     # 駆逐艦
            'DE': 'ship_hull_light',     # 護衛駆逐艦
            'FF': 'ship_hull_frigate',   # フリゲート
            'K': 'ship_hull_frigate',    # コルベット
            
            # 補助戦闘艦
            'FAV': 'ship_hull_heavy',    # 高速攻撃艦
            'SAV': 'ship_hull_medium',   # 標準攻撃艦
            'TAV': 'ship_hull_light',    # 魚雷攻撃艦
            'CC': 'ship_hull_craft',     # 沿岸戦闘艦
            'AV': 'ship_hull_medium',    # 水上機母艦
            
            # 空母系
            'CV': 'ship_hull_carrier',   # 空母
            'CVL': 'ship_hull_light_carrier',  # 軽空母
            'CF': 'ship_hull_cruiser_carrier',  # 巡洋艦空母
            
            # 潜水艦系
            'FS': 'ship_hull_submarine', # フリート潜水艦
            'SS': 'ship_hull_submarine', # 潜水艦
            'SCV': 'ship_hull_submarine_carrier',  # 潜水艦空母
            
            # 追加の一般的なタイプ
            'DDG': 'ship_hull_light',    # ミサイル駆逐艦
            'FFG': 'ship_hull_frigate',  # ミサイルフリゲート
            'CG': 'ship_hull_cruiser',   # ミサイル巡洋艦
            'CVN': 'ship_hull_carrier',  # 原子力空母
            'SSN': 'ship_hull_submarine', # 原子力潜水艦
            'SSK': 'ship_hull_submarine', # ディーゼル潜水艦
            
            # 標準HOI4タイプ（そのまま使用）
            'destroyer': 'ship_hull_light',
            'light_cruiser': 'ship_hull_cruiser',
            'heavy_cruiser': 'ship_hull_cruiser',
            'battle_cruiser': 'ship_hull_heavy',
            'battleship': 'ship_hull_heavy',
            'carrier': 'ship_hull_carrier',
            'submarine': 'ship_hull_submarine'
        }
        
        # 直接マッピングがある場合
        if hull_type in archetype_mapping:
            mapped_type = archetype_mapping[hull_type]
            self.logger.info(f"船体タイプ {hull_type} を標準アーキタイプ {mapped_type} にマッピング")
            return mapped_type
        
        # パターンマッチング（大文字小文字を無視）
        hull_upper = hull_type.upper()
        for pattern, archetype in archetype_mapping.items():
            if pattern.upper() in hull_upper:
                self.logger.info(f"船体タイプ {hull_type} をパターン {pattern} 経由で標準アーキタイプ {archetype} にマッピング")
                return archetype
        
        # デフォルトフォールバック
        self.logger.warning(f"未知の船体タイプ {hull_type} - デフォルトアーキタイプ ship_hull_cruiser を使用")
        return 'ship_hull_cruiser'
    
    def _escape_string(self, text: str) -> str:
        """文字列のエスケープ処理
        
        Args:
            text (str): エスケープ対象の文字列
            
        Returns:
            str: エスケープ済み文字列
        """
        if not isinstance(text, str):
            return str(text)
        
        # HOI4で問題になる文字をエスケープ
        text = text.replace('\\', '\\\\')  # バックスラッシュ
        text = text.replace('"', '\\"')      # ダブルクオート
        text = text.replace('\n', '\\n')     # 改行
        text = text.replace('\t', '\\t')     # タブ
        
        return text

    def _generate_reduced_equipment_id(self, original_id: str, hull_type: str) -> str:
        """軽減後装備の新しいIDを生成
        
        Args:
            original_id (str): 元の装備ID
            hull_type (str): 船体タイプ
            
        Returns:
            str: 軽減後装備ID
        """
        # 船体タイプを簡略化
        hull_type_short = {
            'destroyer': 'dd',
            'light_cruiser': 'cl', 
            'heavy_cruiser': 'ca',
            'battle_cruiser': 'bc',
            'battleship': 'bb',
            'carrier': 'cv',
            'submarine': 'ss'
        }.get(hull_type.lower(), hull_type[:2].lower())
        
        return f"{original_id}_reduced_{hull_type_short}"

    def _export_reduced_equipment(self, original_equipment: dict, hull_stats: dict, reduced_id: str) -> None:
        """軽減後装備をHoI4ファイルに書き出し
        
        Args:
            original_equipment (dict): 元の装備データ
            hull_stats (dict): 船体統計
            reduced_id (str): 軽減後装備ID
        """
        if reduced_id in self.exported_reduced_equipments:
            return  # 既に書き出し済み
        
        # 軽減係数を計算
        reduction_factor = self.stats_calculator._calculate_reduction_factor(hull_stats)
        
        # 軽減後ステータスを計算
        reduced_stats = original_equipment.get('stats', {}).copy()
        
        # build_cost_icの軽減適用
        if 'build_cost_ic' in reduced_stats:
            reduced_stats['build_cost_ic'] *= (1 - reduction_factor)
            
        # 負のnaval_speedの軽減適用（速度低下ペナルティ軽減）
        if 'naval_speed' in reduced_stats and reduced_stats['naval_speed'] < 0:
            reduced_stats['naval_speed'] *= (1 - reduction_factor)
        
        # 軽減後装備データを作成
        reduced_equipment = original_equipment.copy()
        reduced_equipment['id'] = reduced_id
        reduced_equipment['stats'] = reduced_stats
        
        # 軽減後装備ブロックを生成して書き出し
        equipment_block = self._generate_reduced_equipment_block(reduced_equipment)
        self._append_to_file(self.hulls_file, equipment_block)
        
        # 重複防止用セットに追加
        self.exported_reduced_equipments.add(reduced_id)

    def _generate_reduced_equipment_block(self, equipment_data: Dict[str, Any]) -> str:
        """軽減後装備のequipmentsブロックを生成
        
        Args:
            equipment_data (Dict[str, Any]): 軽減後装備データ
            
        Returns:
            str: 生成された装備ブロックテキスト
        """
        equipment_id = equipment_data['id']
        original_id = equipment_id.split('_reduced_')[0]
        stats = equipment_data.get('stats', {})
        
        lines = []
        lines.append(f"    {equipment_id} = {{")
        
        # 派生元（親）の装備を指定
        lines.append(f"        parent = {original_id}")
        
        # is_archetype = no を設定
        lines.append("        is_archetype = no")
        
        # 装備タイプや年度を元のデータから引き継ぐ
        if 'type' in equipment_data:
            lines.append(f"        type = {equipment_data['type']}")
        if 'year' in equipment_data:
            lines.append(f"        year = {equipment_data['year']}")
        
        # 軽減後のステータスを書き出す
        for stat_name, value in stats.items():
            if isinstance(value, float):
                lines.append(f"        {stat_name} = {value:.2f}")
            else:
                lines.append(f"        {stat_name} = {value}")
        
        lines.append("    }")
        lines.append("")  # 空行追加
        
        return "\\n".join(lines)
    
    def _append_to_file(self, file_path: str, content: str):
        """ファイルにコンテンツを追記
        
        Args:
            file_path (str): ファイルパス
            content (str): 追記するコンテンツ
        """
        try:
            with open(file_path, 'a', encoding=self.file_encoding) as f:
                f.write(content + "\n\n")
        except Exception as e:
            raise Exception(f"ファイル書き込みエラー: {e}")
    
    def initialize_files(self):
        """エクスポートファイルを初期化"""
        try:
            # 既存ファイルのバックアップ
            if os.path.exists(self.designs_file):
                self.create_backup_file(self.designs_file)
            if os.path.exists(self.hulls_file):
                self.create_backup_file(self.hulls_file)
            
            # 設計ファイルの初期化
            with open(self.designs_file, 'w', encoding=self.file_encoding) as f:
                f.write(f"# {self.country_tag} Naval Designs\n")
                f.write(f"# Generated by NavalDesignSystem\n")
                f.write(f"# Date: {self._get_timestamp()}\n\n")
                f.write(f"{self.country_tag} = {{\n")
            
            # 船体ファイルの初期化
            with open(self.hulls_file, 'w', encoding=self.file_encoding) as f:
                f.write(f"# {self.country_tag} Naval Hulls\n")
                f.write(f"# Generated by NavalDesignSystem\n")
                f.write(f"# Date: {self._get_timestamp()}\n\n")
                f.write("equipments = {\n")
            
            self._files_initialized = True
            self.logger.info(f"エクスポートファイルを初期化: {self.country_tag}")
            
        except Exception as e:
            raise Exception(f"ファイル初期化エラー: {e}")
    
    def finalize_files(self):
        """エクスポートファイルを完成"""
        try:
            # 設計ファイルの終了
            with open(self.designs_file, 'a', encoding=self.file_encoding) as f:
                f.write("}\n")
            
            # 船体ファイルの終了
            with open(self.hulls_file, 'a', encoding=self.file_encoding) as f:
                f.write("}\n")
            
            self.logger.info(f"エクスポートファイルを完成: {self.country_tag}")
            
            # 一時ファイルのクリーンアップ
            self.cleanup_temp_files()
            
        except Exception as e:
            raise Exception(f"ファイル完成エラー: {e}")
    
    def _get_timestamp(self) -> str:
        """現在のタイムスタンプを取得
        
        Returns:
            str: タイムスタンプ文字列
        """
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def export_batch_designs(self, designs_list: List[Dict[str, Any]], 
                           progress_callback=None) -> Dict[str, Any]:
        """設計データの一括エクスポート
        
        Args:
            designs_list (List[Dict[str, Any]]): 設計データのリスト
            progress_callback: 進捗コールバック関数
            
        Returns:
            Dict[str, Any]: エクスポート結果
        """
        results = {
            'total': len(designs_list),
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        self.reset_stats()
        
        for i, design_data in enumerate(designs_list):
            try:
                if self.export_design(design_data):
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    design_name = design_data.get('design_name', f'Design_{i}')
                    results['errors'].append(f"設計エクスポート失敗: {design_name}")
                
                # 進捗コールバック
                if progress_callback:
                    progress_callback(i + 1, len(designs_list))
                    
            except Exception as e:
                results['failed'] += 1
                design_name = design_data.get('design_name', f'Design_{i}')
                error_msg = f"設計エクスポートエラー: {design_name} - {str(e)}"
                results['errors'].append(error_msg)
                self.logger.error(error_msg)
        
        return results
    
    def export_batch_hulls(self, hulls_list: List[Dict[str, Any]], 
                          progress_callback=None) -> Dict[str, Any]:
        """船体データの一括エクスポート
        
        Args:
            hulls_list (List[Dict[str, Any]]): 船体データのリスト
            progress_callback: 進捗コールバック関数
            
        Returns:
            Dict[str, Any]: エクスポート結果
        """
        results = {
            'total': len(hulls_list),
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for i, hull_data in enumerate(hulls_list):
            try:
                if self.export_hull(hull_data):
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    hull_name = hull_data.get('name', f'Hull_{i}')
                    results['errors'].append(f"船体エクスポート失敗: {hull_name}")
                
                # 進捗コールバック
                if progress_callback:
                    progress_callback(i + 1, len(hulls_list))
                    
            except Exception as e:
                results['failed'] += 1
                hull_name = hull_data.get('name', f'Hull_{i}')
                error_msg = f"船体エクスポートエラー: {hull_name} - {str(e)}"
                results['errors'].append(error_msg)
                self.logger.error(error_msg)
        
        return results
    
    def get_export_summary(self) -> Dict[str, Any]:
        """エクスポート結果のサマリーを取得
        
        Returns:
            Dict[str, Any]: エクスポートサマリー
        """
        stats = self.get_stats()
        
        return {
            'country_tag': self.country_tag,
            'output_directory': self.output_dir,
            'designs_file': self.designs_file,
            'hulls_file': self.hulls_file,
            'exported_designs': stats['exported_designs'],
            'exported_hulls': stats['exported_hulls'],
            'total_errors': stats['errors'],
            'total_warnings': stats['warnings'],
            'files_exist': {
                'designs': os.path.exists(self.designs_file),
                'hulls': os.path.exists(self.hulls_file)
            }
        }