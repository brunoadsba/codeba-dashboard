import zipfile
import xml.etree.ElementTree as ET

def get_xlsx_data(file_path):
    print(f"--- {file_path} ---")
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            # Get shared strings
            shared_strings = []
            if 'xl/sharedStrings.xml' in z.namelist():
                with z.open('xl/sharedStrings.xml') as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                    for si in root.findall('ns:si', ns):
                        t = si.find('ns:t', ns)
                        if t is not None and t.text is not None:
                            shared_strings.append(t.text)
                        else:
                            # Sometimes text is in <r><t>
                            parts = []
                            for r in si.findall('ns:r', ns):
                                t2 = r.find('ns:t', ns)
                                if t2 is not None and t2.text is not None:
                                    parts.append(t2.text)
                            shared_strings.append(''.join(parts))
                            
            # Parse first sheet
            with z.open('xl/worksheets/sheet1.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                
                rows = root.find('ns:sheetData', ns).findall('ns:row', ns)
                if not rows:
                    print("No rows found")
                    return 0
                    
                # Get headers
                headers = []
                for c in rows[0].findall('ns:c', ns):
                    v = c.find('ns:v', ns)
                    if v is not None:
                        val = int(v.text)
                        if c.attrib.get('t') == 's':
                            headers.append(shared_strings[val])
                        else:
                            headers.append(str(val))
                    else:
                        headers.append("")
                        
                print(f"Headers: {headers}")
                
                # Find weight col
                weight_idx = -1
                for i, h in enumerate(headers):
                    if h in ['Peso Líquido', 'Peso (Kg)', 'Peso Bruto', 'Quantidade', 'Volume']:
                        weight_idx = i
                        print(f"Found weight column: {h} at index {i}")
                        break
                        
                if weight_idx == -1:
                    print("Could not find weight column")
                    return 0
                    
                total = 0.0
                for row in rows[1:]:
                    cells = row.findall('ns:c', ns)
                    if weight_idx < len(cells):
                        c = cells[weight_idx]
                        v = c.find('ns:v', ns)
                        if v is not None:
                            val = v.text
                            # if it's a shared string
                            if c.attrib.get('t') == 's':
                                val_str = shared_strings[int(val)]
                                # parse as float
                                try:
                                    # handle comma
                                    val_str = val_str.replace('.', '').replace(',', '.')
                                    total += float(val_str)
                                except:
                                    pass
                            else:
                                total += float(val)
                print(f"Total: {total}")
                return total
    except Exception as e:
        print(f"Error parsing xlsx: {e}")
        return 0

if __name__ == '__main__':
    get_xlsx_data(r"y:\Nazaro\codeba-dashboard-main\data\ÓXIDO DE MAGNÉSIO - MAGNESITA.xlsx")
    get_xlsx_data(r"y:\Nazaro\codeba-dashboard-main\data\LITIO - CBL.xlsx")
