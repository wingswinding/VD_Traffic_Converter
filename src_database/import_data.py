import os
import gzip
import sqlite3
import datetime
import xml.etree.ElementTree as ET
import glob

def parse_iso_datetime(iso_str):
    """
    Converts ISO8601 datetime string (e.g., '2026-07-19T06:59:00+08:00')
    to SQLite standard datetime format 'YYYY-MM-DD HH:MM:SS'.
    """
    # Simply slice the date and time parts before timezone offset
    # E.g., '2026-07-19T06:59:00' -> '2026-07-19 06:59:00'
    try:
        dt_part = iso_str.split('+')[0].split('-')[0:3]
        # Rejoin date and replace T with space
        return iso_str[:19].replace('T', ' ')
    except Exception:
        return iso_str

def import_vd_data(date_str, target_links_file='target_links.txt', db_file='vd_traffic.db', download_dir='downloads'):
    db_path = os.path.join(os.path.dirname(__file__), db_file)
    links_path = os.path.join(os.path.dirname(__file__), target_links_file)
    src_dir = os.path.join(os.path.dirname(__file__), download_dir, date_str)
    
    # 1. Load target LinkIDs
    if not os.path.exists(links_path):
        print(f"Error: Target links file {links_path} not found!")
        return
        
    with open(links_path, 'r', encoding='utf-8') as f:
        target_links = set(line.strip() for line in f if line.strip())
        
    print(f"Loaded {len(target_links)} target LinkIDs for filtering.")
    
    # 2. Get download file list
    xml_files = glob.glob(os.path.join(src_dir, "VDLive_*.xml.gz"))
    if not xml_files:
        print(f"No XML files found in {src_dir}!")
        return
        
    xml_files.sort()
    print(f"Found {len(xml_files)} XML.GZ files to parse...")
    
    # 3. Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear existing data for this date to avoid duplication
    # We estimate date by checking date_str (YYYYMMDD) in timestamp
    sql_date_pattern = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}%"
    cursor.execute("DELETE FROM traffic_records WHERE timestamp LIKE ?", (sql_date_pattern,))
    conn.commit()
    print(f"Cleaned up existing records for {date_str}.")
    
    ns = {'t': 'http://traffic.transportdata.tw/standard/traffic/schema/'}
    
    insert_buffer = []
    processed_files = 0
    total_rows_inserted = 0
    
    for idx, file_path in enumerate(xml_files):
        try:
            with gzip.open(file_path, 'rb') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                
            # Iterate through VDLive nodes
            for vdlive in root.findall('.//t:VDLive', ns):
                vd_id_elem = vdlive.find('t:VDID', ns)
                collect_time_elem = vdlive.find('t:DataCollectTime', ns)
                
                if vd_id_elem is None or collect_time_elem is None:
                    continue
                    
                vd_id = vd_id_elem.text
                collect_time = parse_iso_datetime(collect_time_elem.text)
                
                # Traverse LinkFlows
                for link_flow in vdlive.findall('.//t:LinkFlow', ns):
                    link_id_elem = link_flow.find('t:LinkID', ns)
                    if link_id_elem is None:
                        continue
                    link_id = link_id_elem.text
                    
                    # Apply LinkID filter
                    if link_id not in target_links:
                        continue
                        
                    # Traverse Lanes
                    for lane in link_flow.findall('.//t:Lane', ns):
                        speed_elem = lane.find('t:Speed', ns)
                        speed = float(speed_elem.text) if speed_elem is not None and speed_elem.text else 0.0
                        
                        # Traverse Vehicles
                        for vehicle in lane.findall('.//t:Vehicle', ns):
                            v_type_elem = vehicle.find('t:VehicleType', ns)
                            v_vol_elem = vehicle.find('t:Volume', ns)
                            
                            if v_type_elem is None or v_vol_elem is None:
                                continue
                                
                            v_type = v_type_elem.text
                            volume = int(v_vol_elem.text) if v_vol_elem.text else 0
                            
                            # Add to transaction buffer
                            insert_buffer.append((collect_time, vd_id, link_id, v_type, volume, speed))
            
            processed_files += 1
            # Batch write to database every 10 files to optimize disk I/O
            if len(insert_buffer) >= 10000 or idx == len(xml_files) - 1:
                cursor.executemany('''
                    INSERT INTO traffic_records (timestamp, vd_id, link_id, vehicle_type, volume, speed)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', insert_buffer)
                conn.commit()
                total_rows_inserted += len(insert_buffer)
                insert_buffer.clear()
                
        except Exception as e:
            print(f"Error parsing file {os.path.basename(file_path)}: {e}")
            
    conn.close()
    print(f"\nImport finished:")
    print(f"  - Successfully processed: {processed_files} files")
    print(f"  - Total records imported: {total_rows_inserted} rows")
    print(f"Database size: {os.path.getsize(db_path) / (1024*1024):.2f} MB")

if __name__ == '__main__':
    import_vd_data(date_str='20260719')
