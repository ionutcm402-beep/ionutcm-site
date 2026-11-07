#!/usr/bin/env python3
"""Builds ionutcm.com into ./public from content/apps.json and content/legal/*.html.

Standard library only. Run:  python3 tools/build.py
Cloudflare serves ./public as-is (see wrangler.jsonc); there is no build step on Cloudflare,
so commit the regenerated ./public together with any content change.
"""
import hashlib, html, json, os, re, shutil, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
CONTENT = os.path.join(ROOT, "content")
OUT = os.path.join(ROOT, "public")

SITE = "https://ionutcm.com"
BRAND = "ionutcm"
EMAIL = "contact@ionutcm.com"
YEAR = 2026
UPDATED = "2026-11-07"
SCREEN_W, SCREEN_H = 780, 1688          # every screenshot is exported at this size (390 × 844 pt at 2×)

e = lambda s: html.escape(str(s), quote=True)

# ------------------------------------------------------------------ data
data = json.load(open(os.path.join(CONTENT, "apps.json"), encoding="utf-8"))
APPS = sorted([a for a in data["apps"] if a.get("published")], key=lambda a: a["order"])
PLATFORM_NAMES = {"android": ("Android", "Google Play"), "ios": ("iPhone", "App Store")}


def asset_version(path):
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:10]


def platform_rows(app):
    """Platforms the app is (or will be) on, in a fixed order. 'none' is left out entirely."""
    rows = []
    for key in ("android", "ios"):
        p = app["platforms"].get(key) or {}
        status = p.get("status", "none")
        if status == "none":
            continue
        device, store = PLATFORM_NAMES[key]
        rows.append({"key": key, "device": device, "store": store, "status": status,
                     "url": p.get("url") if status == "available" else None, "note": p.get("note")})
    return rows


def availability_label(app):
    rows = platform_rows(app)
    if not rows:
        return ""
    devices = " and ".join(r["device"] for r in rows)
    if all(r["status"] == "available" and r["url"] for r in rows):
        return f"Available for {devices}"
    if any(r["status"] == "available" and r["url"] for r in rows):
        return " · ".join(f'{r["device"]}: {"available" if r["url"] else "coming soon"}' for r in rows)
    return f"Coming soon for {devices}"


def tagline_html(text):
    """'Small habits. Clear progress.' → two balanced lines, like a product headline."""
    parts = [p for p in re.split(r"(?<=\.)\s+", text) if p]
    return "<br>".join(e(p) for p in parts) if len(parts) == 2 else e(text)


def screen(app, sid):
    for s in app["screens"]:
        if s["id"] == sid:
            return s
    raise KeyError(sid)

# ------------------------------------------------------------------ components
def icon(app, size="md"):
    if app.get("icon"):
        return f'<img class="appicon appicon-{size}" src="{e(app["icon"])}" alt="" width="120" height="120">'
    return f'<span class="appicon appicon-{size} appicon-mono" aria-hidden="true">{e(app["monogram"])}</span>'


def phone(sid, alt, theme="light", eager=False, extra=""):
    src = f"/assets/screens/{sid}-{theme}.webp?v={VERSIONS[f'{sid}-{theme}']}"
    load = 'fetchpriority="high" decoding="async"' if eager else 'loading="lazy" decoding="async"'
    small = f"/assets/screens/{sid}-{theme}-480.webp?v={VERSIONS[f'{sid}-{theme}-480']}"
    return (f'<figure class="phone{(" " + extra) if extra else ""}"><img src="{src}" '
            f'srcset="{small} 480w, {src} 780w" sizes="(max-width: 600px) 62vw, 300px" alt="{e(alt)}" '
            f'width="{SCREEN_W}" height="{SCREEN_H}" {load}></figure>')


def store_buttons(app):
    out = []
    for r in platform_rows(app):
        if r["url"]:
            out.append(f'<a class="btn btn-store" href="{e(r["url"])}" rel="noopener">'
                       f'<span class="btn-store-small">Get it on</span><span>{e(r["store"])}</span></a>')
    return "".join(out)


def platform_chips(app, dark=False):
    chips = []
    for r in platform_rows(app):
        state = "Available" if r["url"] else "Coming soon"
        chips.append(f'<li class="chip{" chip-live" if r["url"] else ""}"><span>{e(r["device"])}</span>'
                     f'<span class="chip-state">{state}</span></li>')
    return f'<ul class="chips" aria-label="Platforms">{"".join(chips)}</ul>' if chips else ""


