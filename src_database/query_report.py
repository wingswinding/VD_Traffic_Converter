import sqlite3
import pandas as pd
import numpy as np
import os

def run_hourly_report(date_str, start_hour='07:00', end_hour='08:00', db_file='vd_traffic.db'):
    db_path = os.path.join(os.path.dirname(__file__), db_file)
    
    if not os.path.exists(db_path):
        print(f"Error: Database {db_path} does not exist!")
        return
        
    conn = sqlite3.connect(db_path)
    
    # Query all raw traffic records for the target date and hour range
    query = """
        SELECT timestamp, vd_id, link_id, vehicle_type, volume, speed 
        FROM traffic_records
        WHERE timestamp >= ? AND timestamp < ?
    """
    
    # Format dates
    # E.g. date_str='20260719', start_hour='07:00' -> '2026-07-19 07:00:00'
    date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    start_time = f"{date_formatted} {start_hour}:00"
    end_time = f"{date_formatted} {end_hour}:00"
    
    df = pd.read_sql_query(query, conn, params=(start_time, end_time))
    conn.close()
    
    if df.empty:
        print(f"No traffic data found in database for time range: {start_time} to {end_time}")
        return
        
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Define 5-minute binning function
    # E.g., '07:00:00' to '07:04:00' -> bin '0705'
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
    
    # Calculate 5-minute aggregates for each (vd_id, link_id, bin, vehicle_type)
    # 1. Volume sum
    # 2. Average Speed (only for rows where speed > 0)
    def calc_mean_speed(x):
        valid_speeds = x[x > 0]
        return valid_speeds.mean() if not valid_speeds.empty else 0.0
        
    agg_df = df_filtered.groupby(['vd_id', 'link_id', 'bin', 'vehicle_type']).agg(
        vol=('volume', 'sum'),
        avg_spd=('speed', calc_mean_speed)
    ).reset_index()
    
    # Calculate Volume * Speed for each vehicle type in each bin
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
    
    # Aggregate over the whole hour for each (vd_id, link_id)
    hourly_report = merged_bins.groupby(['vd_id', 'link_id']).agg(
        S_total_vol=('S_vol', 'sum'),
        L_total_vol=('L_vol', 'sum'),
        T_total_vol=('T_vol', 'sum'),
        Total_Vehicles=('S_vol', 'sum'), # will re-calculate below
        Total_PCU=('bin_pcu', 'sum'),
        Total_Vol_Speed_Sum=('bin_vol_speed_sum', 'sum')
    ).reset_index()
    
    hourly_report['Total_Vehicles'] = hourly_report['S_total_vol'] + hourly_report['L_total_vol'] + hourly_report['T_total_vol']
    
    # Average speed calculation: SUM(bin_vol_speed_sum) / SUM(bin_total_volume)
    hourly_report['Average_Speed_KPH'] = hourly_report['Total_Vol_Speed_Sum'] / hourly_report['Total_Vehicles']
    hourly_report['Average_Speed_KPH'] = hourly_report['Average_Speed_KPH'].fillna(0.0)
    
    print(f"\n=================== HOURLY TRAFFIC REPORT ({start_hour} - {end_hour}) ===================")
    print(f"Date: {date_formatted}")
    print(hourly_report[['vd_id', 'link_id', 'S_total_vol', 'L_total_vol', 'T_total_vol', 'Total_Vehicles', 'Total_PCU', 'Average_Speed_KPH']].to_string(index=False))
    print("==========================================================================")

if __name__ == '__main__':
    run_hourly_report(date_str='20260719')
