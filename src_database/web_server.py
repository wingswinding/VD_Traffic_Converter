import os
import sys
import json
import glob
import datetime
import urllib.parse
import subprocess
import threading
import xml.etree.ElementTree as ET
import openpyxl
from http.server import HTTPServer, SimpleHTTPRequestHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_UI_DIR = os.path.join(BASE_DIR, 'src_database', 'web_ui')
TARGET_LINKS_FILE = os.path.join(BASE_DIR, 'src_database', 'target_links.txt')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
REF_DIR = os.path.join(BASE_DIR, 'reference_files')
VD_POINT_LIST_FILE = os.path.join(REF_DIR, 'vd_point_list.xml')
if not os.path.exists(VD_POINT_LIST_FILE):
    VD_POINT_LIST_FILE = os.path.join(BASE_DIR, 'vd_point_list.xml')

# Global State for Analysis Run
state_lock = threading.Lock()
current_run = {
    "status": "idle",
    "progress": 0,
    "message": "系統已就緒",
    "logs": []
}

def run_analysis_thread(date_str, mode, custom_hours):
    global current_run
    with state_lock:
        current_run["status"] = "running"
        current_run["progress"] = 0
        current_run["message"] = f"開始分析 ({date_str}, 模式: {mode})..."
        current_run["logs"] = [f"=== 開始執行交通量分析 [日期: {date_str}, 模式: {mode}] ==="]

    cmd = [sys.executable, os.path.join(BASE_DIR, 'src_database', 'generate_traffic_report.py'), date_str, mode, custom_hours]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', bufsize=1)

    for line in iter(proc.stdout.readline, ''):
        line_str = line.strip()
        if not line_str:
            continue
        
        with state_lock:
            current_run["logs"].append(line_str)
            if line_str.startswith("PROGRESS:"):
                try:
                    parts = line_str.replace("PROGRESS:", "").split("|")
                    pct = int(parts[0].replace("%", "").strip())
                    msg = parts[1].strip() if len(parts) > 1 else ""
                    current_run["progress"] = pct
                    current_run["message"] = msg
                except Exception:
                    pass

    proc.stdout.close()
    return_code = proc.wait()

    with state_lock:
        if return_code == 0:
            current_run["status"] = "completed"
            current_run["progress"] = 100
            current_run["message"] = "分析完成！報表已產出。"
            current_run["logs"].append("=== 轉檔與分析順利完成 ===")
        else:
            current_run["status"] = "error"
            current_run["message"] = "執行過程發生錯誤！"
            current_run["logs"].append("=== 執行失敗，請檢查 Log ===")

