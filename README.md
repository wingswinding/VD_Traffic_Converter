# VD 交通量轉換與服務水準分析自動化系統

## 專案概述
本專案為 **VD (Vehicle Detector) 交通量資料轉換、速限比對、道路容量計算與服務水準 (LOS) 分析自動化系統**。
系統自動連結高公局開放資料 API 下載歷史 1 分鐘 XML.GZ 點位數據，擷取特定目標路段 (LinkID)，進行車輛當量 (PCU) 換算、流量加權平均車速統計，並對照交通部《公路容量手冊》與相關規範，自動產出含 **雙碼服務水準 (A1~F6)** 之 OpenPyXL 格式 6 Sheet 綜合 Excel 分析報表。

---

## 專案目錄架構

```text
VD_Traffic_Converter/
├── reference_files/                      # 【參考規範與點位對照檔】
│   ├── 1150526 交通部_路段編碼資料標準第二版.pdf # MOTC 14碼路段編碼標準
│   ├── OUTPUT表格範例.xlsx               # Excel 雙欄標頭報表範例
│   ├── VD 點位一覽表（230320）.xlsx       # 歷史點位對照備份檔
│   ├── vd_point_list.xml                # 靜態 VD 點位與 LinkID 對照表
│   ├── 國道LOS.xlsx                     # 服務水準 A1~F6 雙碼劃分標準
│   ├── 國道各主要路段速限表115.6.odt     # 各主線與匝道路段速限標準
│   └── 道路容量計算.xlsx                 # 運研所主線與匝道容量對照表
│
├── src_database/                         # 【核心程式與數據庫】
│   ├── generate_traffic_report.py        # 核心自動化分析與報表生成主程式
│   ├── target_links.txt                  # 分析目標 LinkID 清單設定檔
│   └── downloads/                        # 歷史 XML.GZ 自動下載快取庫
│
├── output/                               # 【分析成果輸出】
│   └── VD_traffic_report_YYYYMMDD.xlsx   # 產出之 6 Sheet 綜合分析 Excel 報表
│
├── README.md                             # 專案說明文件
└── .gitignore                            # Git 版本控制忽略設定
```

---

## 核心計算與邏輯規範

1. **流量與當量換算 (PCPH)**：
   * 小客車 (S)：$1.0$ PCU
   * 大客車 (L)：$1.5$ PCU
   * 聯結車 (T)：$2.0$ PCU
   * 峰期單小時當量 = (2小時總 PCU) / 2

2. **旅行速率 (KPH)**：
   * 採車流量加權平均速率：$\text{Weighted Speed} = \frac{\sum (v_i \times q_i)}{\sum q_i}$

3. **平常日與假日晨昏峰自動判定**：
   * **平常日 (週一~週五)**：晨峰 `0700-0800`、`0800-0900`；昏峰 `1700-1800`、`1800-1900`
   * **假日 (週六~週日)**：晨峰 `1000-1100`、`1100-1200`；昏峰 `1600-1700`、`1700-1800`

4. **雙碼服務水準 (Level of Service, LOS)**：
   * **第一碼 (字母 A~F)**：由 $V/C$ 比值決定 ($\le 0.25 \to \text{A}$, $\le 0.50 \to \text{B}$, $\le 0.80 \to \text{C}$, $\le 0.90 \to \text{D}$, $\le 1.00 \to \text{E}$, $> 1.00 \to \text{F}$)
   * **第二碼 (數字 1~6)**：由車速比 $V / V_{\text{limit}}$ 決定 ($\ge 0.90 \to 1$, $\ge 0.80 \to 2$, $\ge 0.60 \to 3$, $\ge 0.40 \to 4$, $\ge 0.20 \to 5$, $< 0.20 \to 6$)

5. **報表數值位數格式**：
   * 道路容量 (Capacity)：整數（`#,##0`）
   * 法定速限 (Speed Limit)：整數（`0`）
   * 交通當量/車輛數 (Volume/PCU)：整數（`#,##0`）
   * V/C 比值：小數點後兩位（`0.00`）
   * 速率 (Speed)：小數點後一位（`0.0`）

---

## 報表工作表結構 (6 Sheets)

* **Sheet 1: `國道主線`**（主線容量、速限、晨昏峰流量、V/C、速率、服務水準雙碼標註）
* **Sheet 2: `國道匝道`**（匝道型態、出入別、容量、速限、晨昏峰流量、V/C、速率、服務水準雙碼標註）
* **Sheet 3: `0700-0800`**（Raw Data：含 S/L/T 分別數量與速率、總當量及加權速率）
* **Sheet 4: `0800-0900`**（Raw Data：含 S/L/T 分別數量與速率、總當量及加權速率）
* **Sheet 5: `1700-1800`**（Raw Data：含 S/L/T 分別數量與速率、總當量及加權速率）
* **Sheet 6: `1800-1900`**（Raw Data：含 S/L/T 分別數量與速率、總當量及加權速率）

---

## 快速使用說明

1. **設定分析路段**：在 [src_database/target_links.txt](file:///c:/Users/Owner/Desktop/VD_Traffic_Converter/src_database/target_links.txt) 填入欲分析之 LinkID（每行一筆）。
2. **執行報表生成**：
   ```bash
   python src_database/generate_traffic_report.py <YYYYMMDD>
   ```
   *(例如：`python src_database/generate_traffic_report.py 20260716`)*
3. **取得結果**：產出之 Excel 檔將儲存於 `output/VD_traffic_report_YYYYMMDD.xlsx`。
