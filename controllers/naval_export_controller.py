"""海軍編成データのHOI4形式書き出しコントローラー"""

import os
from models.data_models import Ship, TaskForce, Fleet


class NavalExportController:
    """HOI4海軍OOBファイル書き出し機能を提供するコントローラー"""
    
    def __init__(self):
        self.indent_level = 0
        self.indent_char = "\t"
    
    def export_to_hoi4_format(self, fleet_data, output_path):
        """海軍編成データをHOI4形式で書き出し
        
        Args:
            fleet_data (Fleet): 書き出し対象の艦隊データ
            output_path (str): 出力ファイルパス
            
        Returns:
            bool: 書き出し成功時True、失敗時False
        """
        try:
            validation_errors = self.validate_fleet_data(fleet_data)
            if validation_errors:
                raise ValueError(f"データ検証エラー: {', '.join(validation_errors)}")
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                self._write_units_block(f, fleet_data)
            
            return True
            
        except Exception as e:
            print(f"書き出しエラー: {e}")
            return False
    
    def _write_units_block(self, file, fleet_data):
        """unitsブロックの書き出し"""
        file.write("units = {\n")
        self.indent_level += 1
        self._write_fleet_block(file, fleet_data)
        self.indent_level -= 1
        file.write("}\n")
    
    def _write_fleet_block(self, file, fleet):
        """fleetブロックの書き出し"""
        self._write_line(file, "fleet = {")
        self.indent_level += 1
        self._write_line(file, f'name = "{self._escape_string(fleet.name)}"')
        self._write_line(file, f"naval_base = {fleet.naval_base}")
        
        for task_force in fleet.task_forces:
            self._write_task_force_block(file, task_force)
        
        self.indent_level -= 1
        self._write_line(file, "}")
    
    def _write_task_force_block(self, file, task_force):
        """task_forceブロックの書き出し"""
        self._write_line(file, "task_force = {")
        self.indent_level += 1
        self._write_line(file, f'name = "{self._escape_string(task_force.name)}"')
        self._write_line(file, f"location = {task_force.location}")
        
        for ship in task_force.ships:
            self._write_ship_block(file, ship)
        
        self.indent_level -= 1
        self._write_line(file, "}")
    
    def _write_ship_block(self, file, ship):
        """shipブロックの書き出し"""
        self._write_line(file, "ship = {")
        self.indent_level += 1
        self._write_line(file, f'name = "{self._escape_string(ship.name)}"')
        self._write_line(file, f"definition = {ship.definition}")
        
        if ship.equipment:
            self._write_equipment_block(file, ship.equipment)
        
        self.indent_level -= 1
        self._write_line(file, "}")
    
    def _write_equipment_block(self, file, equipment):
        """equipmentブロックの書き出し"""
        self._write_line(file, "equipment = {")
        self.indent_level += 1
        
        for hull_type, hull_data in equipment.items():
            self._write_line(file, f"{hull_type} = {{")
            self.indent_level += 1
            self._write_line(file, f"amount = {hull_data.get('amount', 1)}")
            self._write_line(file, f"owner = {hull_data.get('owner', 'ALB')}")
            version_name = hull_data.get('version_name', '')
            self._write_line(file, f'version_name = "{self._escape_string(version_name)}"')
            self.indent_level -= 1
            self._write_line(file, "}")
        
        self.indent_level -= 1
        self._write_line(file, "}")
    
    def _write_line(self, file, content):
        """インデント付きで行を書き出し"""
        indent = self.indent_char * self.indent_level
        file.write(f"{indent}{content}\n")
    
    def _escape_string(self, text):
        """文字列のエスケープ処理"""
        if not isinstance(text, str):
            return str(text)
        return text.replace('"', '\\"').replace('\\', '\\\\')
    
    def validate_fleet_data(self, fleet):
        """書き出し前のデータ検証
        
        Args:
            fleet (Fleet): 検証対象の艦隊データ
            
        Returns:
            list: 検証エラーのリスト（エラーがない場合は空リスト）
        """
        errors = []
        
        if not isinstance(fleet, Fleet):
            errors.append("Fleet オブジェクトではありません")
            return errors
        
        if not fleet.name.strip():
            errors.append("艦隊名が設定されていません")
        
        if not fleet.naval_base:
            errors.append("海軍基地が設定されていません")
        
        if not fleet.task_forces:
            errors.append("任務部隊が設定されていません")
        
        for i, tf in enumerate(fleet.task_forces):
            if not isinstance(tf, TaskForce):
                errors.append(f"任務部隊 {i+1} が TaskForce オブジェクトではありません")
                continue
                
            if not tf.name.strip():
                errors.append(f"任務部隊 {i+1} の名前が設定されていません")
            
            if not tf.location:
                errors.append(f"任務部隊 '{tf.name}' の配置場所が設定されていません")
            
            if not tf.ships:
                errors.append(f"任務部隊 '{tf.name}' に艦船が設定されていません")
            
            for j, ship in enumerate(tf.ships):
                if not isinstance(ship, Ship):
                    errors.append(f"任務部隊 '{tf.name}' の艦船 {j+1} が Ship オブジェクトではありません")
                    continue
                    
                if not ship.name.strip():
                    errors.append(f"任務部隊 '{tf.name}' の艦船 {j+1} の名前が設定されていません")
                
                if not ship.definition:
                    errors.append(f"艦船 '{ship.name}' の艦種が設定されていません")
        
        return errors
    
    def create_sample_fleet(self):
        """サンプル艦隊データを作成（テスト用）
        
        Returns:
            Fleet: サンプル艦隊データ
        """
        ship1 = Ship(
            name="IJN Yamato",
            definition="battleship",
            equipment={
                "battleship_1": {
                    "amount": 1,
                    "owner": "JAP",
                    "version_name": "Yamato Class"
                }
            }
        )
        
        ship2 = Ship(
            name="IJN Musashi",
            definition="battleship",
            equipment={
                "battleship_1": {
                    "amount": 1,
                    "owner": "JAP",
                    "version_name": "Yamato Class"
                }
            }
        )
        
        task_force = TaskForce(
            name="第一戦艦部隊",
            location="6542",
            ships=[ship1, ship2]
        )
        
        fleet = Fleet(
            name="連合艦隊",
            naval_base="6542",
            task_forces=[task_force]
        )
        
        return fleet