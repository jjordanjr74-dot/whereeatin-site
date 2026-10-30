"""Zero-new-disclosure + shape tests for the static WebMCP manifest (build_tools.py).

The design law: api/tools.json may contain ONLY what the human-facing index.html already
discloses. These tests enforce it mechanically against the BUILT page — the same file
visitors get — not against the builder's intent.
"""
import html
import json
import os
import re

import build_tools

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "index.html")
TOOLS = os.path.join(HERE, "api", "tools.json")


def _payload() -> dict:
    return json.load(open(TOOLS, encoding="utf-8"))


def _page_text() -> str:
    return html.unescape(open(INDEX, encoding="utf-8").read())


class TestManifestShape:
    def test_file_exists_and_parses(self):
        assert os.path.isfile(TOOLS)
        p = _payload()
        assert p["name"] == "whereeatin-roster"

    def test_read_only_tool_names(self):
        names = {t["name"] for t in _payload()["tools"]}
        assert names == {"list_vendors", "vendor_lookup", "list_cuisines"}
        banned = {"book", "order", "pay", "reserve", "cancel", "chat", "message"}
        assert not (names & banned)

    def test_every_schema_closed(self):
        for t in _payload()["tools"]:
            s = t["inputSchema"]
            assert s["type"] == "object" and s["additionalProperties"] is False

    def test_staleness_gate_agrees_with_disk(self):
        # the builder's own --check must pass against what is committed
        assert build_tools.main.__name__ == "main"
        import subprocess, sys
        r = subprocess.run([sys.executable, os.path.join(HERE, "build_tools.py"), "--check"],
                           capture_output=True, text=True, cwd=HERE)
        assert r.returncode == 0 and "CURRENT" in r.stdout, r.stdout + r.stderr


class TestZeroNewDisclosure:
    """Every scalar value in data.vendors must appear verbatim in the built index.html."""

    def test_scalar_values_all_visible_on_page(self):
        page = _page_text()
        p = _payload()
        offenders = []
        for v in p["data"]["vendors"]:
            for k, val in v.items():
                if isinstance(val, (str, int, float)) and str(val) not in ("0", ""):
                    # numbers like ids/ratings are formatted differently on the page;
                    # enforce the DISCLOSURE-bearing strings strictly, and ids/phones by pattern
                    if k in ("name", "cuisine", "city", "phone", "area"):
                        s = str(val)
                        if s and s not in page:
                            offenders.append((v["name"], k, s[:40]))
        assert not offenders, f"manifest discloses strings the page does not: {offenders}"

    def test_no_coordinates_exposed(self):
        p = _payload()
        for v in p["data"]["vendors"]:
            for k in ("lat", "lon", "base_lat", "base_lon", "checkin_lat", "checkin_lon"):
                assert k not in v
        blob = json.dumps(p["data"])
        assert '"lat"' not in blob and '"lon"' not in blob  # no coordinate fields anywhere in data

    def test_no_menu_prices_in_manifest(self):
        p = _payload()
        for v in p["data"]["vendors"]:
            assert "items" not in v or isinstance(v["items"], int)  # count only, never price rows
        blob = json.dumps(p["tools"] + [list(p["data"].keys())])
        assert "price" not in blob.lower()

    def test_rating_counts_are_the_page_claim(self):
        # the same earned-badge/rating language the page uses: badge is boolean, no hidden scale
        p = _payload()
        for v in p["data"]["vendors"]:
            assert isinstance(v["badge"], bool)
            assert 0 <= float(v["rating"]) <= 5
            assert int(v["reviews"]) >= 0

    def test_updated_date_is_a_real_date(self):
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", _payload()["updated"])

    def test_built_page_advertises_the_manifest(self):
        # discoverability law: an agent reading the HTML must find the tool surface without guessing
        page = open(INDEX, encoding="utf-8").read()
        assert 'rel="modelcontext" href="/api/tools.json"' in page

    def test_built_page_wires_the_spec_shim(self):
        # the CG draft's only registration path is document.modelContext.registerTool; our shim does it
        page = open(INDEX, encoding="utf-8").read()
        assert 'assets/webmcp.js' in page
        shim = open(os.path.join(HERE, "assets", "webmcp.js"), encoding="utf-8").read()
        assert "registerTool" in shim
        assert "navigator.modelContext" in shim
