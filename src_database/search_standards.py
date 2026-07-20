import os

scratch_dir = r"C:\Users\Owner\.gemini\antigravity\brain\5da4f6b9-54ae-48d5-bc02-be8a5a3438dd\scratch"
txt_path = os.path.join(scratch_dir, "pages_25_50.txt")

with open(txt_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Searching for Loop/Ramp rules in PDF:")
for idx, line in enumerate(lines):
    if any(k in line for k in ["環道", "匝道", "特性碼", "路段特性", "主線"]):
        print(f"Line {idx+1}: {line.strip()}")