def parse_latest_excel_results():
    if not os.path.exists(OUTPUT_DIR):
        return None
    files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.xlsx")), reverse=True)
    if not files:
        return None
    latest_file = files[0]
    filename = os.path.basename(latest_file)
    
    try:
        wb = openpyxl.load_workbook(latest_file, data_only=True)
        results = []
        highways = set()
        
        # 1. Sheet: 國道主線
        if '國道主線' in wb.sheetnames:
            ws = wb['國道主線']
            for r in range(3, ws.max_row + 1):
                road_name = str(ws.cell(row=r, column=1).value or '').strip()
                segment = str(ws.cell(row=r, column=2).value or '').strip()
                direction = str(ws.cell(row=r, column=3).value or '').strip()
                cap = float(ws.cell(row=r, column=4).value or 0)
                limit = float(ws.cell(row=r, column=5).value or 0)
                
                m_pcu = float(ws.cell(row=r, column=6).value or 0)
                m_vc = float(ws.cell(row=r, column=7).value or 0)
                m_spd = float(ws.cell(row=r, column=8).value or 0)
                m_los = str(ws.cell(row=r, column=9).value or '').strip()
                
                e_pcu = float(ws.cell(row=r, column=10).value or 0)
                e_vc = float(ws.cell(row=r, column=11).value or 0)
                e_spd = float(ws.cell(row=r, column=12).value or 0)
                e_los = str(ws.cell(row=r, column=13).value or '').strip()
                
                if road_name and segment:
                    highways.add(road_name)
                    results.append({
                        "road_name": road_name,
                        "segment": segment,
                        "direction": direction,
                        "type": "主線",
                        "capacity": cap,
                        "speed_limit": limit,
                        "m_pcu": m_pcu, "m_vc": m_vc, "m_speed": m_spd, "m_los": m_los,
                        "e_pcu": e_pcu, "e_vc": e_vc, "e_speed": e_spd, "e_los": e_los
                    })
                    
        # 2. Sheet: 國道匝道
        if '國道匝道' in wb.sheetnames:
            ws = wb['國道匝道']
            for r in range(3, ws.max_row + 1):
                road_name = str(ws.cell(row=r, column=1).value or '').strip()
                ic_name = str(ws.cell(row=r, column=2).value or '').strip()
                direction = str(ws.cell(row=r, column=3).value or '').strip()
                in_out = str(ws.cell(row=r, column=4).value or '').strip()
                dest = str(ws.cell(row=r, column=5).value or '').strip()
                cap = float(ws.cell(row=r, column=6).value or 0)
                limit = float(ws.cell(row=r, column=7).value or 0)
                
                m_pcu = float(ws.cell(row=r, column=8).value or 0)
                m_vc = float(ws.cell(row=r, column=9).value or 0)
                m_spd = float(ws.cell(row=r, column=10).value or 0)
                m_los = str(ws.cell(row=r, column=11).value or '').strip()
                
                e_pcu = float(ws.cell(row=r, column=12).value or 0)
                e_vc = float(ws.cell(row=r, column=13).value or 0)
                e_spd = float(ws.cell(row=r, column=14).value or 0)
                e_los = str(ws.cell(row=r, column=15).value or '').strip()
                
                if road_name and ic_name:
                    highways.add(road_name)
                    results.append({
                        "road_name": road_name,
                        "segment": f"{ic_name} ({in_out}-{dest})",
                        "direction": direction,
                        "type": "匝道",
                        "capacity": cap,
                        "speed_limit": limit,
                        "m_pcu": m_pcu, "m_vc": m_vc, "m_speed": m_spd, "m_los": m_los,
                        "e_pcu": e_pcu, "e_vc": e_vc, "e_speed": e_spd, "e_los": e_los
                    })
                    
        total_links = len(results)
        mainline_count = len([x for x in results if x['type'] == '主線'])
        ramp_count = len([x for x in results if x['type'] == '匝道'])
        
        max_vc_item = max(results, key=lambda x: max(x['m_vc'], x['e_vc'])) if results else None
        max_vc = max(max_vc_item['m_vc'], max_vc_item['e_vc']) if max_vc_item else 0
        max_vc_seg = f"{max_vc_item['segment']} ({max_vc_item['direction']})" if max_vc_item else ''
        
        worst_los_item = max(results, key=lambda x: max(x['m_los'], x['e_los'])) if results else None
        worst_los = max(worst_los_item['m_los'], worst_los_item['e_los']) if worst_los_item else 'A1'
        
        return {
            "report_name": filename,
            "total_links": total_links,
            "mainline_count": mainline_count,
            "ramp_count": ramp_count,
            "max_vc": round(max_vc, 2),
            "max_vc_seg": max_vc_seg,
            "worst_los": worst_los,
            "highways": sorted(list(highways)),
            "data": results
        }
    except Exception as e:
        print(f"Error parsing excel results: {e}")
        return None

def get_link_metadata_details():
    links = []
    if os.path.exists(TARGET_LINKS_FILE):
        with open(TARGET_LINKS_FILE, 'r', encoding='utf-8') as f:
            links = [line.strip() for line in f if line.strip()]
            
    xml_map = {}
    if os.path.exists(VD_POINT_LIST_FILE):
        try:
            tree = ET.parse(VD_POINT_LIST_FILE)
            root = tree.getroot()
            ns = '{http://traffic.transportdata.tw/standard/traffic/schema/}'
            for vd in root.iter(f'{ns}VD'):
                vd_id = vd.findtext(f'{ns}VDID')
                road_name = vd.findtext(f'{ns}RoadName') or '國道2號'
                for dlink in vd.iter(f'{ns}DetectionLink'):
                    link_id = dlink.findtext(f'{ns}LinkID')
                    road_dir = dlink.findtext(f'{ns}RoadDirection')
                    lane_num = dlink.findtext(f'{ns}LaneNum') or '3'
                    if link_id:
                        dir_text = '往東' if road_dir == 'E' else ('往西' if road_dir == 'W' else ('北上' if road_dir == 'N' else '南下'))
                        xml_map[link_id] = {
                            "vd_id": vd_id,
                            "road_name": road_name,
                            "direction": dir_text,
                            "lanes": lane_num
                        }
        except Exception:
            pass
            
    details = []
    for lid in links:
        feature_code = lid[6] if len(lid) >= 7 else '0'
        type_text = '主線' if feature_code == '0' else '匝道'
        info = xml_map.get(lid, {
            "vd_id": "VD-N2-E-LOOP" if lid.startswith("00002010") else ("VD-N2-W-LOOP" if lid.startswith("00002011") else "靜態資料庫未收錄"),
            "road_name": "國道2號",
            "direction": "往東" if lid[7] == '0' else "往西",
            "lanes": "3"
        })
        details.append({
            "link_id": lid,
            "vd_id": info["vd_id"],
            "road_name": info["road_name"],
            "direction": info["direction"],
            "type": type_text,
            "lanes": info["lanes"]
        })
    return details

class VDRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_UI_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == '/api/latest_results':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            res = parse_latest_excel_results()
            self.wfile.write(json.dumps(res or {}, ensure_ascii=False).encode('utf-8'))
        elif path == '/api/link_metadata':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            details = get_link_metadata_details()
            self.wfile.write(json.dumps({"metadata": details}, ensure_ascii=False).encode('utf-8'))
        elif path == '/api/progress':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            with state_lock:
                self.wfile.write(json.dumps(current_run, ensure_ascii=False).encode('utf-8'))
        elif path == '/api/links':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            links = []
            if os.path.exists(TARGET_LINKS_FILE):
                with open(TARGET_LINKS_FILE, 'r', encoding='utf-8') as f:
                    links = [line.strip() for line in f if line.strip()]
            self.wfile.write(json.dumps({"links": links}, ensure_ascii=False).encode('utf-8'))
        elif path == '/api/reports':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            reports = []
            if os.path.exists(OUTPUT_DIR):
                files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.xlsx")), reverse=True)
                for f in files:
                    reports.append({
                        "name": os.path.basename(f),
                        "size": f"{os.path.getsize(f) / 1024:.1f} KB",
                        "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y-%m-%d %H:%M:%S")
                    })
            self.wfile.write(json.dumps({"reports": reports}, ensure_ascii=False).encode('utf-8'))
        elif path == '/api/download':
            file_name = query.get('file', [''])[0]
            file_path = os.path.join(OUTPUT_DIR, os.path.basename(file_name))
            if os.path.exists(file_path):
                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                self.send_header('Content-Disposition', f'attachment; filename*=UTF-8\'\'{urllib.parse.quote(file_name)}')
                self.send_header('Content-Length', str(os.path.getsize(file_path)))
                self.end_headers()
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File Not Found")
        elif path == '/api/logs':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            logs = []
            if os.path.exists(LOGS_DIR):
                files = sorted(glob.glob(os.path.join(LOGS_DIR, "*.log")), reverse=True)
                for f in files:
                    logs.append({
                        "name": os.path.basename(f),
                        "size": f"{os.path.getsize(f) / 1024:.1f} KB",
                        "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y-%m-%d %H:%M:%S")
                    })
            self.wfile.write(json.dumps({"logs": logs}, ensure_ascii=False).encode('utf-8'))
        elif path == '/api/log_content':
            file_name = query.get('file', [''])[0]
            file_path = os.path.join(LOGS_DIR, os.path.basename(file_name))
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            content = ""
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            self.wfile.write(json.dumps({"content": content}, ensure_ascii=False).encode('utf-8'))
        elif path == '/api/references':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            refs = []
            if os.path.exists(REF_DIR):
                for fname in sorted(os.listdir(REF_DIR)):
                    fpath = os.path.join(REF_DIR, fname)
                    if os.path.isfile(fpath):
                        refs.append({
                            "name": fname,
                            "size": f"{os.path.getsize(fpath) / 1024:.1f} KB",
                            "ext": os.path.splitext(fname)[1].lower()
                        })
            self.wfile.write(json.dumps({"references": refs}, ensure_ascii=False).encode('utf-8'))
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        if path == '/api/run':
            data = json.loads(post_data.decode('utf-8'))
            date_str = data.get('date', '20260716')
            mode = data.get('mode', 'peak')
            custom_hours = data.get('custom_hours', '')

            with state_lock:
                if current_run["status"] == "running":
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "目前已有任務正在執行中！"}, ensure_ascii=False).encode('utf-8'))
                    return

            t = threading.Thread(target=run_analysis_thread, args=(date_str, mode, custom_hours), daemon=True)
            t.start()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "started"}, ensure_ascii=False).encode('utf-8'))

        elif path == '/api/save_links':
            data = json.loads(post_data.decode('utf-8'))
            links = data.get('links', [])
            with open(TARGET_LINKS_FILE, 'w', encoding='utf-8') as f:
                for lid in links:
                    if lid.strip():
                        f.write(lid.strip() + '\n')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}, ensure_ascii=False).encode('utf-8'))

def run_server(port=8000):
    os.makedirs(WEB_UI_DIR, exist_ok=True)
    server_address = ('', port)
    httpd = HTTPServer(server_address, VDRequestHandler)
    print(f"==================================================")
    print(f"VD Traffic Report Web UI Server Started!")
    print(f"Please open browser at: http://localhost:{port}")
    print(f"Press Ctrl+C to stop server")
    print(f"==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == '__main__':
    port_input = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8000
    run_server(port_input)
