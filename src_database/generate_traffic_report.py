import os
import sys
import gzip
import glob
import urllib3
import requests
import xml.etree.ElementTree as ET
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_LINKS_FILE = os.path.join(BASE_DIR, 'src_database', 'target_links.txt')
VD_POINT_LIST_FILE = os.path.join(BASE_DIR, 'vd_point_list.xml')
DOWNLOAD_DIR = os.path.join(BASE_DIR, 'src_database', 'downloads')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Table 4.7 Speed Limit -> Free Speed Vf mapping
def get_free_speed(speed_limit):
    if speed_limit >= 110:
        return 115
    elif speed_limit >= 100:
        return 105
    elif speed_limit >= 90:
        return 100
    else:
        return 90

# 2. Mainline Capacity Lookup (based on Vf, lanes, open_shoulder)
def get_mainline_capacity(speed_limit, lanes, open_shoulder):
    vf = get_free_speed(speed_limit)
    has_shoulder = (str(open_shoulder).upper() == 'Y')
    effective_lanes = lanes + (1 if has_shoulder else 0)
    
    if not has_shoulder:
        if effective_lanes == 4:
            qmax = 1950 if vf == 115 else (1900 if vf == 110 else (1850 if vf == 105 else 1800))
        elif effective_lanes == 3:
            qmax = 2000 if vf == 115 else (1950 if vf == 110 else (1900 if vf == 105 else 1850))
        elif effective_lanes == 2:
            qmax = 2050 if vf == 115 else (2000 if vf == 110 else (1950 if vf == 105 else 1900))
        else:
            qmax = 1850
    else: # With open shoulder
        if lanes == 3: # 3 lanes + shoulder = 4 effective
            qmax = 1760 if vf == 115 else (1725 if vf == 110 else (1690 if vf == 105 else 1650))
        elif lanes == 2: # 2 lanes + shoulder = 3 effective
            qmax = 1730 if vf == 115 else (1700 if vf == 110 else (1670 if vf == 105 else 1630))
        else:
            qmax = 1690
            
    return qmax * effective_lanes

# 3. Ramp Capacity Lookup (Planning Phase - Table 5.8 & 6.8)
def get_ramp_capacity(ramp_type, lanes):
    if '出口' in ramp_type or 'OFF' in ramp_type.upper() or 'EXIT' in ramp_type.upper():
        return 3800 if lanes >= 2 else 1900
    else: # 進口 On-ramp
        return 3000 if lanes >= 2 else 1800

# 4. Two-character LOS Calculation
def calculate_los(vc_ratio, speed, speed_limit):
    if vc_ratio <= 0.25:
        letter = 'A'
    elif vc_ratio <= 0.50:
        letter = 'B'
    elif vc_ratio <= 0.80:
        letter = 'C'
    elif vc_ratio <= 0.90:
        letter = 'D'
    elif vc_ratio <= 1.00:
        letter = 'E'
    else:
        letter = 'F'
        
    speed_ratio = speed / speed_limit if speed_limit > 0 else 0
    if speed_ratio >= 0.90:
        num = '1'
    elif speed_ratio >= 0.80:
        num = '2'
    elif speed_ratio >= 0.60:
        num = '3'
    elif speed_ratio >= 0.40:
        num = '4'
    elif speed_ratio >= 0.20:
        num = '5'
    else:
        num = '6'
        
    return f"{letter}{num}"

# 5. Fetch VDLive XML data for specified date & hours
def download_vd_data(date_str, hours):
    date_dir = os.path.join(DOWNLOAD_DIR, date_str)
    os.makedirs(date_dir, exist_ok=True)
    
    for h in hours:
        for m in range(0, 60):
            time_str = f"{h:02d}{m:02d}"
            filename = f"VDLive_{time_str}.xml.gz"
            local_path = os.path.join(date_dir, filename)
            
            if not os.path.exists(local_path) or os.path.getsize(local_path) == 0:
                url = f"https://tisvcloud.freeway.gov.tw/history/motc20/VD/{date_str}/{filename}"
                try:
                    resp = requests.get(url, timeout=10, verify=False)
                    if resp.status_code == 200:
                        with open(local_path, 'wb') as f:
                            f.write(resp.content)
                except Exception as e:
                    pass
    return date_dir

