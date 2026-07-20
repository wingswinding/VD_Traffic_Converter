import os
import time
import requests
import datetime
import urllib3

# Disable insecure request warning for bypassing SSL verification
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def download_vd_files(date_str, start_time_str, end_time_str, download_dir='downloads'):
    """
    Downloads historical VD Live XML.GZ files from the Freeway Bureau website.
    
    Parameters:
        date_str (str): Date in 'YYYYMMDD' format (e.g., '20260719')
        start_time_str (str): Start time in 'HH:MM' format (e.g., '07:00')
        end_time_str (str): End time in 'HH:MM' format (e.g., '08:00')
        download_dir (str): Base directory for storing downloads
    """
    base_url = f"https://tisvcloud.freeway.gov.tw/history/motc20/VD/{date_str}/"
    dest_dir = os.path.join(os.path.dirname(__file__), download_dir, date_str)
    os.makedirs(dest_dir, exist_ok=True)
    
    # Parse start and end times
    start_time = datetime.datetime.strptime(start_time_str, "%H:%M")
    end_time = datetime.datetime.strptime(end_time_str, "%H:%M")
    
    # Generate list of minutes to download
    current_time = start_time
    minutes_list = []
    while current_time <= end_time:
        minutes_list.append(current_time.strftime("%H%M"))
        current_time += datetime.timedelta(minutes=1)
        
    print(f"Preparing to download {len(minutes_list)} files for {date_str} from {start_time_str} to {end_time_str}...")
    
    # Setup session with standard browser headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    session = requests.Session()
    session.headers.update(headers)
    
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for idx, hhmm in enumerate(minutes_list):
        filename = f"VDLive_{hhmm}.xml.gz"
        file_url = base_url + filename
        dest_path = os.path.join(dest_dir, filename)
        
        # Cache check: skip if file already exists and is non-empty
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
            skip_count += 1
            continue
            
        print(f"[{idx+1}/{len(minutes_list)}] Downloading {filename}...")
        
        # Polite delay to prevent rate limit blocks
        if idx > 0 and skip_count < idx:
            time.sleep(0.2)
            
        retries = 3
        while retries > 0:
            try:
                # Bypassing SSL verification (verify=False) since Freeway Bureau's certificate verification fails
                response = session.get(file_url, verify=False, timeout=10)
                if response.status_code == 200:
                    with open(dest_path, 'wb') as f:
                        f.write(response.content)
                    success_count += 1
                    break
                elif response.status_code == 404:
                    print(f"  -> File not found (404) at URL: {file_url}")
                    fail_count += 1
                    break
                elif response.status_code == 429:
                    print("  -> Rate limited (429). Sleeping for 5 seconds before retry...")
                    time.sleep(5)
                    retries -= 1
                else:
                    print(f"  -> HTTP Error {response.status_code}. Retrying...")
                    time.sleep(1)
                    retries -= 1
            except Exception as e:
                print(f"  -> Connection error: {e}. Retrying...")
                time.sleep(2)
                retries -= 1
        else:
            print(f"Failed to download {filename} after retries.")
            fail_count += 1
            
    print(f"\nDownload summary for {date_str}:")
    print(f"  - Successfully downloaded: {success_count} files")
    print(f"  - Skipped (already cached): {skip_count} files")
    print(f"  - Failed/Missing: {fail_count} files")
    print(f"Files saved in: {dest_dir}")

if __name__ == '__main__':
    download_vd_files(date_str='20260719', start_time_str='07:00', end_time_str='08:00')
