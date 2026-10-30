"""The one place the public site URL is defined.

WHY THIS EXISTS
  The site moved to whereeatin.com, but four separate build scripts and two static files still carried the old
  temporary Pages address (`whereeatin.com`) in their canonical tags, og:url, JSON-LD
  and sitemap. That is worse than cosmetic: a canonical tag or sitemap entry naming the github.io URL tells search
  engines the temporary address is the authoritative one, so the custom domain quietly fights the very signal it
  was bought for.

  It was also a trap for maintenance: fixing index.html's canonical by hand looked like a fix, but the next
  `build_site.py` run regenerated the wrong URL from its own BASE constant.

  Every builder now imports BASE from here. One URL, one place to change it.
"""

import html as H
import re

BASE = "https://whereeatin.com"
SITE_NAME = "Where We Eatin'?"
DOMAIN = "whereeatin.com"

# The one place the public desk bot lives. Public intake — vendor signup, reviews, follow-a-truck —
# routes through @Sheba_telegram_bot (bot_id 8968984009), NEVER the Hermes gateway bot (@HermesEbookBot).
# Deep-link commands are handled by vendor_intake.py: ?start=vendor, ?start=review, ?start=follow-<slug>.
DESK_BOT = "Sheba_telegram_bot"


def desk_link(start: str = "") -> str:
    """A deep link into the public desk bot, e.g. desk_link('vendor') -> https://t.me/Sheba_telegram_bot?start=vendor."""
    return f"https://t.me/{DESK_BOT}" + (f"?start={start}" if start else "")


def url(path: str = "/") -> str:
    """Absolute URL for a site path. Accepts 'radar/', '/radar/', or ''."""
    if not path.startswith("/"):
        path = "/" + path
    return BASE + path

def slug(name: str) -> str:
    """URL-safe slug for a vendor name. Shared so the roster's links and the page paths cannot disagree."""
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-") or "truck"


# Generated date stamps, by the text that introduces them. Missing one here means a builder's --check goes
# STALE at midnight for a cosmetic reason.
_STAMPS = (
    re.compile(r"(Data built )\d{4}-\d{2}-\d{2}"),
    re.compile(r"(<lastmod>)\d{4}-\d{2}-\d{2}"),
)


def stamp_agnostic(text: str) -> str:
    """Blank generated date stamps so a --check compares CONTENT, not the calendar.

    Every builder stamps today's date into its output, so a plain string compare reports STALE from midnight
    onward with nothing actually wrong. A gate that goes red daily is a gate people learn to ignore, and a real
    drift then hides behind the noise.
    """
    for rx in _STAMPS:
        text = rx.sub(r"\1YYYY-MM-DD", text)
    return text


def same(generated: str, current: str) -> bool:
    """True when a regenerated page equals what is on disk, ignoring generated date stamps."""
    return generated == current or stamp_agnostic(generated) == stamp_agnostic(current)


# --- shared social-card + navigation snippets -----------------------------------------------------------
# WHY: audit 2026-10-15 found og:image/twitter cards on only 2 of 7 pages and NO mobile nav on any inner
# page, so a shared inner-page link rendered a bare grey card and had no way back to the rest of the site.
# These live here (the one place the site URL lives) so every builder emits the SAME block instead of each
# carrying a drifting copy. Absolute hrefs so the nav works from any path depth on the custom domain.
OG_IMAGE_PATH = "assets/og-card.jpg"      # the existing 1200x630 card the home page already ships


