# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: NavalOOBParserファイルのパーサー
import sys
import os
from ply import yacc
import ply.lex as lex


# --- カスタム例外の定義 ---
class ParserError(Exception):
    """カスタムパーサーエラー"""
    pass


# アプリケーションがフリーズされている（EXE化されている）かどうかを判定
def is_frozen():
    return getattr(sys, 'frozen', False)


# --- レクサー (Lexer) の定義 ---
tokens = (
    'ID',  # 識別子 (例: units, fleet, name, ALF)
    'NUMBER',  # 数値 (整数または浮動小数点数)
    'STRING',  # 引用符で囲まれた文字列 (例: "Task Force 77")
    'EQUALS',  # =
    'LBRACE',  # {
    'RBRACE',  # }
    'COLON',  # : (qualified_idのため: mio:ALF_San_Diego_naval_Shipyard)
    'YES',  # yes (pride_of_the_fleet = yes など)
    'NO',  # no
)

# トークンの正規表現ルール
t_EQUALS = r'='
t_LBRACE = r'{'
t_RBRACE = r'}'
t_COLON = r':'

# オーバーライド名を保持する変数
current_override_name = None

def t_NUMBER(t):
    r'[-+]?\d+\.\d*|[-+]?\d+'
    if '.' in t.value:
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    return t


def t_STRING(t):
    r'"[^"]*"'
    global current_override_name
    t.value = t.value[1:-1]  # 引用符を除去
    if current_override_name is not None:
        t.value = {'override': current_override_name}
        current_override_name = None
    return t


def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    # yes/noを明示的にトークンとして認識（pride_of_the_fleet = yes など）
    if t.value == 'yes':
        t.type = 'YES'
    elif t.value == 'no':
        t.type = 'NO'
    return t


# 無視する文字 (空白とタブ、キャリッジリターン)
t_ignore = ' \t\r'


# コメントの無視 (# から行末まで)
def t_COMMENT(t):
    r'\#.*'
    global current_override_name
    comment = t.value[1:].strip()  # '#'を除去して前後の空白を削除
    if comment.startswith('@override.name='):
        current_override_name = comment[40:]# '@override.name='の長さは15
    return None


# 改行の処理 (行数を追跡するため)
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


# エラーハンドリング
def t_error(t):
    print(f"Illegal character '{t.value[0]}' at line {t.lexer.lineno}")
    t.lexer.skip(1)


# レクサーの構築
lexer = lex.lex()


# --- パーサー (Parser) の定義 ---

def p_naval_file(p):
    '''naval_file : statements'''
    p[0] = p[1]


def p_statements(p):
    '''statements : statement
                  | statements statement
                  | empty'''
    if len(p) == 2:
        if p[1] is None:  # empty case
            p[0] = {}
        else:
            p[0] = p[1]
    else:
        result = {}
        if p[1]:
            for key, value in p[1].items():
                result[key] = value
        if p[2]:
            for key, value in p[2].items():
                if key in result:
                    # 同じキーが複数回現れる場合の処理
                    # 例: 複数のship、task_force、fleetブロック
                    # 或いは pride_of_the_fleet = yes の重複記述
                    if isinstance(result[key], list):
                        result[key].append(value)
                    else:
                        result[key] = [result[key], value]
                else:
                    result[key] = value
        p[0] = result


def p_statement(p):
    '''statement : ID EQUALS value
                 | ID EQUALS block'''
    global current_override_name
    if current_override_name is not None:
        # オーバーライド名が設定されている場合、値に適用
        if isinstance(p[3], str):
            p[3] = {'override': current_override_name}
        current_override_name = None
    p[0] = {p[1]: p[3]}


def p_value(p):
    '''value : ID
             | NUMBER
             | STRING
             | YES
             | NO
             | qualified_id'''
    p[0] = p[1]


def p_qualified_id(p):
    '''qualified_id : ID COLON ID'''
    # mio:ALF_San_Diego_naval_Shipyard のような形式
    p[0] = f"{p[1]}:{p[3]}"


def p_block(p):
    '''block : LBRACE statements RBRACE
             | LBRACE RBRACE'''
    if len(p) == 4:
        p[0] = p[2]
    else:
        p[0] = {}


def p_empty(p):
    '''empty :'''
    p[0] = None


def p_error(p):
    if p:
        print(f"Syntax error at token '{p.value}' (type: {p.type}) at line {p.lineno}")
    else:
        print("Syntax error at EOF")
    raise SyntaxError("Parsing failed")


