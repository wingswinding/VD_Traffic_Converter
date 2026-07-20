import xml.etree.ElementTree as ET
import os

xml_path = 'vd_point_list.xml'
links_path = 'src_database/target_links.txt'

with open(links_path, 'r', encoding='utf-8') as f:
    target_links = set([line.strip() for line in f if line.strip()])

print(f"Target links count: {len(target_links)}")

tree = ET.parse(xml_path)
root = tree.getroot()

# Find all VDs and DetectionLinks
found_info = {}
for vd in root.iter('{http://traffic.transportdata.tw/standard/traffic/schema/}VD'):
    vd_id = vd.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}VDID')
    sub_auth = vd.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}SubAuthorityCode')
    vd_type = vd.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}VDType')
    location_type = vd.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}LocationType')
    road_name = vd.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}RoadName')
    
    for dlink in vd.iter('{http://traffic.transportdata.tw/standard/traffic/schema/}DetectionLink'):
        link_id = dlink.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}LinkID')
        bearing = dlink.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}Bearing')
        road_dir = dlink.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}RoadDirection')
        lane_num = dlink.findtext('{http://traffic.transportdata.tw/standard/traffic/schema/}LaneNum')
        
        if link_id in target_links:
            found_info[link_id] = {
                'vd_id': vd_id,
                'road_name': road_name,
                'bearing': bearing,
                'road_dir': road_dir,
                'lane_num': lane_num,
                'vd_type': vd_type,
                'location_type': location_type
            }

print(f"Matched {len(found_info)} links in vd_point_list.xml:")
for lid, info in found_info.items():
    print(f"  LinkID: {lid} -> VD: {info['vd_id']} | Road: {info['road_name']} | Dir: {info['road_dir']} | Lanes: {info['lane_num']}")