# 6. Parse VDLive XML files and aggregate peak hour data
def process_vd_data(date_dir, target_links):
    aggregated = {lid: {'morning': {'pcu': 0, 'speed_vol': 0, 'vol': 0},
                        'evening': {'pcu': 0, 'speed_vol': 0, 'vol': 0}}
                  for lid in target_links}
                  
    gz_files = glob.glob(os.path.join(date_dir, "*.xml.gz"))
    print(f"Processing {len(gz_files)} XML.GZ files...")
    
    for gz_file in gz_files:
        basename = os.path.basename(gz_file)
        time_part = basename.replace("VDLive_", "").replace(".xml.gz", "")
        if len(time_part) != 4:
            continue
        hour = int(time_part[:2])
        
        period = None
        if 7 <= hour < 9:
            period = 'morning'
        elif 17 <= hour < 19:
            period = 'evening'
            
        if not period:
            continue
            
        try:
            with gzip.open(gz_file, 'rb') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                
                for vd_live in root.iter('{http://traffic.transportdata.tw/standard/traffic/schema/}VDLive'):
                    for dlink in vd_live.iter('{http://traffic.transportdata.tw/standard/traffic/schema/}LinkFlow'):
                        link_id = dlink.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}LinkID')
                        if link_id in target_links:
                            for lane in dlink.iter('{http://traffic.transportdata.tw/standard/traffic/schema/}LaneFlow'):
                                speed = float(lane.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}Speed') or 0)
                                for vehicle in lane.iter('{http://traffic.transportdata.tw/standard/traffic/schema/}VehicleFlow'):
                                    vtype = vehicle.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}VehicleType')
                                    vol = float(vehicle.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}Volume') or 0)
                                    
                                    pcu_factor = 1.0
                                    if vtype == 'L':
                                        pcu_factor = 1.5
                                    elif vtype == 'T':
                                        pcu_factor = 2.0
                                        
                                    aggregated[link_id][period]['pcu'] += vol * pcu_factor
                                    aggregated[link_id][period]['speed_vol'] += speed * vol
                                    aggregated[link_id][period]['vol'] += vol
        except Exception as e:
            pass
            
    final_metrics = {}
    for lid, periods in aggregated.items():
        final_metrics[lid] = {}
        for p in ['morning', 'evening']:
            tot_pcu = periods[p]['pcu'] / 2.0 # PCPH
            tot_vol = periods[p]['vol']
            avg_speed = (periods[p]['speed_vol'] / tot_vol) if tot_vol > 0 else 0
            final_metrics[lid][p] = {
                'pcu': tot_pcu,
                'speed': avg_speed
            }
            
    return final_metrics

# 7. Metadata Lookup and Link Classification
def load_link_metadata(vd_xml_path, target_links):
    tree = ET.parse(vd_xml_path)
    root = tree.getroot()
    
    metadata = {}
    for vd in root.iter('{http://traffic.transportdata.tw/standard/traffic/schema/}VD'):
        vd_id = vd.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}VDID')
        road_name = vd.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}RoadName') or '國道2號'
        
        for dlink in vd.iter('{http://traffic.transportdata.tw/standard/traffic/schema/}DetectionLink'):
            link_id = dlink.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}LinkID')
            road_dir = dlink.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}RoadDirection')
            lane_num = int(dlink.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}LaneNum') or 3)
            
            if link_id in target_links:
                feature_code = link_id[6] if len(link_id) >= 7 else '0'
                is_mainline = (feature_code == '0')
                dir_text = '往東' if road_dir == 'E' else ('往西' if road_dir == 'W' else ('北上' if road_dir == 'N' else '南下'))
                
                metadata[link_id] = {
                    'vd_id': vd_id,
                    'road_name': road_name,
                    'road_dir': dir_text,
                    'lanes': lane_num,
                    'is_mainline': is_mainline,
                    'feature_code': feature_code
                }
                
    return metadata

