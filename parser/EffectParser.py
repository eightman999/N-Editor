import re
import ply.lex as lex
import ply.yacc as yacc

# --- カスタム例外の定義 ---
class ParserError(Exception):
    """カスタムパーサーエラー"""
    pass

# --- レクサー (Lexer) の定義 ---
tokens = (
    'ID',           # 識別子 (例: id, name, owner, infrastructure, ABA, THIS)
    'NUMBER',       # 数値 (整数または浮動小数点数)
    'STRING',       # 引用符で囲まれた文字列 (例: "STATE_367")
    'EQUALS',       # =
    'LBRACE',       # {
    'RBRACE',       # }
    'LPAREN',       # (
    'RPAREN',       # )
    'DOT',          # . (ドット区切りIDのため)
    'COLON',        # : (コロン区切りIDのため)
    'OVERRIDE',     # @override
    'COUNTRY',      # @COUNTRY
    'YES',          # yes
    'NO',           # no
)

# トークンの正規表現ルール
t_EQUALS = r'='
t_LBRACE = r'{'
t_RBRACE = r'}'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_STRING = r'"[^"]*"'
t_DOT = r'\.' # ドットの正規表現
t_COLON = r':'

def t_OVERRIDE(t):
    r'\#@override'
    return t

def t_COUNTRY(t):
    r'\#@COUNTRY'
    return t

def t_NUMBER(t):
    r'[-+]?\d+\.\d*|[-+]?\d+' # 浮動小数点数または整数
    if '.' in t.value:
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    return t

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    return t

def t_YES(t):
    r'yes'
    return t

def t_NO(t):
    r'no'
    return t

# 無視する文字 (空白とタブ、キャリッジリターン)
t_ignore = ' \t\r'

# コメントの無視
def t_COMMENT(t):
    r'\#(?!@).*'
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

def p_effect_file(p):
    '''effect_file : ID EQUALS LBRACE effect_content RBRACE
                  | ID EQUALS LBRACE country_tag effect_content RBRACE
                  | effect_file ID EQUALS LBRACE country_tag effect_content RBRACE'''
    if len(p) == 6:
        p[0] = {p[1]: {'content': p[4]}}
    elif len(p) == 7:
        p[0] = {p[1]: {'content': p[5], 'country_tag': p[4]}}
    else:
        # 複数のブロックの場合
        p[0] = p[1]
        p[0][p[2]] = {'content': p[6], 'country_tag': p[5]}

def p_country_tag(p):
    '''country_tag : COUNTRY EQUALS STRING'''
    p[0] = p[3].strip('"')

def p_effect_content(p):
    '''effect_content : effect_statement
                     | effect_content effect_statement'''
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

def p_effect_statement(p):
    '''effect_statement : ID EQUALS LBRACE variant_content RBRACE
                       | OVERRIDE DOT ID LPAREN STRING RPAREN EQUALS LBRACE variant_content RBRACE
                       | ID EQUALS value
                       | OVERRIDE DOT ID LPAREN STRING RPAREN'''
    if len(p) == 6:
        p[0] = {p[1]: p[4]}
    elif len(p) == 11:
        # オーバーライドの場合（完全な形式）
        override_key = p[3]
        override_value = p[5].strip('"')
        p[0] = {f"override_{override_key}": {'original_key': override_key, 'value': override_value, 'content': p[9]}}
    elif len(p) == 7:
        # オーバーライドの場合（短縮形式）
        override_key = p[3]
        override_value = p[5].strip('"')
        p[0] = {f"override_{override_key}": {'original_key': override_key, 'value': override_value}}
    else:
        p[0] = {p[1]: p[3]}

def p_variant_content(p):
    '''variant_content : variant_item
                      | variant_content variant_item
                      | OVERRIDE DOT ID LPAREN STRING RPAREN
                      | variant_content OVERRIDE DOT ID LPAREN STRING RPAREN'''
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 7:
        # オーバーライドの場合
        override_key = p[3]
        override_value = p[5].strip('"')
        p[0] = {f"override_{override_key}": {'original_key': override_key, 'value': override_value}}
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

def p_variant_item(p):
    '''variant_item : ID EQUALS value
                   | ID EQUALS LBRACE block_content RBRACE
                   | ID EQUALS yes_no'''
    if len(p) == 4:
        p[0] = {p[1]: p[3]}
    else:
        p[0] = {p[1]: p[4]}

