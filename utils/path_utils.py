import os

def get_app_support_dir():
    """アプリケーションサポートディレクトリのパスを取得"""
    home_dir = os.path.expanduser("~")
    app_support_dir = os.path.join(home_dir, 'Library', 'Application Support', 'NavalDesignSystem')
    os.makedirs(app_support_dir, exist_ok=True)
    return app_support_dir

def get_data_dir(data_type):
    """データタイプに応じたディレクトリのパスを取得"""
    app_support_dir = get_app_support_dir()
    data_dir = os.path.join(app_support_dir, data_type)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir 