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