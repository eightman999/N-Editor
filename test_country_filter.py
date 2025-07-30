#!/usr/bin/env python3
"""
船体リストの国家フィルター機能のテストスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.hull_model import HullModel

def test_country_filter():
    print("=== 船体リストの国家フィルター機能テスト ===")
    
    # HullModelのインスタンス作成
    hull_model = HullModel()
    
    # 全ての国家TAGを取得
    print("\n1. 全ての国家TAG:")
    countries = hull_model.get_all_countries()
    for country in countries:
        print(f"  - {country}")
    
    # 全ての船体データを取得
    print("\n2. 全ての船体データ:")
    all_hulls = hull_model.get_all_hulls()
    for hull in all_hulls:
        print(f"  - {hull.get('name', 'N/A')} ({hull.get('country', 'N/A')})")
    
    # 国家別フィルター テスト
    for country in countries:
        print(f"\n3. {country}の船体データ:")
        filtered_hulls = hull_model.get_all_hulls(country_filter=country)
        for hull in filtered_hulls:
            print(f"  - {hull.get('name', 'N/A')} ({hull.get('country', 'N/A')})")
    
    print("\n=== テスト完了 ===")

if __name__ == "__main__":
    test_country_filter()