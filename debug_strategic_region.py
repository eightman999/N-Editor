#!/usr/bin/env python3
"""
Debug script to identify the StrategicRegionParser issue
"""

import sys
import os
sys.path.append('/Users/eightman/Desktop/N-Editor')

from parser.StrategicRegionParser import StrategicRegionParser, lexer
import ply.lex as lex

def debug_lexer(content):
    """Debug the lexer output"""
    print("=== LEXER DEBUG ===")
    lexer.input(content)
    tokens = []
    while True:
        tok = lexer.token()
        if not tok:
            break
        tokens.append((tok.type, tok.value, tok.lineno, tok.lexpos))
        print(f"Token: {tok.type} = '{tok.value}' (line {tok.lineno}, pos {tok.lexpos})")
    return tokens

def test_strategic_region_file():
    """Test the actual problematic file"""
    file_path = "/Users/eightman/Documents/Paradox Interactive/Hearts of Iron IV/mod/SSW_mod/map/strategicregions/173-Eastern North Sea.txt"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        print(f"File size: {len(content)} characters")
        print(f"First 200 characters:\n{content[:200]}")
        print(f"Last 200 characters:\n{content[-200:]}")
        
        # Test lexer
        tokens = debug_lexer(content)
        print(f"\nTotal tokens: {len(tokens)}")
        
        # Test parser
        print("\n=== PARSER DEBUG ===")
        parser = StrategicRegionParser(content)
        result = parser.parse()
        print("✅ Parsing successful!")
        print(f"Result keys: {list(result.keys())}")
        
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_minimal_example():
    """Test with a minimal example that should work"""
    minimal_content = """strategic_region={
    id=173
    name="STRATEGICREGION_173"
    provinces={
        5 1227 2506
    }
    naval_terrain=water_shallow_sea
}"""
    
    print("\n=== MINIMAL EXAMPLE TEST ===")
    try:
        # Test lexer
        tokens = debug_lexer(minimal_content)
        print(f"Minimal tokens: {len(tokens)}")
        
        # Test parser
        parser = StrategicRegionParser(minimal_content)
        result = parser.parse()
        print("✅ Minimal parsing successful!")
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"❌ Minimal test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Debugging StrategicRegionParser...")
    test_minimal_example()
    test_strategic_region_file()