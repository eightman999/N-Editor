# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: hull_performance_service 船体性能サービス
"""船体性能計算サービス

船体の性能計算、装備効果計算、データ管理を提供する
アプリケーションサービスです。
"""

from typing import Dict, List, Any, Optional
import logging

from domain.services.base_service import DomainService, ValidationError, NotFoundError
from domain.entities.hull import Hull
from domain.calculators.hull_calculator import HullPerformanceCalculator
from domain.calculators.equipment_calculator import EquipmentEffectCalculator, Equipment
from domain.value_objects.efficiency_factors import EngineEfficiencyFactors
from infrastructure.repositories.hull_repository import HullRepository
from converters.csv_to_hull_converter import CSVToHullConverter

logger = logging.getLogger(__name__)


class HullPerformanceService(DomainService):
    """船体性能計算サービス

    船体データの管理と性能計算を提供します。
    リポジトリ、計算機、コンバーターを統合して、
    高レベルなユースケースを実装します。
    """

    def __init__(
        self,
        hull_repository: HullRepository,
        hull_calculator: Optional[HullPerformanceCalculator] = None,
        equipment_calculator: Optional[EquipmentEffectCalculator] = None,
        csv_converter: Optional[CSVToHullConverter] = None
    ):
        """初期化

        Args:
            hull_repository: 船体リポジトリ
            hull_calculator: 船体性能計算機（オプション）
            equipment_calculator: 装備効果計算機（オプション）
            csv_converter: CSVコンバーター（オプション）
        """
        super().__init__()

        self.repository = hull_repository

        # 計算機の初期化（デフォルト値）
        if hull_calculator is None:
            efficiency_factors = EngineEfficiencyFactors()
            hull_calculator = HullPerformanceCalculator(efficiency_factors)

        if equipment_calculator is None:
            equipment_calculator = EquipmentEffectCalculator()

        if csv_converter is None:
            csv_converter = CSVToHullConverter()

        self.hull_calculator = hull_calculator
        self.equipment_calculator = equipment_calculator
        self.csv_converter = csv_converter

    def validate_input(self, input_data: Any) -> bool:
        """入力データの検証

        Args:
            input_data: 検証するデータ（HullまたはDict）

        Returns:
            bool: 検証結果

        Raises:
            ValidationError: 検証失敗時
        """
        if isinstance(input_data, Hull):
            if not input_data.validate():
                raise ValidationError(f"Invalid hull data: {input_data.id}")
            return True

        if isinstance(input_data, dict):
            # 必須フィールドのチェック
            required_fields = ['id', 'name']
            for field in required_fields:
                if field not in input_data:
                    raise ValidationError(f"Missing required field: {field}")
            return True

        raise ValidationError(f"Unsupported input type: {type(input_data)}")

    # ========== 船体管理操作 ==========

    def save_hull(self, hull: Hull) -> bool:
        """船体を保存

        Args:
            hull: 保存する船体

        Returns:
            bool: 保存成功

        Raises:
            ValidationError: 検証失敗時
        """
        self.validate_input(hull)
        result = self.repository.save(hull)
        self._log_operation("save_hull", {"hull_id": hull.id})
        return result

    def get_hull(self, hull_id: str) -> Hull:
        """船体を取得

        Args:
            hull_id: 船体ID

        Returns:
            Hull: 船体エンティティ

        Raises:
            NotFoundError: 船体が見つからない場合
        """
        hull = self.repository.find_by_id(hull_id)
        if hull is None:
            raise NotFoundError(f"Hull not found: {hull_id}")

        self._log_operation("get_hull", {"hull_id": hull_id})
        return hull

    def get_all_hulls(self, filter_criteria: Optional[Dict[str, Any]] = None) -> List[Hull]:
        """全船体を取得（フィルタ可能）

        Args:
            filter_criteria: フィルタ条件（オプション）

        Returns:
            List[Hull]: 船体リスト
        """
        hulls = self.repository.find_all(filter_criteria)
        self._log_operation("get_all_hulls", {
            "count": len(hulls),
            "filter": filter_criteria
        })
        return hulls

    def delete_hull(self, hull_id: str) -> bool:
        """船体を削除

        Args:
            hull_id: 船体ID

        Returns:
            bool: 削除成功
        """
        result = self.repository.delete(hull_id)
        self._log_operation("delete_hull", {"hull_id": hull_id, "success": result})
        return result

    def hull_exists(self, hull_id: str) -> bool:
        """船体の存在確認

        Args:
            hull_id: 船体ID

        Returns:
            bool: 存在する場合True
        """
        return self.repository.exists(hull_id)

    # ========== 性能計算操作 ==========

    def calculate_hull_performance(
        self,
        hull_id: str,
        engine_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """船体の性能を計算

        Args:
            hull_id: 船体ID
            engine_data: 機関データ（オプション）

        Returns:
            Dict[str, float]: 計算された性能データ

        Raises:
            NotFoundError: 船体が見つからない場合
        """
        hull = self.get_hull(hull_id)
        performance = self.hull_calculator.calculate(hull, engine_data)

        self._log_operation("calculate_hull_performance", {
            "hull_id": hull_id,
            "has_engine": engine_data is not None
        })

        return performance

    def calculate_equipment_effect(
        self,
        hull_id: str,
        equipment_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """装備効果を計算

        Args:
            hull_id: 船体ID
            equipment_list: 装備リスト（辞書形式）
                各装備は {'id': str, 'name': str, 'weight': float, ...} の形式

        Returns:
            Dict[str, Any]: 装備効果を含む性能データ

        Raises:
            NotFoundError: 船体が見つからない場合
        """
        hull = self.get_hull(hull_id)

        # 辞書形式の装備リストをEquipmentオブジェクトに変換
        equipments = []
        for eq_dict in equipment_list:
            equipment = Equipment(
                id=eq_dict.get('id', ''),
                name=eq_dict.get('name', eq_dict.get('type', '')),
                weight=eq_dict.get('weight', 0.0)
            )
            equipments.append(equipment)

        # 装備計算機で計算
        result = self.equipment_calculator.calculate(hull, equipments)

        self._log_operation("calculate_equipment_effect", {
            "hull_id": hull_id,
            "equipment_count": len(equipment_list)
        })

        return result

    def calculate_complete_performance(
        self,
        hull_id: str,
        engine_data: Optional[Dict[str, Any]] = None,
        equipment_list: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """完全な性能計算（船体性能 + 装備効果）

        Args:
            hull_id: 船体ID
            engine_data: 機関データ（オプション）
            equipment_list: 装備リスト（オプション）

        Returns:
            Dict[str, Any]: 完全な性能データ

        Raises:
            NotFoundError: 船体が見つからない場合
        """
        # 船体基本性能の計算
        hull_performance = self.calculate_hull_performance(hull_id, engine_data)

        # 装備効果の計算
        if equipment_list:
            equipment_effect = self.calculate_equipment_effect(hull_id, equipment_list)
            # 装備効果を統合
            hull_performance.update({
                'equipment_effect': equipment_effect,
                'final_speed': equipment_effect.get('new_speed', hull_performance['max_speed'])
            })

        self._log_operation("calculate_complete_performance", {
            "hull_id": hull_id,
            "has_engine": engine_data is not None,
            "has_equipment": equipment_list is not None
        })

        return hull_performance

    # ========== CSV操作 ==========

    def import_from_csv(self, csv_file_path: str, encoding: str = 'utf-8') -> int:
        """CSVファイルから船体をインポート

        Args:
            csv_file_path: CSVファイルパス
            encoding: ファイルエンコーディング

        Returns:
            int: インポートされた船体数
        """
        hulls = self.csv_converter.convert_csv_file(csv_file_path, encoding)

        # 全船体を保存
        saved_count = 0
        for hull in hulls:
            try:
                if self.save_hull(hull):
                    saved_count += 1
            except Exception as e:
                self.logger.warning(f"Failed to save hull {hull.id}: {e}")

        self._log_operation("import_from_csv", {
            "file": csv_file_path,
            "total": len(hulls),
            "saved": saved_count
        })

        return saved_count

    def export_to_csv(
        self,
        csv_file_path: str,
        filter_criteria: Optional[Dict[str, Any]] = None,
        encoding: str = 'utf-8'
    ) -> int:
        """船体をCSVファイルにエクスポート

        Args:
            csv_file_path: 出力CSVファイルパス
            filter_criteria: フィルタ条件（オプション）
            encoding: ファイルエンコーディング

        Returns:
            int: エクスポートされた船体数
        """
        hulls = self.get_all_hulls(filter_criteria)

        self.csv_converter.export_to_csv(hulls, csv_file_path, encoding)

        self._log_operation("export_to_csv", {
            "file": csv_file_path,
            "count": len(hulls),
            "filter": filter_criteria
        })

        return len(hulls)

    # ========== バッチ操作 ==========

    def batch_calculate_performance(
        self,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, float]]:
        """複数船体の性能を一括計算

        Args:
            filter_criteria: フィルタ条件（オプション）

        Returns:
            Dict[str, Dict[str, float]]: 船体ID → 性能データのマッピング
        """
        hulls = self.get_all_hulls(filter_criteria)

        results = {}
        for hull in hulls:
            try:
                performance = self.hull_calculator.calculate(hull)
                results[hull.id] = performance
            except Exception as e:
                self.logger.warning(f"Failed to calculate performance for {hull.id}: {e}")

        self._log_operation("batch_calculate_performance", {
            "total": len(hulls),
            "calculated": len(results)
        })

        return results

    def get_statistics(self, filter_criteria: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """船体統計情報を取得

        Args:
            filter_criteria: フィルタ条件（オプション）

        Returns:
            Dict[str, Any]: 統計情報
        """
        hulls = self.get_all_hulls(filter_criteria)

        if not hulls:
            return {
                'count': 0,
                'avg_weight': 0.0,
                'avg_speed': 0.0,
                'avg_range': 0.0
            }

        total_weight = sum(h.weight for h in hulls)
        total_speed = sum(h.max_speed for h in hulls)
        total_range = sum(h.naval_range for h in hulls)

        count = len(hulls)

        stats = {
            'count': count,
            'avg_weight': total_weight / count if count > 0 else 0.0,
            'avg_speed': total_speed / count if count > 0 else 0.0,
            'avg_range': total_range / count if count > 0 else 0.0,
            'max_weight': max(h.weight for h in hulls),
            'min_weight': min(h.weight for h in hulls),
            'max_speed': max(h.max_speed for h in hulls),
            'min_speed': min(h.max_speed for h in hulls),
        }

        self._log_operation("get_statistics", {"filter": filter_criteria, "count": count})

        return stats

    # ========== キャッシュ管理 ==========

    def clear_cache(self):
        """キャッシュをクリア"""
        self.repository.clear_cache()
        self._log_operation("clear_cache")

    def get_cache_info(self) -> Dict[str, Any]:
        """キャッシュ情報を取得

        Returns:
            Dict[str, Any]: キャッシュ情報
        """
        return self.repository.get_cache_info()
