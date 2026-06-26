import json

f_path = r"C:\Users\bruno.santos\.gemini\antigravity-ide\brain\18a5fe82-0667-4b32-bdcc-4ad80a1222aa\.system_generated\logs\transcript.jsonl"
with open(f_path, encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        if obj.get("type") == "USER_INPUT":
            print(f"=== STEP {obj.get('step_index')} ===")
            print(obj.get("content"))
            print("-" * 50)
