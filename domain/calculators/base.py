# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: base計算機基底クラス
"""性能計算機の基底インターフェース

全ての性能計算機が実装すべきインターフェースを定義します。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class PerformanceCalculator(ABC):
    """性能計算機の抽象基底クラス

    全ての計算機はこのインターフェースを実装する必要があります。
    これにより、計算機の交換可能性とテスタビリティが向上します。
    """

    @abstractmethod
    def calculate(self, input_data: Any) -> Dict[str, float]:
        """性能を計算

        Args:
            input_data: 計算に必要な入力データ

        Returns:
            Dict[str, float]: 計算された性能値の辞書

        Raises:
            ValueError: 入力データが不正な場合
        """
        pass

    @abstractmethod
    def validate(self, input_data: Any) -> bool:
        """入力データの妥当性を検証

        Args:
            input_data: 検証する入力データ

        Returns:
            bool: データが妥当な場合True
        """
        pass

    def get_dependencies(self) -> List[str]:
        """依存する他の計算機のリストを返す

        Returns:
            List[str]: 依存する計算機のクラス名リスト
                      （依存がない場合は空リスト）
        """
        return []

    def get_calculator_info(self) -> Dict[str, Any]:
        """計算機の情報を返す

        Returns:
            Dict[str, Any]: 計算機のメタ情報
        """
        return {
            'name': self.__class__.__name__,
            'version': '2.0',
            'dependencies': self.get_dependencies()
        }


class CompositeCalculator(PerformanceCalculator):
    """複合計算機の基底クラス

    複数の計算機を組み合わせて使用する場合の基底クラス。
    """

    def __init__(self):
        self.calculators: Dict[str, PerformanceCalculator] = {}

    def add_calculator(self, name: str, calculator: PerformanceCalculator) -> None:
        """計算機を追加

        Args:
            name: 計算機の識別名
            calculator: 追加する計算機インスタンス
        """
        self.calculators[name] = calculator

    def get_calculator(self, name: str) -> Optional[PerformanceCalculator]:
        """登録済み計算機を取得

        Args:
            name: 計算機の識別名

        Returns:
            Optional[PerformanceCalculator]: 計算機インスタンス
                                            （存在しない場合はNone）
        """
        return self.calculators.get(name)

    def get_dependencies(self) -> List[str]:
        """全ての子計算機の依存関係を集約

        Returns:
            List[str]: 依存する計算機のクラス名リスト
        """
        all_deps = []
        for calc in self.calculators.values():
            all_deps.extend(calc.get_dependencies())
        return list(set(all_deps))  # 重複を削除
