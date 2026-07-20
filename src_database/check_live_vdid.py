import gzip
import xml.etree.ElementTree as ET

sample_file = r"src_database/downloads/20260716/VDLive_0700.xml.gz"
ramp_links = ['0000201001000H', '0000201101040H']

ns = '{http://traffic.transportdata.tw/standard/traffic/schema/}'

with gzip.open(sample_file, 'rb') as f:
    tree = ET.parse(f)
    root = tree.getroot()
    
    for r_link in ramp_links:
        found_vdids = []
        for vd_live in root.iter(f'{ns}VDLive'):
            vd_id = vd_live.findtext(f'{ns}VDID')
            for dlink in vd_live.iter(f'{ns}LinkFlow'):
                link_id = dlink.findtext(f'{ns}LinkID')
                if link_id == r_link:
                    found_vdids.append(vd_id)
        print(f"Ramp LinkID: {r_link} -> Live VDIDs found in XML: {found_vdids}")
