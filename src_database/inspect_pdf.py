import pypdf
import os

pdf_path = "1150526 交通部_路段編碼資料標準第二版.pdf"
if os.path.exists(pdf_path):
    print("PDF exists. Total size:", os.path.getsize(pdf_path))
    reader = pypdf.PdfReader(pdf_path)
    print("Total pages:", len(reader.pages))
    
    found_pages = []
    for idx, page in enumerate(reader.pages):
        text = page.extract_text()
        if any(k in text for k in ["環道", "匝道", "主線", "編碼", "方向", "LinkID", "VD"]):
            found_pages.append((idx + 1, text))
            
    print("Found keyword pages count:", len(found_pages))
    
    scratch_dir = r"C:\Users\Owner\.gemini\antigravity\brain\5da4f6b9-54ae-48d5-bc02-be8a5a3438dd\scratch"
    os.makedirs(scratch_dir, exist_ok=True)
    out_path = os.path.join(scratch_dir, "pdf_extracted.txt")
    with open(out_path, 'w', encoding='utf-8') as f:
        for pnum, text in found_pages:
            f.write(f"=== Page {pnum} ===\n")
            f.write(text)
            f.write("\n\n")
    print("Wrote matches to", out_path)
else:
    print("PDF does not exist.")
