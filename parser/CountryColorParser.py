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
    'ID',           # 識別子 (例: color, HSV, rgb)
    'NUMBER',       # 数値 (整数または浮動小数点数)
    'EQUALS',       # =
    'LBRACE',       # {
    'RBRACE',       # }
    'COLOR',        # color
    'COLOR_UI',     # color_ui
    'HSV',          # HSV
    'RGB',          # rgb
)

# トークンの正規表現ルール
t_EQUALS = r'='
t_LBRACE = r'{'
t_RBRACE = r'}'

# 予約語の定義
reserved = {
    'color': 'COLOR',
    'color_ui': 'COLOR_UI',
    'HSV': 'HSV',
    'rgb': 'RGB'
}

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value, 'ID')
    return t

def t_NUMBER(t):
    r'[-+]?\d+\.\d*|[-+]?\d+' # 浮動小数点数または整数
    if '.' in t.value:
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    return t

# 無視する文字 (空白とタブ、キャリッジリターン)
t_ignore = ' \t\r'

# コメントの無視
def t_COMMENT(t):
    r'\#.*'
    pass # コメントは何もしない

# 改行の処理 (行数を追跡するため)
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

def p_country_file(p):
    '''country_file : country_blocks'''
    p[0] = p[1]

def p_country_blocks(p):
    '''country_blocks : country_block
                     | country_blocks country_block'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = {**p[1], **p[2]}

def p_country_block(p):
    'country_block : ID EQUALS LBRACE color_defs RBRACE'
    p[0] = {p[1]: p[4]}

def p_color_defs(p):
    '''color_defs : color_def
                 | color_defs color_def'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = {**p[1], **p[2]}

def p_color_def(p):
    '''color_def : COLOR EQUALS color_value
                | COLOR_UI EQUALS color_value'''
    p[0] = {p[1]: p[3]}

def p_color_value(p):
    '''color_value : HSV LBRACE NUMBER NUMBER NUMBER RBRACE
                  | RGB LBRACE NUMBER NUMBER NUMBER RBRACE'''
    if p[1] == 'HSV':
        p[0] = _hsv_to_rgb(p[3], p[4], p[5])
    else:  # RGB
        p[0] = (p[3], p[4], p[5])

def p_error(p):
    if p:
        print(f"Syntax error at token '{p.value}' (type: {p.type}) at line {p.lineno}, index {p.lexpos}")
    else:
        print("Syntax error at EOF (Unexpected end of file).")
    raise SyntaxError("Parsing failed due to syntax error.")

def _hsv_to_rgb(h, s, v):
    if s == 0.0:
        return (int(v * 255), int(v * 255), int(v * 255))
    
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i % 6

    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q

    return (int(r * 255), int(g * 255), int(b * 255))

class CountryColorParser:
    def __init__(self, content):
        self.content = content

    def parse(self):
        try:
            result = parser.parse(self.content, lexer=lexer)
            # color_uiを除外し、colorのみを返す
            return {country: {'color': data['color']} for country, data in result.items()}
        except SyntaxError as e:
            raise ParserError(f"Parsing failed due to syntax error: {e}")
        except Exception as e:
            raise ParserError(f"An unexpected error occurred during parsing: {e}")

# パーサーの構築
# Find the absolute path to the directory containing this script
current_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = current_dir
tab_module = "country_color_parsetab"

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
    print(f"Error creating CountryColorParser: {e}")
    if is_frozen():
        print(f"PLY YACC Error in frozen app (CountryColorParser): {e}")
    raise 