import os
import sys
import logging
import platform

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


# Windows対応: PyQt5プラットフォームプラグインのパス設定
def setup_qt_plugin_path():
    """プラットフォームに応じてQtプラグインのパスを設定"""
    try:
        if platform.system() == "Windows":
            # Windows環境でのパス設定
            if hasattr(sys, 'frozen'):
                # 実行ファイルの場合
                plugin_path = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt', 'plugins')
            else:
                # 開発環境の場合 - Windowsの仮想環境パス
                python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
                possible_paths = [
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), '.venv', 'Lib', 'site-packages', 'PyQt5',
                                 'Qt5', 'plugins'),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'venv', 'Lib', 'site-packages', 'PyQt5',
                                 'Qt5', 'plugins'),
                    os.path.join(sys.prefix, 'Lib', 'site-packages', 'PyQt5', 'Qt5', 'plugins'),
                ]

                plugin_path = None
                for path in possible_paths:
                    if os.path.exists(path):
                        plugin_path = path
                        break

        elif platform.system() == "Darwin":
            # macOS環境
            if hasattr(sys, 'frozen'):
                plugin_path = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt', 'plugins')
            else:
                plugin_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           '.venv', 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}',
                                           'site-packages',
                                           'PyQt5', 'Qt5', 'plugins')

        else:
            # Linux環境
            if hasattr(sys, 'frozen'):
                plugin_path = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt', 'plugins')
            else:
                plugin_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           '.venv', 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}',
                                           'site-packages',
                                           'PyQt5', 'Qt5', 'plugins')

        # プラグインパスが存在する場合のみ設定
        if plugin_path and os.path.exists(plugin_path):
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path
            logger.info(f"Qt plugin path set to: {plugin_path}")
        else:
            logger.warning(f"Qt plugin path not found. Tried: {plugin_path if plugin_path else 'None'}")
            # 環境変数をクリア（システムデフォルトを使用）
            if "QT_QPA_PLATFORM_PLUGIN_PATH" in os.environ:
                del os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"]

    except Exception as e:
        logger.error(f"Error setting up Qt plugin path: {e}")


# プラットフォーム設定
setup_qt_plugin_path()

# PyQt5のインポートを試行
try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtCore import QT_VERSION_STR, PYQT_VERSION_STR

    logger.info(f"PyQt5 successfully imported. Qt version: {QT_VERSION_STR}, PyQt version: {PYQT_VERSION_STR}")
except ImportError as e:
    logger.error(f"Failed to import PyQt5: {e}")
    print("エラー: PyQt5がインストールされていません。")
    print("以下のコマンドでインストールしてください:")
    print("pip install PyQt5")
    sys.exit(1)
except Exception as e:
    logger.error(f"Unexpected error importing PyQt5: {e}")
    print(f"PyQt5のインポート中に予期しないエラーが発生しました: {e}")
    sys.exit(1)


# 依存関係のチェック
def check_dependencies():
    """必要な依存関係をチェック"""
    missing_deps = []

    try:
        import PIL
        logger.info("PIL/Pillow is available")
    except ImportError:
        missing_deps.append("Pillow")

    try:
        import cv2
        logger.info("OpenCV is available")
    except ImportError:
        logger.warning("OpenCV is not available (optional)")

    try:
        import yaml
        logger.info("PyYAML is available")
    except ImportError:
        missing_deps.append("PyYAML")

    try:
        import ply
        logger.info("PLY is available")
    except ImportError:
        missing_deps.append("ply")

    if missing_deps:
        error_msg = f"以下の依存関係がインストールされていません: {', '.join(missing_deps)}\n"
        error_msg += "以下のコマンドでインストールしてください:\n"
        error_msg += f"pip install {' '.join(missing_deps)}"
        logger.error(error_msg)
        print(error_msg)
        return False

    return True


# アプリケーションモジュールのインポート
try:
    from models.app_settings import AppSettings
    from controllers.app_controller import AppController

    logger.info("Application modules imported successfully")
except ImportError as e:
    logger.error(f"Failed to import application modules: {e}")
    print(f"アプリケーションモジュールのインポートエラー: {e}")
    sys.exit(1)


def main():
    """
    アプリケーションのエントリーポイント
    MVCパターンに従い、コントローラーを通じてアプリケーションを起動します
    """
    logger.info(f"Starting Naval Design System on {platform.system()} {platform.release()}")

    # 依存関係チェック
    if not check_dependencies():
        input("Enterキーを押して終了...")
        return

    # PyQt5アプリケーションの初期化
    try:
        app = QApplication(sys.argv)
        logger.info("QApplication created successfully")
    except Exception as e:
        logger.error(f"Failed to create QApplication: {e}")
        print(f"QApplicationの作成に失敗しました: {e}")
        input("Enterキーを押して終了...")
        return

    # Windows 95風スタイルの適用
    try:
        app.setStyle("Fusion")
        logger.info("Application style set to Fusion")
    except Exception as e:
        logger.warning(f"Failed to set application style: {e}")

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

    try:
        # 設定の初期化
        app_settings = AppSettings()
        logger.info("AppSettings initialized")

        # コントローラーの初期化
        controller = AppController(app_settings)
        logger.info("AppController initialized")

        # メインウィンドウの表示
        controller.show_main_window()
        logger.info("Main window displayed")

        # イベントループの開始
        logger.info("Starting event loop")
        sys.exit(app.exec_())

    except Exception as e:
        logger.error(f"Application error: {e}")
        try:
            # エラーダイアログを表示
            QMessageBox.critical(None, "エラー", f"アプリケーションエラーが発生しました:\n{e}")
        except:
            print(f"アプリケーションエラー: {e}")
        input("Enterキーを押して終了...")


def ensure_assets_directory():
    """assets ディレクトリが存在することを確認する"""
    try:
        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        if not os.path.exists(assets_dir):
            os.makedirs(assets_dir)
            logger.info(f"Created assets directory: {assets_dir}")

        # デフォルトMODアイコンがなければサンプルを作成
        default_icon_path = os.path.join(assets_dir, "default_mod_icon.png")
        if not os.path.exists(default_icon_path):
            # 簡単な空のPNGファイルを作成
            with open(default_icon_path, 'wb') as f:
                # 最小限のPNGファイルのバイナリデータ
                png_data = bytes.fromhex(
                    '89504E470D0A1A0A0000000D4948445200000040000000400806000000AA6971DE'
                    '0000001C4944415478DA6364A031601CB560D45AA3160C5AB41683C5FF1F00A5051DC0F9E172FB0000000049454E44AE426082'
                )
                f.write(png_data)
            logger.info(f"Created default icon: {default_icon_path}")
    except Exception as e:
        logger.warning(f"Failed to ensure assets directory: {e}")


if __name__ == "__main__":
    main()