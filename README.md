# VD 交通量轉換與自動化處理系統

## 專案概述
這是一個 VD 交通量資料轉換與自動化處理系統，主要用於將下載的車輛偵測器（VD）原始 XML 資料進行解析，擷取特定路段（LinkID）的交通量，並自動化整併成 5 分鐘或 60 分鐘週期的 CSV/Excel 分析報表。本專案目前已由舊版 Excel 轉檔模式，演進至新版的 **SQLite 資料庫儲存與運算模式**，可支援從高公局網站直接下載 1 分鐘壓縮檔並進行加權平均車速統計。

## 技術棧
- **資料庫與資料處理**：SQLite3, Python (Pandas)
- **網路爬蟲與下載**：Requests (支援 Keep-Alive, Rate-limiting, User-Agent 偽裝)
- **XML 解析**：Python `xml.etree.ElementTree` 串流解析
- **傳統工具（舊版備份）**：Windows Executables (.exe / PyInstaller 封裝)
- **環境規格**：Python 3.10.x+

## 專案目錄架構
- [src_database/](file:///c:/Users/Owner/Desktop/VD_Traffic_Converter/src_database/)：新版資料庫核心模組
  - [db_setup.py](file:///c:/Users/Owner/Desktop/VD_Traffic_Converter/src_database/db_setup.py)：SQLite 資料庫初始化與索引建立
  - [downloader.py](file:///c:/Users/Owner/Desktop/VD_Traffic_Converter/src_database/downloader.py)：高公局 1 分鐘 XML.GZ 歷史資料 polite 下載器
  - [import_data.py](file:///c:/Users/Owner/Desktop/VD_Traffic_Converter/src_database/import_data.py)：XML.GZ 串流解析與目標路段高效匯入器
  - [query_report.py](file:///c:/Users/Owner/Desktop/VD_Traffic_Converter/src_database/query_report.py)：加權平均車速與 PCU 報表 SQL/Pandas 查詢器
  - [target_links.txt](file:///c:/Users/Owner/Desktop/VD_Traffic_Converter/src_database/target_links.txt)：要進行過濾與計算的目標 LinkID 列表
- [legacy_files/](file:///c:/Users/Owner/Desktop/VD_Traffic_Converter/legacy_files/)：舊版執行檔與傳統工具備份目錄
- [VD（空白）231120 車種代號修正/](file:///c:/Users/Owner/Desktop/VD_Traffic_Converter/VD（空白）231120%20車種代號修正/)：舊版 Excel 範本與手動統計結果
- [VD 點位一覽表（230320）.xlsx](file:///c:/Users/Owner/Desktop/VD_Traffic_Converter/VD%20點位一覽表（230320）.xlsx)：全國 VD 偵測器與 LinkID 對照表

## 使用說明 (資料庫模式)

1. **路段設定**：在 [target_links.txt](file:///c:/Users/Owner/Desktop/VD_Traffic_Converter/src_database/target_links.txt) 填入欲查詢的路段 LinkID（每行一筆）。
2. **下載資料**：
   執行 `downloader.py`（預設下載 2026/07/19 07:00 ~ 08:00 間 61 個分鐘檔至 `downloads/` 暫存資料夾）：
   ```bash
   python src_database/downloader.py
   ```
3. **匯入資料庫**：
   執行 `import_data.py` 將 XML 資料過濾並寫入 `vd_traffic.db`：
   ```bash
   python src_database/import_data.py
   ```
4. **產出報表**：
   執行 `query_report.py` 產出 PCU 交通量與加權平均速度報表：
   ```bash
   python src_database/query_report.py
   ```

## 行為準則
- 溝通請全程使用繁體中文。
- 在修改系統核心轉檔邏輯、編寫腳本或優化 Excel 計算範本前，請先列出思考過程與預計執行步驟。
- 嚴格遵守安全性設定，若需執行具破壞性或全機層級 (Full machine) 的終端機指令，必須先請求確認。
- 每次修正/改版轉檔程式碼或調整 Excel 範本前，必須備份原始檔案到 `backup` 資料夾，尾綴為 `_YYYYMMDD_HHMMSS`。
