import os
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ".venv/lib/python3.13/site-packages/PyQt5/Qt5/plugins/platforms"
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox, QToolBar
from PyQt5.QtCore import Qt
import sys



from views.map_widget import MapViewWidget

class MapTestApp(QMainWindow):
    """マップ表示のテスト用アプリケーション"""
    
    def __init__(self):
        super().__init__()
        
        # ウィンドウの設定
        self.setWindowTitle("Map Test")
        self.setGeometry(100, 100, 1024, 768)
        
        # マップウィジェットを作成
        self.map_widget = MapViewWidget(self)
        self.setCentralWidget(self.map_widget)
        
        # メニューバーを作成
        self.create_menu()
        
        # ツールバーを追加
        self.create_toolbar()
    
    def create_menu(self):
        """メニューバーを作成"""
        # メニューバー
        menu_bar = self.menuBar()
        
        # ファイルメニュー
        file_menu = menu_bar.addMenu("ファイル")
        
        # MOD選択アクション
        select_mod_action = file_menu.addAction("MODフォルダを選択")
        select_mod_action.triggered.connect(self.select_mod_folder)
        
        # 終了アクション
        exit_action = file_menu.addAction("終了")
        exit_action.triggered.connect(self.close)
        
        # 表示メニュー
        view_menu = menu_bar.addMenu("表示")
        
        # ズームインアクション
        zoom_in_action = view_menu.addAction("拡大")
        zoom_in_action.triggered.connect(self.map_widget.zoom_in)
        
        # ズームアウトアクション
        zoom_out_action = view_menu.addAction("縮小")
        zoom_out_action.triggered.connect(self.map_widget.zoom_out)
        
        # リセットアクション
        reset_action = view_menu.addAction("表示をリセット")
        reset_action.triggered.connect(self.map_widget.reset_view)
    
    def create_toolbar(self):
        """ツールバーを作成"""
        # メインツールバー
        main_toolbar = QToolBar("メインツールバー")
        main_toolbar.setMovable(False)  # ツールバーの位置を固定
        self.addToolBar(main_toolbar)
        
        # MODフォルダ選択ボタン
        select_mod_action = main_toolbar.addAction("MODフォルダを選択")
        select_mod_action.triggered.connect(self.select_mod_folder)
        
        # 区切り線を追加
        main_toolbar.addSeparator()
        
        # ズームコントロール
        zoom_in_action = main_toolbar.addAction("拡大")
        zoom_in_action.triggered.connect(self.map_widget.zoom_in)
        
        zoom_out_action = main_toolbar.addAction("縮小")
        zoom_out_action.triggered.connect(self.map_widget.zoom_out)
        
        reset_view_action = main_toolbar.addAction("表示をリセット")
        reset_view_action.triggered.connect(self.map_widget.reset_view)
    
    def select_mod_folder(self):
        """MODフォルダを選択"""
        folder = QFileDialog.getExistingDirectory(self, "MODフォルダを選択")
        
        if folder:
            # MODフォルダが有効かチェック
            if self.is_valid_mod_folder(folder):
                # マップデータを読み込む
                self.map_widget.load_map_data(folder)
            else:
                QMessageBox.warning(self, "エラー", "選択されたフォルダは有効なHOI4 MODフォルダではありません。\n必要なファイルが見つかりません。")
    
    def is_valid_mod_folder(self, folder):
        """MODフォルダが有効かチェック"""
        # 必要なファイルやディレクトリが存在するか確認
        map_dir = os.path.join(folder, "map")
        if not os.path.exists(map_dir):
            return False
        
        provinces_file = os.path.join(map_dir, "provinces.bmp")
        definition_file = os.path.join(map_dir, "definition.csv")
        
        if not os.path.exists(provinces_file) or not os.path.exists(definition_file):
            return False
        
        return True

def main():
    """メイン関数"""
    app = QApplication(sys.argv)
    
    # スタイルシートを設定（Windows 95風）
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow, QDialog, QWidget {
            background-color: #c0c0c0;
            color: black;
        }
        QPushButton {
            background-color: #c0c0c0;
            border: 2px outset #a0a0a0;
            padding: 4px;
            min-width: 80px;
            min-height: 24px;
        }
        QPushButton:pressed {
            border: 2px inset #a0a0a0;
        }
        QMenuBar {
            background-color: #c0c0c0;
            border-bottom: 1px solid #a0a0a0;
        }
        QMenuBar::item {
            background-color: #c0c0c0;
            padding: 4px 6px;
        }
        QMenuBar::item:selected {
            background-color: #0078d7;
            color: white;
        }
        QMenu {
            background-color: #c0c0c0;
            border: 1px solid #a0a0a0;
        }
        QMenu::item {
            padding: 4px 20px 4px 20px;
        }
        QMenu::item:selected {
            background-color: #0078d7;
            color: white;
        }
        QToolBar {
            background-color: #c0c0c0;
            border: 1px solid #a0a0a0;
            spacing: 3px;
        }
        QToolButton {
            background-color: #c0c0c0;
            border: 2px outset #a0a0a0;
            padding: 4px;
        }
        QToolButton:pressed {
            border: 2px inset #a0a0a0;
        }
    """)
    
    # メインウィンドウを作成
    window = MapTestApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()