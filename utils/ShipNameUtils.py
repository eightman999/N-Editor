import os
from ..parser.ShipNamePlyParser import ShipNamePlyParser

class ShipNameUtils:
    """艦船名を処理するためのユーティリティクラス"""

    def __init__(self, mod_path):
        self.mod_path = mod_path
        self.ship_names_path = os.path.join(mod_path, "common", "units", "names_ships")
        self.parsed_data = {}

    def load_ship_names(self):
        """艦船名ファイルを読み込む"""
        if not os.path.exists(self.ship_names_path):
            print(f"艦船名ディレクトリが見つかりません: {self.ship_names_path}")
            return

        for filename in os.listdir(self.ship_names_path):
            if filename.endswith(".txt"):
                file_path = os.path.join(self.ship_names_path, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    parser = ShipNamePlyParser(content, filename)
                    result = parser.parse()
                    if result:
                        self.parsed_data[filename] = result

    def get_ship_names_for_country(self, country_tag):
        """指定された国家タグの艦船名を取得"""
        ship_names = {}
        for filename, data in self.parsed_data.items():
            for block in data:
                if 'for_countries' in block['content']:
                    countries = block['content']['for_countries']
                    if country_tag in countries:
                        ship_names[block['name']] = block['content']
        return ship_names 