import os
import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
import sys

# Ensure stdout uses UTF-8 if written directly
sys.stdout.reconfigure(encoding='utf-8')

output_lines = []

def log(msg):
    output_lines.append(str(msg))

def inspect_xlsx(file_path):
    log(f"=== Inspecting Excel: {os.path.basename(file_path)} ===")
    if not os.path.exists(file_path):
        log("File does not exist.")
        return
    
    xl = pd.ExcelFile(file_path)
    log(f"Sheets: {xl.sheet_names}")
    for name in xl.sheet_names:
        df = xl.parse(name)
        log(f"\nSheet '{name}' dimensions: {df.shape}")
        log("Columns: " + str(df.columns.tolist()[:10]) + " ...")
        log("First 15 rows:")
        log(df.head(15).to_string())

def inspect_odt(file_path):
    log(f"\n=== Inspecting ODT: {os.path.basename(file_path)} ===")
    if not os.path.exists(file_path):
        log("File does not exist.")
        return
        
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            content_xml = z.read('content.xml')
            
        root = ET.fromstring(content_xml)
        
        text_content = []
        for elem in root.iter():
            if elem.tag.endswith('p') or elem.tag.endswith('span'):
                if elem.text:
                    text_content.append(elem.text)
            elif elem.tag.endswith('tab'):
                text_content.append("\t")
                    
        full_text = "\n".join(text_content)
        log("Extracting text sample (first 2000 characters):")
        log(full_text[:2000])
        log(f"\n... Total extracted paragraphs: {len(text_content)} ...")
        
        # Tables
        tables = list(root.iter('{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table'))
        log(f"\nFound {len(tables)} tables in ODT file.")
        for idx, table in enumerate(tables):
            log(f"\nTable {idx+1}:")
            rows = list(table.iter('{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table-row'))
            log(f"  Total rows: {len(rows)}")
            for r_idx, row in enumerate(rows[:20]):
                cells = []
                for cell in row.iter('{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table-cell'):
                    # get all text inside cell
                    cell_text = "".join(cell.itertext()).strip()
                    cells.append(cell_text)
                log(f"    Row {r_idx+1}: {cells[:10]}")
                
    except Exception as e:
        log(f"Error reading ODT: {e}")

if __name__ == '__main__':
    # Use absolute paths or relative paths in CWD
    inspect_xlsx('國道LOS.xlsx')
    inspect_odt('國道各主要路段速限表115.6.odt')
    
    # Save output to scratch file
    scratch_dir = r"C:\Users\Owner\.gemini\antigravity\brain\5da4f6b9-54ae-48d5-bc02-be8a5a3438dd\scratch"
    os.makedirs(scratch_dir, exist_ok=True)
    out_path = os.path.join(scratch_dir, "new_files_inspection.txt")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(output_lines))
    print(f"Inspection complete. Written to {out_path}")
