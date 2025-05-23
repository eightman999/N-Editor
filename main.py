import os
import sys
import logging

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ".venv/lib/python3.13/site-packages/PyQt5/Qt5/plugins/platforms"

from PyQt5.QtWidgets import QApplication
from models.app_settings import AppSettings
from controllers.app_controller import AppController

def main():
    """
    アプリケーションのエントリーポイント
    MVCパターンに従い、コントローラーを通じてアプリケーションを起動します
    """
    # PyQt5プラグインパスの設定（必要な場合）
    if hasattr(sys, 'frozen'):
        # 実行ファイルにバンドルされている場合のパス
        plugin_path = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt', 'plugins')
    else:
        # 開発環境の場合のパス
        plugin_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   '.venv', 'lib', 'python3.13', 'site-packages',
                                   'PyQt5', 'Qt5', 'plugins', 'platforms')

    if os.path.exists(plugin_path):
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path

    # アプリケーションの初期化
    app = QApplication(sys.argv)

    # Windows 95風スタイルの適用
    app.setStyle("Fusion")

    # Windows 95風のグローバルスタイルシート
    app.setStyleSheet("""
        QMainWindow, QDialog, QWidget {
            background-color: #e6e6e6;
            color: black;
        }
        QPushButton {
            background-color: #e6e6e6;
            border: 2px outset #d4d0c8;
            border-top-color: white;
            border-left-color: white;
            padding: 4px;
            min-width: 80px;
            min-height: 24px;
        }
        QPushButton:pressed {
            border: 2px inset #808080;
            border-bottom-color: white;
            border-right-color: white;
        }
        QLineEdit, QTextEdit, QComboBox {
            background-color: white;
            border: 2px inset #808080;
        }
        QGroupBox {
            border: 2px groove #e6e6e6;
            border-top: 1px solid #808080;
            border-left: 1px solid #808080;
            border-bottom: 1px solid white;
            border-right: 1px solid white;
            margin-top: 12px;
            padding-top: 10px;
        }
        QTabWidget::pane {
            border: 2px outset #d4d0c8;
        }
        QTabBar::tab {
            background-color: #e6e6e6;
            border: 2px outset #d4d0c8;
            border-bottom: none;
            padding: 4px 8px;
        }
        QTabBar::tab:selected {
            background-color: #e6e6e6;
            border-bottom: 2px solid #e6e6e6;
        }
        QHeaderView::section {
            background-color: #e6e6e6;
            border: 2px outset #d4d0c8;
            padding: 4px;
        }
    """)

    # assetsディレクトリの確認
    ensure_assets_directory()

    # 設定の初期化
    app_settings = AppSettings()

    # コントローラーの初期化
    controller = AppController(app_settings)

    # メインウィンドウの表示
    controller.show_main_window()

    # イベントループの開始
    sys.exit(app.exec_())

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

if __name__ == "__main__":
    main()