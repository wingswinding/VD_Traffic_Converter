import os
import xml.etree.ElementTree as ET

target_links_file = r"src_database/target_links.txt"
vd_point_file = "vd_point_list.xml"

with open(target_links_file, 'r', encoding='utf-8') as f:
    target_links = [line.strip() for line in f if line.strip()]

tree = ET.parse(vd_point_file)
root = tree.getroot()
ns = '{http://traffic.transportdata.tw/standard/traffic/schema/}'

# Build full mapping of LinkID -> List of VDIDs from vd_point_list.xml
link_to_vds = {}
for vd in root.iter(f'{ns}VD'):
    vd_id = vd.findtext(f'{ns}VDID')
    for dlink in vd.iter(f'{ns}DetectionLink'):
        link_id = dlink.findtext(f'{ns}LinkID')
        if link_id:
            if link_id not in link_to_vds:
                link_to_vds[link_id] = []
            link_to_vds[link_id].append(vd_id)

print(f"Total target links: {len(target_links)}")
print(f"Total links registered in vd_point_list.xml: {len(link_to_vds)}")

missing_vds = []
found_vds = []

for lid in target_links:
    if lid in link_to_vds:
        found_vds.append((lid, link_to_vds[lid]))
    else:
        missing_vds.append(lid)

print(f"\n--- Matched Target Links ({len(found_vds)}) ---")
for lid, vds in found_vds:
    print(f"LinkID: {lid} -> VDID: {vds}")

print(f"\n--- Missing VDIDs in vd_point_list.xml ({len(missing_vds)}) ---")
for lid in missing_vds:
    print(f"LinkID: {lid}")
