# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: StrategicRegionParserファイルのパーサー
import sys
import os
from ply import yacc
import ply.lex as lex
import re

# --- カスタム例外の定義 ---
class ParserError(Exception):
    """カスタムパーサーエラー"""
    pass

# アプリケーションがフリーズされている（EXE化されている）かどうかを判定
def is_frozen():
    return getattr(sys, 'frozen', False)

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
    # Get context around the error
    lines = t.lexer.lexdata.split('\n')
    current_line = t.lexer.lineno - 1 if t.lexer.lineno > 0 else 0
    if current_line < len(lines):
        line_content = lines[current_line]
        char_pos = t.lexer.lexpos - sum(len(line) + 1 for line in lines[:current_line])
        char_pos = max(0, char_pos)
        
        # Create a visual indicator of where the error occurred
        error_indicator = " " * char_pos + "^"
        print(f"Lexer error: Illegal character '{t.value[0]}' at line {t.lexer.lineno}, position {t.lexer.lexpos}")
        print(f"Line content: {line_content}")
        print(f"             {error_indicator}")
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
        # Get surrounding context for better error reporting
        lines = p.lexer.lexdata.split('\n')
        error_line = p.lineno - 1 if p.lineno > 0 else 0
        context_start = max(0, error_line - 2)
        context_end = min(len(lines), error_line + 3)
        
        context_lines = []
        for i in range(context_start, context_end):
            marker = " -> " if i == error_line else "    "
            context_lines.append(f"{marker}{i+1:3}: {lines[i]}")
        
        context = "\n".join(context_lines)
        error_msg = f"Syntax error at token '{p.value}' (type: {p.type}) at line {p.lineno}, position {p.lexpos}\n"
        error_msg += f"Context:\n{context}"
        raise SyntaxError(error_msg)
    else:
        raise SyntaxError("Syntax error at EOF (Unexpected end of file).")

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

# パーサーの構築
# Find the absolute path to the directory containing this script
current_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = current_dir
tab_module = "strategic_region_parsetab"

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
    print(f"Error creating StrategicRegionParser: {e}")
    if is_frozen():
        print(f"PLY YACC Error in frozen app (StrategicRegionParser): {e}")
    raise 