def nav(current):
    items = [("/apps", "Apps", "apps"), ("/about", "About", "about"), ("/support", "Support", "support")]
    links = "".join(f'<a href="{h}"{" aria-current=\"page\"" if current == k else ""}>{t}</a>' for h, t, k in items)
    return f'''<header class="site-header">
  <div class="wrap header-in">
    <a class="brand" href="/" aria-label="{BRAND}, home"><img class="brand-mark" src="/assets/logo-96.png" srcset="/assets/logo-96.png 1x, /assets/logo-192.png 2x" alt="" width="32" height="32"><span>{BRAND}</span></a>
    <nav class="nav" aria-label="Main">{links}</nav>
  </div>
</header>'''


def footer():
    app_links = "".join(f'<li><a href="/apps/{a["slug"]}">{e(a["name"])}</a></li>' for a in APPS)
    legal = "".join(f'<li><a href="{a["legal"]["privacy"]}">{e(a["name"])} privacy</a></li>'
                    f'<li><a href="{a["legal"]["terms"]}">{e(a["name"])} terms</a></li>' for a in APPS)
    return f'''<footer class="site-footer">
  <div class="wrap">
    <div class="footer-grid">
      <div class="footer-brand">
        <a class="brand" href="/"><img class="brand-mark" src="/assets/logo-96.png" srcset="/assets/logo-96.png 1x, /assets/logo-192.png 2x" alt="" width="32" height="32"><span>{BRAND}</span></a>
        <p>Simple, private apps for everyday life. Made independently in the United Kingdom.</p>
      </div>
      <nav aria-label="Apps"><h2>Apps</h2><ul>{app_links}<li><a href="/apps">All apps</a></li></ul></nav>
      <nav aria-label="Legal"><h2>Legal</h2><ul>{legal}<li><a href="/privacy">Website privacy</a></li></ul></nav>
      <div><h2>Contact</h2><ul><li><a href="/support">Support</a></li><li><a href="mailto:{EMAIL}">{EMAIL}</a></li><li><a href="/about">About</a></li></ul></div>
    </div>
    <p class="footer-base">© {YEAR} {BRAND}. Independent apps made in the UK.</p>
  </div>
</footer>'''


def page(path, title, desc, body, current="", og_image="/og.png", body_class=""):
    canonical = SITE + ("/" if path == "/" else path)
    full_title = title if title.endswith(BRAND) else f"{title} · {BRAND}"
    doc = f'''<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(full_title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{canonical}">
<meta name="theme-color" content="#fbfbfd">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:title" content="{e(full_title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{SITE}{og_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon-32.png" type="image/png" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="stylesheet" href="/assets/site.css?v={VERSIONS['css']}">
<script src="/assets/site.js?v={VERSIONS['js']}" defer></script>
</head>
<body{f' class="{body_class}"' if body_class else ""}>
<a class="skip" href="#main">Skip to content</a>
{nav(current)}
<main id="main">
{body}
</main>
{footer()}
</body>
</html>
'''
    rel = "index.html" if path == "/" else path.strip("/") + ".html"
    dest = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(doc)
    PAGES.append(path)

