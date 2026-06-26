import sqlite3
import json

db_path = r"c:\Users\bruno.santos\Downloads\Bruno\Codeba\projetos-tech\balanca-openport\codeba-dashboard\data\auditoria.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT id, created_at, file_names, payload FROM audit_runs WHERE payload LIKE '%RPJ0I50%' LIMIT 5")
runs = cursor.fetchall()

print(f"Runs com RPJ0I50: {len(runs)}")
for r in runs:
    run_id, created_at, file_names, payload_str = r
    payload = json.loads(payload_str)
    ok_items = payload.get("ok", [])
    divs = payload.get("divergencias", [])
    
    print(f"\nRun: {run_id} ({created_at})")
    print(f"Arquivos: {file_names}")
    for item in ok_items:
        if "RPJ0I50" in str(item.values()) or "RPJ0150" in str(item.values()):
            print(f"  OK Item: {json.dumps(item, indent=2)}")
            
    for item in divs:
        if "RPJ0I50" in str(item.values()) or "RPJ0150" in str(item.values()):
            print(f"  DIV Item: {json.dumps(item, indent=2)}")

conn.close()
