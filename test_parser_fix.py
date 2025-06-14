#!/usr/bin/env python3
"""
Test script to verify StateParser fixes
"""

# Test data that mimics the problematic state file
TEST_STATE_CONTENT = """state={
    id=86
    name="STATE_86"
    manpower = 2106500
    
    state_category = city
    history={
        owner = OZY
        victory_points = {
            6558 10
        }
        buildings = {
            infrastructure = 3
            industrial_complex = 1
            11232 = {
                bunker = 1
            }
            9532 = {
                bunker = 1
            }
            3381 = {
                bunker = 1
            }
            air_base = 3
        }
        add_core_of = OZY
        1938.3.12 = {
            add_claim_by = DEU
        }
    }

    provinces={
        17 388 3381 3460 3532 6558 9532 11232 11558 11478 13767
    }

    local_supplies=0.0 
    buildings_max_level_factor=1.0
}"""

def test_parser():
    """Test the StateParser with the fixed implementation"""
    print("Testing StateParser with DATE token support...")
    
    # Simple lexer test
    import sys
    import os
    sys.path.append('/Users/eightman/Desktop/N-Editor')
    
    try:
        from parser.StateParser import StateParser
        
        parser = StateParser(TEST_STATE_CONTENT)
        result = parser.parse()
        
        print("✅ Parsing successful!")
        print("\nParsed data structure:")
        
        # Check for specific fields
        expected_fields = ['id', 'name', 'manpower', 'state_category', 'provinces', 'local_supplies', 'buildings_max_level_factor']
        for field in expected_fields:
            if field in result:
                print(f"  ✅ {field}: {result[field]}")
            else:
                print(f"  ❌ Missing field: {field}")
        
        # Check for dated events
        if 'dated_events' in result:
            print(f"  ✅ dated_events: {result['dated_events']}")
        else:
            print("  ⚠️  No dated_events found")
            
        print("\nAll parsed keys:", list(result.keys()))
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Note: This test requires PLY library to be installed")
    except Exception as e:
        print(f"❌ Parsing failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_parser()