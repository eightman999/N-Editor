# Copyright (c) eightman 2005-2025
# Rights reserved by Furin-lab
# 動作設計: StateParserファイルのパーサー
import re
import sys
import os
import threading
from ply import yacc
import ply.lex as lex

# Thread-local storage for parser and lexer instances
_thread_local = threading.local()

# --- カスタム例外の定義 ---
class ParserError(Exception):
    """カスタムパーサーエラー"""
    pass

# アプリケーションがフリーズされている（EXE化されている）かどうかを判定
def is_frozen():
    return getattr(sys, 'frozen', False)

# --- レクサー (Lexer) の定義 ---
tokens = (
    'ID',           # 識別子 (例: id, name, owner, infrastructure, ABA, THIS)
    'NUMBER',       # 数値 (整数または浮動小数点数)
    'DATE',         # 日付 (例: 1938.3.12)
    'STRING',       # 引用符で囲まれた文字列 (例: "STATE_367")
    'EQUALS',       # =
    'LBRACE',       # {
    'RBRACE',       # }
    'DOT',          # . (ドット区切りIDのため)
    'SPACE',        # スペース
)

# トークンの正規表現ルール
t_EQUALS = r'='
t_LBRACE = r'{'
t_RBRACE = r'}'
t_STRING = r'"[^\n"]*"'
t_DOT = r'\.'  # ドットの正規表現
t_SPACE = r'\s+'

# PLYのレクサーは、定義順が早いもの、またはより長いパターンを優先します。
def t_DATE(t):
    r'\d{4}\.\d{1,2}\.\d{1,2}'  # 日付形式 (例: 1938.3.12)
    t.value = str(t.value)  # 日付は文字列として保持
    return t

def t_NUMBER(t):
    r'[-+]?\d+\.\d*|[-+]?\d+'  # 浮動小数点数または整数
    if '.' in t.value:
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    return t

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    # NUMBERでマッチしなかったID（文字列識別子）のみがここに来る
    return t

# 無視する文字 (空白とタブ、キャリッジリターン)
t_ignore = ' \t\r'

# コメントの無視
def t_COMMENT(t):
    r'\#.*'
    pass  # コメントは何もしない

# 改行の処理 (行数を追跡するため)
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# エラーハンドリング
def t_error(t):
    print(f"Illegal character '{t.value[0]}' at line {t.lexer.lineno}, position {t.lexer.lexpos}")
    t.lexer.skip(1)



# --- パーサー (Parser) の定義 ---

# 構文規則の定義
def p_state_file(p):
    'state_file : KEY EQUALS LBRACE statements RBRACE'
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

# 新しいルール: キーはID、NUMBER、DATE、またはQUALIFIED_ID
def p_KEY(p):
    '''KEY : ID
           | NUMBER
           | DATE
           | QUALIFIED_ID'''
    p[0] = p[1]

# 新しいルール: ドット区切りのID (例: COR.pfk_state_array_1)
def p_QUALIFIED_ID(p):
    '''QUALIFIED_ID : ID DOT ID'''
    p[0] = f"{p[1]}.{p[3]}" # 'COR.pfk_state_array_1' のような文字列として結合

def p_statement(p):
    '''statement : KEY EQUALS value
                 | KEY EQUALS LBRACE add_to_array_content RBRACE'''
    if len(p) == 4:
        p[0] = {p[1]: p[3]}
    else:  # len(p) == 6
        p[0] = {p[1]: p[4]}

