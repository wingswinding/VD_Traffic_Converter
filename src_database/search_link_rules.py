import os
import re

scratch_dir = r"C:\Users\Owner\.gemini\antigravity\brain\5da4f6b9-54ae-48d5-bc02-be8a5a3438dd\scratch"
pdf_txt_path = os.path.join(scratch_dir, "pdf_extracted.txt")

with open(pdf_txt_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Search for LinkID structure, Ramp types, Loop types
keywords = ["LinkID", "路段編碼", "匝道", "環道", "主線", "集散", "轉向", "第14碼", "第13碼", "第12碼", "第11碼", "第10碼", "編碼結構"]
for kw in keywords:
    print(f"=== Keyword: {kw} ===")
    matches = [m.start() for m in re.finditer(kw, text)]
    print(f"Found {len(matches)} occurrences.")
    for pos in matches[:3]:
        start = max(0, pos - 150)
        end = min(len(text), pos + 250)
        print("--- Snippet ---")
        print(text[start:end].replace('\n', ' '))
