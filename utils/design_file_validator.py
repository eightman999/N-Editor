# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: design_file_validatorユーティリティ
"""
設計ファイルのバリデーション機能

このモジュールは設計ファイルのヘッダーチェックやファイル形式の検証を行います。
"""

import os
import json
import logging
from typing import Optional, Dict, Any


def validate_design_file_header(file_path: str) -> bool:
    """
    設計ファイルのヘッダーをチェックする
    
    ファイルの先頭行に「@config.design」が含まれているかを確認します。
    
    Args:
        file_path (str): チェックするファイルのパス
        
    Returns:
        bool: ヘッダーが正しい場合True、そうでなければFalse
    """
    try:
        if not os.path.exists(file_path):
            logging.warning(f"設計ファイルが存在しません: {file_path}")
            return False
            
        # ファイルの先頭行を読み込み
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            
        # ヘッダーチェック
        if first_line == "@config.design":
            logging.info(f"設計ファイルのヘッダーが正しいです: {file_path}")
            return True
        else:
            logging.info(f"設計ファイルのヘッダーが不正です（スキップします）: {file_path}")
            logging.debug(f"期待値: '@config.design', 実際: '{first_line}'")
            return False
            
    except Exception as e:
        logging.error(f"設計ファイルのヘッダーチェック中にエラーが発生しました: {file_path}, エラー: {e}")
        return False


def load_design_file_with_validation(file_path: str) -> Optional[Dict[str, Any]]:
    """
    設計ファイルをヘッダーチェック付きで読み込む
    
    Args:
        file_path (str): 読み込むファイルのパス
        
    Returns:
        Optional[Dict[str, Any]]: 読み込み成功時は設計データ、失敗時はNone
    """
    try:
        # ヘッダーチェック
        if not validate_design_file_header(file_path):
            logging.info(f"設計ファイルをスキップしました（ヘッダー不正）: {file_path}")
            return None
            
        # JSONファイルとして読み込み
        with open(file_path, 'r', encoding='utf-8') as f:
            # 最初の行（ヘッダー）をスキップ
            first_line = f.readline()
            if first_line.strip() == "@config.design":
                # ヘッダーがある場合、残りの部分をJSONとして読み込み
                remaining_content = f.read()
                design_data = json.loads(remaining_content)
            else:
                # ファイルポインターを先頭に戻す（ヘッダーがない場合）
                f.seek(0)
                design_data = json.load(f)
            
        logging.info(f"設計ファイルを正常に読み込みました: {file_path}")
        return design_data
        
    except json.JSONDecodeError as e:
        logging.error(f"設計ファイルのJSON形式が不正です: {file_path}, エラー: {e}")
        return None
    except Exception as e:
        logging.error(f"設計ファイル読み込み中にエラーが発生しました: {file_path}, エラー: {e}")
        return None


def is_valid_design_file(file_path: str) -> bool:
    """
    設計ファイルが有効かどうかをチェックする
    
    Args:
        file_path (str): チェックするファイルのパス
        
    Returns:
        bool: ファイルが有効な設計ファイルの場合True
    """
    # ファイル拡張子チェック
    if not file_path.endswith('.json'):
        return False
        
    # ヘッダーチェック
    return validate_design_file_header(file_path)


def get_design_files_with_validation(directory: str) -> list:
    """
    ディレクトリ内の有効な設計ファイル一覧を取得する
    
    Args:
        directory (str): 検索するディレクトリのパス
        
    Returns:
        list: 有効な設計ファイルのパスのリスト
    """
    valid_files = []
    
    try:
        if not os.path.exists(directory):
            logging.warning(f"設計ディレクトリが存在しません: {directory}")
            return valid_files
            
        # ディレクトリ内のJSONファイルをチェック
        for file_name in os.listdir(directory):
            if file_name.endswith('.json'):
                file_path = os.path.join(directory, file_name)
                
                if is_valid_design_file(file_path):
                    valid_files.append(file_path)
                    logging.debug(f"有効な設計ファイル: {file_path}")
                else:
                    logging.debug(f"無効な設計ファイル（スキップ）: {file_path}")
                    
        logging.info(f"設計ファイル検索完了: {len(valid_files)}個の有効なファイルを発見")
        
    except Exception as e:
        logging.error(f"設計ファイル一覧取得中にエラーが発生しました: {directory}, エラー: {e}")
        
    return valid_files