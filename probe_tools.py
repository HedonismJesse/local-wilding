"""Beat-0 for the video: what can this key actually use?

GET /api/v1/tools — the gateway's own availability surface: per-tool
available + reason + accepted wire spellings. Free call, real receipt.
"""

import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

import urllib.request
import os

req = urllib.request.Request(
    "https://api.otari.ai/api/v1/tools",
    headers={"Authorization": f"Bearer {os.environ['OTARI_API_KEY']}"},
)
body = json.loads(urllib.request.urlopen(req, timeout=30).read())
for t in body["data"]:
    print(f"\n  {t['id']}")
    print(f"    available : {t['available']}   reason: {t.get('reason')}")
    print(f"    accepts   : {', '.join(t.get('accepted_types', []))}")
    print(f"    input     : {json.dumps(t.get('input_schema', {}).get('properties', {}))[:180]}")
