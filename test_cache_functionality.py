#!/usr/bin/env python3
"""
キャッシュ機能とスプライトシート機能の基本動作確認テスト
"""

import os
import sys
import tempfile
import shutil
from PIL import Image

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.cache_manager import CacheManager
from utils.flag_sprite_manager import FlagSpriteManager

def test_cache_manager():
    """CacheManagerの基本機能テスト"""
    print("CacheManager テスト開始...")
    
    # 一時ディレクトリでテスト
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_manager = CacheManager("test_mod")
        cache_manager.base_cache_dir = temp_dir
        
        # テストデータ
        test_data = [{"tag": "USA", "name": "United States"}, {"tag": "GER", "name": "Germany"}]
        test_file_path = os.path.join(temp_dir, "test_file.txt")
        
        # ダミーファイルを作成
        with open(test_file_path, 'w') as f:
            f.write("test content")
        
        # データを保存
        cache_manager.save("nations_cache", test_file_path, test_data)
        print("✓ データ保存成功")
        
        # データを読み込み
        loaded_data = cache_manager.load("nations_cache", test_file_path)
        assert loaded_data == test_data, "読み込みデータが一致しません"
        print("✓ データ読み込み成功")
        
        # キャッシュ情報を取得
        cache_info = cache_manager.get_cache_info()
        print(f"✓ キャッシュ情報取得成功: {cache_info['metadata_entries']}個のエントリ")
        
        print("CacheManager テスト完了✓\n")

def test_flag_sprite_manager():
    """FlagSpriteManagerの基本機能テスト"""
    print("FlagSpriteManager テスト開始...")
    
    # 一時ディレクトリでテスト
    with tempfile.TemporaryDirectory() as temp_dir:
        sprite_manager = FlagSpriteManager(temp_dir)
        
        # テスト用の国旗画像を作成
        flags_dir = os.path.join(temp_dir, "flags")
        os.makedirs(flags_dir, exist_ok=True)
        
        test_nations = []
        flag_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]  # 赤、緑、青
        
        for i, (tag, color) in enumerate(zip(["USA", "GER", "FRA"], flag_colors)):
            # テスト用国旗画像を作成
            flag_path = os.path.join(flags_dir, f"{tag}.tga")
            flag_img = Image.new('RGB', (64, 40), color)
            flag_img.save(flag_path, 'TGA')
            
            test_nations.append({
                "tag": tag,
                "name": f"Country {tag}",
                "flag_path": flag_path
            })
        
        # スプライトシートを生成
        success = sprite_manager.generate_sprite_sheet(test_nations)
        assert success, "スプライトシート生成に失敗"
        print("✓ スプライトシート生成成功")
        
        # キャッシュの有効性をチェック
        is_valid = sprite_manager.is_cache_valid(test_nations)
        assert is_valid, "キャッシュが無効です"
        print("✓ キャッシュ有効性チェック成功")
        
        # 個別国旗の切り出し
        for nation in test_nations:
            flag_img = sprite_manager.extract_flag(nation["tag"])
            assert flag_img is not None, f"{nation['tag']}の国旗切り出しに失敗"
            assert flag_img.size == (32, 20), f"国旗サイズが正しくありません: {flag_img.size}"
        print("✓ 国旗切り出し成功")
        
        # スプライトシート情報を取得
        sprite_info = sprite_manager.get_cache_info()
        print(f"✓ スプライトシート情報取得成功: {sprite_info['flag_count']}個の国旗")
        
        print("FlagSpriteManager テスト完了✓\n")

def test_integration():
    """統合テスト（実際の使用パターン）"""
    print("統合テスト開始...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # CacheManagerとFlagSpriteManagerを連携
        cache_manager = CacheManager("integration_test")
        cache_manager.base_cache_dir = temp_dir
        
        sprite_cache_dir = os.path.join(temp_dir, "flags")
        sprite_manager = FlagSpriteManager(sprite_cache_dir)
        
        # サンプル国家データ
        sample_nations = [
            {"tag": "USA", "name": "United States", "flag_path": None},
            {"tag": "GER", "name": "Germany", "flag_path": None},
            {"tag": "FRA", "name": "France", "flag_path": None},
        ]
        
        # 国家データをキャッシュに保存
        dummy_file = os.path.join(temp_dir, "countries.txt")
        with open(dummy_file, 'w') as f:
            f.write("dummy content")
        
        cache_manager.save("nations_cache", dummy_file, sample_nations)
        print("✓ 国家データキャッシュ保存成功")
        
        # スプライトシートを生成（国旗画像なしでもデフォルト画像が生成される）
        success = sprite_manager.generate_sprite_sheet(sample_nations)
        assert success, "スプライトシート生成に失敗"
        print("✓ デフォルト国旗でスプライトシート生成成功")
        
        # キャッシュからデータを復元
        loaded_nations = cache_manager.load("nations_cache", dummy_file)
        assert loaded_nations == sample_nations, "国家データの復元に失敗"
        print("✓ 国家データ復元成功")
        
        # 統合キャッシュ情報
        cache_info = cache_manager.get_cache_info()
        sprite_info = sprite_manager.get_cache_info()
        
        print(f"✓ 統合テスト完了")
        print(f"  - 国家キャッシュエントリ: {cache_info['metadata_entries']}")
        print(f"  - スプライトシート国旗数: {sprite_info['flag_count']}")
        print(f"  - スプライトシートサイズ: {sprite_info['sprite_sheet_size']} bytes")
        
        print("統合テスト完了✓\n")

def main():
    """メイン関数"""
    print("国家リスト・国旗キャッシュシステム 動作確認テスト")
    print("=" * 60)
    
    try:
        # 個別機能テスト
        test_cache_manager()
        test_flag_sprite_manager()
        test_integration()
        
        print("全テスト成功! 🎉")
        print("実装されたキャッシュシステムは正常に動作しています。")
        
    except Exception as e:
        print(f"テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())