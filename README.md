# 🚦 VD 交通量轉換、速限比對與服務水準分析自動化系統

本專案為 **VD (Vehicle Detector) 交通量資料轉檔、車當量 (PCE) 換算、道路容量比對與服務水準 (LOS) 自動化分析系統**。

系統自動連結交通部 / 高公局開放資料 API 下載歷史 1 分鐘 XML.GZ 點位數據，支援 **15 分鐘滑動 1 小時視窗尖峰極值計算** 與 **全日 24 小時連續時序趨勢分析**，並提供以 Web GUI 介面為核心之雙視圖看板、路段智慧瀏覽器、24hr LOS 熱圖矩陣與自動化 Excel 報表匯出功能。

---

## 🌟 核心特色與亮點

* **一鍵式全自動環境檢測與安裝**：雙擊 `start_ui.bat` 即可全自動完成 Python 3.11 檢測安裝（透過 `winget`）與套件自動安裝（`pip install -r requirements.txt`），零設定即可開啟 Web 操作介面。
* **雙視圖動態視覺化看板**：
  * **`📊 晨昏峰極值總覽`**：呈現 15 分鐘滑動視窗計算之最尖峰 PCU 流量、V/C 比值、旅行速率與 A1~F6 雙碼服務水準。
  * **`⏱️ 24小時連續動態視圖`**：
    * **24 小時 LOS 熱圖矩陣 (Heatmap Matrix)**：以綠 (A/B)、黃 (C/D)、紅 (E)、紫 (F) 顏色直觀呈現路段全天 24 小時熱點演變。
    * **24 小時雙軸連續時序趨勢圖 (Diurnal Continuous Curve)**：結合小時當量流量柱狀圖與速率/速限趨勢線，支援「全路段平均」或「個別特定路段」切換。
    * **全日專屬 KPI**：全日瓶頸路段車流 (ADT PCU/day)、尖峰小時率 ($K$ Factor %) 與全日壅塞持續總時數 ($V/C \ge 1.0$)。
* **靈活自訂車當量係數 (PCE)**：預設符合國內交通工程標準（小型車 S=1.0、大型車 L=1.8、聯結車 T=2.5），亦提供介面供使用者自訂並實時聯動。
* **起迄交流道智慧搜尋與自動擴展**：搜尋匝道時，系統自動將範圍擴張為起迄交流道里程 $\pm 2\text{ km}$，確保不漏採連動路段。
* **精確時間戳記與雙重備份**：報表檔名統一為 `VD_traffic_report_YYYYMMDDHHMM.xlsx`，覆蓋舊檔時自動建立時間戳備份至 `backup/` 資料夾。

---

## 📂 專案目錄結構

```text
VD_Traffic_Converter/
├── start_ui.bat                          # 【一鍵啟動與自動安裝腳本】
├── requirements.txt                      # 【Python 依賴套件清單】
├── USER_MANUAL.md                        # 【完整使用者操作手冊 V4.5】
├── README.md                             # 【本專案說明文件】
├── .gitignore                            # 【Git 版控忽略設定檔】
│
├── src_database/                         # 【核心程式與數據庫】
│   ├── generate_traffic_report.py        # 核心自動化分析與報表生成主程式
│   ├── web_server.py                     # Python Web API 服務伺服器
│   ├── target_links.txt                  # 分析目標 LinkID 清單設定檔
│   ├── web_ui/                           # Web 介面前端核心檔 (index.html, app.js, style.css)
│   └── downloads/                        # 歷史 XML.GZ 自動下載快取庫
│
├── reference_files/                      # 【參考規範與對照資料檔】
│   ├── vd_point_list.xml                 # 靜態 VD 點位與 LinkID 對照表
│   ├── Freeway_Interchanges_Full.csv     # 國道交流道里程與起迄資料表
│   └── Expressway_Interchanges.csv       # 快速道路交流道里程資料表
│
├── logs/                                 # 【程式執行歷程 Log】
│   └── run_YYYYMMDD_HHMMSS.log           # 每次執行時之控制台 Console 紀錄檔
│
├── backup/                               # 【自動備份檔案庫】
│   └── VD_traffic_report_YYYYMMDD_YYYYMMDD_HHMMSS.xlsx # 時間戳自動備份檔
│
└── output/                               # 【分析成果輸出】
    └── VD_traffic_report_YYYYMMDDHHMM.xlsx # 產出之綜合分析 Excel 報表
```

