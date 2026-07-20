import xml.etree.ElementTree as ET

xml_path = 'vd_point_list.xml'
links_path = 'src_database/target_links.txt'

with open(links_path, 'r', encoding='utf-8') as f:
    target_links = [line.strip() for line in f if line.strip()]

unmatched = ['0000201001000H', '0000201101040H']

tree = ET.parse(xml_path)
root = tree.getroot()

print("Searching for unmatched links or similar links in vd_point_list.xml:")
for vd in root.iter('{http://traffic.transportdata.tw/standard/traffic/schema/}VD'):
    vd_id = vd.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}VDID')
    road_name = vd.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}RoadName')
    
    for dlink in vd.iter('{http://traffic.transportdata.tw/standard/traffic/schema/}DetectionLink'):
        link_id = dlink.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}LinkID')
        if any(u in link_id or link_id in u for u in unmatched) or '0000201' in link_id:
            print(f"VD: {vd_id} | Road: {road_name} | LinkID: {link_id}")
