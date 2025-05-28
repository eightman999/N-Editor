import os
import pickle
import time
import logging
from typing import Optional, Any
from utils.path_utils import get_user_documents_path

# ロガーの設定
logger = logging.getLogger(__name__)


class CacheManager:
    """
    MODデータのパース結果をキャッシュして、パフォーマンスを向上させるクラス
    """

    def __init__(self, mod_name: str):
        """
        CacheManagerを初期化

        Args:
            mod_name: MOD名（バニラの場合は '_vanilla_' を使用）
        """
        self.mod_name = mod_name

        # ベースキャッシュディレクトリパスを生成
        # 例: Documents/NavalDesignSystem/caches/MyMod/
        self.base_cache_dir = os.path.join(
            get_user_documents_path(),
            'caches',
            self.mod_name
        )

        logger.info(f"CacheManager初期化: MOD={mod_name}, キャッシュディレクトリ={self.base_cache_dir}")

    def _get_cache_file_path(self, file_type: str, original_file_path: str) -> str:
        """
        対応するキャッシュファイルのフルパスを返す

        Args:
            file_type: ファイル種別 (states, naval_oob, strategic_regions, country_colors, equipments など)
            original_file_path: パース対象の元ファイルのフルパス

        Returns:
            キャッシュファイルのフルパス
            例: .../Documents/NavalDesignSystem/caches/MyMod/states/some_state_file.txt.pkl
        """
        # 元ファイル名を取得
        original_filename = os.path.basename(original_file_path)

        # キャッシュファイル名を生成（元ファイル名 + .pkl）
        cache_filename = f"{original_filename}.pkl"

        # キャッシュファイルのフルパスを生成
        cache_file_path = os.path.join(
            self.base_cache_dir,
            file_type,
            cache_filename
        )

        return cache_file_path

    def load(self, file_type: str, original_file_path: str) -> Optional[Any]:
        """
        キャッシュからデータを読み込む

        Args:
            file_type: ファイル種別
            original_file_path: 元ファイルのフルパス

        Returns:
            キャッシュされたデータ。キャッシュが存在しないか古い場合はNone
        """
        try:
            # 元ファイルが存在しない場合はNoneを返す
            if not os.path.exists(original_file_path):
                logger.debug(f"元ファイルが存在しません: {original_file_path}")
                return None

            # キャッシュファイルパスを取得
            cache_file_path = self._get_cache_file_path(file_type, original_file_path)

            # キャッシュファイルが存在しない場合はNoneを返す
            if not os.path.exists(cache_file_path):
                logger.debug(f"キャッシュファイルが存在しません: {cache_file_path}")
                return None

            # ファイルの最終更新日時を比較
            original_mtime = os.path.getmtime(original_file_path)
            cache_mtime = os.path.getmtime(cache_file_path)

            # 元ファイルの方が新しい場合（キャッシュが古い）はNoneを返す
            if original_mtime > cache_mtime:
                logger.debug(f"キャッシュが古いため無効: 元={original_mtime}, キャッシュ={cache_mtime}")
                return None

            # キャッシュファイルからデータをデシリアライズして返す
            with open(cache_file_path, 'rb') as f:
                data = pickle.load(f)

            logger.debug(f"キャッシュからデータを読み込み成功: {cache_file_path}")
            return data

        except (FileNotFoundError, pickle.UnpicklingError, EOFError) as e:
            logger.warning(f"キャッシュ読み込みエラー ({original_file_path}): {e}")
            return None
        except Exception as e:
            logger.error(f"予期しないキャッシュ読み込みエラー ({original_file_path}): {e}")
            return None

    def save(self, file_type: str, original_file_path: str, data: Any) -> None:
        """
        データをキャッシュに保存する

        Args:
            file_type: ファイル種別
            original_file_path: 元ファイルのフルパス
            data: 保存するデータ
        """
        try:
            # キャッシュファイルパスを取得
            cache_file_path = self._get_cache_file_path(file_type, original_file_path)

            # 保存先ディレクトリが存在しない場合は作成
            cache_dir = os.path.dirname(cache_file_path)
            os.makedirs(cache_dir, exist_ok=True)

            # データをシリアライズして保存
            with open(cache_file_path, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

            logger.debug(f"キャッシュにデータを保存成功: {cache_file_path}")

        except Exception as e:
            logger.error(f"キャッシュ保存エラー ({original_file_path}): {e}")
            # エラーが発生してもアプリケーションを停止させない

    def clear_cache(self, file_type: Optional[str] = None) -> None:
        """
        キャッシュをクリアする

        Args:
            file_type: 特定のファイル種別のキャッシュのみクリアする場合に指定。
                      Noneの場合は全てのキャッシュをクリア
        """
        try:
            if file_type is None:
                # 全キャッシュをクリア
                import shutil
                if os.path.exists(self.base_cache_dir):
                    shutil.rmtree(self.base_cache_dir)
                    logger.info(f"全キャッシュをクリアしました: {self.base_cache_dir}")
            else:
                # 特定のファイル種別のキャッシュをクリア
                type_cache_dir = os.path.join(self.base_cache_dir, file_type)
                if os.path.exists(type_cache_dir):
                    import shutil
                    shutil.rmtree(type_cache_dir)
                    logger.info(f"{file_type} キャッシュをクリアしました: {type_cache_dir}")

        except Exception as e:
            logger.error(f"キャッシュクリアエラー: {e}")

    def get_cache_info(self) -> dict:
        """
        キャッシュの情報を取得する（デバッグ用）

        Returns:
            キャッシュ情報の辞書
        """
        info = {
            'mod_name': self.mod_name,
            'base_cache_dir': self.base_cache_dir,
            'cache_exists': os.path.exists(self.base_cache_dir),
            'file_types': []
        }

        try:
            if os.path.exists(self.base_cache_dir):
                for item in os.listdir(self.base_cache_dir):
                    item_path = os.path.join(self.base_cache_dir, item)
                    if os.path.isdir(item_path):
                        cache_files = []
                        try:
                            cache_files = [f for f in os.listdir(item_path) if f.endswith('.pkl')]
                        except:
                            pass
                        info['file_types'].append({
                            'type': item,
                            'cache_count': len(cache_files)
                        })
        except Exception as e:
            logger.error(f"キャッシュ情報取得エラー: {e}")

        return info