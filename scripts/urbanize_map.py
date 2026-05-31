#!/usr/bin/env python3
"""
Urbanizes the AI Town map by swapping the default tileset with the NYC tileset.
"""
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent.parent
GENTLE_JS = HERE / "fanfic_town" / "data" / "gentle.js"

def main():
    if not GENTLE_JS.exists():
        print(f"Error: {GENTLE_JS} not found.")
        return

    content = GENTLE_JS.read_text()
    
    # Swap tileset path
    # OLD: export const tilesetpath = "/ai-town/assets/gentle-obj.png"
    # NEW: export const tilesetpath = "/ai-town/assets/nyc-tileset.png"
    
    new_content = re.sub(
        r'export const tilesetpath = ".*"',
        'export const tilesetpath = "/ai-town/assets/nyc-tileset.png"',
        content
    )
    
    if new_content != content:
        GENTLE_JS.write_text(new_content)
        print(f"Updated {GENTLE_JS} to use /ai-town/assets/nyc-tileset.png")
    else:
        print("Tileset path already updated or not found.")

if __name__ == "__main__":
    main()
