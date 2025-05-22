import re
import ply.lex as lex
import ply.yacc as yacc

# --- カスタム例外の定義 ---
class ParserError(Exception):
    """カスタムパーサーエラー"""
    pass

# --- レクサー (Lexer) の定義 ---
tokens = (
    'ID',           # 識別子 (例: id, name, provinces, weather)
    'NUMBER',       # 数値 (整数または浮動小数点数)
    'STRING',       # 引用符で囲まれた文字列
    'EQUALS',       # =
    'LBRACE',       # {
    'RBRACE',       # }
    'DOT',          # . (ドット区切りIDのため)
)

# トークンの正規表現ルール
t_EQUALS = r'='
t_LBRACE = r'{'
t_RBRACE = r'}'
t_STRING = r'"[^\n"]*"'
t_DOT = r'\.'

def t_NUMBER(t):
    r'[-+]?\d+\.\d*|[-+]?\d+'
    if '.' in t.value:
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    return t

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    return t

# 無視する文字
t_ignore = ' \t\r'

# コメントの無視
def t_COMMENT(t):
    r'\#.*'
    pass

# 改行の処理
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# エラーハンドリング
def t_error(t):
    print(f"Illegal character '{t.value[0]}' at line {t.lexer.lineno}, position {t.lexer.lexpos}")
    t.lexer.skip(1)

# レクサーの構築
lexer = lex.lex()

# --- パーサー (Parser) の定義 ---
def p_strategic_region(p):
    'strategic_region : ID EQUALS LBRACE statements RBRACE'
    p[0] = p[4]

def p_statements(p):
    '''statements : statement
                  | statements statement'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        result = {}
        if p[1]:
            for key, value in p[1].items():
                result[key] = value
        if p[2]:
            for key, value in p[2].items():
                if key in result:
                    if isinstance(result[key], list):
                        result[key].append(value)
                    else:
                        result[key] = [result[key], value]
                else:
                    result[key] = value
        p[0] = result

def p_statement(p):
    '''statement : ID EQUALS value'''
    p[0] = {p[1]: p[3]}

def p_value(p):
    '''value : ID
             | NUMBER
             | STRING
             | LBRACE block_content_inside RBRACE'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[2]

def p_block_content_inside(p):
    '''block_content_inside : statements
                           | value_list'''
    p[0] = p[1]

def p_value_list(p):
    '''value_list : value_item
                  | value_list value_item'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        if isinstance(p[1], list):
            p[0] = p[1] + [p[2]]
        else:
            p[0] = [p[1], p[2]]

def p_value_item(p):
    '''value_item : ID
                  | NUMBER
                  | STRING'''
    p[0] = p[1]

# エラーハンドリング
def p_error(p):
    if p:
        print(f"Syntax error at token '{p.value}' (type: {p.type}) at line {p.lineno}, index {p.lexpos}")
    else:
        print("Syntax error at EOF (Unexpected end of file).")
    raise SyntaxError("Parsing failed due to syntax error.")

# パーサーの構築
parser = yacc.yacc()

class StrategicRegionParser:
    def __init__(self, content):
        self.content = content

    def parse(self):
        try:
            raw_parsed_data = parser.parse(self.content, lexer=lexer)
            final_data = {}

            # 基本情報の処理
            for key in ['id', 'name']:
                if key in raw_parsed_data:
                    final_data[key] = raw_parsed_data[key]

            # 州IDリストの処理
            if 'provinces' in raw_parsed_data:
                prov_list = raw_parsed_data['provinces']
                if isinstance(prov_list, list):
                    final_data['provinces'] = [int(p) for p in prov_list if isinstance(p, (int, str)) and (isinstance(p, int) or str(p).isdigit())]
                else:
                    final_data['provinces'] = [int(prov_list)] if isinstance(prov_list, (int, str)) and (isinstance(prov_list, int) or str(prov_list).isdigit()) else []

            # 天気情報の処理
            if 'weather' in raw_parsed_data and isinstance(raw_parsed_data['weather'], dict):
                weather_data = raw_parsed_data['weather']
                final_data['weather'] = []
                
                if 'period' in weather_data:
                    periods = weather_data['period']
                    if not isinstance(periods, list):
                        periods = [periods]
                    
                    for period in periods:
                        if isinstance(period, dict):
                            weather_period = {}
                            for key, value in period.items():
                                if key == 'between' or key == 'temperature' or key == 'temperature_day_night':
                                    weather_period[key] = [float(v) for v in value] if isinstance(value, list) else float(value)
                                else:
                                    weather_period[key] = float(value) if isinstance(value, (int, float, str)) else value
                            final_data['weather'].append(weather_period)

            return final_data

        except SyntaxError as e:
            raise ParserError(f"Parsing failed due to syntax error: {e}")
        except Exception as e:
            raise ParserError(f"An unexpected error occurred during parsing: {e}") 