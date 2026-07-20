import os
import sys
import gzip
import glob
import urllib3
import requests
import datetime
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

# 6. Parse VDLive XML files and aggregate BOTH hourly raw data & peak metrics
def process_vd_data(date_dir, target_links, hours_config):
    hours_list, period_map = hours_config
    
    hourly_data = {h: {lid: {
        'S': 0, 'S_speed_vol': 0,
        'L': 0, 'L_speed_vol': 0,
        'T': 0, 'T_speed_vol': 0,
        'speed_vol': 0, 'vol': 0
    } for lid in target_links} for h in hours_list}
    
    gz_files = glob.glob(os.path.join(date_dir, "*.xml.gz"))
    print(f"Processing {len(gz_files)} XML.GZ files...")
    
    ns = '{http://traffic.transportdata.tw/standard/traffic/schema/}'
    
    for gz_file in gz_files:
        basename = os.path.basename(gz_file)
        time_part = basename.replace("VDLive_", "").replace(".xml.gz", "")
        if len(time_part) != 4:
            continue
        hour = int(time_part[:2])
        
        h_key = period_map.get(hour)
        if not h_key:
            continue
            
        try:
            with gzip.open(gz_file, 'rb') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                
                for vd_live in root.iter(f'{ns}VDLive'):
                    for dlink in vd_live.iter(f'{ns}LinkFlow'):
                        link_id = dlink.findtext(f'{ns}LinkID')
                        if link_id in target_links:
                            for lane in dlink.iter(f'{ns}Lane'):
                                speed = float(lane.findtext(f'{ns}Speed') or 0)
                                for vehicle in lane.iter(f'{ns}Vehicle'):
                                    vtype = vehicle.findtext(f'{ns}VehicleType')
                                    vol = float(vehicle.findtext(f'{ns}Volume') or 0)
                                    veh_speed = float(vehicle.findtext(f'{ns}Speed') or speed)
                                    
                                    if vtype == 'S':
                                        hourly_data[h_key][link_id]['S'] += vol
                                        hourly_data[h_key][link_id]['S_speed_vol'] += veh_speed * vol
                                    elif vtype == 'L':
                                        hourly_data[h_key][link_id]['L'] += vol
                                        hourly_data[h_key][link_id]['L_speed_vol'] += veh_speed * vol
                                    elif vtype == 'T':
                                        hourly_data[h_key][link_id]['T'] += vol
                                        hourly_data[h_key][link_id]['T_speed_vol'] += veh_speed * vol
                                        
                                    hourly_data[h_key][link_id]['speed_vol'] += veh_speed * vol
                                    hourly_data[h_key][link_id]['vol'] += vol
        except Exception as e:
            pass
            
    final_peak_metrics = {lid: {'morning': {'pcu': 0, 'speed': 0}, 'evening': {'pcu': 0, 'speed': 0}} for lid in target_links}
    
    m_h1, m_h2 = hours_list[0], hours_list[1]
    e_h1, e_h2 = hours_list[2], hours_list[3]
    
    for lid in target_links:
        # Morning peak (2 hours total)
        m_s = hourly_data[m_h1][lid]['S'] + hourly_data[m_h2][lid]['S']
        m_l = hourly_data[m_h1][lid]['L'] + hourly_data[m_h2][lid]['L']
        m_t = hourly_data[m_h1][lid]['T'] + hourly_data[m_h2][lid]['T']
        m_sv = hourly_data[m_h1][lid]['speed_vol'] + hourly_data[m_h2][lid]['speed_vol']
        m_v = hourly_data[m_h1][lid]['vol'] + hourly_data[m_h2][lid]['vol']
        
        m_pcu_ph = (m_s * 1.0 + m_l * 1.5 + m_t * 2.0) / 2.0
        m_avg_spd = (m_sv / m_v) if m_v > 0 else 0
        
        # Evening peak (2 hours total)
        e_s = hourly_data[e_h1][lid]['S'] + hourly_data[e_h2][lid]['S']
        e_l = hourly_data[e_h1][lid]['L'] + hourly_data[e_h2][lid]['L']
        e_t = hourly_data[e_h1][lid]['T'] + hourly_data[e_h2][lid]['T']
        e_sv = hourly_data[e_h1][lid]['speed_vol'] + hourly_data[e_h2][lid]['speed_vol']
        e_v = hourly_data[e_h1][lid]['vol'] + hourly_data[e_h2][lid]['vol']
        
        e_pcu_ph = (e_s * 1.0 + e_l * 1.5 + e_t * 2.0) / 2.0
        e_avg_spd = (e_sv / e_v) if e_v > 0 else 0
        
        final_peak_metrics[lid]['morning'] = {'pcu': m_pcu_ph, 'speed': m_avg_spd}
        final_peak_metrics[lid]['evening'] = {'pcu': e_pcu_ph, 'speed': e_avg_spd}
        
    return hourly_data, final_peak_metrics

# 7. Metadata Lookup
def load_link_metadata(vd_xml_path, target_links):
    tree = ET.parse(vd_xml_path)
    root = tree.getroot()
    ns = '{http://traffic.transportdata.tw/standard/traffic/schema/}'
    
    metadata = {}
    for vd in root.iter(f'{ns}VD'):
        vd_id = vd.findtext(f'{ns}VDID')
        road_name = vd.findtext(f'{ns}RoadName') or '國道2號'
        
        for dlink in vd.iter(f'{ns}DetectionLink'):
            link_id = dlink.findtext(f'{ns}LinkID')
            road_dir = dlink.findtext(f'{ns}RoadDirection')
            lane_num = int(dlink.findtext(f'{ns}LaneNum') or 3)
            
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

# 8. Generate Excel report with openpyxl in exact requested sheet order:
# 1. 國道主線, 2. 國道匝道, 3-6. Raw hourly sheets
def build_excel_report(output_file, hourly_data, mainline_data, ramp_data, target_links, meta, hours_list):
    wb = openpyxl.Workbook()
    
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
    
    # ------------------ Sheet 1: 國道主線 Analysis ------------------
    ws_main = wb.active
    ws_main.title = '國道主線'
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
        
    # ------------------ Sheet 2: 國道匝道 Analysis ------------------
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

    # ------------------ Sheets 3-6: Raw Hourly Data ------------------
    raw_headers = [
        '偵測器代碼 (VDID)', '路段代碼 (LinkID)', 
        '小客車數量 (S)', '小客車速率 (KPH)',
        '大客車數量 (L)', '大客車速率 (KPH)',
        '聯結車數量 (T)', '聯結車速率 (KPH)',
        '總車輛數 (車)', '總當量 (PCU)', '加權速率 (KPH)'
    ]
    
    for h_name in hours_list:
        ws = wb.create_sheet(title=h_name)
        ws.views.sheetView[0].showGridLines = True
        
        for col_idx, h_text in enumerate(raw_headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=h_text)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = align_center
            cell.border = border_thin
            
        row_idx = 2
        for lid in target_links:
            vd_info = meta.get(lid, {})
            vd_id = vd_info.get('vd_id', '')
            
            d = hourly_data[h_name][lid]
            s_vol = d['S']
            s_spd = (d['S_speed_vol'] / s_vol) if s_vol > 0 else 0
            
            l_vol = d['L']
            l_spd = (d['L_speed_vol'] / l_vol) if l_vol > 0 else 0
            
            t_vol = d['T']
            t_spd = (d['T_speed_vol'] / t_vol) if t_vol > 0 else 0
            
            tot_veh = s_vol + l_vol + t_vol
            tot_pcu = s_vol * 1.0 + l_vol * 1.5 + t_vol * 2.0
            avg_spd = (d['speed_vol'] / d['vol']) if d['vol'] > 0 else 0
            
            ws.cell(row=row_idx, column=1, value=vd_id).alignment = align_center
            ws.cell(row=row_idx, column=2, value=lid).alignment = align_center
            ws.cell(row=row_idx, column=3, value=s_vol).number_format = '#,##0'
            ws.cell(row=row_idx, column=4, value=s_spd).number_format = '0.00'
            ws.cell(row=row_idx, column=5, value=l_vol).number_format = '#,##0'
            ws.cell(row=row_idx, column=6, value=l_spd).number_format = '0.00'
            ws.cell(row=row_idx, column=7, value=t_vol).number_format = '#,##0'
            ws.cell(row=row_idx, column=8, value=t_spd).number_format = '0.00'
            ws.cell(row=row_idx, column=9, value=tot_veh).number_format = '#,##0'
            ws.cell(row=row_idx, column=10, value=tot_pcu).number_format = '#,##0.0'
            ws.cell(row=row_idx, column=11, value=avg_spd).number_format = '0.00'
            
            for c in range(1, 12):
                ws.cell(row=row_idx, column=c).font = data_font
                ws.cell(row=row_idx, column=c).border = border_thin
            row_idx += 1

    # Auto-adjust column widths for all sheets
    for ws in wb.worksheets:
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 15)
            
    wb.save(output_file)
    print(f"Report successfully saved to {output_file}")

# Main execution entry
def main(date_str='20260716'):
    print(f"=== Starting Traffic Report Generation for Date: {date_str} ===")
    
    # Determine Weekday vs Weekend Peak Hours
    dt = datetime.datetime.strptime(date_str, "%Y%m%d")
    is_weekend = dt.weekday() in [5, 6] # Saturday=5, Sunday=6
    
    if is_weekend:
        print("Date type: Weekend / Holiday (10-12 Morning Peak, 16-18 Evening Peak)")
        hours_list = ['1000-1100', '1100-1200', '1600-1700', '1700-1800']
        period_map = {10: '1000-1100', 11: '1100-1200', 16: '1600-1700', 17: '1700-1800'}
        download_hours = [10, 11, 16, 17]
    else:
        print("Date type: Weekday (07-09 Morning Peak, 17-19 Evening Peak)")
        hours_list = ['0700-0800', '0800-0900', '1700-1800', '1800-1900']
        period_map = {7: '0700-0800', 8: '0800-0900', 17: '1700-1800', 18: '1800-1900'}
        download_hours = [7, 8, 17, 18]
        
    with open(TARGET_LINKS_FILE, 'r', encoding='utf-8') as f:
        target_links = [line.strip() for line in f if line.strip()]
        
    print(f"Loaded {len(target_links)} target LinkIDs.")
    
    date_dir = download_vd_data(date_str, download_hours)
    hourly_data, metrics = process_vd_data(date_dir, target_links, (hours_list, period_map))
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
    build_excel_report(output_path, hourly_data, mainline_rows, ramp_rows, target_links, meta, hours_list)
    print("Execution completed successfully.")

if __name__ == '__main__':
    date_input = sys.argv[1] if len(sys.argv) > 1 else '20260716'
    main(date_input)
