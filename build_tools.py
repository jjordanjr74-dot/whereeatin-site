#!/usr/bin/env python3
"""Generate api/tools.json — a static WebMCP typed-tool manifest for Where We Eatin'.

WHY (2026-10-10, Jev cluster): agents that pick WEBSITE-EXPOSED typed tools solved 49/49 browser
tasks vs 25/49 on raw controls (nekuda-ai WindTunnel). This is a GitHub Pages site — no server — so
the contract is a static manifest + the SAME public data embedded once. A client (agent or page)
executes the operations locally: filter/search/lookup by id. Nothing new is served; nothing is
computed per call.

ZERO-NEW-DISCLOSURE GUARANTEE, enforced mechanically by test_tools.py:
  every field written here must already appear verbatim on the built index.html (which itself comes
  from data()), so the manifest cannot disclose anything the human-facing page does not.

Usage: python build_tools.py [--check]   (staleness gate, same convention as the other builders)
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_site  # noqa: E402  reuse the ONE loader; never re-read the DB here

OUT = os.path.join(HERE, "api", "tools.json")

TOOLS = [
    {"name": "list_vendors",
     "description": "The public roster: tracked food trucks with name, cuisine, city, phone, reported area, check-in time, rating, review count, earned badge and paid tier. Same fields the homepage cards show.",
     "inputSchema": {"type": "object", "properties": {
         "city": {"type": "string", "enum": ["Pueblo West", "Colorado Springs", "Cañon City", "Pueblo"]},
         "cuisine": {"type": "string"}},
         "required": [], "additionalProperties": False}},
    {"name": "vendor_lookup",
     "description": "One truck by its roster id (from list_vendors).",
     "inputSchema": {"type": "object", "properties": {"id": {"type": "integer"}},
         "required": ["id"], "additionalProperties": False}},
    {"name": "list_cuisines",
     "description": "Cuisine categories present in the roster right now.",
     "inputSchema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}},
]

# exactly the public card fields — deliberately NO lat/lon (only city + vendor-reported area text
# is shown to humans; coordinates live in the app DB, not the directory), no menu prices.
FIELDS = ("id", "name", "cuisine", "city", "phone", "area", "reported", "rating", "reviews", "badge", "tier")


def build() -> dict:
    d = build_site.data()
    vendors = [{k: t[k] for k in FIELDS} for t in d["trucks"]]
    return {
        "name": "whereeatin-roster",
        "description": "Typed read-only tools over the Where We Eatin' public food-truck directory (Southern Colorado). Static manifest + embedded public data; execution is client-side filtering. No booking, no payment, no PHI, no live GPS.",
        "updated": d["built"],
        "site": "https://whereeatin.com",
        "tools": TOOLS,
        "data": {"vendors": vendors,
                 "cities": d["cities"],
                 "cuisines": sorted({v["cuisine"] for v in vendors if v["cuisine"]})},
    }


def main() -> int:
    payload = json.dumps(build(), indent=1, ensure_ascii=False)
    if "--check" in sys.argv:
        current = open(OUT, encoding="utf-8").read() if os.path.isfile(OUT) else ""
        if current.rstrip("\n") == payload.rstrip("\n"):
            print("tools.json CURRENT")
            return 0
        print("tools.json STALE — run: python build_tools.py")
        return 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(payload + "\n")
    os.replace(tmp, OUT)  # atomic: a killed run can't leave a half-written manifest
    n = json.loads(payload)["data"]["vendors"]
    print(f"wrote {OUT} ({len(n)} vendors, {len(TOOLS)} tools)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
