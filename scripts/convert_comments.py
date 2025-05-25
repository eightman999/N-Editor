import re

def convert_comments(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 正規表現パターン
    pattern = r'(create_equipment_variant = {\n\s*)(#[^#\n]+)(\n\s*name = "[^"]+")'
    
    # 置換
    def replace_func(match):
        indent = match.group(1)
        comment = match.group(2).strip()
        name_line = match.group(3)
        return f"{indent}#@override.name(\"{comment[1:]}\"){name_line}"

    # 置換実行
    new_content = re.sub(pattern, replace_func, content)

    # 結果を保存
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

if __name__ == "__main__":
    file_path = "/Users/eightman/Documents/Paradox Interactive/Hearts of Iron IV/mod/SSW_mod/common/scripted_effects/_ssw_variants_navy.txt"
    convert_comments(file_path) 