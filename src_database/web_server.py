import os
import sys
import json
import glob
import urllib.parse
import subprocess
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_UI_DIR = os.path.join(BASE_DIR, 'src_database', 'web_ui')
TARGET_LINKS_FILE = os.path.join(BASE_DIR, 'src_database', 'target_links.txt')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
REF_DIR = os.path.join(BASE_DIR, 'reference_files')

# Global State for Analysis Run
state_lock = threading.Lock()
current_run = {
    "status": "idle", # idle, running, completed, error
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

class VDRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_UI_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == '/api/progress':
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
    print(f"VD 交通量轉換與服務水準 Web UI 伺服器已啟動！")
    print(f"請在瀏覽器開啟: http://localhost:{port}")
    print(f"按下 Ctrl+C 可停止伺服器")
    print(f"==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n伺服器已關閉。")

if __name__ == '__main__':
    port_input = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8000
    run_server(port_input)