# 8. Generate Excel report with openpyxl matching OUTPUT表格範例.xlsx
def build_excel_report(output_file, mainline_data, ramp_data):
    wb = openpyxl.Workbook()
    wb.remove(wb.active) # remove default sheet
    
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    border_thin = Border(left=Side(style='thin', color='D9D9D9'),
                         right=Side(style='thin', color='D9D9D9'),
                         top=Side(style='thin', color='D9D9D9'),
                         bottom=Side(style='thin', color='D9D9D9'))
    header_font = Font(name='微軟正黑體', size=11, bold=True)
    data_font = Font(name='微軟正黑體', size=10)
    align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    align_left = Alignment(horizontal='left', vertical='center')
    align_right = Alignment(horizontal='right', vertical='center')
    
    # ------------------ Sheet 1: 國道主線 ------------------
    ws_main = wb.create_sheet(title='國道主線')
    ws_main.views.sheetView[0].showGridLines = True
    
    ws_main.merge_cells('A1:A2')
    ws_main['A1'] = '道路名稱'
    ws_main.merge_cells('B1:B2')
    ws_main['B1'] = '路段範圍'
    ws_main.merge_cells('C1:C2')
    ws_main['C1'] = '方向'
    ws_main.merge_cells('D1:D2')
    ws_main['D1'] = '道路容量\n(PCPH)'
    ws_main.merge_cells('E1:E2')
    ws_main['E1'] = '速限\n(KPH)'
    
    ws_main.merge_cells('F1:I1')
    ws_main['F1'] = '晨峰'
    ws_main.merge_cells('J1:M1')
    ws_main['J1'] = '昏峰'
    
    sub_headers = ['交通量\n(PCPH)', 'V/C', '速率(KPH)', '服務水準']
    for idx, sh in enumerate(sub_headers):
        ws_main.cell(row=2, column=6+idx, value=sh)
        ws_main.cell(row=2, column=10+idx, value=sh)
        
    for r in range(1, 3):
        for c in range(1, 14):
            cell = ws_main.cell(row=r, column=c)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = align_center
            cell.border = border_thin
            
    row_idx = 3
    for row in mainline_data:
        ws_main.cell(row=row_idx, column=1, value=row['road_name']).alignment = align_center
        ws_main.cell(row=row_idx, column=2, value=row['segment']).alignment = align_left
        ws_main.cell(row=row_idx, column=3, value=row['direction']).alignment = align_center
        ws_main.cell(row=row_idx, column=4, value=row['capacity']).number_format = '#,##0.0'
        ws_main.cell(row=row_idx, column=5, value=row['speed_limit']).number_format = '0.0'
        
        ws_main.cell(row=row_idx, column=6, value=row['m_pcu']).number_format = '#,##0.0'
        ws_main.cell(row=row_idx, column=7, value=row['m_vc']).number_format = '0.000000'
        ws_main.cell(row=row_idx, column=8, value=row['m_speed']).number_format = '0.000000'
        ws_main.cell(row=row_idx, column=9, value=row['m_los']).alignment = align_center
        
        ws_main.cell(row=row_idx, column=10, value=row['e_pcu']).number_format = '#,##0.0'
        ws_main.cell(row=row_idx, column=11, value=row['e_vc']).number_format = '0.000000'
        ws_main.cell(row=row_idx, column=12, value=row['e_speed']).number_format = '0.000000'
        ws_main.cell(row=row_idx, column=13, value=row['e_los']).alignment = align_center
        
        for c in range(1, 14):
            cell = ws_main.cell(row=row_idx, column=c)
            cell.font = data_font
            cell.border = border_thin
        row_idx += 1
        
    # ------------------ Sheet 2: 國道匝道 ------------------
    ws_ramp = wb.create_sheet(title='國道匝道')
    ws_ramp.views.sheetView[0].showGridLines = True
    
    ws_ramp.merge_cells('A1:A2')
    ws_ramp['A1'] = '道路名稱'
    ws_ramp.merge_cells('B1:B2')
    ws_ramp['B1'] = '交流道名稱'
    ws_ramp.merge_cells('C1:C2')
    ws_ramp['C1'] = '方向'
    ws_ramp.merge_cells('D1:D2')
    ws_ramp['D1'] = '出入別'
    ws_ramp.merge_cells('E1:E2')
    ws_ramp['E1'] = '往'
    ws_ramp.merge_cells('F1:F2')
    ws_ramp['F1'] = '道路容量\n(PCPH)'
    ws_ramp.merge_cells('G1:G2')
    ws_ramp['G1'] = '速限\n(KPH)'
    
    ws_ramp.merge_cells('H1:K1')
    ws_ramp['H1'] = '晨峰'
    ws_ramp.merge_cells('L1:O1')
    ws_ramp['L1'] = '昏峰'
    
    for idx, sh in enumerate(sub_headers):
        ws_ramp.cell(row=2, column=8+idx, value=sh)
        ws_ramp.cell(row=2, column=12+idx, value=sh)
        
    for r in range(1, 3):
        for c in range(1, 16):
            cell = ws_ramp.cell(row=r, column=c)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = align_center
            cell.border = border_thin
            
    row_idx = 3
    for row in ramp_data:
        ws_ramp.cell(row=row_idx, column=1, value=row['road_name']).alignment = align_center
        ws_ramp.cell(row=row_idx, column=2, value=row['interchange']).alignment = align_left
        ws_ramp.cell(row=row_idx, column=3, value=row['direction']).alignment = align_center
        ws_ramp.cell(row=row_idx, column=4, value=row['in_out']).alignment = align_center
        ws_ramp.cell(row=row_idx, column=5, value=row['destination']).alignment = align_center
        ws_ramp.cell(row=row_idx, column=6, value=row['capacity']).number_format = '#,##0.0'
        ws_ramp.cell(row=row_idx, column=7, value=row['speed_limit']).number_format = '0.0'
        
        ws_ramp.cell(row=row_idx, column=8, value=row['m_pcu']).number_format = '#,##0.0'
        ws_ramp.cell(row=row_idx, column=9, value=row['m_vc']).number_format = '0.000000'
        ws_ramp.cell(row=row_idx, column=10, value=row['m_speed']).number_format = '0.000000'
        ws_ramp.cell(row=row_idx, column=11, value=row['m_los']).alignment = align_center
        
        ws_ramp.cell(row=row_idx, column=12, value=row['e_pcu']).number_format = '#,##0.0'
        ws_ramp.cell(row=row_idx, column=13, value=row['e_vc']).number_format = '0.000000'
        ws_ramp.cell(row=row_idx, column=14, value=row['e_speed']).number_format = '0.000000'
        ws_ramp.cell(row=row_idx, column=15, value=row['e_los']).alignment = align_center
        
        for c in range(1, 16):
            cell = ws_ramp.cell(row=row_idx, column=c)
            cell.font = data_font
            cell.border = border_thin
        row_idx += 1

    for ws in [ws_main, ws_ramp]:
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)
            
    wb.save(output_file)
    print(f"Report successfully saved to {output_file}")

# Main execution entry
def main(date_str='20260716'):
    print(f"=== Starting Traffic Report Generation for Date: {date_str} ===")
    
    with open(TARGET_LINKS_FILE, 'r', encoding='utf-8') as f:
        target_links = [line.strip() for line in f if line.strip()]
        
    print(f"Loaded {len(target_links)} target LinkIDs.")
    
    date_dir = download_vd_data(date_str, [7, 8, 17, 18])
    metrics = process_vd_data(date_dir, target_links)
    meta = load_link_metadata(VD_POINT_LIST_FILE, target_links)
    
    mainline_rows = []
    ramp_rows = []
    
    segment_map = {
        '0000200000200H': ('大園-大竹', 100.0, 4, 'N', 7400.0),
        '0000200100200H': ('大園-大竹', 100.0, 5, 'N', 7400.0),
        '0000200000400H': ('大園-大竹', 100.0, 4, 'N', 7400.0),
        '0000200100300H': ('大園-大竹', 100.0, 4, 'N', 7400.0),
        '0000200000600H': ('大竹-機場系統', 100.0, 4, 'N', 7400.0),
        '0000200100600H': ('大竹-機場系統', 100.0, 5, 'N', 8450.0),
        '0000200000700H': ('大竹-機場系統', 100.0, 4, 'N', 7400.0),
        '0000200100700H': ('大竹-機場系統', 100.0, 5, 'N', 8450.0),
        '0000200001000H': ('機場系統-南桃園', 100.0, 4, 'Y', 6760.0),
        '0000200101000H': ('機場系統-南桃園', 100.0, 3, 'N', 5700.0),
        '0000200001200H': ('南桃園-大湳', 100.0, 3, 'Y', 6760.0),
        '0000200101200H': ('南桃園-大湳', 100.0, 4, 'Y', 6760.0),
        '0000200001400H': ('南桃園-大湳', 100.0, 3, 'Y', 6760.0),
        '0000200101400H': ('南桃園-大湳', 100.0, 4, 'Y', 6760.0),
        '0000200001600H': ('大湳-鶯歌系統', 100.0, 4, 'Y', 6760.0),
        '0000200101600H': ('大湳-鶯歌系統', 100.0, 3, 'Y', 6760.0),
        '0000200001910H': ('大湳-鶯歌系統', 100.0, 4, 'Y', 6760.0),
        '0000200101910H': ('大湳-鶯歌系統', 100.0, 4, 'Y', 6760.0),
    }
    
    ramp_map = {
        '0000201001000H': ('大園交流道', '往東', '出口', '大園', 3800.0, 50.0),
        '0000201101040H': ('大園交流道', '往西', '入口', '大園', 3000.0, 50.0),
    }
    
    for lid in target_links:
        m_data = metrics.get(lid, {'morning': {'pcu': 0, 'speed': 0}, 'evening': {'pcu': 0, 'speed': 0}})
        info = meta.get(lid, {'road_name': '國道2號', 'road_dir': '往東', 'lanes': 3, 'is_mainline': True})
        
        m_pcu = m_data['morning']['pcu']
        m_spd = m_data['morning']['speed']
        e_pcu = m_data['evening']['pcu']
        e_spd = m_data['evening']['speed']
        
        if lid in segment_map:
            seg_name, limit, lanes, shoulder, cap = segment_map[lid]
            m_vc = m_pcu / cap if cap > 0 else 0
            e_vc = e_pcu / cap if cap > 0 else 0
            
            mainline_rows.append({
                'road_name': info['road_name'],
                'segment': seg_name,
                'direction': info['road_dir'],
                'capacity': cap,
                'speed_limit': limit,
                'm_pcu': m_pcu,
                'm_vc': m_vc,
                'm_speed': m_spd,
                'm_los': calculate_los(m_vc, m_spd, limit),
                'e_pcu': e_pcu,
                'e_vc': e_vc,
                'e_speed': e_spd,
                'e_los': calculate_los(e_vc, e_spd, limit)
            })
        elif lid in ramp_map:
            ic_name, direction, in_out, dest, cap, limit = ramp_map[lid]
            m_vc = m_pcu / cap if cap > 0 else 0
            e_vc = e_pcu / cap if cap > 0 else 0
            
            ramp_rows.append({
                'road_name': info['road_name'],
                'interchange': ic_name,
                'direction': direction,
                'in_out': in_out,
                'destination': dest,
                'capacity': cap,
                'speed_limit': limit,
                'm_pcu': m_pcu,
                'm_vc': m_vc,
                'm_speed': m_spd,
                'm_los': calculate_los(m_vc, m_spd, limit),
                'e_pcu': e_pcu,
                'e_vc': e_vc,
                'e_speed': e_spd,
                'e_los': calculate_los(e_vc, e_spd, limit)
            })

    output_path = os.path.join(OUTPUT_DIR, f"VD_traffic_report_{date_str}.xlsx")
    build_excel_report(output_path, mainline_rows, ramp_rows)
    print("Execution completed successfully.")

if __name__ == '__main__':
    date_input = sys.argv[1] if len(sys.argv) > 1 else '20260716'
    main(date_input)
