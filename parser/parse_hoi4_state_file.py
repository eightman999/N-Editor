import os
import os
# --- plyライブラリのインポート ---
import ply.lex as lex
import ply.yacc as yacc
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ".venv/lib/python3.13/site-packages/PyQt5/Qt5/plugins/platforms"
import os
import sys
import re
import json
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout,
                             QTextEdit, QFileDialog, QLabel, QMessageBox)
from PyQt5.QtCore import Qt

# --- PyQt5プラグインパスの設定 ---
try:
    base_path = os.path.dirname(sys.executable)
    plugin_path = os.path.join(base_path, "PyQt5", "Qt5", "plugins", "platforms")

    if not os.path.exists(plugin_path):
        site_packages_path = None
        for p in sys.path:
            if 'site-packages' in p and 'PyQt5' in p:
                site_packages_path = p
                break

        if site_packages_path:
            plugin_path = os.path.join(site_packages_path, "PyQt5", "Qt5", "plugins", "platforms")

    if os.path.exists(plugin_path):
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path
    else:
        print("Warning: Could not find PyQt5 platform plugins. GUI might not start correctly.")
        print(f"Attempted path: {plugin_path}")
except Exception as e:
    print(f"Error setting QT_QPA_PLATFORM_PLUGIN_PATH: {e}")

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
    'STRING',       # 引用符で囲まれた文字列 (例: "STATE_367")
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
t_DOT = r'\.' # ドットの正規表現

# PLYのレクサーは、定義順が早いもの、またはより長いパターンを優先します。
def t_NUMBER(t):
    r'[-+]?\d+\.\d*|[-+]?\d+' # 浮動小数点数または整数
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

# 新しいルール: キーはID、NUMBER、またはQUALIFIED_ID
def p_KEY(p):
    '''KEY : ID
           | NUMBER
           | QUALIFIED_ID'''
    p[0] = p[1]

# 新しいルール: ドット区切りのID (例: COR.pfk_state_array_1)
def p_QUALIFIED_ID(p):
    '''QUALIFIED_ID : ID DOT ID'''
    p[0] = f"{p[1]}.{p[3]}" # 'COR.pfk_state_array_1' のような文字列として結合

def p_statement(p):
    '''statement : KEY EQUALS value'''
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

# ブロックの中身が 'statements' (key=value) か 'value_list' (value1 value2 ...) か
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

# --- HOI4ParserPLY クラス (plyラッパーとデータ整形) ---
class HOI4ParserPLY:
    def __init__(self, content):
        self.content = content
        self.known_province_ids = set()

    def parse(self):
        try:
            raw_parsed_data = parser.parse(self.content, lexer=lexer)

            final_data = {}

            for key in ['id', 'name', 'manpower', 'state_category', 'local_supplies']:
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
                    if key not in processed_history_keys and isinstance(value, dict):
                        if 'other_history_blocks' not in final_data:
                            final_data['other_history_blocks'] = {}
                        final_data['other_history_blocks'][key] = value

            return final_data

        except SyntaxError as e:
            raise ParserError(f"Parsing failed due to syntax error: {e}")
        except Exception as e:
            raise ParserError(f"An unexpected error occurred during parsing: {e}")

# パーサーの構築
# Find the absolute path to the directory containing this script
current_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = current_dir
tab_module = "hoi4_state_parsetab"

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
    print(f"Error creating HOI4ParserPLY: {e}")
    if is_frozen():
        print(f"PLY YACC Error in frozen app (HOI4ParserPLY): {e}")
    raise

# --- Qt5 GUIアプリケーション ---
class StateParserApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('HOI4 State File Parser (PLY Lex/Yacc)')
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout()

        self.select_file_button = QPushButton('Select State File')
        self.select_file_button.clicked.connect(self.select_file)
        layout.addWidget(self.select_file_button)

        self.file_path_label = QLabel('No file selected.')
        layout.addWidget(self.file_path_label)

        self.result_text_edit = QTextEdit()
        self.result_text_edit.setReadOnly(True)
        layout.addWidget(self.result_text_edit)

        self.setLayout(layout)

    def select_file(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select HOI4 State File",
            "",
            "HOI4 State Files (*.txt);;All Files (*)",
            options=options
        )

        if file_path:
            self.file_path_label.setText(f"Selected file: {file_path}")
            self.parse_and_display_file(file_path)
        else:
            self.file_path_label.setText("No file selected.")
            self.result_text_edit.clear()

    def parse_and_display_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()

            parser_ply = HOI4ParserPLY(file_content)
            parsed_data = parser_ply.parse()

            self.result_text_edit.setText(json.dumps(parsed_data, indent=4, ensure_ascii=False))

        except FileNotFoundError:
            QMessageBox.critical(self, "Error", f"File not found at {file_path}")
            self.result_text_edit.setText(f"Error: File not found at {file_path}")
        except ParserError as e:
            QMessageBox.critical(self, "Parsing Error", f"Failed to parse file: {e}")
            self.result_text_edit.setText(f"Parsing Error: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred: {e}")
            self.result_text_edit.setText(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = StateParserApp()
    ex.show()
    sys.exit(app.exec_())