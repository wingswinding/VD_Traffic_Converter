import os
import re

scratch_dir = r"C:\Users\Owner\.gemini\antigravity\brain\5da4f6b9-54ae-48d5-bc02-be8a5a3438dd\scratch"
pdf_txt_path = os.path.join(scratch_dir, "pdf_extracted.txt")

with open(pdf_txt_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Search for 第7碼 and 路段特性碼
matches = [m.start() for m in re.finditer(r"7碼|特性碼|第 7 碼|路段屬性|匝道|環道", text)]
print(f"Total matches: {len(matches)}")

for pos in matches[:15]:
    start = max(0, pos - 100)
    end = min(len(text), pos + 300)
    print("--- Snippet ---")
    print(text[start:end].replace('\n', ' '))