# ------------------------------------------------------------------ sections
def showcase(app, i):
    """One app on the home page. Bands alternate dark/light, so any number of apps stays balanced."""
    dark = i % 2 == 0
    theme = "dark" if dark else "light"
    shots = app["screens"][:3]
    hero_id = app.get("hero") or shots[0]["id"]
    ordered = [s for s in shots if s["id"] != hero_id]
    ordered.insert(len(ordered) // 2, screen(app, hero_id))
    phones = "".join(phone(s["id"], s["alt"], theme, extra="phone-main" if s["id"] == hero_id else "phone-side")
                     for s in ordered)
    hl = "".join(f"<li>{e(h)}</li>" for h in app["highlights"])
    return f'''<section class="band {'band-dark' if dark else 'band-light'} showcase{' flip' if i % 2 else ''}" aria-labelledby="sc-{app['slug']}">
  <div class="wrap showcase-in">
    <div class="showcase-text reveal">
      <div class="app-id">{icon(app)}<span>{e(app['name'])}</span></div>
      <h2 id="sc-{app['slug']}" class="display">{tagline_html(app['tagline'])}</h2>
      <p class="lede">{e(app['summary'])}</p>
      <ul class="ticks">{hl}</ul>
      <div class="showcase-foot">
        <a class="btn btn-primary" href="/apps/{app['slug']}">Discover {e(app['name'])}</a>
        <span class="availability">{e(availability_label(app))}</span>
      </div>
    </div>
    <div class="phones phones-{len(ordered)} reveal">{phones}</div>
  </div>
</section>'''


def app_card(app):
    s = screen(app, app.get("hero") or app["screens"][0]["id"])
    return f'''<li class="card-app reveal">
  <a href="/apps/{app['slug']}" class="card-app-link">
    <div class="card-app-shot">{phone(s['id'], s['alt'], 'light')}</div>
    <div class="card-app-text">
      <div class="app-id">{icon(app, 'sm')}<span>{e(app['name'])}</span></div>
      <h2 class="card-title">{e(app['tagline'])}</h2>
      <p>{e(app['summary'])}</p>
      <span class="availability">{e(availability_label(app))}</span>
      <span class="more" aria-hidden="true">Learn more</span>
    </div>
  </a>
</li>'''

# ------------------------------------------------------------------ pages
def build_home():
    first, second = APPS[0], APPS[1 % len(APPS)]
    hero_phones = (phone(first["hero"], screen(first, first["hero"])["alt"], "light", eager=True, extra="phone-a")
                   + (phone(second["hero"], screen(second, second["hero"])["alt"], "light", eager=True, extra="phone-b")
                      if second is not first else ""))
    showcases = "\n".join(showcase(a, i) for i, a in enumerate(APPS))
    body = f'''<section class="hero">
  <div class="wrap hero-in">
    <p class="eyebrow">Independent apps from the UK</p>
    <h1 class="display-xl">Thoughtfully simple apps.</h1>
    <p class="lede">Useful everyday apps, designed to be simple, private and a pleasure to use.</p>
    <a class="link-arrow" href="#apps">Explore the apps</a>
  </div>
  <div class="hero-phones" aria-hidden="false">{hero_phones}</div>
</section>
<div id="apps" class="anchor"></div>
{showcases}
<section class="band band-mist principles" aria-labelledby="principles-h">
  <div class="wrap">
    <h2 id="principles-h" class="display center reveal">Built the same way, every time.</h2>
    <ul class="principle-grid">
      <li class="reveal"><h3>Your data stays on your phone</h3><p>What you enter is stored on your device. There's no account to create and no server holding a copy.</p></li>
      <li class="reveal"><h3>Works offline</h3><p>The apps don't need a connection to do their job. Only store purchases go through Google Play or the App Store.</p></li>
      <li class="reveal"><h3>Focused on one job</h3><p>Each app solves one everyday problem well, without extra features you have to work around.</p></li>
    </ul>
  </div>
</section>
<section class="band band-light closing" aria-labelledby="closing-h">
  <div class="wrap narrow center reveal">
    <h2 id="closing-h" class="display">Made by one person, with care.</h2>
    <p class="lede">I'm an independent developer in the UK, building small apps that make everyday life a little easier.</p>
    <a class="link-arrow" href="/about">About ionutcm</a>
  </div>
</section>'''
    page("/", f"{BRAND} — Thoughtfully simple apps", "Useful everyday apps for Android and iPhone, designed to be simple, private and a pleasure to use. Made independently in the UK.", body)


def build_apps_index():
    cards = "".join(app_card(a) for a in APPS)
    body = f'''<section class="page-head">
  <div class="wrap">
    <p class="eyebrow">Apps</p>
    <h1 class="display-xl">Every app, in one place.</h1>
    <p class="lede">Small, focused apps that keep your information on your phone.</p>
  </div>
</section>
<section class="band band-light tight-top">
  <div class="wrap"><ul class="app-grid">{cards}</ul></div>
</section>'''
    page("/apps", "Apps", "All apps by ionutcm: simple, private apps for Android and iPhone.", body, "apps")


def build_app(app):
    slug = app["slug"]
    hero = screen(app, app["hero"])
    others = [s for s in app["screens"] if s["id"] != app["hero"]]
    hero_phones = phone(hero["id"], hero["alt"], "light", eager=True, extra="phone-main")
    if others:
        hero_phones += phone(others[0]["id"], others[0]["alt"], "light", eager=True, extra="phone-side")

    gallery = "".join(f'''<li class="gallery-item">{phone(s['id'], s['alt'], 'light')}<p class="gallery-cap"><b>{e(s['title'])}</b></p></li>'''
                      for s in app["screens"])
    gallery_dark = "".join(f'''<li class="gallery-item">{phone(s['id'], s['alt'] + ' (dark appearance)', 'dark')}<p class="gallery-cap"><b>{e(s['title'])}</b> · Dark</p></li>'''
                           for s in app["screens"])

    if app.get("steps"):
        rows = "".join(f'''<div class="feature-row{' flip' if i % 2 else ''}">
      <div class="feature-shot reveal">{phone(st['screen'], screen(app, st['screen'])['alt'], 'light')}</div>
      <div class="feature-text reveal"><p class="step-num">Step {i + 1}</p><h3 class="display-sm">{e(st['title'])}</h3><p>{e(st['text'])}</p></div>
    </div>''' for i, st in enumerate(app["steps"]))
        rows_title = "How it works"
    else:
        rows = "".join(f'''<div class="feature-row{' flip' if i % 2 else ''}">
      <div class="feature-shot reveal">{phone(s['id'], s['alt'], 'light')}</div>
      <div class="feature-text reveal"><p class="eyebrow">{e(s['title'])}</p><h3 class="display-sm">{e(s['headline'])}</h3><p>{e(s['text'])}</p></div>
    </div>''' for i, s in enumerate(app["screens"]))
        rows_title = "Everything in its place."

    feats = "".join(f'<li class="reveal"><h3>{e(f["title"])}</h3><p>{e(f["text"])}</p></li>' for f in app["features"])

    plat_cards = ""
    for r in platform_rows(app):
        action = (f'<a class="btn btn-primary" href="{e(r["url"])}" rel="noopener">Get it on {e(r["store"])}</a>' if r["url"]
                  else f'<span class="status">Coming soon to {e(r["store"])}</span>')
        plat_cards += f'''<li class="plat-card"><h3>{e(r["device"])}</h3><p>{e(r["note"] or "")}</p>{action}</li>'''

    body = f'''<section class="app-hero">
  <div class="wrap app-hero-in">
    <div class="app-hero-text">
      {icon(app, 'lg')}
      <p class="app-name">{e(app['name'])}</p>
      <h1 class="display-xl app-title">{tagline_html(app['tagline'])}</h1>
      <p class="lede">{e(app['description'])}</p>
      <div class="app-hero-actions">{store_buttons(app)}{platform_chips(app)}</div>
    </div>
    <div class="phones phones-{min(2, len(app['screens']))} app-hero-phones">{hero_phones}</div>
  </div>
</section>

<section class="band band-mist" aria-labelledby="gallery-h">
  <div class="wrap gallery-head">
    <h2 id="gallery-h" class="display">A closer look.</h2>
    <div class="gallery-nav" hidden>
      <button type="button" class="round-btn" data-gallery-prev aria-label="Previous screenshots"><span aria-hidden="true">‹</span></button>
      <button type="button" class="round-btn" data-gallery-next aria-label="Next screenshots"><span aria-hidden="true">›</span></button>
    </div>
  </div>
  <div class="gallery" tabindex="0" role="region" aria-label="{e(app['name'])} screenshots">
    <ul class="gallery-track">{gallery}{gallery_dark}</ul>
  </div>
  <p class="wrap fine">Screens show example data. Light and dark follow your phone's setting.</p>
</section>

<section class="band band-light" aria-labelledby="rows-h">
  <div class="wrap">
    <h2 id="rows-h" class="display center reveal">{e(rows_title)}</h2>
    <div class="feature-rows">{rows}</div>
  </div>
</section>

<section class="band band-mist" aria-labelledby="more-h">
  <div class="wrap">
    <h2 id="more-h" class="display-sm center reveal">Thoughtful details.</h2>
    <ul class="principle-grid compact">{feats}</ul>
  </div>
</section>

<section class="band band-dark privacy-band" aria-labelledby="privacy-h">
  <div class="wrap privacy-in">
    <div class="reveal">
      <p class="eyebrow">Privacy</p>
      <h2 id="privacy-h" class="display">Private by design.</h2>
      <p class="lede">{e(app['privacy'])}</p>
      <a class="link-arrow" href="{app['legal']['privacy']}">Read the privacy policy</a>
    </div>
    <div class="privacy-shot reveal">{phone(hero['id'], hero['alt'] + ' (dark appearance)', 'dark')}</div>
  </div>
</section>

<section class="band band-light" aria-labelledby="get-h">
  <div class="wrap">
    <h2 id="get-h" class="display center reveal">Availability.</h2>
    <p class="lede center narrow reveal">{e(app['pricing'])}</p>
    <ul class="plat-grid reveal">{plat_cards}</ul>
  </div>
</section>

<section class="band band-light tight-top help-band" aria-labelledby="help-h">
  <div class="wrap">
    <h2 id="help-h" class="display-sm center">Help and legal.</h2>
    <ul class="link-cards">
      <li><a href="/support#{slug}"><b>Support</b><span>Answers and contact</span></a></li>
      <li><a href="{app['legal']['privacy']}"><b>Privacy policy</b><span>What happens to your data</span></a></li>
      <li><a href="{app['legal']['terms']}"><b>Terms of use</b><span>Purchases and your rights</span></a></li>
    </ul>
  </div>
</section>'''
    page(f"/apps/{slug}", f"{app['name']} — {app['tagline']}", f"{app['name']}: {app['summary']}", body, "apps",
         og_image=f"/og-{slug}.png")


def build_about():
    values = [("Simplicity", "Each app does one job, and does it without fuss."),
              ("Privacy", "Your information stays on your phone. No accounts, no servers holding your data."),
              ("Practical usefulness", "Every feature has to earn its place by solving a real, everyday problem."),
              ("Clean design", "Calm screens, clear numbers and nothing competing for your attention."),
              ("Independence", "No investors and no growth targets. Just apps I'd want to use myself.")]
    vals = "".join(f'<li class="reveal"><h3>{e(t)}</h3><p>{e(d)}</p></li>' for t, d in values)
    body = f'''<section class="page-head">
  <div class="wrap narrow">
    <p class="eyebrow">About</p>
    <h1 class="display-xl">Technology should make everyday life easier.</h1>
    <p class="lede">I'm an independent app developer based in the UK. I build focused apps that solve everyday problems, without the features nobody asked for.</p>
  </div>
</section>
<section class="band band-light tight-top">
  <div class="wrap narrow prose-block reveal">
    <p>ionutcm is one person, not a company with departments. I design, build and support every app myself, and I answer every email myself too.</p>
    <p>My apps keep your information on your device, work without an account, and try to be clear about what they do. If something doesn't work the way you expect, I'd like to hear about it.</p>
  </div>
</section>
<section class="band band-mist" aria-labelledby="values-h">
  <div class="wrap">
    <h2 id="values-h" class="display center reveal">What I care about.</h2>
    <ul class="principle-grid five">{vals}</ul>
  </div>
</section>
<section class="band band-light">
  <div class="wrap narrow center reveal">
    <h2 class="display-sm">Get in touch.</h2>
    <p class="lede">Questions, ideas or problems: <a href="mailto:{EMAIL}">{EMAIL}</a></p>
    <a class="link-arrow" href="/apps">See the apps</a>
  </div>
</section>'''
    page("/about", "About", "ionutcm is an independent app developer in the UK, building simple, private apps for everyday life.", body, "about")


def build_support():
    sections = ""
    for a in APPS:
        qa = "".join(f'<details class="qa"><summary>{e(x["q"])}</summary><p>{e(x["a"])}</p></details>' for x in a["support"])
        sections += f'''<section class="support-app" id="{a['slug']}" aria-labelledby="sup-{a['slug']}">
      <div class="app-id">{icon(a, 'sm')}<h2 id="sup-{a['slug']}">{e(a['name'])}</h2></div>
      <div class="qa-list">{qa}</div>
      <p class="support-links"><a href="/apps/{a['slug']}">About the app</a><a href="{a['legal']['privacy']}">Privacy policy</a><a href="{a['legal']['terms']}">Terms of use</a></p>
    </section>'''
    body = f'''<section class="page-head">
  <div class="wrap narrow">
    <p class="eyebrow">Support</p>
    <h1 class="display-xl">How can I help?</h1>
    <p class="lede">Email me about a problem, an idea or a privacy question. I usually reply within two working days.</p>
    <div class="contact-card">
      <a class="contact-mail" href="mailto:{EMAIL}">{EMAIL}</a>
      <p>Please include the app name, your phone model and what happened.</p>
    </div>
  </div>
</section>
<section class="band band-light tight-top">
  <div class="wrap narrow">{sections}</div>
</section>'''
    page("/support", "Support", "Support and contact for ionutcm apps: answers to common questions and an email address that reaches the developer.", body, "support")


def build_legal(path, fragment, title, desc, app=None):
    body_html = open(os.path.join(CONTENT, "legal", fragment), encoding="utf-8").read()
    if "<!--APP_POLICY_LIST-->" in body_html:
        lst = "".join(f'<li><a href="{a["legal"]["privacy"]}">{e(a["name"])} privacy policy</a></li>' for a in APPS)
        body_html = body_html.replace("<!--APP_POLICY_LIST-->", f"<ul>{lst}</ul>")
    side = ""
    if app:
        side = (f'<nav class="legal-switch" aria-label="{e(app["name"])} documents">'
                f'<a href="{app["legal"]["privacy"]}"{" aria-current=\"page\"" if path == app["legal"]["privacy"] else ""}>Privacy policy</a>'
                f'<a href="{app["legal"]["terms"]}"{" aria-current=\"page\"" if path == app["legal"]["terms"] else ""}>Terms of use</a>'
                f'<a href="/apps/{app["slug"]}">About {e(app["name"])}</a></nav>')
    body = f'''<section class="legal">
  <div class="wrap narrow">
    {side}
    <article class="doc">
{body_html}
    <h2>Contact</h2>
    <div class="contact-card"><a class="contact-mail" href="mailto:{EMAIL}">{EMAIL}</a><p>ionutcm · United Kingdom</p></div>
    </article>
  </div>
</section>'''
    page(path, title, desc, body, body_class="legal-page")


def build_404():
    body = '''<section class="page-head notfound">
  <div class="wrap narrow center">
    <p class="eyebrow">404</p>
    <h1 class="display-xl">This page doesn't exist.</h1>
    <p class="lede">The link may be old or mistyped.</p>
    <div class="btn-row"><a class="btn btn-primary" href="/">Go to the home page</a><a class="btn btn-ghost" href="/apps">See the apps</a></div>
  </div>
</section>'''
    page("/404", "Page not found", "This page doesn't exist.", body)
    PAGES.remove("/404")

# ------------------------------------------------------------------ run
if __name__ == "__main__":
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(os.path.join(SRC, "static"), OUT)
    VERSIONS = {"css": asset_version(os.path.join(OUT, "assets", "site.css")),
                "js": asset_version(os.path.join(OUT, "assets", "site.js"))}
    for f in os.listdir(os.path.join(OUT, "assets", "screens")):
        VERSIONS[f[:-5]] = asset_version(os.path.join(OUT, "assets", "screens", f))
    # every screen referenced in apps.json must exist in both appearances
    for a in APPS:
        for s in a["screens"]:
            for t in ("light", "dark"):
                for suffix in ("", "-480"):
                    assert f'{s["id"]}-{t}{suffix}' in VERSIONS, f'missing screenshot {s["id"]}-{t}{suffix}.webp'
    PAGES = []
    build_home(); build_apps_index()
    for a in APPS:
        build_app(a)
    build_about(); build_support()
    build_legal("/privacy", "website-privacy.html", "Website privacy", "Privacy information for the ionutcm.com website.")
    for a in APPS:
        build_legal(a["legal"]["privacy"], f'{a["slug"]}-privacy.html', f'{a["name"]} Privacy Policy', f'Privacy policy for {a["name"]}.', a)
        build_legal(a["legal"]["terms"], f'{a["slug"]}-terms.html', f'{a["name"]} Terms of Use', f'Terms of use for {a["name"]}.', a)
    build_404()
    with open(os.path.join(OUT, "sitemap.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + "".join(f"  <url><loc>{SITE}{'/' if p == '/' else p}</loc><lastmod>{UPDATED}</lastmod></url>\n" for p in PAGES)
                + "</urlset>\n")
    with open(os.path.join(OUT, "robots.txt"), "w") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    print(f"built {len(PAGES)} pages into public/")
