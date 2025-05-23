from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from views.nation_list_view import NationListView
from views.nation_details_view import NationDetailsView
from views.equipment_form import EquipmentForm
from views.hull_form import HullForm
from views.design_view import DesignView
from views.mod_formation_view import ModFormationView
from parser.EffectParser import EffectParser
import os
import json

class AppController:
    """アプリケーションのメインコントローラー"""

    def __init__(self):
        """初期化"""
        self.current_mod = None
        self.nation_list_view = None
        self.nation_details_view = None
        self.equipment_form = None
        self.hull_form = None
        self.design_view = None
        self.mod_formation_view = None

    def initialize(self):
        """アプリケーションの初期化"""
        try:
            # メインウィンドウの作成
            self.main_window = QMainWindow()
            self.main_window.setWindowTitle("N-Editor")
            self.main_window.setGeometry(100, 100, 1200, 800)

            # 国家リスト画面の表示
            self.show_nation_list()

            # メインウィンドウの表示
            self.main_window.show()

        except Exception as e:
            QMessageBox.critical(None, "エラー", f"アプリケーションの初期化中にエラーが発生しました：\n{str(e)}")

    def show_nation_list(self):
        """国家リスト画面を表示"""
        try:
            if not self.nation_list_view:
                self.nation_list_view = NationListView(parent=self.main_window, app_controller=self)
            self.main_window.setCentralWidget(self.nation_list_view)
        except Exception as e:
            QMessageBox.critical(None, "エラー", f"国家リスト画面の表示中にエラーが発生しました：\n{str(e)}")

    def show_nation_details(self, nation_tag):
        """国家詳細画面を表示"""
        try:
            if not self.nation_details_view:
                self.nation_details_view = NationDetailsView(parent=self.main_window, app_controller=self)
            self.main_window.setCentralWidget(self.nation_details_view)
            self.nation_details_view.load_nation_data(nation_tag)
        except Exception as e:
            QMessageBox.critical(None, "エラー", f"国家詳細画面の表示中にエラーが発生しました：\n{str(e)}")

    def show_equipment_form(self, equipment_data):
        """装備フォームを表示"""
        try:
            if not self.equipment_form:
                self.equipment_form = EquipmentForm(parent=self.main_window, app_controller=self)
            self.equipment_form.set_equipment_data(equipment_data)
            self.equipment_form.show()
        except Exception as e:
            QMessageBox.critical(None, "エラー", f"装備フォームの表示中にエラーが発生しました：\n{str(e)}")

    def show_hull_form(self, hull_data):
        """船体フォームを表示"""
        try:
            if not self.hull_form:
                self.hull_form = HullForm(parent=self.main_window, app_controller=self)
            self.hull_form.set_hull_data(hull_data)
            self.hull_form.show()
        except Exception as e:
            QMessageBox.critical(None, "エラー", f"船体フォームの表示中にエラーが発生しました：\n{str(e)}")

    def show_design_view(self, design_data):
        """設計ビューを表示"""
        try:
            if not self.design_view:
                self.design_view = DesignView(parent=self.main_window, app_controller=self)
            self.design_view.set_design_data(design_data)
            self.design_view.show()
        except Exception as e:
            QMessageBox.critical(None, "エラー", f"設計ビューの表示中にエラーが発生しました：\n{str(e)}")

    def show_mod_formation_view(self, formation_data):
        """mod内の編成ビューを表示"""
        try:
            if not self.mod_formation_view:
                self.mod_formation_view = ModFormationView(parent=self.main_window, app_controller=self)
            self.mod_formation_view.set_formation_data(formation_data)
            self.mod_formation_view.show()
        except Exception as e:
            QMessageBox.critical(None, "エラー", f"mod内の編成ビューの表示中にエラーが発生しました：\n{str(e)}")

    def get_current_mod(self):
        """現在選択されているMODを取得"""
        return self.current_mod

    def set_current_mod(self, mod_data):
        """現在選択されているMODを設定"""
        self.current_mod = mod_data

    def get_nations(self, mod_path):
        """国家リストを取得"""
        try:
            nations = []
            # 国家ファイルのディレクトリパス
            countries_dir = os.path.join(mod_path, "common", "countries")
            
            # ディレクトリ内の全ファイルを処理
            if os.path.exists(countries_dir):
                for filename in os.listdir(countries_dir):
                    if filename.endswith('.txt'):
                        # ファイル名から国家タグを取得
                        tag = os.path.splitext(filename)[0]
                        
                        # 国家名を取得
                        name = self.get_nation_name(tag, mod_path)
                        
                        nations.append({
                            'tag': tag,
                            'name': name
                        })
            
            return nations

        except Exception as e:
            QMessageBox.critical(None, "エラー", f"国家リストの取得中にエラーが発生しました：\n{str(e)}")
            return []

    def get_nation_name(self, tag, mod_path):
        """国家名を取得"""
        try:
            # ローカライズファイルのディレクトリパス
            localisation_dir = os.path.join(mod_path, "localisation")
            
            # ディレクトリ内の全ファイルを処理
            if os.path.exists(localisation_dir):
                for filename in os.listdir(localisation_dir):
                    if filename.endswith('.yml'):
                        file_path = os.path.join(localisation_dir, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.startswith(f"{tag}_name:"):
                                    # 国家名を抽出
                                    name = line.split(':', 1)[1].strip().strip('"')
                                    return name
            
            return tag

        except Exception as e:
            QMessageBox.critical(None, "エラー", f"国家名の取得中にエラーが発生しました：\n{str(e)}")
            return tag

    def get_nation_equipment(self, nation_tag):
        """国家の装備データを取得"""
        try:
            equipment_data = []
            if not self.current_mod or "path" not in self.current_mod:
                return equipment_data

            # 装備ファイルのディレクトリパス
            equipment_dir = os.path.join(self.current_mod["path"], "common", "units", "equipment")
            
            # ディレクトリ内の全ファイルを処理
            if os.path.exists(equipment_dir):
                for filename in os.listdir(equipment_dir):
                    if filename.endswith('.txt'):
                        file_path = os.path.join(equipment_dir, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            parser = EffectParser(f.read(), filename=file_path)
                            equipment_data.extend(parser.parse_equipment())

            return equipment_data

        except Exception as e:
            QMessageBox.critical(None, "エラー", f"装備データの取得中にエラーが発生しました：\n{str(e)}")
            return []

    def get_nation_hulls(self, nation_tag):
        """国家の船体データを取得"""
        try:
            hull_data = []
            if not self.current_mod or "path" not in self.current_mod:
                return hull_data

            # 船体ファイルのディレクトリパス
            hulls_dir = os.path.join(self.current_mod["path"], "common", "units", "equipment")
            
            # ディレクトリ内の全ファイルを処理
            if os.path.exists(hulls_dir):
                for filename in os.listdir(hulls_dir):
                    if filename.endswith('.txt'):
                        file_path = os.path.join(hulls_dir, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            parser = EffectParser(f.read(), filename=file_path)
                            hull_data.extend(parser.parse_hulls())

            return hull_data

        except Exception as e:
            QMessageBox.critical(None, "エラー", f"船体データの取得中にエラーが発生しました：\n{str(e)}")
            return []

    def get_nation_designs(self, nation_tag):
        """国家の設計データを取得"""
        try:
            design_data = []
            if not self.current_mod or "path" not in self.current_mod:
                return design_data

            # 設計ファイルのディレクトリパス
            designs_dir = os.path.join(self.current_mod["path"], "common", "units", "equipment")
            
            # ディレクトリ内の全ファイルを処理
            if os.path.exists(designs_dir):
                for filename in os.listdir(designs_dir):
                    if filename.endswith('.txt'):
                        file_path = os.path.join(designs_dir, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            parser = EffectParser(f.read(), filename=file_path)
                            design_data.extend(parser.parse_designs())

            return design_data

        except Exception as e:
            QMessageBox.critical(None, "エラー", f"設計データの取得中にエラーが発生しました：\n{str(e)}")
            return []

    def get_nation_mod_formations(self, nation_tag):
        """国家のmod内の編成データを取得"""
        try:
            formation_data = []
            if not self.current_mod or "path" not in self.current_mod:
                return formation_data

            # 編成ファイルのディレクトリパス
            formations_dir = os.path.join(self.current_mod["path"], "common", "units", "formations")
            
            # ディレクトリ内の全ファイルを処理
            if os.path.exists(formations_dir):
                for filename in os.listdir(formations_dir):
                    if filename.endswith('.txt'):
                        file_path = os.path.join(formations_dir, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            parser = EffectParser(f.read(), filename=file_path)
                            formation_data.extend(parser.parse_formations())

            return formation_data

        except Exception as e:
            QMessageBox.critical(None, "エラー", f"mod内の編成データの取得中にエラーが発生しました：\n{str(e)}")
            return []

    def load_fleet_data(self, nation_tag):
        """艦隊データを読み込む"""
        try:
            if not self.current_mod or "path" not in self.current_mod:
                return None

            # 艦隊データファイルのパス
            fleet_data_path = os.path.join(self.current_mod["path"], "common", "units", "fleet_data.json")
            
            if os.path.exists(fleet_data_path):
                with open(fleet_data_path, 'r', encoding='utf-8') as f:
                    fleet_data = json.load(f)
                    return fleet_data.get(nation_tag)
            
            return None

        except Exception as e:
            QMessageBox.critical(None, "エラー", f"艦隊データの読み込み中にエラーが発生しました：\n{str(e)}")
            return None 