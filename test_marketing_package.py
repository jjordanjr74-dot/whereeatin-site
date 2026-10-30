"""Mechanical acceptance checks for the public marketing/sign-up surfaces.

Run: python test_marketing_package.py
Vendor intake persistence is exercised against a temporary database copy.
"""
from __future__ import annotations

import html as html_lib
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENDORS = HERE.parent / "vendors_row"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(VENDORS))

import build_promotions  # noqa: E402
import build_site  # noqa: E402
import vendor_intake  # noqa: E402


def test_customer_page_uses_roster_and_only_real_offers():
    page = build_promotions.build()
    vendors = build_promotions.roster.load()
    assert len(vendors) >= 9
    assert all(html_lib.escape(v["name"]) in page for v in vendors)
    assert 'href="https://whereeatin.com/radar/"' in page
    assert 'href="https://whereeatin.com/list-your-truck/"' in page
    assert "No time-limited offers are published here" in page
    assert "authenticated vendor offer-submission flow" in page
    assert "order ahead" not in page.lower()
    assert "gluten-free" not in page.lower()
    assert "free food" not in page.lower()


def test_homepage_discloses_price_confirmation_state_and_promotion_cta():
    page = build_site.build()
    data = build_site.data()
    assert data["confirmed_prices"] == 0
    assert "menu items listed · 0 prices vendor-confirmed" in page
    assert "prices confirmed by the truck, item by item" not in page
    assert "Specials" in page and 'href="promotions/"' in page


def test_signup_page_routes_to_desk_bot_not_gateway_bot():
    page = (HERE / "list-your-truck" / "index.html").read_text(encoding="utf-8").lower()
    assert "sheba_telegram_bot" in page
    assert "free listings will remain free" in page
    assert "hermesebookbot" not in page
    assert "browse the current truck list" in page


def test_signup_parser_extracts_actionable_fields():
    assert vendor_intake.parse_vendor_submission(
        "QA Demo Truck / tacos / 7195550100 / Pueblo / Saturdays 11am-6pm"
    ) == {
        "truck_name": "QA Demo Truck", "cuisine": "tacos", "phone": "7195550100",
        "city": "Pueblo", "serves": "Saturdays 11am-6pm",
    }
    assert vendor_intake.parse_vendor_submission("not five fields") is None


def test_signup_persists_structured_lead_in_isolated_database():
    with tempfile.TemporaryDirectory(prefix="wwe-marketing-test-") as td:
        copied = Path(td) / "vendors_row.db"
        shutil.copy2(VENDORS / "vendors_row.db", copied)
        original_db = vendor_intake.DB
        message = "QA Demo Truck / tacos / 7195550100 / Pueblo / Saturdays"
        try:
            vendor_intake.DB = str(copied)
            assert vendor_intake.file_lead(987654321, "QA Contact", message)
        finally:
            vendor_intake.DB = original_db
        con = sqlite3.connect(copied)
        try:
            row = con.execute(
                "SELECT truck_name, contact_name, phone, city, serves, cuisine, notes "
                "FROM vendor_leads WHERE contact_name=?",
                ("QA Contact",),
            ).fetchone()
            assert row == (
                "QA Demo Truck", "QA Contact", "7195550100", "Pueblo",
                "Saturdays", "tacos", message,
            )
        finally:
            con.close()


def test_no_public_html_routes_to_shared_gateway_bot():
    offenders = []
    pages = list(HERE.rglob("*.html"))
    assert len(pages) >= 18, f"expected built public HTML pages, found {len(pages)}"
    for path in pages:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        if "hermesebookbot" in text:
            offenders.append(str(path.relative_to(HERE)))
    assert not offenders, f"public pages point at the shared/private Telegram bot: {offenders}"


def main() -> int:
    tests = (
        test_customer_page_uses_roster_and_only_real_offers,
        test_homepage_discloses_price_confirmation_state_and_promotion_cta,
        test_signup_page_routes_to_desk_bot_not_gateway_bot,
        test_signup_parser_extracts_actionable_fields,
        test_signup_persists_structured_lead_in_isolated_database,
        test_no_public_html_routes_to_shared_gateway_bot,
    )
    failed = []
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception as exc:
            failed.append(test.__name__)
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"{len(tests)-len(failed)}/{len(tests)} checks passed")
    return bool(failed)


if __name__ == "__main__":
    raise SystemExit(main())


def test_suite_passes():
    assert main() == 0
