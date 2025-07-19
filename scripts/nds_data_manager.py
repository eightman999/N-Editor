# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: nds_data_managerスクリプト
import argparse
import json
import os
import sys
import uuid # ユニークID生成用

# N-EditorのルートディレクトリをPythonのパスに追加
# このスクリプトがN-Editorのルートディレクトリ直下のscripts/にあることを前提とする
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# N-Editorのモデルをインポート
try:
    from models.equipment_model import EquipmentModel
    from models.hull_model import HullModel
    from models.app_settings import AppSettings # data_dirを取得するために必要
except ImportError as e:
    print(f"Error importing N-Editor modules: {e}", file=sys.stderr)
    print("Please ensure this script is run from the N-Editor project root or its 'scripts' subdirectory.", file=sys.stderr)
    sys.exit(1)

def add_hull_data(hull_model: HullModel, hull_data: dict):
    """
    船体データをN-Editorシステムに追加するロジック。
    HullModelのsave_hullメソッドを呼び出す。
    """
    print(f"Attempting to add hull data: {hull_data}")
    try:
        # IDが提供されていない場合、新しいIDを生成
        if 'id' not in hull_data or not hull_data['id']:
            hull_data['id'] = str(uuid.uuid4())

        success = hull_model.save_hull(hull_data)
        if success:
            print(f"Hull added successfully with ID: {hull_data['id']}")
            return hull_data['id']
        else:
            print("Failed to add hull data.", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Failed to add hull data: {e}", file=sys.stderr)
        sys.exit(1)

def add_equipment_data(equipment_model: EquipmentModel, equipment_data: dict):
    """
    装備品データをN-Editorシステムに追加するロジック。
    EquipmentModelのsave_equipmentメソッドを呼び出す。
    """
    print(f"Attempting to add equipment data: {equipment_data}")
    try:
        # IDが提供されていない場合、新しいIDを生成
        # equipment_modelはcommon.IDを期待する
        if 'common' not in equipment_data:
            equipment_data['common'] = {}
        if 'ID' not in equipment_data['common'] or not equipment_data['common']['ID']:
            equipment_data['common']['ID'] = str(uuid.uuid4())

        # equipment_typeがcommon.カテゴリから取得されることを確認
        if 'カテゴリ' in equipment_data['common'] and 'equipment_type' not in equipment_data:
            equipment_data['equipment_type'] = equipment_data['common']['カテゴリ']

        success = equipment_model.save_equipment(equipment_data)
        if success:
            print(f"Equipment added successfully with ID: {equipment_data['common']['ID']}")
            return equipment_data['common']['ID']
        else:
            print("Failed to add equipment data.", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Failed to add equipment data: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Add hull or equipment data to N-Editor system.")
    parser.add_argument('--type', required=True, choices=['hull', 'equipment'],
                        help="Type of data to add: 'hull' or 'equipment'.")
    parser.add_argument('--data', required=True,
                        help="JSON string of the data to add.")

    args = parser.parse_args()

    try:
        data = json.loads(args.data)
    except json.JSONDecodeError:
        print("Error: --data argument must be a valid JSON string.", file=sys.stderr)
        sys.exit(1)

    # AppSettingsを初期化してデータディレクトリを取得
    try:
        app_settings = AppSettings()
        equipment_data_dir = app_settings.equipment_dir
        hull_data_dir = app_settings.hull_dir
    except Exception as e:
        print(f"Error initializing AppSettings: {e}", file=sys.stderr)
        sys.exit(1)

    if args.type == 'hull':
        hull_model = HullModel(data_dir=hull_data_dir)
        add_hull_data(hull_model, data)
    elif args.type == 'equipment':
        equipment_model = EquipmentModel(data_dir=equipment_data_dir)
        add_equipment_data(equipment_model, data)

if __name__ == "__main__":
    main()
