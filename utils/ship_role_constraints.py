# -*- coding: utf-8 -*-
"""
船体種別とロール種別の制約マッピング
ship_type:role_typeで利用可能なロール種別を定義
"""

# ship_type : 利用可能なrole_typeのリスト
SHIP_ROLE_CONSTRAINTS = {
    "BB": [  # 一等戦艦
        "BB", "B", "BC", "FBB", "BBG", "SB", "PB", "IC", "ACR", "CDB", "CA", "CB", "BM", "CG"
    ],
    "BC": [  # 二等戦艦
        "BC", "CB", "CA", "CG", "PB", "B", "FBB", "BB"
    ],
    "BF": [  # 航空戦艦（バトルキャリア）──► **BF のみ**
        "BF"
    ],
    "CDB": [  # 海防戦艦
        "CDB", "IC", "B", "BM", "PB", "CA"
    ],
    "CB": [  # 大型巡洋艦
        "CB", "CA", "CG", "PB", "BC"
    ],
    "CA": [  # 一等巡洋艦
        "CA", "CB", "CG", "CL", "C", "CM", "CS", "HTC", "TC", "TCL"
    ],
    "CL": [  # 二等巡洋艦
        "CL", "C", "CM", "CS", "HTC", "TC", "TCL", "FF", "PF", "K"
    ],
    "MC": [  # 特設巡洋艦
        "AC", "AG", "AAA", "AAG", "AAM", "AAS", "AAV", "AMS", "APC", "APS", "CAM", "MAC", "CM", "CS", "CL", "C"
    ],
    "DD": [  # 一等駆逐艦
        "DD", "D", "DDE", "DDG", "DDR", "DL", "DE", "DM", "DMS", "DB", "AM", "CMC", "MCM", "MCS", "PC", "PT", "TB"
    ],
    "DE": [  # 二等駆逐艦
        "DE", "D", "DDE", "DB", "DM", "DMS", "AM", "CMC", "MCM", "MCS", "PC", "PT", "TB"
    ],
    "FF": [  # フリゲート
        "FF", "PF", "PC", "PG", "K", "MB", "AM", "CMC", "MCM", "MCS", "PT", "TB"
    ],
    "K": [   # コルベット
        "K", "PC", "PT", "MB", "TB", "AM", "CMC", "MCM", "MCS", "LCSL"
    ],
    "FAV": [  # 一等補助艦
        "APB", "PL", "PLH", "PM", "WHEC", "LCSL", "MAC", "CAM", "AAA", "AAG", "AAM", "AAS", "AAV", "AMS"
    ],
    "SAV": [  # 二等補助艦
        "APB", "PL", "PLH", "PM", "WHEC", "LCSL", "AM", "CMC", "MCM", "MCS", "AAA", "AAG", "AAM", "AAS", "AAV", "AMS"
    ],
    "TAV": [  # 三等補助艦
        "AM", "CMC", "MCM", "MCS", "LCSL", "PC", "PT", "TB", "PL", "PM", "MAC", "APS", "APC"
    ],
    "CC": [  # 戦闘艇
        "PC", "PT", "MB", "TB", "K", "FF"
    ],
    "AV": [  # 水上機母艦
        "AV", "SV", "CVE"
    ],
    "CV": [  # 一等空母
        "CV", "CVE", "CVL", "CVS", "AV", "SV"
    ],
    "CVL": [ # 二等空母
        "CVL", "CVE", "CVS", "AV", "SV"
    ],
    "CF": [  # 航空巡洋艦 ──► **CF のみ**
        "CF"
    ],
    "FS": [  # 一等潜水艦
        "SF", "SC", "SM", "SS", "CSS"
    ],
    "SS": [  # 二等潜水艦
        "SS", "CSS", "SM", "MSM", "SF"
    ],
    "SCV": [ # 潜水空母 ──► **SCV のみ**
        "SCV"
    ]
}

def get_allowed_roles(ship_type):
    """
    指定されたship_typeで利用可能なrole_typeのリストを取得
    
    Args:
        ship_type (str): 船体種別
        
    Returns:
        list: 利用可能なrole_typeのリスト
    """
    return SHIP_ROLE_CONSTRAINTS.get(ship_type, [])

def is_role_allowed(ship_type, role_type):
    """
    指定されたship_typeでrole_typeが利用可能かをチェック
    
    Args:
        ship_type (str): 船体種別
        role_type (str): ロール種別
        
    Returns:
        bool: 利用可能な場合True
    """
    allowed_roles = get_allowed_roles(ship_type)
    return role_type in allowed_roles

def get_ship_type_from_role_display(role_display):
    """
    ロール表示名（例: "BB - 戦艦"）からロール略称（例: "BB"）を抽出
    
    Args:
        role_display (str): ロール表示名
        
    Returns:
        str: ロール略称
    """
    if " - " in role_display:
        return role_display.split(" - ")[0]
    return role_display

def get_ship_types_for_role(role_type):
    """
    指定されたrole_typeを利用可能なship_typeのリストを取得（逆引き）
    
    Args:
        role_type (str): ロール種別
        
    Returns:
        list: 利用可能なship_typeのリスト
    """
    compatible_ship_types = []
    for ship_type, allowed_roles in SHIP_ROLE_CONSTRAINTS.items():
        if role_type in allowed_roles:
            compatible_ship_types.append(ship_type)
    return compatible_ship_types

def get_constraint_info():
    """
    制約情報を取得（デバッグ用）
    
    Returns:
        dict: 制約情報
    """
    info = {}
    for ship_type, roles in SHIP_ROLE_CONSTRAINTS.items():
        info[ship_type] = {
            "allowed_roles": roles,
            "count": len(roles)
        }
    return info