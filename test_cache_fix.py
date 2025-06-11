#!/usr/bin/env python3
"""
キャッシュマネージャーの修正をテストするスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QWidget
from controllers.app_controller import AppController
from models.app_settings import AppSettings
from utils.maptest2 import MapViewer

def test_cache_manager_fix():
    """キャッシュマネージャーの修正をテスト"""
    app = QApplication([])
    
    # AppSettingsとAppControllerを初期化
    app_settings = AppSettings()
    app_controller = AppController(app_settings)
    
    # テスト用の親ウィジェット
    class TestParent(QWidget):
        def __init__(self):
            super().__init__()
            self.app_controller = app_controller
    
    parent = TestParent()
    
    # MapViewerを初期化
    map_viewer = MapViewer(parent)
    
    # 結果を確認
    print("=== キャッシュマネージャー修正テスト ===")
    print(f"app_controller存在: {map_viewer.app_controller is not None}")
    
    if map_viewer.app_controller:
        print(f"cache_manager存在: {map_viewer.app_controller.cache_manager is not None}")
        if map_viewer.app_controller.cache_manager:
            cache_info = map_viewer.app_controller.get_cache_info()
            print(f"キャッシュ情報: {cache_info}")
    
    # MODを設定してテスト
    # 注意: 実際のMODパスを設定してください
    # app_controller.open_mod("/path/to/mod", "TestMod")
    
    print("テスト完了")
    
    app.quit()

if __name__ == "__main__":
    test_cache_manager_fix()