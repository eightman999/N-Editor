import os
import logging
from typing import Optional, Dict
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QFont, QPen, QBrush
from PyQt5.QtCore import Qt, QSize
from utils.ship_type_mapping import ship_type_mapping

logger = logging.getLogger(__name__)

class ShipIconManager:
    """艦種アイコン管理クラス"""
    
    def __init__(self, assets_base_dir: str = None):
        """
        アイコン管理システムを初期化
        
        Args:
            assets_base_dir: assetsディレクトリのベースパス
        """
        if assets_base_dir is None:
            # main.pyと同じディレクトリのassetsを使用
            self.assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
        else:
            self.assets_dir = assets_base_dir
            
        self.role_icons_dir = os.path.join(self.assets_dir, "ROLE")
        
        # アイコンキャッシュ
        self._icon_cache: Dict[str, QIcon] = {}
        self._pixmap_cache: Dict[str, QPixmap] = {}
        
        # ディレクトリが存在しない場合は作成
        os.makedirs(self.role_icons_dir, exist_ok=True)
        
        # 艦種略号から表示名へのマッピング（逆引き用）
        self._abbreviation_to_display = {}
        for abbrev, display_name in ship_type_mapping.items():
            self._abbreviation_to_display[abbrev] = display_name
        
        logger.info(f"ShipIconManager初期化完了: {self.role_icons_dir}")
    
    def get_ship_icon(self, ship_type: str, size: QSize = None) -> QIcon:
        """
        艦種のアイコンを取得
        
        Args:
            ship_type: 艦種（日本語名または略号）
            size: アイコンサイズ（デフォルト: 43x43）
            
        Returns:
            QIcon: 艦種アイコン
        """
        if size is None:
            size = QSize(43, 43)
            
        cache_key = f"{ship_type}_{size.width()}x{size.height()}"
        
        try:
            if cache_key in self._icon_cache:
                return self._icon_cache[cache_key]
            
            # 艦種から略号を取得
            abbreviation = self._get_ship_abbreviation(ship_type)
            
            # アイコンファイルパス
            icon_path = os.path.join(self.role_icons_dir, f"{abbreviation}.png")
            
            icon = QIcon()
            
            if os.path.exists(icon_path):
                try:
                    # アイコンファイルが存在する場合
                    pixmap = QPixmap(icon_path)
                    if not pixmap.isNull():
                        # サイズ調整
                        scaled_pixmap = pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        icon.addPixmap(scaled_pixmap)
                        logger.debug(f"アイコン読み込み成功: {icon_path}")
                    else:
                        # ファイルが壊れている場合はデフォルトアイコンを生成
                        icon.addPixmap(self._create_default_icon(abbreviation, size))
                        logger.warning(f"アイコンファイルが壊れています: {icon_path}")
                        # 壊れたファイルを削除して再生成
                        try:
                            os.remove(icon_path)
                            default_pixmap = self._create_default_icon(abbreviation, size)
                            default_pixmap.save(icon_path, "PNG")
                            logger.info(f"アイコンファイルを再生成: {icon_path}")
                        except Exception as e:
                            logger.error(f"アイコンファイルの再生成に失敗: {e}")
                except Exception as e:
                    logger.error(f"アイコン読み込みエラー: {e}")
                    icon.addPixmap(self._create_default_icon(abbreviation, size))
            else:
                # アイコンファイルが存在しない場合はデフォルトアイコンを生成
                default_pixmap = self._create_default_icon(abbreviation, size)
                icon.addPixmap(default_pixmap)
                try:
                    default_pixmap.save(icon_path, "PNG")
                    logger.info(f"デフォルトアイコンを作成: {icon_path}")
                except Exception as e:
                    logger.error(f"デフォルトアイコンの保存に失敗: {e}")
            
            # キャッシュに保存
            self._icon_cache[cache_key] = icon
            return icon
            
        except Exception as e:
            logger.error(f"アイコン取得エラー ({ship_type}): {e}")
            # エラー時は空のアイコンを返す
            return QIcon()
    
    def get_ship_pixmap(self, ship_type: str, size: QSize = None) -> QPixmap:
        """
        艦種のピクスマップを取得
        
        Args:
            ship_type: 艦種（日本語名または略号）
            size: ピクスマップサイズ（デフォルト: 43x43）
            
        Returns:
            QPixmap: 艦種ピクスマップ
        """
        if size is None:
            size = QSize(43, 43)
            
        cache_key = f"{ship_type}_{size.width()}x{size.height()}"
        
        try:
            if cache_key in self._pixmap_cache:
                return self._pixmap_cache[cache_key]
            
            # アイコンからピクスマップを取得
            icon = self.get_ship_icon(ship_type, size)
            if icon.isNull():
                logger.warning(f"無効なアイコン: {ship_type}")
                return QPixmap(size)
                
            pixmap = icon.pixmap(size)
            if pixmap.isNull():
                logger.warning(f"無効なピクスマップ: {ship_type}")
                return QPixmap(size)
            
            # キャッシュに保存
            self._pixmap_cache[cache_key] = pixmap
            return pixmap
            
        except Exception as e:
            logger.error(f"ピクスマップ取得エラー ({ship_type}): {e}")
            return QPixmap(size)
    
    def _get_ship_abbreviation(self, ship_type: str) -> str:
        """
        艦種から略号を取得
        
        Args:
            ship_type: 艦種（日本語名または略号）
            
        Returns:
            str: 艦種略号
        """
        # 既に略号の場合はそのまま返す
        if ship_type in ship_type_mapping:
            return ship_type
        
        # 日本語名から略号を検索
        for abbrev, display_name in ship_type_mapping.items():
            if display_name == ship_type:
                return abbrev
            # 部分一致も試行
            if ship_type in display_name:
                return abbrev
        
        # 見つからない場合は特殊なマッピングを試行
        special_mappings = {
            "戦艦": "BB",
            "巡洋戦艦": "BC", 
            "重巡洋艦": "CA",
            "軽巡洋艦": "CL",
            "駆逐艦": "DD",
            "潜水艦": "SS",
            "空母": "CV",
            "軽空母": "CVL",
            "護衛空母": "CVE",
            "水上機母艦": "AV",
            "輸送艦": "AP",
            "補給艦": "AO",
            "工作艦": "AR",
            "掃海艦": "AM",
            "哨戒艇": "PC",
            "魚雷艇": "PT",
            "砲艦": "PG",
            "フリゲート": "FF",
            "コルベット": "K"
        }
        
        for jp_name, abbrev in special_mappings.items():
            if jp_name in ship_type:
                return abbrev
        
        # それでも見つからない場合はデフォルト
        logger.warning(f"艦種略号が見つかりません: {ship_type}")
        return "UNKNOWN"
    
    def _create_default_icon(self, abbreviation: str, size: QSize) -> QPixmap:
        """
        デフォルトアイコンを生成
        
        Args:
            abbreviation: 艦種略号
            size: アイコンサイズ
            
        Returns:
            QPixmap: 生成されたデフォルトアイコン
        """
        pixmap = QPixmap(size)
        pixmap.fill(Qt.lightGray)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 外枠を描画
        painter.setPen(QPen(Qt.darkGray, 2))
        painter.setBrush(QBrush(Qt.white))
        painter.drawRoundedRect(2, 2, size.width()-4, size.height()-4, 4, 4)
        
        # 略号テキストを描画
        painter.setPen(QPen(Qt.black))
        font = QFont("Arial", max(8, size.width() // 6), QFont.Bold)
        painter.setFont(font)
        
        # テキストを中央に配置
        text_rect = painter.fontMetrics().boundingRect(abbreviation)
        x = (size.width() - text_rect.width()) // 2
        y = (size.height() + text_rect.height()) // 2
        
        painter.drawText(x, y, abbreviation)
        painter.end()
        
        logger.debug(f"デフォルトアイコンを生成: {abbreviation}")
        return pixmap
    
    def get_available_ship_types(self) -> list:
        """
        利用可能な艦種一覧を取得
        
        Returns:
            list: 艦種略号のリスト
        """
        available_types = []
        
        # ROLEディレクトリ内のPNGファイルをチェック
        if os.path.exists(self.role_icons_dir):
            for filename in os.listdir(self.role_icons_dir):
                if filename.endswith('.png'):
                    abbreviation = filename[:-4]  # .pngを除去
                    available_types.append(abbreviation)
        
        # ship_type_mappingからも追加
        for abbrev in ship_type_mapping.keys():
            if abbrev not in available_types:
                available_types.append(abbrev)
        
        return sorted(available_types)
    
    def create_fleet_composition_pixmap(self, fleet_composition: Dict[str, int], 
                                       total_size: QSize = None) -> QPixmap:
        """
        艦隊編成を表すピクスマップを作成
        
        Args:
            fleet_composition: 艦種別隻数の辞書 {"DD": 3, "CA": 2, ...}
            total_size: 全体サイズ（デフォルト: 120x43）
            
        Returns:
            QPixmap: 艦隊編成ピクスマップ
        """
        if total_size is None:
            total_size = QSize(120, 43)
        
        pixmap = QPixmap(total_size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # アイコンサイズを計算
        icon_size = QSize(24, 24)  # 小さめのアイコン
        
        x_offset = 2
        y_offset = (total_size.height() - icon_size.height()) // 2
        
        for ship_type, count in fleet_composition.items():
            if count > 0:
                # アイコンを描画
                ship_pixmap = self.get_ship_pixmap(ship_type, icon_size)
                painter.drawPixmap(x_offset, y_offset, ship_pixmap)
                
                # 隻数を描画
                painter.setPen(QPen(Qt.black))
                font = QFont("Arial", 8, QFont.Bold)
                painter.setFont(font)
                
                count_text = str(count)
                text_x = x_offset + icon_size.width() + 2
                text_y = y_offset + icon_size.height() // 2 + 4
                
                painter.drawText(text_x, text_y, count_text)
                
                # 次のアイコンの位置を計算
                text_width = painter.fontMetrics().width(count_text)
                x_offset += icon_size.width() + text_width + 8
                
                # 右端に達したら改行（簡易実装）
                if x_offset > total_size.width() - icon_size.width():
                    break
        
        painter.end()
        return pixmap
    
    def clear_cache(self):
        """アイコンキャッシュをクリア"""
        self._icon_cache.clear()
        self._pixmap_cache.clear()
        logger.info("アイコンキャッシュをクリアしました")
    
    def ensure_default_icons(self):
        """デフォルトアイコンファイルを生成（存在しない場合）"""
        default_types = [
            "BB", "BC", "CA", "CL", "DD", "SS", 
            "CV", "CVL", "CVE", "AV", "AM", "PC", "PT"
        ]
        
        created_count = 0
        
        for ship_type in default_types:
            icon_path = os.path.join(self.role_icons_dir, f"{ship_type}.png")
            
            if not os.path.exists(icon_path):
                # デフォルトアイコンを生成して保存
                default_pixmap = self._create_default_icon(ship_type, QSize(43, 43))
                default_pixmap.save(icon_path, "PNG")
                created_count += 1
                logger.info(f"デフォルトアイコンを作成: {icon_path}")
        
        if created_count > 0:
            logger.info(f"{created_count}個のデフォルトアイコンを作成しました") 