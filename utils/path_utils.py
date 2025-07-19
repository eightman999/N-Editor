# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: path_utilsユーティリティ

import os
import platform

def get_user_documents_path():
    """ユーザーのドキュメントディレクトリのパスを取得"""
    home_dir = os.path.expanduser("~")

    # Windows/macOS両方でDocuments/NavalDesignSystemを使用
    documents_dir = os.path.join(home_dir, 'Documents', 'NavalDesignSystem')

    os.makedirs(documents_dir, exist_ok=True)
    return documents_dir

def get_app_support_dir():
    """アプリケーションサポートディレクトリのパスを取得（下位互換性のため残す）"""
    return get_user_documents_path()

def get_data_dir(data_type):
    """データタイプに応じたディレクトリのパスを取得"""
    app_support_dir = get_user_documents_path()
    data_dir = os.path.join(app_support_dir, data_type)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir