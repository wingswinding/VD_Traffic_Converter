import os
import re

scratch_dir = r"C:\Users\Owner\.gemini\antigravity\brain\5da4f6b9-54ae-48d5-bc02-be8a5a3438dd\scratch"
pdf_txt_path = os.path.join(scratch_dir, "pdf_extracted.txt")

with open(pdf_txt_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Let's search for "環道" and "匝道" and print the exact surrounding paragraphs
for match in re.finditer(r"(?:環道|匝道|對角匝道|集散道路|轉向匝道|主線|側車道)", text):
    pos = match.start()
    snippet = text[max(0, pos-100):min(len(text), pos+300)].replace('\n', ' ')
    if any(code in snippet for code in ["代碼", "編碼", "第", "欄位", "定義", "型態", "分類", "LinkID"]):
        print("=== MATCH ===")
        print(snippet)
        print()
