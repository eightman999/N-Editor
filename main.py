import os
import sys
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ".venv/lib/python3.13/site-packages/PyQt5/Qt5/plugins/platforms"

from PyQt5.QtWidgets import QApplication
from views.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 基本的なスタイル
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()