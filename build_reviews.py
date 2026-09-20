#!/usr/bin/env python3
"""Build the public reviews page — the promise the site had been making without a mechanism.

`vendor_reviews` now receives real rows from the Telegram desk (`?start=review`), and this page shows
them the way the homepage always claimed they would be shown: a five-star average per truck, the
customer comments that produced it, and HIGHLY RECOMMENDED only where the documented rule is met
(>= 3 reviews, average >= 4.5, no sub-3-star review in 90 days). Trucks with no reviews say so.

Usage: python build_reviews.py [--check]
"""
from __future__ import annotations

import datetime
import html as H
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "reviews", "index.html")
VR = os.path.dirname(HERE)
DB = os.path.join(VR, "vendors_row", "vendors_row.db")
sys.path.insert(0, os.path.join(VR, "vendors_row"))
import reviews  # the fairness rule + badge thresholds live there, not here

BOT = "https://t.me/HermesEbookBot?start=review"


def stars_html(avg: float, count: int) -> str:
    if not count:
        return '<span class="none">no reviews yet</span>'
    full = int(round(avg))
    return ('<span class="stars" aria-label="%s out of 5">%s</span>'
            % (avg, "★" * full + "☆" * (5 - full)))


def rows() -> list[dict]:
    r = {x["id"]: x for x in reviews.summary()}
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    for v in con.execute("select id, name, category, city from vendors order by name"):
        r[v["id"]]["cuisine"] = v["category"] or ""
        r[v["id"]]["city"] = v["city"] or ""
    reviews_by_vendor: dict[int, list] = {}
    for rv in con.execute("select vendor_id, stars, comment, author, created_at from vendor_reviews order by created_at desc"):
        reviews_by_vendor.setdefault(rv["vendor_id"], []).append(dict(rv))
    con.close()
    out = []
    for vid, rv in r.items():
        rv["reviews"] = reviews_by_vendor.get(vid, [])
        out.append(rv)
    # badge first, then rating, then most-reviewed
    out.sort(key=lambda x: (not x["highly_recommended"], -x["average"], -x["count"], x["name"]))
    return out


def build() -> str:
    data = rows()
    total = sum(x["count"] for x in data)
    badged = [x for x in data if x["highly_recommended"]]
    cards = []
    for v in data:
        revs = "".join(
            f'<li><strong>{"★" * rv["stars"]}{"☆" * (5 - rv["stars"])}</strong> '
            f'{H.escape(rv["comment"] or "(stars only)")} <span class="meta">— {H.escape(rv["author"] or "customer")}, '
            f'{rv["created_at"][:10]}</span></li>' for rv in v["reviews"][:5])
        missing = v["missing_for_badge"] or ""
        badge = ('<span class="badge">HIGHLY RECOMMENDED</span>' if v["highly_recommended"]
                 else (f'<span class="badge badge-no">not yet — needs {H.escape(missing)}</span>' if v["count"] else
                       '<span class="badge badge-no">unrated</span>'))
        cards.append(f"""<article class="card">
      <h3>{H.escape(v['name'])} {badge}</h3>
      <p class="meta">{H.escape(v['cuisine'])} · {H.escape(v['city'])}</p>
      <p class="score">{stars_html(v['average'], v['count'])}
         <strong>{v['average'] if v['count'] else '—'}</strong>
         <span class="meta">({v['count']} review{'s' if v['count'] != 1 else ''})</span></p>
      {'<ul class="revs">' + revs + '</ul>' if revs else '<p class="meta">Be the first to rate this truck. One message, no account.</p>'}
    </article>""")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reviews and ratings — Where We Eatin'?</title>
<meta name="description" content="Real customer reviews for Southern Colorado food trucks, a five-star average per truck, and the HIGHLY RECOMMENDED badge that has to be earned.">
<link rel="canonical" href="https://jjordanjr74-dot.github.io/whereeatin-site/reviews/">
<style>
  :root{{--ink:#111827;--muted:#4b5563;--brand:#dc2626;--paper:#fef2f2;--line:#e5e7eb}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 Karla,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
  header,main{{max-width:980px;margin:0 auto;padding:18px 20px}}
  h1{{margin:0 0 4px;font-size:26px}} h2{{font-size:19px;margin:26px 0 8px}}
  .sub{{color:var(--muted);margin:0 0 8px}}
  .cta{{display:inline-block;background:var(--brand);color:#fff;text-decoration:none;font-weight:700;
       padding:11px 16px;border-radius:10px;margin:10px 0 4px}}
  .card{{background:#fff;border-radius:14px;padding:16px 18px;margin:12px 0;box-shadow:0 8px 30px rgba(17,24,39,.06)}}
  .card h3{{margin:0 0 4px;font-size:17px}}
  .meta{{color:var(--muted);font-size:14px;margin:2px 0}}
  .score{{margin:6px 0 2px;font-size:17px}}
  .stars{{color:#f59e0b;letter-spacing:1px}}
  .none{{color:var(--muted);font-size:14px}}
  .badge{{background:#ecfdf5;color:#065f46;border-radius:999px;padding:2px 9px;font-size:12px;font-weight:700;vertical-align:middle}}
  .badge-no{{background:#f3f4f6;color:#6b7280}}
  ul.revs{{margin:8px 0 0;padding-left:18px}} ul.revs li{{margin:6px 0}}
  .rule{{background:#fff;border-left:4px solid var(--brand);padding:12px 16px;border-radius:8px;font-size:14px;color:var(--muted)}}
  a{{color:var(--brand)}}
</style>
</head>
<body>
<header>
  <h1>Reviews humans write</h1>
  <p class="sub">{total} review{'s' if total != 1 else ''} across {len(data)} tracked trucks · {len(badged)} holding the
  HIGHLY RECOMMENDED badge. Every review comes from a real customer message; nothing is seeded, bought or written by us.</p>
  <a class="cta" href="{BOT}">Leave a review (one message, no account)</a>
  <p class="meta">Opens Telegram — tap Start, then send e.g. <em>“5 Big Papa's Grill — best brisket in Pueblo”</em>.</p>
</header>
<main>
  <p class="rule"><strong>How the badge works:</strong> HIGHLY RECOMMENDED is earned, never sold — it needs at
  least {reviews.MIN_REVIEWS} reviews, an average of {reviews.MIN_AVG} or better, and no review below 3 stars in the last
  {reviews.BADGE_WINDOW_DAYS} days. It is recalculated on every review, so it can be lost. One review per truck per
  {reviews.COOLDOWN_HOURS} hours per person, and only a first name and last initial are ever stored.</p>
  {''.join(cards)}
  <p class="meta">Data built {datetime.date.today().isoformat()} from vendors_row.db. Back to the
  <a href="../">radar and truck list</a> · <a href="../list-your-truck/">get your truck listed</a>.</p>
</main>
</body>
</html>
"""


if __name__ == "__main__":
    page = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    cur = open(OUT, encoding="utf-8").read() if os.path.isfile(OUT) else ""
    if "--check" in sys.argv:
        print("CURRENT" if page == cur else "STALE")
        raise SystemExit(0 if page == cur else 1)
    open(OUT, "w", encoding="utf-8").write(page)
    n = sum(1 for x in rows() if x["count"])
    print(f"wrote {OUT} ({len(page)} bytes, {n} truck(s) with reviews)")