class NavalOOBParser:
    def __init__(self, content):
        self.content = content
        global current_override_name
        current_override_name = None  # パーサーインスタンスごとにリセット

    def parse(self):
        """
        Naval OOBファイルをパースする

        Returns:
            dict: パースされたデータ構造

        Examples:
            pride_of_the_fleet = yes のような真偽値や、
            同じキーが複数回現れる場合（shipブロックの重複など）も適切に処理
        """
        try:
            global current_override_name
            current_override_name = None  # パース開始時にリセット
            result = parser.parse(self.content, lexer=lexer)
            return result
        except SyntaxError as e:
            raise ParserError(f"Parsing failed due to syntax error: {e}")
        except Exception as e:
            raise ParserError(f"An unexpected error occurred during parsing: {e}")

    def extract_fleets(self):
        """
        パースされたデータから艦隊情報を抽出する便利メソッド

        Returns:
            list: 艦隊データのリスト
        """
        try:
            parsed_data = self.parse()
            units = parsed_data.get('units', {})
            fleets = units.get('fleet', [])

            # fleetが単一の辞書の場合はリストに変換
            if isinstance(fleets, dict):
                fleets = [fleets]

            # 各艦隊の名前をオーバーライド名に置き換え
            for fleet in fleets:
                fleet_name = fleet.get('name', '')
                if isinstance(fleet_name, dict) and 'override' in fleet_name:
                    fleet['name'] = fleet_name['override']

                # 任務部隊の名前もオーバーライド名に置き換え
                task_forces = fleet.get('task_force', [])
                if isinstance(task_forces, dict):
                    task_forces = [task_forces]

                for task_force in task_forces:
                    task_force_name = task_force.get('name', '')
                    if isinstance(task_force_name, dict) and 'override' in task_force_name:
                        task_force['name'] = task_force_name['override']

                    # 艦艇の名前もオーバーライド名に置き換え
                    ships = task_force.get('ship', [])
                    if isinstance(ships, dict):
                        ships = [ships]

                    for ship in ships:
                        ship_name = ship.get('name', '')
                        if isinstance(ship_name, dict) and 'override' in ship_name:
                            ship['name'] = ship_name['override']

            return fleets
        except Exception as e:
            raise ParserError(f"Failed to extract fleet data: {e}")

    def extract_ships_with_pride(self):
        """
        pride_of_the_fleet = yes が設定された艦艇を抽出する

        Returns:
            list: プライド艦艇のリスト
        """
        try:
            fleets = self.extract_fleets()
            pride_ships = []

            for fleet in fleets:
                task_forces = fleet.get('task_force', [])
                if isinstance(task_forces, dict):
                    task_forces = [task_forces]

                for task_force in task_forces:
                    ships = task_force.get('ship', [])
                    if isinstance(ships, dict):
                        ships = [ships]

                    for ship in ships:
                        # pride_of_the_fleetがyesの場合（重複している場合は最後の値を使用）
                        pride_value = ship.get('pride_of_the_fleet')
                        if pride_value == 'yes' or (isinstance(pride_value, list) and 'yes' in pride_value):
                            # 艦艇名のオーバーライドを確認
                            ship_name = ship.get('name', '')
                            if isinstance(ship_name, dict) and 'override' in ship_name:
                                ship_name = ship_name['override']
                            
                            # 艦隊名のオーバーライドを確認
                            fleet_name = fleet.get('name', '')
                            if isinstance(fleet_name, dict) and 'override' in fleet_name:
                                fleet_name = fleet_name['override']
                            
                            # 任務部隊名のオーバーライドを確認
                            task_force_name = task_force.get('name', '')
                            if isinstance(task_force_name, dict) and 'override' in task_force_name:
                                task_force_name = task_force_name['override']
                            
                            pride_ships.append({
                                'name': ship_name,
                                'definition': ship.get('definition'),
                                'fleet': fleet_name,
                                'task_force': task_force_name
                            })

            return pride_ships
        except Exception as e:
            raise ParserError(f"Failed to extract pride ships: {e}")

    def extract_ships(self):
        """
        パースされたデータから艦艇情報を抽出する

        Returns:
            list: 艦艇データのリスト
        """
        try:
            fleets = self.extract_fleets()
            ships = []

            for fleet in fleets:
                # 艦隊名のオーバーライドを確認
                fleet_name = fleet.get('name', '')
                if isinstance(fleet_name, dict) and 'override' in fleet_name:
                    fleet_name = fleet_name['override']

                task_forces = fleet.get('task_force', [])
                if isinstance(task_forces, dict):
                    task_forces = [task_forces]

                for task_force in task_forces:
                    # 任務部隊名のオーバーライドを確認
                    task_force_name = task_force.get('name', '')
                    if isinstance(task_force_name, dict) and 'override' in task_force_name:
                        task_force_name = task_force_name['override']

                    fleet_ships = task_force.get('ship', [])
                    if isinstance(fleet_ships, dict):
                        fleet_ships = [fleet_ships]

                    for ship in fleet_ships:
                        # 艦艇名のオーバーライドを確認
                        ship_name = ship.get('name', '')
                        if isinstance(ship_name, dict) and 'override' in ship_name:
                            ship_name = ship_name['override']

                        # 設計名の取得（equipment内のversion_name）
                        design_name = ''
                        equipment = ship.get('equipment', {})
                        for hull_key, hull_data in equipment.items():
                            if isinstance(hull_data, dict):
                                version_name = hull_data.get('version_name', '')
                                if isinstance(version_name, dict) and 'override' in version_name:
                                    version_name = version_name['override']
                                if version_name:
                                    design_name = version_name
                                    break

                        # 艦艇データを構造化
                        ship_data = {
                            'name': ship_name,
                            'type': ship.get('definition', ''),
                            'design': design_name,
                            'fleet': fleet_name,
                            'task_force': task_force_name,
                            'data': ship
                        }
                        ships.append(ship_data)

            return ships
        except Exception as e:
            raise ParserError(f"Failed to extract ship data: {e}")

# パーサーの構築
# Find the absolute path to the directory containing this script
current_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = current_dir
tab_module = "naval_oob_parsetab"

# デバッグログとエラーログを無効化するためのロガーを取得
try:
    class SimpleNullLogger:
        def write(self, *args, **kwargs):
            pass
        def flush(self, *args, **kwargs):
            pass

    error_logger = yacc.NullLogger() if hasattr(yacc, 'NullLogger') else SimpleNullLogger()
except AttributeError:
    class SimpleNullLogger:
        def write(self, *args, **kwargs): pass
        def flush(self, *args, **kwargs): pass
    error_logger = SimpleNullLogger()

try:
    parser = yacc.yacc(
        outputdir=output_dir,
        tabmodule=tab_module,
        debug=False,
        write_tables=not is_frozen(),
        debuglog=None,
        errorlog=error_logger
    )
except Exception as e:
    print(f"Error creating NavalOOBParser: {e}")
    if is_frozen():
        print(f"PLY YACC Error in frozen app (NavalOOBParser): {e}")
    raise