---

## 🚀 快速開始與啟動步驟

### 一鍵啟動 (推薦)
1. 雙擊執行專案根目錄下的 **`start_ui.bat`** 批次檔。
2. 系統將自動進行 Python 與套件環境檢測、啟動 Web Server，並自動開啟瀏覽器頁面 `http://localhost:8000`。

### 命令列手動啟動 (開發者)
```bash
# 1. 安裝套件
pip install -r requirements.txt

# 2. 啟動 Web UI 服務
python src_database/web_server.py 8000

# 3. 或直接透過命令行進行單次分析
python src_database/generate_traffic_report.py 20260716 fullday "" 1.0 1.8 2.5
```

---

## 📊 核心計算與邏輯規範

1. **流量與當量換算 (PCPH)**：
   * 小客車 (S)：$1.0$ PCU
   * 大客車 (L)：$1.8$ PCU (預設，可自訂)
   * 聯結車 (T)：$2.5$ PCU (預設，可自訂)
2. **尖峰極值演算法**：
   * **15 分鐘滑動 1 小時視窗**：以 15 分鐘為步階連續掃描 60 分鐘區間，找出最大當量流量 PCU 與同步車速（適用於晨昏峰與 $\le 4$ 小時自訂時段）。
   * **獨立小時法**：適用於全日 24hr 分析或 $> 4$ 小時自訂時段。
3. **旅行速率 (KPH)**：
   * 採車流量加權平均速率：$\text{Weighted Speed} = \frac{\sum (v_i \times q_i)}{\sum q_i}$
4. **雙碼服務水準 (Level of Service, LOS)**：
   * **第一碼 (字母 A~F)**：由 $V/C$ 容積比決定 ($\le 0.25 \to \text{A}$, $\le 0.50 \to \text{B}$, $\le 0.80 \to \text{C}$, $\le 0.90 \to \text{D}$, $\le 1.00 \to \text{E}$, $> 1.00 \to \text{F}$)
   * **第二碼 (數字 1~6)**：由車速比 $V / V_{\text{limit}}$ 決定 ($\ge 0.90 \to 1$, $\ge 0.80 \to 2$, $\ge 0.60 \to 3$, $\ge 0.40 \to 4$, $\ge 0.20 \to 5$, $< 0.20 \to 6$)

---

## 📄 Excel 輸出報表結構 (Worksheet Structure)

1. **`國道主線` Sheet**：包含路段範圍、方向、設計容量 (PCPH)、速限、晨昏峰之 PCU 流量、V/C 比、速率與雙碼服務水準。
2. **`國道匝道` Sheet**：包含交流道名稱、方向、出入別（入口/出口）、目的地、容量、速限與晨昏峰評估結果。
3. **`24小時流量與車速矩陣` Sheet**（全日分析時自動產生）：呈現所有路段在 `0000-0100` 至 `2300-2400` 共 24 小時各自的流量 (PCU) 與速率 (KPH)。
4. **`24小時LOS對照表` Sheet**（全日分析時自動產生）：呈現所有路段 24 小時之雙碼 LOS (A1~F6)，並套用對應 openpyxl 背景填色。
5. **分時 Raw Data Sheets (`0000-0100`, `0100-0200` ...)**：記錄每個偵測器 (VDID) 與路段 (LinkID) 各小時之 S/L/T 車流量、車速、總車輛數、套用自訂 PCE 換算之總當量 (PCU) 及加權速率。

---

## 🌐 雲端部署與遠端存取 (Cloud & Domain Setup)

本專案支援免雲端租賃費用的本機外網穿透：
* 可結合 **Cloudflare Tunnel (`cloudflared`)**，將本機 `http://localhost:8000` 綁定至您的專屬網域（如 `https://vd.yourdomain.com`），享有免費全自動 HTTPS 安全憑證，提供多人隨時遠端連線使用。
* 詳細操作步驟請參閱 **[USER_MANUAL.md 使用者手冊](USER_MANUAL.md)**。
