import re
import ply.lex as lex
import ply.yacc as yacc

# --- カスタム例外の定義 ---
class ParserError(Exception):
    """カスタムパーサーエラー"""
    pass

# --- レクサー (Lexer) の定義 ---
tokens = (
    'LBRACE',    # {
    'RBRACE',    # }
    'EQUALS',    # =
    'IDENTIFIER', # 識別子
    'STRING',    # 文字列
    'NUMBER',    # 数字
)

# トークンルール
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_EQUALS = r'='
t_ignore = ' \t\n'

def t_IDENTIFIER(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    return t

def t_STRING(t):
    r'"[^"]*"'
    t.value = t.value[1:-1]  # 引用符を除去
    return t

def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

# コメントの処理
def t_COMMENT(t):
    r'\#.*'
    t.lexer.lineno += t.value.count('\n')  # コメント内の改行をカウント
    return None  # コメントは無視

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    if t.value[0] != '#':  # コメント以外の不正な文字の場合のみエラーを表示
        raise ParserError(f"不正な文字 '{t.value[0]}' が検出されました。位置: {t.lexpos}, 行: {t.lexer.lineno}")
    t.lexer.skip(1)

# レクサーの構築
lexer = lex.lex()

# --- パーサー (Parser) の定義 ---
def p_ship_names(p):
    '''ship_names : ship_name_block
                 | ship_names ship_name_block
                 | empty'''
    if len(p) == 2:
        if p[1] is None:
            p[0] = []
        else:
            p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

def p_ship_name_block(p):
    '''ship_name_block : IDENTIFIER EQUALS LBRACE block_content RBRACE'''
    p[0] = {
        'name': p[1],
        'content': p[4]
    }

def p_block_content(p):
    '''block_content : block_item
                    | block_content block_item
                    | empty'''
    if len(p) == 2:
        if p[1] is None:
            p[0] = {}
        else:
            p[0] = {p[1][0]: p[1][1]}
    else:
        p[0] = p[1]
        if p[2] is not None:
            p[0][p[2][0]] = p[2][1]

def p_block_item(p):
    '''block_item : IDENTIFIER EQUALS value
                 | IDENTIFIER EQUALS LBRACE value_list RBRACE'''
    if len(p) == 4:
        p[0] = (p[1], p[3])
    else:
        p[0] = (p[1], p[4])

def p_value(p):
    '''value : STRING
            | NUMBER
            | IDENTIFIER'''
    p[0] = p[1]

def p_value_list(p):
    '''value_list : value
                 | value_list value
                 | empty'''
    if len(p) == 2:
        if p[1] is None:
            p[0] = []
        else:
            p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

def p_empty(p):
    'empty :'
    p[0] = None

def p_error(p):
    if p:
        raise ParserError(f"構文エラー: '{p.value}' の位置で予期しないトークンが検出されました。")
    else:
        raise ParserError("構文エラー: 予期せぬファイル終端（EOF）が検出されました。")

# パーサーの構築
parser = yacc.yacc()

# --- ShipNameParser クラス ---
class ShipNameParser:
    def __init__(self, content, filename=None):
        # BOMを除去
        if content.startswith('\ufeff'):
            content = content[1:]
        self.content = content
        self.filename = filename
        self.ship_names = {}

    def parse(self):
        """艦船名をパースする"""
        try:
            result = parser.parse(self.content, lexer=lexer)
            if not result:
                return []

            return result

        except SyntaxError as e:
            raise ParserError(f"構文エラーによりパースに失敗しました: {str(e)}")
        except ParserError as e:
            raise e
        except Exception as e:
            raise ParserError(f"パース中に予期せぬエラーが発生しました: {str(e)}\nファイル: {self.filename}") 