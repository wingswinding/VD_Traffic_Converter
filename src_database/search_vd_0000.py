import os
import re

file_path = r"C:\Users\Owner\.gemini\antigravity\brain\5da4f6b9-54ae-48d5-bc02-be8a5a3438dd\.system_generated\steps\314\content.md"

if os.path.exists(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Let's search for files containing '0000' or not matching 'VDLive_' but containing '.xml'
    xml_files = re.findall(r'/[^\s]*\.xml(?:\.gz)?', content)
    print("Found xml files in links:")
    for f in sorted(list(set(xml_files))):
        print("  -", f)
else:
    print("content.md not found!")
