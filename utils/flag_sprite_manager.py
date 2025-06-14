import os
import json
import logging
from typing import List, Dict, Tuple, Optional
from PIL import Image, ImageDraw
import hashlib
import time

logger = logging.getLogger(__name__)

class FlagSpriteManager:
    """
    国旗画像を統合スプライトシート形式で管理するクラス
    複数の小さな国旗画像を1枚の大きな画像に統合し、メモリ使用量と読み込み時間を削減
    """

    def __init__(self, cache_dir: str, mod_name: str = "vanilla"):
        """
        FlagSpriteManagerを初期化

        Args:
            cache_dir: キャッシュディレクトリのパス
            mod_name: MOD名（ファイル名の接頭辞として使用）
        """
        self.cache_dir = cache_dir
        self.mod_name = mod_name
        self.sprite_sheet_path = os.path.join(cache_dir, f"{mod_name}_flags_sprite.png")
        self.coords_file_path = os.path.join(cache_dir, f"{mod_name}_flags_coords.json")
        self.flag_size = (32, 20)  # 国旗サイズを32x20に統一
        
        # スプライトシートとメタデータのキャッシュ
        self._sprite_sheet = None
        self._coords_cache = None
        
        logger.info(f"FlagSpriteManager初期化: キャッシュディレクトリ={cache_dir}, MOD名={mod_name}")

    def _calculate_sprite_dimensions(self, flag_count: int) -> Tuple[int, int, int, int]:
        """
        国旗数に基づいてスプライトシートの最適な寸法を計算

        Args:
            flag_count: 国旗の総数

        Returns:
            (cols, rows, sheet_width, sheet_height): 列数、行数、シート幅、シート高さ
        """
        if flag_count == 0:
            return 1, 1, self.flag_size[0], self.flag_size[1]
        
        # 正方形に近い形状を目指す
        cols = int(flag_count ** 0.5) + 1
        rows = (flag_count + cols - 1) // cols  # 切り上げ除算
        
        sheet_width = cols * self.flag_size[0]
        sheet_height = rows * self.flag_size[1]
        
        logger.debug(f"スプライトシート寸法計算: 国旗数={flag_count}, 列={cols}, 行={rows}, サイズ={sheet_width}x{sheet_height}")
        return cols, rows, sheet_width, sheet_height

    def _generate_flags_hash(self, nations: List[Dict]) -> str:
        """
        国家リストから国旗データのハッシュを生成（キャッシュ有効性判定用）

        Args:
            nations: 国家情報のリスト

        Returns:
            ハッシュ文字列
        """
        hash_data = []
        for nation in nations:
            flag_path = nation.get('flag_path')
            if flag_path and os.path.exists(flag_path):
                # ファイルパス + 更新時刻でハッシュを生成
                mtime = os.path.getmtime(flag_path)
                hash_data.append(f"{flag_path}:{mtime}")
        
        hash_string = "|".join(sorted(hash_data))
        return hashlib.md5(hash_string.encode('utf-8')).hexdigest()

    def _load_coords_cache(self) -> Optional[Dict]:
        """
        座標キャッシュファイルを読み込む

        Returns:
            座標情報の辞書、読み込み失敗時はNone
        """
        try:
            if os.path.exists(self.coords_file_path):
                with open(self.coords_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"座標キャッシュ読み込みエラー: {e}")
        return None

    def _save_coords_cache(self, coords_data: Dict) -> None:
        """
        座標キャッシュファイルを保存

        Args:
            coords_data: 保存する座標情報
        """
        try:
            os.makedirs(os.path.dirname(self.coords_file_path), exist_ok=True)
            with open(self.coords_file_path, 'w', encoding='utf-8') as f:
                json.dump(coords_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"座標キャッシュ保存エラー: {e}")

    def _load_flag_image(self, flag_path: str) -> Optional[Image.Image]:
        """
        国旗画像ファイルを読み込んで指定サイズにリサイズ

        Args:
            flag_path: 国旗画像ファイルのパス

        Returns:
            リサイズされたImage、読み込み失敗時はNone
        """
        try:
            if not os.path.exists(flag_path):
                return None
            
            # TGAファイルも含めて画像を読み込み
            img = Image.open(flag_path)
            
            # RGBA形式に変換（透明度対応）
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # 指定サイズにリサイズ
            img = img.resize(self.flag_size, Image.LANCZOS)
            
            return img
            
        except Exception as e:
            logger.warning(f"国旗画像読み込みエラー ({flag_path}): {e}")
            return None

    def _create_default_flag(self) -> Image.Image:
        """
        デフォルト国旗画像を作成（画像が見つからない場合用）

        Returns:
            デフォルト国旗のImage
        """
        img = Image.new('RGBA', self.flag_size, (128, 128, 128, 255))  # グレー
        draw = ImageDraw.Draw(img)
        
        # "?" マークを描画
        try:
            # フォントサイズを調整
            font_size = min(self.flag_size) // 2
            draw.text((self.flag_size[0]//2, self.flag_size[1]//2), '?', 
                     fill=(255, 255, 255, 255), anchor="mm")
        except:
            # フォントが利用できない場合は四角を描画
            draw.rectangle([5, 5, self.flag_size[0]-5, self.flag_size[1]-5], 
                          outline=(255, 255, 255, 255), width=2)
        
        return img

    def generate_sprite_sheet(self, nations: List[Dict]) -> bool:
        """
        国家リストから国旗スプライトシートを生成

        Args:
            nations: 国家情報のリスト（flag_pathを含む）

        Returns:
            生成成功時True
        """
        try:
            logger.info(f"国旗スプライトシート生成開始: 国家数={len(nations)}")
            
            # 有効な国旗がある国家のみをフィルタリング
            valid_nations = []
            for nation in nations:
                flag_path = nation.get('flag_path')
                if flag_path and os.path.exists(flag_path):
                    valid_nations.append(nation)
                else:
                    # 国旗がない場合もデフォルト国旗を使用
                    valid_nations.append(nation)
            
            if not valid_nations:
                logger.warning("有効な国家情報がありません")
                return False
            
            # スプライトシート寸法を計算
            cols, rows, sheet_width, sheet_height = self._calculate_sprite_dimensions(len(valid_nations))
            
            # スプライトシートを作成
            sprite_sheet = Image.new('RGBA', (sheet_width, sheet_height), (0, 0, 0, 0))
            coords_data = {
                'metadata': {
                    'generated_at': time.time(),
                    'flag_count': len(valid_nations),
                    'flag_size': self.flag_size,
                    'sheet_size': [sheet_width, sheet_height],
                    'cols': cols,
                    'rows': rows,
                    'flags_hash': self._generate_flags_hash(valid_nations)
                },
                'flags': {}
            }
            
            # 各国旗をスプライトシートに配置
            for i, nation in enumerate(valid_nations):
                row = i // cols
                col = i % cols
                x = col * self.flag_size[0]
                y = row * self.flag_size[1]
                
                # 国旗画像を読み込み
                flag_path = nation.get('flag_path')
                flag_img = None
                
                if flag_path and os.path.exists(flag_path):
                    flag_img = self._load_flag_image(flag_path)
                
                # 読み込み失敗時はデフォルト国旗を使用
                if flag_img is None:
                    flag_img = self._create_default_flag()
                
                # スプライトシートに貼り付け
                sprite_sheet.paste(flag_img, (x, y))
                
                # 座標情報を記録
                tag = nation.get('tag', f'UNKNOWN_{i}')
                coords_data['flags'][tag] = {
                    'x': x,
                    'y': y,
                    'width': self.flag_size[0],
                    'height': self.flag_size[1],
                    'index': i,
                    'name': nation.get('name', tag),
                    'flag_path': flag_path
                }
                
                logger.debug(f"国旗配置: {tag} at ({x}, {y})")
            
            # スプライトシートを保存
            os.makedirs(os.path.dirname(self.sprite_sheet_path), exist_ok=True)
            sprite_sheet.save(self.sprite_sheet_path, 'PNG', optimize=True)
            
            # 座標データを保存
            self._save_coords_cache(coords_data)
            
            # キャッシュを更新
            self._sprite_sheet = sprite_sheet
            self._coords_cache = coords_data
            
            logger.info(f"国旗スプライトシート生成完了: {len(valid_nations)}個の国旗, ファイルサイズ={os.path.getsize(self.sprite_sheet_path)} bytes")
            return True
            
        except Exception as e:
            logger.error(f"スプライトシート生成エラー: {e}")
            return False

    def is_cache_valid(self, nations: List[Dict]) -> bool:
        """
        スプライトシートキャッシュが有効かどうかを判定

        Args:
            nations: 国家情報のリスト

        Returns:
            キャッシュが有効な場合True
        """
        try:
            # スプライトシートファイルが存在するか
            if not os.path.exists(self.sprite_sheet_path):
                return False
            
            # 座標ファイルが存在するか
            if not os.path.exists(self.coords_file_path):
                return False
            
            # 座標データを読み込み
            coords_data = self._load_coords_cache()
            if not coords_data:
                return False
            
            # 国旗ハッシュを比較
            current_hash = self._generate_flags_hash(nations)
            cached_hash = coords_data.get('metadata', {}).get('flags_hash', '')
            
            is_valid = current_hash == cached_hash
            logger.debug(f"スプライトシートキャッシュ有効性: {is_valid}")
            
            return is_valid
            
        except Exception as e:
            logger.warning(f"キャッシュ有効性チェックエラー: {e}")
            return False

    def get_flag_region(self, nation_tag: str) -> Optional[Tuple[int, int, int, int]]:
        """
        指定された国家タグの国旗の座標情報を取得

        Args:
            nation_tag: 国家タグ

        Returns:
            (x, y, width, height) または None
        """
        try:
            if self._coords_cache is None:
                self._coords_cache = self._load_coords_cache()
            
            if not self._coords_cache:
                return None
            
            flag_info = self._coords_cache.get('flags', {}).get(nation_tag)
            if flag_info:
                return (flag_info['x'], flag_info['y'], flag_info['width'], flag_info['height'])
            
            return None
            
        except Exception as e:
            logger.warning(f"国旗座標取得エラー ({nation_tag}): {e}")
            return None

    def get_sprite_sheet(self) -> Optional[Image.Image]:
        """
        スプライトシート画像を取得

        Returns:
            スプライトシートのImage、読み込み失敗時はNone
        """
        try:
            if self._sprite_sheet is None:
                if os.path.exists(self.sprite_sheet_path):
                    self._sprite_sheet = Image.open(self.sprite_sheet_path)
                else:
                    return None
            
            return self._sprite_sheet
            
        except Exception as e:
            logger.error(f"スプライトシート読み込みエラー: {e}")
            return None

    def extract_flag(self, nation_tag: str) -> Optional[Image.Image]:
        """
        スプライトシートから指定された国旗を切り出し

        Args:
            nation_tag: 国家タグ

        Returns:
            国旗のImage、見つからない場合はNone
        """
        try:
            # 座標情報を取得
            region = self.get_flag_region(nation_tag)
            if not region:
                return None
            
            # スプライトシートを取得
            sprite_sheet = self.get_sprite_sheet()
            if not sprite_sheet:
                return None
            
            # 国旗部分を切り出し
            x, y, width, height = region
            flag_img = sprite_sheet.crop((x, y, x + width, y + height))
            
            return flag_img
            
        except Exception as e:
            logger.warning(f"国旗切り出しエラー ({nation_tag}): {e}")
            return None

    def get_cache_info(self) -> Dict:
        """
        キャッシュ情報を取得

        Returns:
            キャッシュ情報の辞書
        """
        info = {
            'sprite_sheet_exists': os.path.exists(self.sprite_sheet_path),
            'coords_file_exists': os.path.exists(self.coords_file_path),
            'sprite_sheet_size': 0,
            'flag_count': 0,
            'generated_at': None
        }
        
        try:
            if info['sprite_sheet_exists']:
                info['sprite_sheet_size'] = os.path.getsize(self.sprite_sheet_path)
            
            coords_data = self._load_coords_cache()
            if coords_data:
                metadata = coords_data.get('metadata', {})
                info['flag_count'] = metadata.get('flag_count', 0)
                info['generated_at'] = metadata.get('generated_at')
                info['sheet_dimensions'] = metadata.get('sheet_size', [0, 0])
                info['flag_size'] = metadata.get('flag_size', self.flag_size)
                
        except Exception as e:
            logger.warning(f"キャッシュ情報取得エラー: {e}")
        
        return info

    def clear_cache(self) -> None:
        """
        スプライトシートキャッシュをクリア
        """
        try:
            if os.path.exists(self.sprite_sheet_path):
                os.remove(self.sprite_sheet_path)
                logger.info(f"スプライトシートを削除: {self.sprite_sheet_path}")
            
            if os.path.exists(self.coords_file_path):
                os.remove(self.coords_file_path)
                logger.info(f"座標ファイルを削除: {self.coords_file_path}")
            
            # メモリキャッシュもクリア
            self._sprite_sheet = None
            self._coords_cache = None
            
        except Exception as e:
            logger.error(f"キャッシュクリアエラー: {e}")