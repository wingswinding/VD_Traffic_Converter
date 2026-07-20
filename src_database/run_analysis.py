import os
import sys

# Ensure src_database is in Python path
sys.path.append(os.path.dirname(__file__))

from downloader import download_vd_files
from import_data import import_vd_data
from query_report import run_hourly_report

def main():
    date_str = '20260716'
    
    print(f"=== Starting Traffic Pipeline for {date_str} ===")
    
    # 1. Download Morning Peak Files (07:00 - 09:00)
    print("\n--- Downloading Morning Peak (07:00 - 09:00) ---")
    download_vd_files(date_str=date_str, start_time_str='07:00', end_time_str='09:00')
    
    # 2. Download Evening Peak Files (17:00 - 19:00)
    print("\n--- Downloading Evening Peak (17:00 - 19:00) ---")
    download_vd_files(date_str=date_str, start_time_str='17:00', end_time_str='19:00')
    
    # 3. Import data into SQLite database
    print("\n--- Importing Data into SQLite Database ---")
    import_vd_data(date_str=date_str)
    
    # 4. Generate Reports for each Peak Hour
    print("\n--- Generating Reports ---")
    print("\n[Morning Peak Hour 1]")
    run_hourly_report(date_str=date_str, start_hour='07:00', end_hour='08:00')
    
    print("\n[Morning Peak Hour 2]")
    run_hourly_report(date_str=date_str, start_hour='08:00', end_hour='09:00')
    
    print("\n[Evening Peak Hour 1]")
    run_hourly_report(date_str=date_str, start_hour='17:00', end_hour='18:00')
    
    print("\n[Evening Peak Hour 2]")
    run_hourly_report(date_str=date_str, start_hour='18:00', end_hour='19:00')
    
    print("\n=== Pipeline Complete ===")

if __name__ == '__main__':
    main()
