from views.main_window import MainWindow
from views.home_view import HomeView
from views.equipment_form import EquipmentForm
from views.hull_form import HullForm
from views.design_view import DesignView
from views.fleet_view import FleetView
from views.settings_view import SettingsView

class AppController:
    """アプリケーション全体のコントローラークラス"""
    def __init__(self, app_settings):
        self.app_settings = app_settings
        self.main_window = None
        self.views = {}

        # 初回起動時の処理
        if self.app_settings.get_setting("first_run"):
            self.on_first_run()

    def on_first_run(self):
        """初回起動時の処理"""
        # 初回起動フラグをオフに
        self.app_settings.set_setting("first_run", False)

        # その他の初期設定や案内など
        # TODO: ウェルカムメッセージなどを表示

    def show_main_window(self):
        """メインウィンドウを表示"""
        if self.main_window is None:
            self.main_window = MainWindow(self, self.app_settings)

            # ビューを初期化して登録
            self.initialize_views()

            # ウィンドウサイズとポジションを復元
            window_size = self.app_settings.get_setting("window_size")
            window_position = self.app_settings.get_setting("window_position")

            if window_size:
                self.main_window.resize(*window_size)
            if window_position:
                self.main_window.move(*window_position)

        self.main_window.show()

    def initialize_views(self):
        """各ビューを初期化して登録"""
        self.views["home"] = HomeView(self.main_window, self.app_settings)
        self.views["equipment"] = EquipmentForm(self.main_window)
        self.views["hull"] = HullForm(self.main_window)
        self.views["design"] = DesignView(self.main_window)
        self.views["fleet"] = FleetView(self.main_window)
        self.views["settings"] = SettingsView(self.main_window, self.app_settings)

        # メインウィンドウのスタックウィジェットに各ビューを追加
        for view_name, view in self.views.items():
            self.main_window.add_view(view_name, view)

        # ホーム画面を表示
        self.main_window.show_view("home")

    def navigate_to(self, view_name):
        """指定したビューに移動"""
        if view_name in self.views:
            self.main_window.show_view(view_name)

    def save_app_state(self):
        """アプリケーションの状態を保存"""
        # ウィンドウサイズとポジション
        if self.main_window:
            size = self.main_window.size()
            pos = self.main_window.pos()

            self.app_settings.set_setting("window_size", [size.width(), size.height()])
            self.app_settings.set_setting("window_position", [pos.x(), pos.y()])

    def on_quit(self):
        """アプリケーション終了時の処理"""
        self.save_app_state()
        # その他の必要な終了処理