import gzip
import xml.etree.ElementTree as ET
import os

file_path = os.path.join(os.path.dirname(__file__), 'downloads', '20260719', 'VDLive_0700.xml.gz')

with gzip.open(file_path, 'rb') as f:
    tree = ET.parse(f)
    root = tree.getroot()

ns = {'t': 'http://traffic.transportdata.tw/standard/traffic/schema/'}
lane = root.find('.//t:Lane', ns)
if lane is not None:
    print("--- Lane elements ---")
    for child in lane:
        print(f"Tag: {child.tag.split('}')[-1]}, Text: {child.text or ''}")
        if child.tag.endswith('Vehicles'):
            vehicle = child.find('t:Vehicle', ns)
            if vehicle is not None:
                print("  --- Vehicle elements ---")
                for vchild in vehicle:
                    print(f"  Tag: {vchild.tag.split('}')[-1]}, Text: {vchild.text or ''}")
else:
    print("No Lane found!")
