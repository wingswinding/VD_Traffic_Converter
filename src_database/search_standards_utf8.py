import os
import re

scratch_dir = r"C:\Users\Owner\.gemini\antigravity\brain\5da4f6b9-54ae-48d5-bc02-be8a5a3438dd\scratch"
txt_path = os.path.join(scratch_dir, "pages_25_50.txt")

with open(txt_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Let's search for "主線", "匝道", "環道", "第7碼" and write matching lines and blocks to a text file
out_lines = []
out_lines.append("=== Detailed Standard Analysis ===")

# Find paragraph around '路段特性' or '7碼'
pattern = re.compile(r"(.{1,150}(?:主線|匝道|環道|特性碼|第7碼|路段特性).{1,250})", re.DOTALL)
matches = pattern.findall(text)
for idx, match in enumerate(matches):
    clean_match = match.replace('\n', ' ').strip()
    out_lines.append(f"Match {idx+1}:\n{clean_match}\n")

out_file = os.path.join(scratch_dir, "standards_search_results.txt")
with open(out_file, 'w', encoding='utf-8') as f:
    f.write("\n".join(out_lines))
print("Wrote results to", out_file)
