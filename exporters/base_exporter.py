# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: base_exporter形式のエクスポート機能
"""エクスポーター基底クラス

このモジュールは、全てのエクスポーターが継承する基底クラスを提供します。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import os
import json
import logging


class BaseExporter(ABC):
    """エクスポーターの基底クラス
    
    全てのエクスポーター実装が継承すべき基底クラスです。
    共通的な機能とインターフェースを定義します。
    """
    
    def __init__(self, output_dir: str):
        """エクスポーターを初期化
        
        Args:
            output_dir (str): 出力ディレクトリパス
        """
        self.output_dir = output_dir
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 出力ディレクトリを作成
        os.makedirs(output_dir, exist_ok=True)
        
        # エクスポート統計
        self.stats = {
            'exported_designs': 0,
            'exported_hulls': 0,
            'errors': 0,
            'warnings': 0
        }
    
    @abstractmethod
    def export_design(self, design_data: Dict[str, Any]) -> bool:
        """設計データをエクスポート
        
        Args:
            design_data (Dict[str, Any]): 設計データ
            
        Returns:
            bool: エクスポート成功時True、失敗時False
        """
        pass
    
    @abstractmethod
    def export_hull(self, hull_data: Dict[str, Any]) -> bool:
        """船体データをエクスポート
        
        Args:
            hull_data (Dict[str, Any]): 船体データ
            
        Returns:
            bool: エクスポート成功時True、失敗時False
        """
        pass
    
    def validate_data(self, data: Dict[str, Any], required_fields: List[str]) -> bool:
        """データ検証
        
        Args:
            data (Dict[str, Any]): 検証対象のデータ
            required_fields (List[str]): 必須フィールドのリスト
            
        Returns:
            bool: 検証成功時True、失敗時False
        """
        for field in required_fields:
            if field not in data:
                self.logger.error(f"必須フィールドが不足: {field}")
                return False
            
            # 空文字列や空値もチェック
            value = data[field]
            if value is None or (isinstance(value, str) and not value.strip()):
                self.logger.error(f"必須フィールドが空: {field}")
                return False
        
        return True
    
    def validate_design_data(self, design_data: Dict[str, Any]) -> bool:
        """設計データの詳細検証
        
        Args:
            design_data (Dict[str, Any]): 設計データ
            
        Returns:
            bool: 検証成功時True、失敗時False
        """
        required_fields = ['design_name', 'hull_id']
        
        if not self.validate_data(design_data, required_fields):
            return False
        
        # 設計名の検証
        design_name = design_data['design_name']
        if len(design_name) > 100:  # 長すぎる名前をチェック
            self.logger.warning(f"設計名が長すぎます (100文字制限): {design_name}")
        
        # モジュールデータの検証
        modules = design_data.get('modules', {})
        if not isinstance(modules, dict):
            self.logger.error("modulesが辞書形式ではありません")
            return False
        
        return True
    
    def validate_hull_data(self, hull_data: Dict[str, Any]) -> bool:
        """船体データの詳細検証
        
        Args:
            hull_data (Dict[str, Any]): 船体データ
            
        Returns:
            bool: 検証成功時True、失敗時False
        """
        required_fields = ['hull_id', 'name', 'type']
        
        if not self.validate_data(hull_data, required_fields):
            return False
        
        # 船体タイプの検証
        hull_type = hull_data['type']
        valid_types = ['destroyer', 'light_cruiser', 'heavy_cruiser', 'battle_cruiser', 
                      'battleship', 'carrier', 'submarine']
        
        if hull_type not in valid_types:
            self.logger.warning(f"未知の船体タイプ: {hull_type}")
        
        # スロットデータの検証
        slots = hull_data.get('slots', {})
        if not isinstance(slots, dict):
            self.logger.error("slotsが辞書形式ではありません")
            return False
        
        return True
    
    def get_stats(self) -> Dict[str, int]:
        """エクスポート統計を取得
        
        Returns:
            Dict[str, int]: エクスポート統計情報
        """
        return self.stats.copy()
    
    def reset_stats(self):
        """エクスポート統計をリセット"""
        for key in self.stats:
            self.stats[key] = 0
    
    def log_export_start(self, target_type: str, target_name: str):
        """エクスポート開始ログ
        
        Args:
            target_type (str): エクスポート対象タイプ（'design' or 'hull'）
            target_name (str): エクスポート対象名
        """
        self.logger.info(f"{target_type}エクスポート開始: {target_name}")
    
    def log_export_success(self, target_type: str, target_name: str):
        """エクスポート成功ログ
        
        Args:
            target_type (str): エクスポート対象タイプ（'design' or 'hull'）
            target_name (str): エクスポート対象名
        """
        self.logger.info(f"{target_type}エクスポート成功: {target_name}")
        
        # 統計を更新
        if target_type == 'design':
            self.stats['exported_designs'] += 1
        elif target_type == 'hull':
            self.stats['exported_hulls'] += 1
    
    def log_export_error(self, target_type: str, target_name: str, error: str):
        """エクスポートエラーログ
        
        Args:
            target_type (str): エクスポート対象タイプ（'design' or 'hull'）
            target_name (str): エクスポート対象名
            error (str): エラーメッセージ
        """
        self.logger.error(f"{target_type}エクスポートエラー: {target_name} - {error}")
        self.stats['errors'] += 1
    
    def log_export_warning(self, target_type: str, target_name: str, warning: str):
        """エクスポート警告ログ
        
        Args:
            target_type (str): エクスポート対象タイプ（'design' or 'hull'）
            target_name (str): エクスポート対象名
            warning (str): 警告メッセージ
        """
        self.logger.warning(f"{target_type}エクスポート警告: {target_name} - {warning}")
        self.stats['warnings'] += 1
    
    def create_backup_file(self, file_path: str) -> Optional[str]:
        """既存ファイルのバックアップを作成
        
        Args:
            file_path (str): バックアップ対象ファイルパス
            
        Returns:
            Optional[str]: バックアップファイルパス（失敗時はNone）
        """
        if not os.path.exists(file_path):
            return None
        
        try:
            import shutil
            from datetime import datetime
            
            # バックアップファイル名を生成
            base_name = os.path.basename(file_path)
            dir_name = os.path.dirname(file_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{base_name}.backup_{timestamp}"
            backup_path = os.path.join(dir_name, backup_name)
            
            # ファイルをコピー
            shutil.copy2(file_path, backup_path)
            self.logger.info(f"バックアップファイルを作成: {backup_path}")
            
            return backup_path
            
        except Exception as e:
            self.logger.error(f"バックアップ作成エラー: {e}")
            return None
    
    def ensure_file_encoding(self, file_path: str, encoding: str = 'utf-8') -> bool:
        """ファイルのエンコーディングを確認・修正
        
        Args:
            file_path (str): ファイルパス
            encoding (str): 目標エンコーディング
            
        Returns:
            bool: 成功時True、失敗時False
        """
        try:
            # ファイルが存在しない場合はTrue（新規作成時）
            if not os.path.exists(file_path):
                return True
            
            # ファイルを読み込んでエンコーディングをチェック
            with open(file_path, 'r', encoding=encoding) as f:
                f.read()
            
            return True
            
        except UnicodeDecodeError:
            self.logger.warning(f"ファイルエンコーディングが{encoding}ではありません: {file_path}")
            return False
        except Exception as e:
            self.logger.error(f"ファイルエンコーディングチェックエラー: {e}")
            return False
    
    def cleanup_temp_files(self):
        """一時ファイルをクリーンアップ"""
        try:
            temp_pattern = os.path.join(self.output_dir, "*.tmp")
            import glob
            
            temp_files = glob.glob(temp_pattern)
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                    self.logger.debug(f"一時ファイルを削除: {temp_file}")
                except Exception as e:
                    self.logger.warning(f"一時ファイル削除エラー: {temp_file} - {e}")
                    
        except Exception as e:
            self.logger.error(f"一時ファイルクリーンアップエラー: {e}")