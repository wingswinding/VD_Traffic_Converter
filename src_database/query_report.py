import sqlite3
import pandas as pd
import numpy as np
import os

def run_hourly_report(date_str, start_hour='07:00', end_hour='08:00', db_file='vd_traffic.db', export_excel=True):
    db_path = os.path.join(os.path.dirname(__file__), db_file)
    
    if not os.path.exists(db_path):
        print(f"Error: Database {db_path} does not exist!")
        return None
        
    conn = sqlite3.connect(db_path)
    
    # Query all raw traffic records for the target date and hour range
    query = """
        SELECT timestamp, vd_id, link_id, vehicle_type, volume, speed 
        FROM traffic_records
        WHERE timestamp >= ? AND timestamp < ?
    """
    
    date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    start_time = f"{date_formatted} {start_hour}:00"
    end_time = f"{date_formatted} {end_hour}:00"
    
    df = pd.read_sql_query(query, conn, params=(start_time, end_time))
    conn.close()
    
    if df.empty:
        print(f"No traffic data found in database for time range: {start_time} to {end_time}")
        return None
        
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Define 5-minute binning function
    def get_5min_bin(dt):
        hour = dt.hour
        minute = dt.minute
        bin_min = ((minute // 5) + 1) * 5
        if bin_min == 60:
            return f"{hour+1:02d}00"
        else:
            return f"{hour:02d}{bin_min:02d}"
            
    df['bin'] = df['timestamp'].apply(get_5min_bin)
    
    # Filter only target vehicle types (S, L, T)
    df_filtered = df[df['vehicle_type'].isin(['S', 'L', 'T'])].copy()
    
    # Calculate 5-minute aggregates
    def calc_mean_speed(x):
        valid_speeds = x[x > 0]
        return valid_speeds.mean() if not valid_speeds.empty else 0.0
        
    agg_df = df_filtered.groupby(['vd_id', 'link_id', 'bin', 'vehicle_type']).agg(
        vol=('volume', 'sum'),
        avg_spd=('speed', calc_mean_speed)
    ).reset_index()
    
    # Calculate Volume * Speed
    agg_df['vol_speed'] = agg_df['vol'] * agg_df['avg_spd']
    
    # Pivot vehicle types (S, L, T) into columns
    pivot_vol = agg_df.pivot(index=['vd_id', 'link_id', 'bin'], columns='vehicle_type', values='vol').fillna(0).reset_index()
    pivot_vspd = agg_df.pivot(index=['vd_id', 'link_id', 'bin'], columns='vehicle_type', values='vol_speed').fillna(0).reset_index()
    
    # Merge pivoted volumes and volume-speeds
    merged_bins = pd.merge(pivot_vol, pivot_vspd, on=['vd_id', 'link_id', 'bin'], suffixes=('_vol', '_vspd'))
    
    # Ensure S, L, T columns exist
    for col in ['S_vol', 'L_vol', 'T_vol', 'S_vspd', 'L_vspd', 'T_vspd']:
        if col not in merged_bins.columns:
            merged_bins[col] = 0.0
            
    # Calculate 5-minute PCU: S*1 + L*1.8 + T*2.5
    merged_bins['bin_pcu'] = merged_bins['S_vol']*1.0 + merged_bins['L_vol']*1.8 + merged_bins['T_vol']*2.5
    # Calculate bin total volume * speed
    merged_bins['bin_vol_speed_sum'] = merged_bins['S_vspd'] + merged_bins['L_vspd'] + merged_bins['T_vspd']
    
    # Aggregate over the whole hour
    hourly_report = merged_bins.groupby(['vd_id', 'link_id']).agg(
        S_total_vol=('S_vol', 'sum'),
        L_total_vol=('L_vol', 'sum'),
        T_total_vol=('T_vol', 'sum'),
        Total_Vehicles=('S_vol', 'sum'),
        Total_PCU=('bin_pcu', 'sum'),
        Total_Vol_Speed_Sum=('bin_vol_speed_sum', 'sum')
    ).reset_index()
    
    hourly_report['Total_Vehicles'] = hourly_report['S_total_vol'] + hourly_report['L_total_vol'] + hourly_report['T_total_vol']
    hourly_report['Average_Speed_KPH'] = hourly_report['Total_Vol_Speed_Sum'] / hourly_report['Total_Vehicles']
    hourly_report['Average_Speed_KPH'] = hourly_report['Average_Speed_KPH'].fillna(0.0).round(2)
    
    # Drop intermediate columns
    hourly_report = hourly_report.drop(columns=['Total_Vol_Speed_Sum'])
    
    # Rename columns for clarity
    hourly_report.columns = [
        '偵測器代碼 (VDID)', '路段代碼 (LinkID)', 
        '小客車數量 (S)', '大客車數量 (L)', '聯結車數量 (T)', 
        '總車輛數 (輛)', '總當量 (PCU)', '加權平均車速 (KPH)'
    ]
    
    print(f"\n=================== HOURLY TRAFFIC REPORT ({start_hour} - {end_hour}) ===================")
    print(f"Date: {date_formatted}")
    print(hourly_report.to_string(index=False))
    print("==========================================================================")
    
    return hourly_report

def export_all_reports(date_str, ranges=[('07:00', '08:00'), ('08:00', '09:00'), ('17:00', '18:00'), ('18:00', '19:00')]):
    project_root = os.path.dirname(os.path.dirname(__file__))
    output_dir = os.path.join(project_root, 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    excel_path = os.path.join(output_dir, f"VD_traffic_report_{date_str}.xlsx")
    
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        for start_hour, end_hour in ranges:
            report_df = run_hourly_report(date_str, start_hour, end_hour)
            if report_df is not None:
                sheet_name = f"{start_hour.replace(':', '')}-{end_hour.replace(':', '')}"
                report_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
    print(f"\n[Export OK] Excel report successfully generated and saved to:")
    print(f"  -> {excel_path}")

if __name__ == '__main__':
    export_all_reports(date_str='20260719', ranges=[('07:00', '08:00')])