def p_value(p):
    '''value : ID
             | NUMBER
             | DATE
             | STRING
             | LBRACE block_content_inside RBRACE'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[2]

# ブロックの中身が 'statements' (key=value) か 'value_list' (value1 value2 ...) か
def p_block_content_inside(p):
    '''block_content_inside : statements
                            | value_list
                            | empty'''
    if len(p) == 2:
        p[0] = p[1]

def p_empty(p):
    'empty :'
    p[0] = {}

def p_value_list(p):
    '''value_list : value_item
                  | value_list value_item
                  | value_list SPACE value_item'''
    if len(p) == 2:
        p[0] = [p[1]]
    elif len(p) == 3:
        # value_list value_item
        if isinstance(p[1], list):
            p[0] = p[1] + [p[2]]
        else:
            p[0] = [p[1], p[2]]
    else:
        # value_list SPACE value_item
        if isinstance(p[1], list):
            p[0] = p[1] + [p[3]]
        else:
            p[0] = [p[1], p[3]]

def p_value_item(p):
    '''value_item : ID
                  | NUMBER
                  | DATE
                  | STRING
                  | QUALIFIED_ID'''
    p[0] = p[1]

def p_add_to_array_content(p):
    '''add_to_array_content : QUALIFIED_ID EQUALS ID'''
    p[0] = {p[1]: p[3]}

# エラーハンドリング
def p_error(p):
    if p:
        # より詳細なエラー情報を提供
        error_msg = f"Syntax error at token '{p.value}' (type: {p.type}) at line {p.lineno}, position {p.lexpos}"
        
        # パーサースタックの状態情報も表示（デバッグ用）
        if hasattr(p.lexer, 'lexdata'):
            # エラー位置周辺のコンテキストを表示
            start = max(0, p.lexpos - 50)
            end = min(len(p.lexer.lexdata), p.lexpos + 50)
            context = p.lexer.lexdata[start:end]
            error_msg += f"\nContext: ...{context}..."
        
        print(error_msg)
        raise SyntaxError(f"Parsing failed due to syntax error: {error_msg}")
    else:
        error_msg = "Syntax error at EOF (Unexpected end of file)."
        print(error_msg)
        raise SyntaxError(f"Parsing failed due to syntax error: {error_msg}")

class StateParser:
    def __init__(self, content):
        self.content = content
        self.known_province_ids = set()

    def parse(self):
        try:
            parser_instance, lexer_instance = _get_thread_parser()
            lexer_instance.lineno = 1
            raw_parsed_data = parser_instance.parse(self.content, lexer=lexer_instance)

            final_data = {}

            for key in ['id', 'name', 'manpower', 'state_category', 'local_supplies', 'buildings_max_level_factor']:
                if key in raw_parsed_data:
                    final_data[key] = raw_parsed_data[key]

            if 'provinces' in raw_parsed_data:
                prov_list = raw_parsed_data['provinces']
                if isinstance(prov_list, list):
                    # リストの要素が int または str で、かつ str の場合は数字のみか確認
                    final_data['provinces'] = [int(p) for p in prov_list if isinstance(p, (int, str)) and (isinstance(p, int) or str(p).isdigit())]
                else:
                    # 単一の要素がパースされた場合
                    final_data['provinces'] = [int(prov_list)] if isinstance(prov_list, (int, str)) and (isinstance(prov_list, int) or str(prov_list).isdigit()) else []
                self.known_province_ids.update(final_data['provinces'])

            if 'history' in raw_parsed_data and isinstance(raw_parsed_data['history'], dict):
                history_data = raw_parsed_data['history']

                for key in ['owner', 'add_core_of', 'add_claim_by', 'add_to_array']:
                    if key in history_data:
                        if key == 'add_core_of':
                            # add_core_ofは複数回出現する可能性があるため、リストとして処理
                            if key not in final_data:
                                final_data[key] = []
                            if isinstance(history_data[key], list):
                                final_data[key].extend(history_data[key])
                            else:
                                final_data[key].append(history_data[key])
                        else:
                            final_data[key] = history_data[key]

                final_data['buildings'] = {}
                final_data['province_buildings'] = {}

                if 'buildings' in history_data and isinstance(history_data['buildings'], dict):
                    for key, value in history_data['buildings'].items():
                        try:
                            # buildingsブロックのキーはIDまたはNUMBERとしてパースされる
                            int_key = int(key)
                            if int_key in self.known_province_ids:
                                final_data['province_buildings'][int_key] = value
                            else:
                                final_data['buildings'][key] = value
                        except (ValueError, TypeError):
                            final_data['buildings'][key] = value

                final_data['victory_points'] = []
                if 'victory_points' in history_data:
                    vp_raw = history_data['victory_points']

                    # vp_raw が単一の要素（リストではない）の場合も、ループ処理のためにリスト化する
                    if not isinstance(vp_raw, list):
                        vp_raw = [vp_raw]

                    # 勝利点のペアを収集するためのリスト
                    collected_vp_pairs = []

                    # 数値のリストとして処理
                    if isinstance(vp_raw, list):
                        # 平坦化されたリストを処理
                        flat_list = []
                        for item in vp_raw:
                            if isinstance(item, list):
                                flat_list.extend(item)
                            else:
                                flat_list.append(item)

                        # 要素数が偶数ならペアのリストとして処理
                        if len(flat_list) % 2 == 0:
                            for i in range(0, len(flat_list), 2):
                                province_id = flat_list[i]
                                value = flat_list[i+1]
                                if isinstance(province_id, (int, str)) and isinstance(value, (int, str)):
                                    collected_vp_pairs.append({
                                        'province': int(province_id),
                                        'value': int(value)
                                    })
                                else:
                                    print(f"Warning: Unexpected victory_points element type: {flat_list[i:i+2]}")
                        else:
                            print(f"Warning: Incomplete victory_points list format (odd number of elements): {flat_list}")
                    else:
                        # 既存の処理を維持（後方互換性のため）
                        for vp_item_candidate in vp_raw:
                            if isinstance(vp_item_candidate, list):
                                if len(vp_item_candidate) % 2 == 0:
                                    for i in range(0, len(vp_item_candidate), 2):
                                        province_id = vp_item_candidate[i]
                                        value = vp_item_candidate[i+1]
                                        if isinstance(province_id, (int, str)) and isinstance(value, (int, str)):
                                            collected_vp_pairs.append({
                                                'province': int(province_id),
                                                'value': int(value)
                                            })
                                        else:
                                            print(f"Warning: Unexpected victory_points element type in list: {vp_item_candidate[i:i+2]}")
                                else:
                                    print(f"Warning: Incomplete victory_points list format (odd number of elements): {vp_item_candidate}")
                            elif isinstance(vp_item_candidate, dict) and len(vp_item_candidate) == 1:
                                prov_id_str = list(vp_item_candidate.keys())[0]
                                value = vp_item_candidate[prov_id_str]
                                if isinstance(prov_id_str, (int, str)) and isinstance(value, (int, str)):
                                    collected_vp_pairs.append({
                                        'province': int(prov_id_str),
                                        'value': int(value)
                                    })
                                else:
                                    print(f"Warning: Unexpected victory_points dict element type: {vp_item_candidate}")
                            else:
                                print(f"Warning: Unexpected victory_points format: {vp_item_candidate}")

                    # 収集したペアを最終データに格納
                    final_data['victory_points'] = collected_vp_pairs

                processed_history_keys = ['owner', 'add_core_of', 'add_claim_by', 'buildings', 'victory_points', 'add_to_array']
                for key, value in history_data.items():
                    if key not in processed_history_keys:
                        # 日付キー（例: "1938.3.12"）の処理
                        if isinstance(key, str) and '.' in key and key.replace('.', '').isdigit():
                            if 'dated_events' not in final_data:
                                final_data['dated_events'] = {}
                            final_data['dated_events'][key] = value
                        elif isinstance(value, dict):
                            if 'other_history_blocks' not in final_data:
                                final_data['other_history_blocks'] = {}
                            final_data['other_history_blocks'][key] = value

            return final_data

        except SyntaxError as e:
            raise ParserError(f"Parsing failed due to syntax error: {e}")
        except Exception as e:
            raise ParserError(f"An unexpected error occurred during parsing: {e}")

# パーサーの構築設定
# Find the absolute path to the directory containing this script
current_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = current_dir
tab_module = "state_parsetab"

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
        def write(self, *args, **kwargs):
            pass
        def flush(self, *args, **kwargs):
            pass
    error_logger = SimpleNullLogger()


def _create_parser_and_lexer():
    """Create a new parser and lexer instance."""
    lexer_instance = lex.lex()
    parser_instance = yacc.yacc(
        outputdir=output_dir,
        tabmodule=tab_module,
        debug=False,
        write_tables=not is_frozen(),
        debuglog=None,
        errorlog=error_logger,
    )
    return parser_instance, lexer_instance


def _get_thread_parser():
    """Return parser and lexer instances specific to the current thread."""
    if not hasattr(_thread_local, "parser"):
        _thread_local.parser, _thread_local.lexer = _create_parser_and_lexer()
    return _thread_local.parser, _thread_local.lexer
