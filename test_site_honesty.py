"""Honesty, navigation, social-card and template-leak gates for the public static site.

The live-status tests run against a TEMP COPY of vendors_row.db (the real DB is read-only to this repo).
"""
import datetime as dt
import glob
import os
import re
import shutil
import sqlite3
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
VR = os.path.join(os.path.dirname(HERE), "vendors_row")
REAL_DB = os.path.join(VR, "vendors_row.db")
sys.path.insert(0, HERE)
sys.path.insert(0, VR)

PAGES = ["index.html", "radar/index.html", "reviews/index.html", "promotions/index.html", "travel/index.html",
         "trucks/index.html", "list-your-truck/index.html", "privacy/index.html", "404.html"]


def _truck_pages():
    return sorted(glob.glob(os.path.join(HERE, "trucks", "*", "index.html")))


def _city_pages():
    return sorted(glob.glob(os.path.join(HERE, "food-trucks-*-co", "index.html")))


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    dst = tmp_path / "vendors_row.db"
    shutil.copy(REAL_DB, dst)
    import build_site as BS
    import build_radar as BR
    monkeypatch.setattr(BS, "DB", str(dst))
    monkeypatch.setattr(BR, "DB", str(dst))
    monkeypatch.setattr(BR, "VENDORS_DB", str(dst))
    return str(dst)


def _write(db, sql, args=()):
    con = sqlite3.connect(db)
    con.execute(sql, args)
    con.commit()
    con.close()


def test_no_truck_is_live_without_fresh_checkin(temp_db):
    # stale everything: old serving status and old check-in coordinates must NOT read as live
    _write(temp_db, "UPDATE vendors SET serving_status='serving', status_updated_at='2020-01-01T00:00:00+00:00', "
                    "location_source='vendor-checkin', location_updated_at='2020-01-01T00:00:00+00:00', "
                    "checkin_lat=38.25, checkin_lon=-104.6")
    import build_site as BS
    import build_listing as BL
    import build_radar as BR
    home = BS.build()
    assert "Open right now" not in home
    assert "pin-live" not in home
    assert "serving now" not in home.lower()
    assert "No trucks have checked in right now" in home
    d = BS.data()
    assert d["live_count"] == 0
    assert d["trucks"], "temp DB should still list trucks"
    for t in d["trucks"]:
        page = BL.page(t, [], "")
        assert "Open right now" not in page
        assert "pin-live" not in page and "Checked in" not in page and "Serving now" not in page
        assert "Usually around" in page
    radar = BR.build()
    assert "Open right now" not in radar
    assert '"serving": true' not in radar
    assert "No trucks have checked in right now" in radar


def test_fresh_checkin_is_the_only_thing_that_goes_live(temp_db):
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    _write(temp_db, "UPDATE vendors SET serving_status='serving', status_updated_at=?, location_source='vendor-checkin', "
                    "location_updated_at=?, checkin_lat=38.2544, checkin_lon=-104.6091 WHERE id=14", (now, now))
    import build_site as BS
    import build_listing as BL
    d = BS.data()
    assert d["live_count"] == 1
    live = [t for t in d["trucks"] if t["live"]]
    assert [t["name"] for t in live] == ["Big Papa's Grill"]
    assert "1 truck checked in or confirmed serving" in BS.build()
    assert "pin-live" in BL.page(live[0], [], "")


def test_every_built_page_has_nav_canonical_and_social_tags():
    pages = [os.path.join(HERE, p) for p in PAGES] + _truck_pages() + _city_pages()
    assert len(pages) >= 29, pages
    for path in pages:
        assert os.path.isfile(path), path
        s = _read(path)
        rel = os.path.relpath(path, HERE)
        assert 'class="sitnav"' in s, f"{rel}: no shared nav"
        assert 'property="og:title"' in s, f"{rel}: no og:title"
        assert 'rel="canonical"' in s, f"{rel}: no canonical"
        assert 'name="twitter:card"' in s, f"{rel}: no twitter:card"
        assert 'property="og:image"' in s and 'property="og:url"' in s, f"{rel}: og image/url missing"
        assert 'id="sitfoot"' in s, f"{rel}: no shared footer"


def test_no_template_placeholders_leak_into_built_html():
    pages = [os.path.join(HERE, p) for p in PAGES] + _truck_pages() + _city_pages()
    for path in pages:
        s = _read(path)
        rel = os.path.relpath(path, HERE)
        assert not re.findall(r"__[A-Z][A-Z_]+__", s), f"{rel}: placeholder token survived"
        # braces are legitimate inside <style>/<script> bodies; a template leak shows up in markup text
        markup = re.sub(r"(?is)<(style|script)\b.*?</\1>", "", s)
        assert "{{" not in markup and "}}" not in markup, f"{rel}: doubled-brace template leak"
        assert not re.findall(r"\{(?:site_base|BASE|canonical|DESK|REVIEW_DESK|d|t)[\w.\[\]'\"]*\}", s), rel


def test_no_built_page_says_open_right_now():
    hits = []
    for p in PAGES:
        if "Open right now" in _read(os.path.join(HERE, p)):
            hits.append(p)
    for p in _truck_pages() + _city_pages():
        if "Open right now" in _read(p):
            hits.append(p)
    assert hits == [], hits


def test_squadpoll_and_city_hubs_stay_built():
    import site_base
    home = _read(os.path.join(HERE, "index.html"))
    sitemap = _read(os.path.join(HERE, "sitemap.xml"))
    assert 'id="squadpoll"' in home
    assert 'id="community-hub"' in home
    assert 'assets/share.js' in home
    assert 'https://coloradobounceclub.com/' in home
    assert 'www.coloradobounceclub.com' not in home
    assert len(site_base.CITY_HUBS) == 11
    for h in site_base.CITY_HUBS:
        assert h["path"] in home, f"{h['path']} missing from index.html"
        assert f"https://whereeatin.com/{h['path']}" in sitemap, f"{h['path']} missing from sitemap.xml"
        city_file = os.path.join(HERE, h["path"], "index.html")
        assert os.path.isfile(city_file), f"{city_file} missing on disk"


def test_truck_pages_share_favorites_and_per_truck_card():
    sitemap = _read(os.path.join(HERE, "sitemap.xml"))
    for path in _truck_pages():
        s = _read(path)
        rel = os.path.relpath(path, HERE)
        slug = os.path.basename(os.path.dirname(path))
        assert 'data-share="1"' in s and "/assets/share.js" in s, rel
        assert 'data-fav="' + slug + '"' in s and "/assets/favorites.js" in s, rel
        assert f"https://whereeatin.com/trucks/{slug}/" in sitemap, f"{slug} missing from sitemap"
        assert f'<link rel="canonical" href="https://whereeatin.com/trucks/{slug}/">' in s, rel
    for js in ("assets/favorites.js", "assets/share.js"):
        code = _read(os.path.join(HERE, js))
        for banned in ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket"):
            assert banned not in code, f"{js} must stay client-side only ({banned})"
    assert "localStorage" in _read(os.path.join(HERE, "assets", "favorites.js"))
