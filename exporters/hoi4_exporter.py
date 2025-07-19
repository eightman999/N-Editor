# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: hoi4_exporter形式のエクスポート機能
"""HOI4形式エクスポーター

このモジュールは、Naval Design Systemの設計データを
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
        """create_equipment_variantブロックを生成
        
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
        lines.append("    create_equipment_variant = {")
        lines.append(f'        name = "{self._escape_string(design_name)}"')
        lines.append(f"        type = {hull_id}")
        
        # name_group があれば追加
        if 'name_group' in design_data and design_data['name_group']:
            lines.append(f"        name_group = {design_data['name_group']}")
        
        # upgrades セクション
        if self.include_upgrades and upgrades:
            lines.append("        upgrades = {")
            for upgrade_type, level in upgrades.items():
                lines.append(f"            {upgrade_type} = {level}")
            lines.append("        }")
        
        # modules セクション
        if modules:
            lines.append("        modules = {")
            for slot_id, module_id in modules.items():
                if module_id and module_id != 'empty':
                    lines.append(f"            {slot_id} = {module_id}")
            lines.append("        }")
        
        lines.append("    }")

        return "\\n".join(lines)
    
    def _generate_equipment_block(self, hull_data: Dict[str, Any]) -> str:
        """equipmentsブロックを生成
        
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
        
        lines = []
        lines.append(f"    {hull_id} = {{")
        lines.append(f"        year = {year}")
        lines.append("        is_archetype = yes")
        lines.append("        is_buildable = no")
        lines.append(f"        type = {hull_type}")
        lines.append(f"        sprite = {hull_type}")
        lines.append("        group_by = archetype")
        lines.append("        priority = 1000")
        
        # interface_categoryの設定
        interface_category = self._get_interface_category(hull_type)
        lines.append(f"        interface_category = {interface_category}")
        
        # module_slots セクション
        if slots:
            lines.append("        module_slots = {")
            for slot_id, slot_config in slots.items():
                lines.append(f"            {slot_id} = {{")
                lines.append(f"                required = {str(slot_config.get('required', False)).lower()}")
                
                categories = slot_config.get('categories', [])
                if categories:
                    lines.append("                allowed_module_categories = {")
                    for category in categories:
                        lines.append(f"                    {category}")
                    lines.append("                }")
                
                if 'gfx' in slot_config:
                    lines.append(f"                gfx = {slot_config['gfx']}")
                    
                lines.append("            }")
            lines.append("        }")
        
        # default_modules セクション
        if slots:
            lines.append("        default_modules = {")
            for slot_id, slot_config in slots.items():
                default_module = slot_config.get('default_module', 'empty')
                lines.append(f"            {slot_id} = {default_module}")
            lines.append("        }")
        
        # 基本性能
        if base_stats:
            lines.append("")  # 空行を追加
            lines.append("        # 基本性能")
            for stat_name, value in base_stats.items():
                lines.append(f"        {stat_name} = {value}")
        
        lines.append("    }")
        
        return "\\n".join(lines)
    
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
        
        return category_mapping.get(hull_type, 'interface_category_capital_ships')
    
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
        text = text.replace('\\\\', '\\\\\\\\')  # バックスラッシュ
        text = text.replace('"', '\\\\"')      # ダブルクオート
        text = text.replace('\\n', '\\\\n')     # 改行
        text = text.replace('\\t', '\\\\t')     # タブ
        
        return text
    
    def _append_to_file(self, file_path: str, content: str):
        """ファイルにコンテンツを追記
        
        Args:
            file_path (str): ファイルパス
            content (str): 追記するコンテンツ
        """
        try:
            with open(file_path, 'a', encoding=self.file_encoding) as f:
                f.write(content + "\\n\\n")
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
                f.write(f"# {self.country_tag} Naval Designs\\n")
                f.write(f"# Generated by Naval Design System\\n")
                f.write(f"# Date: {self._get_timestamp()}\\n\\n")
                f.write(f"{self.country_tag} = {{\\n")
            
            # 船体ファイルの初期化
            with open(self.hulls_file, 'w', encoding=self.file_encoding) as f:
                f.write(f"# {self.country_tag} Naval Hulls\\n")
                f.write(f"# Generated by Naval Design System\\n")
                f.write(f"# Date: {self._get_timestamp()}\\n\\n")
                f.write("equipments = {\\n")
            
            self._files_initialized = True
            self.logger.info(f"エクスポートファイルを初期化: {self.country_tag}")
            
        except Exception as e:
            raise Exception(f"ファイル初期化エラー: {e}")
    
    def finalize_files(self):
        """エクスポートファイルを完成"""
        try:
            # 設計ファイルの終了
            with open(self.designs_file, 'a', encoding=self.file_encoding) as f:
                f.write("}\\n")
            
            # 船体ファイルの終了
            with open(self.hulls_file, 'a', encoding=self.file_encoding) as f:
                f.write("}\\n")
            
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