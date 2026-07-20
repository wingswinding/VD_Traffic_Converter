import gzip
import xml.etree.ElementTree as ET
import os

file_path = os.path.join(os.path.dirname(__file__), 'downloads', '20260719', 'VDLive_0700.xml.gz')

with gzip.open(file_path, 'rb') as f:
    tree = ET.parse(f)
    root = tree.getroot()

print("XML Root tag:", root.tag)

# Find first few VDLive elements and print their children recursively
count = 0
for elem in root.iter():
    # print tag name without namespace for readability
    clean_tag = elem.tag.split('}')[-1]
    indent = "  " * (clean_tag == 'VDLive' or clean_tag == 'LinkFlow' or clean_tag == 'Lane' or clean_tag == 'Vehicle')
    
    if clean_tag in ['VDLive', 'VDID', 'DataCollectTime', 'LinkID', 'LaneID', 'Speed', 'VehicleType', 'Volume']:
        print(f"{indent}{clean_tag}: {elem.text or ''}")
        if clean_tag == 'Volume':
            count += 1
            if count >= 30:
                break
