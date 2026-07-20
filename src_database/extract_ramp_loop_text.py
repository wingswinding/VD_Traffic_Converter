import os
import pypdf

pdf_path = "1150526 交通部_路段編碼資料標準第二版.pdf"
reader = pypdf.PdfReader(pdf_path)

out_lines = []
# Extract pages 25 to 50
for pnum in range(25, 50):
    if pnum < len(reader.pages):
        page = reader.pages[pnum]
        out_lines.append(f"=== Page {pnum+1} ===")
        out_lines.append(page.extract_text())
        out_lines.append("\n")

scratch_dir = r"C:\Users\Owner\.gemini\antigravity\brain\5da4f6b9-54ae-48d5-bc02-be8a5a3438dd\scratch"
out_path = os.path.join(scratch_dir, "pages_25_50.txt")
with open(out_path, 'w', encoding='utf-8') as f:
    f.write("\n".join(out_lines))
print("Wrote pages 25-50 to", out_path)
