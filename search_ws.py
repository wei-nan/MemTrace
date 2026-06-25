with open("C:/Users/wilia/.gemini/antigravity/brain/89d348c4-2b33-464e-84e5-b217f256967b/.system_generated/steps/227/output.txt", encoding="utf-8") as f:
    content = f.read()

import json
data = json.loads(content)
for idx, ws in enumerate(data):
    if ws.get("id") == "ws_26d8f586":
        print(f"Index: {idx}")
        print(json.dumps(ws, indent=2, ensure_ascii=False))
