import os
import zipfile
import re

search_dir = r"C:\Users\bruno.santos\Downloads"
query = b"RPJ0"

print(f"Starting fast search for {query} in {search_dir}...")

for root, dirs, files in os.walk(search_dir):
    for name in files:
        if name.lower().endswith(".xlsx"):
            path = os.path.join(root, name)
            try:
                with zipfile.ZipFile(path, 'r') as z:
                    # Search inside sharedStrings.xml (where text is stored in Excel)
                    for zinfo in z.infolist():
                        if "sharedStrings.xml" in zinfo.filename or "sheet" in zinfo.filename:
                            content = z.read(zinfo.filename)
                            if query in content:
                                print(f"Found match in: {path} (file: {zinfo.filename})")
                                break
            except Exception as e:
                # ignore corrupt zip files
                pass
