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

class ProvinceCoordinates:
    """プロヴィンス中心座標データモデル"""
    
    def __init__(self, province_id, x, y):
        self.province_id = province_id
        self.x = x
        self.y = y
    
    def __repr__(self):
        return f"ProvinceCoordinates(id={self.province_id}, x={self.x}, y={self.y})"
    
    def to_tuple(self):
        """座標をタプルとして返す"""
        return (self.x, self.y)
    
    def distance_to(self, other_coords):
        """他の座標との距離を計算"""
        if isinstance(other_coords, tuple):
            other_x, other_y = other_coords
        elif isinstance(other_coords, ProvinceCoordinates):
            other_x, other_y = other_coords.x, other_coords.y
        else:
            raise ValueError("座標はタプルまたはProvinceCoordinatesオブジェクトである必要があります")
        
        return ((self.x - other_x) ** 2 + (self.y - other_y) ** 2) ** 0.5


class Ship:
    """HOI4海軍OOBファイル用の艦船データモデル"""
    
    def __init__(self, name="", definition="", equipment=None):
        self.name = name
        self.definition = definition
        self.equipment = equipment or {}
    
    def __repr__(self):
        return f"Ship(name='{self.name}', definition='{self.definition}')"


class TaskForce:
    """HOI4海軍OOBファイル用の任務部隊データモデル"""
    
    def __init__(self, name="", location="", ships=None):
        self.name = name
        self.location = location
        self.ships = ships or []
    
    def add_ship(self, ship):
        """艦船を任務部隊に追加"""
        if isinstance(ship, Ship):
            self.ships.append(ship)
        else:
            raise ValueError("Shipオブジェクトである必要があります")
    
    def __repr__(self):
        return f"TaskForce(name='{self.name}', location='{self.location}', ships={len(self.ships)})"


class Fleet:
    """HOI4海軍OOBファイル用の艦隊データモデル"""
    
    def __init__(self, name="", naval_base="", task_forces=None):
        self.name = name
        self.naval_base = naval_base
        self.task_forces = task_forces or []
    
    def add_task_force(self, task_force):
        """任務部隊を艦隊に追加"""
        if isinstance(task_force, TaskForce):
            self.task_forces.append(task_force)
        else:
            raise ValueError("TaskForceオブジェクトである必要があります")
    
    def get_total_ships(self):
        """艦隊内の総艦船数を取得"""
        return sum(len(tf.ships) for tf in self.task_forces)
    
    def __repr__(self):
        return f"Fleet(name='{self.name}', naval_base='{self.naval_base}', task_forces={len(self.task_forces)})"