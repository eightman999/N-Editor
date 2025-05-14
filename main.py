import os
import sys

from controllers.app_controller import AppController
from models.app_settings import AppSettings

os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ".venv/lib/python3.13/site-packages/PyQt5/Qt5/plugins/platforms"

from PyQt5.QtWidgets import QApplication
from views.main_window import MainWindow

def ensure_assets_directory():
    """assets ディレクトリが存在することを確認する"""
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)

    # デフォルトMODアイコンがなければサンプルを作成
    default_icon_path = os.path.join(assets_dir, "default_mod_icon.png")
    if not os.path.exists(default_icon_path):
        # 簡単な空のPNGファイルを作成（実際はもっと良いアイコンを用意すべき）
        # この部分は実際のプロジェクトではアイコンファイルを含めるべき
        with open(default_icon_path, 'wb') as f:
            # 最小限のPNGファイルのバイナリデータ
            png_data = bytes.fromhex(
                '89504E470D0A1A0A0000000D4948445200000040000000400806000000AA6971DE'
                '0000001C4944415478DA6364A031601CB560D45AA3160C5AB41683C5FF1F00A5051DC0F9E172FB0000000049454E44AE426082'
            )
            f.write(png_data)

def main():
    """アプリケーションのメインエントリーポイント"""
    # アセットディレクトリを確認
    ensure_assets_directory()

    # アプリケーション設定をロード
    app_settings = AppSettings()

    # PyQtアプリケーションの初期化
    app = QApplication(sys.argv)

    # アプリケーションコントローラーの作成
    controller = AppController(app_settings)
    controller.show_main_window()

    # イベントループの実行
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()