def p_value(p):
    '''value : ID
             | NUMBER
             | STRING
             | ID COLON ID'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        # ID:ID の形式の場合（例：mio:mio_key）
        p[0] = f"{p[1]}:{p[3]}"

def p_block_content(p):
    '''block_content : block_item
                    | block_content block_item'''
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

def p_block_item(p):
    '''block_item : ID EQUALS value
                 | ID EQUALS LBRACE block_content RBRACE'''
    if len(p) == 4:
        p[0] = {p[1]: p[3]}
    else:
        p[0] = {p[1]: p[4]}

def p_yes_no(p):
    '''yes_no : YES
              | NO'''
    p[0] = p[1]

# エラーハンドリング
def p_error(p):
    if p:
        print(f"Syntax error at token '{p.value}' (type: {p.type}) at line {p.lineno}, index {p.lexpos}")
        print(f"Current file: {getattr(p.lexer, 'filename', 'unknown')}")
        print(f"Context: {p.lexer.lexdata[max(0, p.lexpos-50):p.lexpos+50]}")
    else:
        print("Syntax error at EOF (Unexpected end of file).")
    raise SyntaxError("Parsing failed due to syntax error.")

# パーサーの構築
parser = yacc.yacc()

# --- EffectParser クラス ---
class EffectParser:
    def __init__(self, content, filename=None):
        self.content = content
        self.filename = filename

    def parse(self):
        try:
            # レクサーにファイル名を設定
            lexer.filename = self.filename
            raw_parsed_data = parser.parse(self.content, lexer=lexer)
            
            # 最終的なデータ構造を整形
            final_data = {}
            
            # 最上位のキー（例：siam_navy）を取得
            top_key = list(raw_parsed_data.keys())[0]
            data = raw_parsed_data[top_key]
            
            # 国家タグがある場合は保存
            country_tag = data.get('country_tag')
            if country_tag:
                final_data['country_tag'] = country_tag
            
            variants = data['content']
            
            # create_equipment_variantの内容をnameを基準に辞書化
            for variant in variants.get('create_equipment_variant', []):
                if isinstance(variant, dict):
                    # オーバーライドの処理
                    for key, value in variant.items():
                        if key.startswith('override_'):
                            original_key = value['original_key']
                            override_value = value['value']
                            content = value.get('content')
                            
                            # オーバーライドされたキーと値、および元のキーを保存
                            variant[original_key] = override_value
                            if content:
                                variant[f'original_{original_key}'] = content
                            del variant[key]
                    
                    if 'name' in variant:
                        name = variant['name']
                        final_data[name] = variant
            
            return final_data

        except SyntaxError as e:
            raise ParserError(f"Parsing failed due to syntax error: {e}")
        except Exception as e:
            raise ParserError(f"An unexpected error occurred during parsing: {e}")

    def parse_designs(self):
        """設計データをパースして国家タグ別に集計する"""
        try:
            # レクサーにファイル名を設定
            lexer.filename = self.filename
            raw_parsed_data = parser.parse(self.content, lexer=lexer)
            designs_by_country = {}

            print("デバッグ: パース開始")
            # print(f"デバッグ: raw_parsed_data = {raw_parsed_data}")

            # 各設計データを処理
            for design_key, design_data in raw_parsed_data.items():
                country_tag = design_data.get('country_tag')
                if not country_tag:
                    continue

                if country_tag not in designs_by_country:
                    designs_by_country[country_tag] = {}

                variants = design_data['content'].get('create_equipment_variant', {})
                if isinstance(variants, dict):
                    # 単一の設計の場合
                    if 'name' in variants:
                        designs_by_country[country_tag][variants['name']] = variants
                elif isinstance(variants, list):
                    # 複数の設計の場合
                    for variant in variants:
                        if isinstance(variant, dict) and 'name' in variant:
                            designs_by_country[country_tag][variant['name']] = variant

            # print(f"デバッグ: designs_by_country = {designs_by_country}")
            return designs_by_country

        except SyntaxError as e:
            raise ParserError(f"設計データのパース中に構文エラーが発生しました: {e}")
        except Exception as e:
            raise ParserError(f"設計データのパース中に予期せぬエラーが発生しました: {e}")

    def print_design_counts(self):
        """各国の設計数を表示する"""
        try:
            designs_by_country = self.parse_designs()
            print("\n=== 各国の設計数 ===")
            for country, designs in designs_by_country.items():
                print(f"{country}: {len(designs)}設計")
            print("==================\n")
        except ParserError as e:
            print(f"エラー: {e}") 