# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: migration_helper マイグレーションヘルパー
"""レガシーシステムから新システムへのマイグレーションヘルパー

旧HullModelのデータを新システムに移行するための
ユーティリティを提供します。
"""

from typing import Dict, List, Any, Optional, Tuple
import os
import json
import logging
from datetime import datetime

from domain.services.hull_performance_service import HullPerformanceService
from infrastructure.repositories.hull_repository import HullRepository
from infrastructure.adapters.legacy_hull_adapter import LegacyHullAdapter
from converters.csv_to_hull_converter import CSVToHullConverter

logger = logging.getLogger(__name__)


class MigrationReport:
    """マイグレーション結果レポート"""

    def __init__(self):
        self.total_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.errors = []
        self.warnings = []
        self.start_time = None
        self.end_time = None

    def add_success(self, hull_id: str):
        """成功を記録"""
        self.success_count += 1

    def add_failure(self, hull_id: str, error: str):
        """失敗を記録"""
        self.failed_count += 1
        self.errors.append(f"{hull_id}: {error}")

    def add_skip(self, hull_id: str, reason: str):
        """スキップを記録"""
        self.skipped_count += 1
        self.warnings.append(f"{hull_id}: {reason}")

    def add_warning(self, message: str):
        """警告を追加"""
        self.warnings.append(message)

    def start(self):
        """マイグレーション開始"""
        self.start_time = datetime.now()

    def finish(self):
        """マイグレーション終了"""
        self.end_time = datetime.now()

    def get_duration(self) -> float:
        """処理時間を取得（秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'total_count': self.total_count,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'skipped_count': self.skipped_count,
            'success_rate': (
                (self.success_count / self.total_count * 100)
                if self.total_count > 0 else 0.0
            ),
            'duration_seconds': self.get_duration(),
            'errors': self.errors,
            'warnings': self.warnings,
            'timestamp': self.end_time.isoformat() if self.end_time else None
        }

    def __str__(self) -> str:
        """文字列表現"""
        lines = [
            "=== Migration Report ===",
            f"Total: {self.total_count}",
            f"Success: {self.success_count}",
            f"Failed: {self.failed_count}",
            f"Skipped: {self.skipped_count}",
            f"Success Rate: {self.success_count / self.total_count * 100:.1f}%" if self.total_count > 0 else "Success Rate: 0%",
            f"Duration: {self.get_duration():.2f}s",
        ]

        if self.errors:
            lines.append(f"\nErrors ({len(self.errors)}):")
            for error in self.errors[:10]:  # 最初の10件のみ表示
                lines.append(f"  - {error}")
            if len(self.errors) > 10:
                lines.append(f"  ... and {len(self.errors) - 10} more")

        if self.warnings:
            lines.append(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings[:10]:
                lines.append(f"  - {warning}")
            if len(self.warnings) > 10:
                lines.append(f"  ... and {len(self.warnings) - 10} more")

        return "\n".join(lines)


class MigrationHelper:
    """レガシーから新システムへのマイグレーションヘルパー"""

    def __init__(
        self,
        new_data_dir: str,
        cache_manager=None
    ):
        """初期化

        Args:
            new_data_dir: 新システムのデータディレクトリ
            cache_manager: キャッシュマネージャー
        """
        self.new_data_dir = new_data_dir
        self.cache_manager = cache_manager

        # 新システムの初期化
        self.repository = HullRepository(new_data_dir, cache_manager)
        self.service = HullPerformanceService(self.repository)
        self.csv_converter = CSVToHullConverter()

        logger.info(f"MigrationHelper initialized: {new_data_dir}")

    def migrate_from_legacy_dict(
        self,
        legacy_data_list: List[Dict[str, Any]],
        overwrite: bool = False
    ) -> MigrationReport:
        """レガシー辞書形式からマイグレーション

        Args:
            legacy_data_list: レガシー形式のデータリスト
            overwrite: 既存データを上書きするか

        Returns:
            MigrationReport: マイグレーションレポート
        """
        report = MigrationReport()
        report.total_count = len(legacy_data_list)
        report.start()

        for legacy_data in legacy_data_list:
            hull_id = legacy_data.get('id', 'UNKNOWN')

            try:
                # 既存確認
                if not overwrite and self.service.hull_exists(hull_id):
                    report.add_skip(hull_id, "Already exists")
                    continue

                # 変換
                hull = LegacyHullAdapter.from_legacy(legacy_data)

                # 保存
                if self.service.save_hull(hull):
                    report.add_success(hull_id)
                else:
                    report.add_failure(hull_id, "Save failed")

            except Exception as e:
                report.add_failure(hull_id, str(e))

        report.finish()
        logger.info(f"Migration completed: {report.success_count}/{report.total_count}")

        return report

    def migrate_from_csv(
        self,
        csv_file_path: str,
        encoding: str = 'utf-8',
        overwrite: bool = False
    ) -> MigrationReport:
        """CSVファイルからマイグレーション

        Args:
            csv_file_path: CSVファイルパス
            encoding: エンコーディング
            overwrite: 既存データを上書きするか

        Returns:
            MigrationReport: マイグレーションレポート
        """
        report = MigrationReport()
        report.start()

        try:
            # CSVから読み込み
            hulls = self.csv_converter.convert_csv_file(csv_file_path, encoding)
            report.total_count = len(hulls)

            for hull in hulls:
                try:
                    # 既存確認
                    if not overwrite and self.service.hull_exists(hull.id):
                        report.add_skip(hull.id, "Already exists")
                        continue

                    # 保存
                    if self.service.save_hull(hull):
                        report.add_success(hull.id)
                    else:
                        report.add_failure(hull.id, "Save failed")

                except Exception as e:
                    report.add_failure(hull.id, str(e))

        except Exception as e:
            report.add_failure("CSV", f"Failed to read CSV: {e}")

        report.finish()
        logger.info(f"CSV migration completed: {report.success_count}/{report.total_count}")

        return report

    def verify_migration(
        self,
        legacy_data_list: List[Dict[str, Any]]
    ) -> Tuple[int, List[str]]:
        """マイグレーション結果の検証

        Args:
            legacy_data_list: 元のレガシーデータリスト

        Returns:
            Tuple[int, List[str]]: (一致数, 不一致IDリスト)
        """
        match_count = 0
        mismatch_ids = []

        for legacy_data in legacy_data_list:
            hull_id = legacy_data.get('id', 'UNKNOWN')

            try:
                # 新システムからデータを取得
                hull = self.service.get_hull(hull_id)

                # レガシー形式に変換
                converted_data = LegacyHullAdapter.to_legacy(hull)

                # 主要フィールドを比較
                key_fields = ['id', 'name', 'weight', 'speed', 'country']
                is_match = True

                for field in key_fields:
                    if field in legacy_data and field in converted_data:
                        # 数値フィールドは近似比較
                        if isinstance(legacy_data[field], (int, float)):
                            if abs(float(legacy_data[field]) - float(converted_data[field])) > 0.01:
                                is_match = False
                                break
                        else:
                            if legacy_data[field] != converted_data[field]:
                                is_match = False
                                break

                if is_match:
                    match_count += 1
                else:
                    mismatch_ids.append(hull_id)

            except Exception as e:
                logger.warning(f"Verification failed for {hull_id}: {e}")
                mismatch_ids.append(hull_id)

        logger.info(f"Verification: {match_count}/{len(legacy_data_list)} match")
        return match_count, mismatch_ids

    def generate_migration_plan(
        self,
        legacy_data_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """マイグレーション計画を生成

        Args:
            legacy_data_list: レガシーデータリスト

        Returns:
            Dict[str, Any]: マイグレーション計画
        """
        plan = {
            'total_count': len(legacy_data_list),
            'new_count': 0,
            'update_count': 0,
            'by_country': {},
            'by_archetype': {},
            'by_year': {},
            'potential_issues': []
        }

        for legacy_data in legacy_data_list:
            hull_id = legacy_data.get('id', 'UNKNOWN')

            # 新規 or 更新
            if self.service.hull_exists(hull_id):
                plan['update_count'] += 1
            else:
                plan['new_count'] += 1

            # 国別集計
            country = legacy_data.get('country', 'UNKNOWN')
            plan['by_country'][country] = plan['by_country'].get(country, 0) + 1

            # 艦種別集計
            archetype = legacy_data.get('archetype', 'UNKNOWN')
            plan['by_archetype'][archetype] = plan['by_archetype'].get(archetype, 0) + 1

            # 年代別集計
            year = legacy_data.get('year', 0)
            year_range = f"{(year // 10) * 10}s" if year > 0 else 'UNKNOWN'
            plan['by_year'][year_range] = plan['by_year'].get(year_range, 0) + 1

            # 潜在的な問題の検出
            try:
                LegacyHullAdapter.from_legacy(legacy_data)
            except Exception as e:
                plan['potential_issues'].append(f"{hull_id}: {str(e)}")

        return plan

    def export_migration_report(
        self,
        report: MigrationReport,
        output_path: str
    ):
        """マイグレーションレポートをJSON出力

        Args:
            report: マイグレーションレポート
            output_path: 出力パス
        """
        report_dict = report.to_dict()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)

        logger.info(f"Migration report exported to: {output_path}")
