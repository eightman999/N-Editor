from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from .mod_selector_widget import ModSelectorWidget

class HomeView(QWidget):
    """ホーム画面のビュー"""
    def __init__(self, parent=None, app_settings=None, app_controller=None):
        super().__init__(parent)
        self.app_settings = app_settings
        self.app_controller = app_controller
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # ウェルカムメッセージ
        welcome_label = QLabel("Naval Design System へようこそ", self)
        welcome_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(welcome_label)

        description_label = QLabel("Hearts of Iron IV向け艦艇設計ツール", self)
        layout.addWidget(description_label)

        # 現在のMOD表示
        self.current_mod_label = QLabel("", self)
        self.current_mod_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        layout.addWidget(self.current_mod_label)

        # MOD選択リストを追加
        mod_label = QLabel("編集対象MODを選択", self)
        mod_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(mod_label)

        # コントローラーをModSelectorWidgetに渡す
        self.mod_selector = ModSelectorWidget(self, app_settings=self.app_settings, app_controller=self.app_controller)
        layout.addWidget(self.mod_selector)

        # データディレクトリ情報
        if self.app_settings:
            data_dir_label = QLabel(f"データ保存先: {self.app_settings.data_dir}", self)
            data_dir_label.setStyleSheet("font-size: 10px; color: gray; margin-top: 10px;")
            layout.addWidget(data_dir_label)

        self.setLayout(layout)

        # 現在のMOD情報を更新
        self.update_current_mod_info()

    def showEvent(self, event):
        """ビューが表示される際に呼ばれるメソッド"""
        super().showEvent(event)
        # 現在のMOD情報を更新
        self.update_current_mod_info()

    def update_current_mod_info(self):
        """現在選択中のMOD情報を表示更新"""
        if self.app_controller:
            current_mod = self.app_controller.get_current_mod()
            if current_mod and current_mod.get("name"):
                self.current_mod_label.setText(f"現在のMOD: {current_mod.get('name')}")
            else:
                self.current_mod_label.setText("MODが選択されていません")
        else:
            # コントローラーがない場合は設定から直接取得
            if self.app_settings:
                mod_name = self.app_settings.get_setting("current_mod_name")
                if mod_name:
                    self.current_mod_label.setText(f"現在のMOD: {mod_name}")
                else:
                    self.current_mod_label.setText("MODが選択されていません")