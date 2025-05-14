# このファイルにはデータモデルを定義します（将来的に）
class Equipment:
    def __init__(self, name, type, properties):
        self.name = name
        self.type = type
        self.properties = properties

class Hull:
    def __init__(self, name, displacement, dimensions, properties):
        self.name = name
        self.displacement = displacement
        self.dimensions = dimensions
        self.properties = properties