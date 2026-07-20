import os
import re

scratch_dir = r"C:\Users\Owner\.gemini\antigravity\brain\5da4f6b9-54ae-48d5-bc02-be8a5a3438dd\scratch"
pdf_txt_path = os.path.join(scratch_dir, "pdf_extracted.txt")

with open(pdf_txt_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Find pages mentioning LinkID structure
matches = re.finditer(r"LinkID.*?編碼", text, re.DOTALL)
for m in matches:
    pos = m.start()
    print("--- Found LinkID structure section ---")
    print(text[pos:pos+500].replace('\n', ' '))

# Also search for '路段屬性' or '路型' or '匝道' or '環道'
matches2 = re.finditer(r"路段特性|路段型態|匝道型態|環道", text)
for m in matches2:
    pos = m.start()
    print("--- Found Road/Ramp Type section ---")
    print(text[pos-50:pos+350].replace('\n', ' '))
