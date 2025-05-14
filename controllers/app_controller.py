# このファイルにはアプリケーションのロジックを定義します（将来的に）
class AppController:
    def __init__(self):
        self.equipments = []
        self.hulls = []

    def add_equipment(self, equipment):
        self.equipments.append(equipment)

    def add_hull(self, hull):
        self.hulls.append(hull)