def og_block(title: str, description: str, path: str, image: str = "") -> str:
    """Open Graph + Twitter card meta for one page. Reuses the site's single og-card.jpg (no new artwork)."""
    page_url = url(path)          # NOT `url = url(path)`: that shadows the module function inside this
    img = url("assets/" + image) if image else url(OG_IMAGE_PATH)      # scope and raises UnboundLocalError (measured 2026-10-15, child bug)
    def q(v: str) -> str:
        # meta content is a double-quoted attribute: escape the only characters that can break out
        return (v or "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
    tags = [
        ('property', 'og:type', 'website'),
        ('property', 'og:title', q(title)),
        ('property', 'og:description', q(description)),
        ('property', 'og:url', page_url),
        ('property', 'og:image', img),
        ('property', 'og:image:width', '1200'),
        ('property', 'og:image:height', '630'),
        ('name', 'twitter:card', 'summary_large_image'),
        ('name', 'twitter:title', q(title)),
        ('name', 'twitter:description', q(description)),
        ('name', 'twitter:image', img),
    ]
    return "".join(f'<meta {k}="{n}" content="{c}">' for k, n, c in tags)


# The home page's own menu, with one link per public section. `current` (a site path) marks the active one.
NAV_ITEMS = (
    ("Trucks", "/"),
    ("Live radar", "/radar/"),
    ("Road trip", "/travel/"),
    ("Specials", "/promotions/"),
    ("Reviews", "/reviews/"),
    ("For trucks", "/list-your-truck/"),
)

# 11 Southern Colorado & Front Range Corridor City Hubs (Pueblo + 120-Mile Radius)
# Used by build_cities.py for SEO landing pages, build_site.py for the community hub, and build_listing.py for sitemap.xml.
CITY_HUBS = (
    {
        "slug": "pueblo",
        "city": "Pueblo",
        "state": "CO",
        "path": "food-trucks-pueblo-co/",
        "distance_miles": 0,
        "title": "Food Trucks in Pueblo, CO | Where We Eatin'?",
        "h1": "Pueblo Food Truck Directory & Live Radar",
        "desc": "Verified food trucks serving Pueblo, CO. Real-time truck locations, menus, sibling reviews, and direct event booking across Downtown Pueblo, Riverwalk, Union Ave, and CSU Pueblo.",
        "spots": (
            "Pueblo Riverwalk & Historic Arkansas Riverwalk",
            "Downtown Pueblo & Union Avenue Historic District",
            "CSU Pueblo Campus & Walking Stick",
            "Colorado State Fairgrounds & Midtown",
            "Pueblo Memorial Airport Industrial Park",
        ),
        "local_cities": ("Pueblo", "Downtown Pueblo"),
    },
    {
        "slug": "colorado-springs",
        "city": "Colorado Springs",
        "state": "CO",
        "path": "food-trucks-colorado-springs-co/",
        "distance_miles": 42,
        "title": "Food Trucks in Colorado Springs, CO | Where We Eatin'?",
        "h1": "Colorado Springs Food Truck Radar & Guide",
        "desc": "Verified food trucks serving Colorado Springs, CO. Live location reports, food truck rallies, catering menus, and direct booking across Downtown, Old Colorado City, Powers Corridor, and Briargate.",
        "spots": (
            "Downtown Colorado Springs & Tejon Street",
            "Old Colorado City Historic District",
            "Powers Boulevard & North Carefree Corridor",
            "Garden of the Gods & Westside Breweries",
            "Briargate & Interquest Entertainment District",
        ),
        "local_cities": ("Colorado Springs", "Springs", "Downtown Colorado Springs"),
    },
    {
        "slug": "pueblo-west",
        "city": "Pueblo West",
        "state": "CO",
        "path": "food-trucks-pueblo-west-co/",
        "distance_miles": 12,
        "title": "Food Trucks in Pueblo West, CO | Where We Eatin'?",
        "h1": "Pueblo West Food Truck Tracker & Rally Guide",
        "desc": "Verified food trucks serving Pueblo West, CO. Live mobile truck radar, neighborhood pop-ups, and catering across Purcell Blvd, McCulloch Blvd, Civic Center Park, and Lake Pueblo North Shore.",
        "spots": (
            "Purcell Boulevard & US-50 Corridor",
            "McCulloch Boulevard Business Strip",
            "Civic Center Park & Lovell Arts Pavilion",
            "Lake Pueblo State Park North Shore",
            "Pueblo West High School & Sports Complex",
        ),
        "local_cities": ("Pueblo West",),
    },
    {
        "slug": "canon-city",
        "city": "Cañon City",
        "state": "CO",
        "path": "food-trucks-canon-city-co/",
        "distance_miles": 39,
        "title": "Food Trucks in Cañon City, CO | Where We Eatin'?",
        "h1": "Cañon City Food Truck Directory & Riverwalk Stops",
        "desc": "Verified food trucks and mobile pop-ups in Cañon City, CO. Find local food trucks along US-50, Historic Downtown Main Street, Royal Gorge Route, and the Arkansas Riverwalk.",
        "spots": (
            "Historic Downtown Main Street",
            "Royal Gorge Route Railroad Depot",
            "Arkansas Riverwalk Trailheads",
            "The Abbey Event Complex",
            "Fremont County Fairgrounds & 9th Street",
        ),
        "local_cities": ("Cañon City", "Canon City"),
    },
    {
        "slug": "fountain",
        "city": "Fountain",
        "state": "CO",
        "path": "food-trucks-fountain-co/",
        "distance_miles": 28,
        "title": "Food Trucks in Fountain & Fort Carson, CO | Where We Eatin'?",
        "h1": "Fountain & Fort Carson Food Truck Tracker",
        "desc": "Verified food trucks serving Fountain, CO and Fort Carson Gate corridors. Live truck schedules, military family event catering, and pop-ups across Fountain Mesa, Metcalfe Park, and US-85.",
        "spots": (
            "Metcalfe Park & Heritage Days Fairgrounds",
            "Fountain Mesa Road & Cross Creek Corridor",
            "Fort Carson Gate 20 & Gate 19 Access Corridors",
            "Historic Downtown Fountain & Ohio Ave",
            "US-85 / Santa Fe Commercial Corridor",
        ),
        "local_cities": ("Fountain", "Fort Carson"),
    },
    {
        "slug": "monument",
        "city": "Monument",
        "state": "CO",
        "path": "food-trucks-monument-co/",
        "distance_miles": 62,
        "title": "Food Trucks in Monument & Tri-Lakes, CO | Where We Eatin'?",
        "h1": "Monument & Tri-Lakes Food Truck Guide",
        "desc": "Verified food trucks serving Monument, Palmer Lake, and Woodmoor in Northern El Paso County. Find mobile food trucks at local breweries, community concerts, and Tri-Lakes trailheads.",
        "spots": (
            "Historic Downtown Monument & Limbach Park",
            "Palmer Lake Town Green & Lakefront Breweries",
            "Jackson Creek Commercial Center",
            "Woodmoor Country Club & Community Trails",
            "I-25 Exit 161 Gateway",
        ),
        "local_cities": ("Monument", "Palmer Lake", "Tri-Lakes"),
    },
    {
        "slug": "castle-rock",
        "city": "Castle Rock",
        "state": "CO",
        "path": "food-trucks-castle-rock-co/",
        "distance_miles": 84,
        "title": "Food Trucks in Castle Rock, CO | Where We Eatin'?",
        "h1": "Castle Rock Food Truck Directory & Events",
        "desc": "Verified food trucks serving Castle Rock, CO along the Southern Denver corridor. Find food trucks at Festival Park, Philip S. Miller Park, Outlets at Castle Rock, and Meadows community events.",
        "spots": (
            "Festival Park & Historic Downtown Castle Rock",
            "Philip S. Miller Park Amphitheater & Plaza",
            "Outlets at Castle Rock Event Lots",
            "The Meadows Town Center",
            "Rock Park & Plum Creek Parkway",
        ),
        "local_cities": ("Castle Rock",),
    },
    {
        "slug": "salida",
        "city": "Salida",
        "state": "CO",
        "path": "food-trucks-salida-co/",
        "distance_miles": 96,
        "title": "Food Trucks in Salida & Upper Arkansas Valley, CO | Where We Eatin'?",
        "h1": "Salida & Chaffee County Food Truck Tracker",
        "desc": "Verified food trucks and outdoor dining across Salida, Buena Vista, and the Upper Arkansas River Valley. Find riverside food trucks, brewery pop-ups, and mountain festival catering.",
        "spots": (
            "Riverside Park & Arkansas Riverfront",
            "Historic Downtown F Street Art & Dining District",
            "Poncha Springs US-50 / US-285 Crossroads",
            "Salida Hot Springs Aquatic Park",
            "Chaffee County Fairgrounds",
        ),
        "local_cities": ("Salida", "Poncha Springs", "Buena Vista"),
    },
    {
        "slug": "walsenburg",
        "city": "Walsenburg",
        "state": "CO",
        "path": "food-trucks-walsenburg-co/",
        "distance_miles": 48,
        "title": "Food Trucks in Walsenburg & Huerfano County, CO | Where We Eatin'?",
        "h1": "Walsenburg Food Truck & Highway 160 Guide",
        "desc": "Verified food trucks serving Walsenburg, La Veta, and Huerfano County. Find mobile vendors along I-25 Exit 52, Highway 160 toward Cuchara Pass, and Lathrop State Park.",
        "spots": (
            "Downtown Walsenburg Main Street & 7th St",
            "Lathrop State Park Visitor Center & Martin Lake",
            "US-160 / Highway 10 Gateway Corridors",
            "La Veta Town Park & Scenic Highway of Legends",
            "Huerfano County Community Center",
        ),
        "local_cities": ("Walsenburg", "La Veta"),
    },
    {
        "slug": "trinidad",
        "city": "Trinidad",
        "state": "CO",
        "path": "food-trucks-trinidad-co/",
        "distance_miles": 85,
        "title": "Food Trucks in Trinidad, CO | Where We Eatin'?",
        "h1": "Trinidad Food Truck Directory & Santa Fe Trail Radar",
        "desc": "Verified food trucks in Trinidad, CO near Raton Pass and the Historic Santa Fe Trail. Discover local taco trucks, barbecue rigs, and mobile kitchens in Las Animas County.",
        "spots": (
            "Historic Downtown Commercial Street & Main St",
            "Central Park & Purgatoire Riverwalk",
            "Trinidad Lake State Park Campgrounds",
            "I-25 Exit 13 & 14 Commercial Hubs",
            "Space to Create Arts District",
        ),
        "local_cities": ("Trinidad",),
    },
    {
        "slug": "la-junta",
        "city": "La Junta",
        "state": "CO",
        "path": "food-trucks-la-junta-co/",
        "distance_miles": 65,
        "title": "Food Trucks in La Junta & Lower Arkansas Valley, CO | Where We Eatin'?",
        "h1": "La Junta & Otero County Food Truck Tracker",
        "desc": "Verified food trucks serving La Junta, Rocky Ford, and the Lower Arkansas Valley along US-50. Find food trucks at Bent's Old Fort events, Otero College, and Arkansas Valley farm rallies.",
        "spots": (
            "Downtown La Junta & 3rd Street Corridor",
            "Otero College Campus & Tiger Stadium",
            "Bent's Old Fort National Historic Site Approach",
            "Rocky Ford US-50 Watermelon Capital Corridor",
            "Arkansas Valley Fairgrounds in Rocky Ford",
        ),
        "local_cities": ("La Junta", "Rocky Ford"),
    },
)

# Self-contained ProPublica / Bloomberg civic-atlas standard navigation & footer styling.
# `.sitnav` prefix avoids colliding with any page's own `.nav`/`.wrap`/`header` rules.
NAV_CSS = (
    ".sitnav{position:sticky;top:0;z-index:60;background:rgba(250,247,242,.94);backdrop-filter:blur(10px);"
    "border-bottom:1px solid #ddd3c6;font:16px/1.5 \"Karla\",system-ui,-apple-system,\"Segoe UI\",Roboto,sans-serif}"
    ".sitnav-in{max-width:1180px;margin:0 auto;display:flex;align-items:center;gap:26px;padding:0 28px;min-height:70px;flex-wrap:nowrap}"
    ".sitnav .brand{display:flex;align-items:baseline;font:600 1.32rem/1 \"Fraunces\",Georgia,serif;letter-spacing:-.02em;"
    "text-decoration:none;color:#221c17;white-space:nowrap}"
    ".sitnav .brand-mark{background:none;width:auto;height:auto;display:inline;border-radius:2px;font:inherit;color:inherit}"
    ".sitnav .nav-links{display:flex;flex-wrap:nowrap;gap:2px;margin-left:auto;align-items:center}"
    ".sitnav .nav-links a{padding:8px 11px;border-radius:2px;text-decoration:none;font-size:.93rem;font-weight:500;"
    "color:#453b31;white-space:nowrap;border-bottom:2px solid transparent}"
    ".sitnav .nav-links a:hover{background:none;color:#b23a26}"
    ".sitnav .nav-links a[aria-current=\"page\"]{background:none;color:#221c17;border-bottom-color:#b23a26}"
    ".sitnav .nav-toggle{display:none;margin-left:auto;background:none;border:1px solid #c4b8a8;border-radius:2px;"
    "padding:9px 14px;font:500 .9rem \"Karla\",system-ui,sans-serif;cursor:pointer;color:#221c17}"
    ".skip{position:absolute;left:-9999px}"
    ".skip:focus{left:16px;top:10px;z-index:100;background:#faf7f2;border:1px solid #b23a26;border-radius:2px;padding:10px 14px}"
    "@media(max-width:940px){.sitnav .nav-toggle{display:block}"
    ".sitnav .nav-links{position:absolute;left:0;right:0;top:100%;flex-direction:column;align-items:stretch;gap:0;"
    "background:#faf7f2;border-bottom:1px solid #ddd3c6;padding:8px 20px 18px;display:none}"
    ".sitnav .nav-links.open{display:flex}.sitnav .nav-links a{padding:12px 4px;border-bottom:1px solid #eee5d8}}"
)

# Inline (no external script) so a page's own script-count assertions are not disturbed; guards on element
# existence so it is safe to concatenate onto an existing inline block.
NAV_JS = (
    "(function(){var t=document.getElementById('navToggle'),l=document.getElementById('navLinks');"
    "if(t&&l){t.addEventListener('click',function(){var o=l.classList.toggle('open');"
    "t.setAttribute('aria-expanded',o?'true':'false');t.textContent=o?'Close':'Menu';});"
    "l.addEventListener('click',function(e){if(e.target.tagName==='A'){l.classList.remove('open');"
    "t.setAttribute('aria-expanded','false');t.textContent='Menu';}});}})();"
)


def nav_block(current: str = "") -> str:
    """The same sticky nav + hamburger the home page uses, with absolute hrefs so it works at any depth.

    `current` is the page's own site path (e.g. '/travel/'); it gets aria-current="page".
    """
    links = "".join(
        '<a href="{h}"{c}>{t}</a>'.format(
            h=href, t=label, c=' aria-current="page"' if href == current else "")
        for label, href in NAV_ITEMS)
    return (
        '<div class="sitnav" id="nav"><div class="sitnav-in">'
        '<a class="brand" href="/">Where We Eatin\'?</a>'
        '<button class="nav-toggle" id="navToggle" aria-expanded="false" aria-controls="navLinks">Menu</button>'
        '<nav class="nav-links" id="navLinks" aria-label="Main">' + links +
        '</nav></div></div>')


# --- shared footer links -------------------------------------------------------------------------------------
FOOT_LINKS = (("Trucks", "/trucks/"), ("Live radar", "/radar/"), ("Road trip", "/travel/"),
              ("Specials", "/promotions/"), ("Reviews", "/reviews/"), ("For trucks", "/list-your-truck/"),
              ("Privacy", "/privacy/"), ("Sitemap", "/sitemap.xml"))
FOOT_CSS = (
    ".sitfoot{border-top:1px solid #ddd3c6;margin-top:60px;padding:32px 28px;"
    "font:15px/1.6 \"Karla\",system-ui,-apple-system,\"Segoe UI\",Roboto,sans-serif;color:#5a4f43;background:#faf7f2}"
    ".sitfoot-in{max-width:1180px;margin:0 auto;display:flex;flex-wrap:wrap;gap:12px 24px;align-items:center}"
    ".sitfoot nav{display:flex;flex-wrap:wrap;gap:8px 18px}"
    ".sitfoot a{color:#221c17;text-decoration:none;font-weight:500;border-bottom:1px solid #c4b8a8}"
    ".sitfoot a:hover{color:#b23a26;border-bottom-color:#b23a26}"
)
NAV_CSS = NAV_CSS + FOOT_CSS


def footer_block() -> str:
    """The one footer every public page ends with. Same links everywhere, generated here only."""
    links = "".join(f'<a href="{h}">{t}</a>' for t, h in FOOT_LINKS)
    partners = (
        '<div style="width:100%;font-size:13px;color:#6b5e50;margin-top:6px;padding-top:8px;border-top:1px dashed #e2d8ca">'
        'Southern CO Sister Network: '
        '<a href="https://restaurantradar.app/">Restaurant Radar (Dining &amp; Fuel)</a> &middot; '
        '<a href="https://www.coloradobounceclub.com/">Colorado Bounce Club ($25 OFF w/ Truck)</a> &middot; '
        '<a href="https://beethelightmassage.com/">Bee The Light Massage</a> &middot; '
        '<a href="https://thesoapbook.com/">SOAP Autopilot</a> &middot; '
        '<a href="https://baadlandsfarms.com/">Baadlands Farms</a> &middot; '
        '<a href="https://politicalpayola.com/">Political Payola</a>'
        '</div>'
    )
    return ('<footer class="sitfoot" id="sitfoot"><div class="sitfoot-in">'
            '<span>Where We Eatin&#39;? &middot; Independent civic directory &middot; 0% commission &middot; Pueblo, CO + 120-mile corridor</span>'
            f'<nav aria-label="Footer">{links}</nav>{partners}</div></footer>')


def live_sentence(n: int) -> str:
    """The one sentence that says how many trucks are live. Shared so home and radar cannot disagree.

    A truck counts as live only when checkin_state reports a fresh vendor check-in or fresh vendor-confirmed
    serving status. Zero is said plainly, never softened into implied live data.
    """
    if n <= 0:
        return "No trucks have checked in right now - here's who usually serves today"
    return f"{n} truck{'s' if n != 1 else ''} checked in or confirmed serving in the last four hours"


def _attr(v: str) -> str:
    return H.escape(v or "", quote=True)


def fav_button(slug_: str, name: str) -> str:
    """Save/unsave toggle. Ships hidden: favorites.js un-hides it, so with JS off the button never appears."""
    return (f'<button type="button" class="fav-btn" data-fav="{_attr(slug_)}" data-name="{_attr(name)}" '
            f'aria-pressed="false" hidden>Save</button>')


def share_button(page_url: str, title: str) -> str:
    """Share button. Ships hidden: share.js un-hides it (Web Share API, copy-link fallback)."""
    return (f'<button type="button" class="btn btn-sm btn-ghost share-btn" data-share="1" '
            f'data-url="{_attr(page_url)}" data-title="{_attr(title)}" hidden>Share this truck</button>')


def follow_button(slug_: str, name: str) -> str:
    """Follow-a-truck deep link: opens the desk bot so a customer gets check-in alerts for this truck."""
    return (f'<a class="btn btn-sm btn-ghost" href="{desk_link("follow-" + slug_)}" '
            f'aria-label="Follow {_attr(name)} for check-in alerts">Follow</a>')
