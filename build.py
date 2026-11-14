#!/usr/bin/env python3
"""Build the site.

Reads site.json and everything in content/, then writes the finished website
into dist/. Preview it with:

    python build.py
    python -m http.server -d dist
"""
import datetime
import html
import json
import re
import shutil
import zlib
from pathlib import Path
from urllib.parse import quote

import markdown
import yaml

try:
    from PIL import Image, ImageOps
except ImportError:  # without Pillow, photos are copied as they are, without resizing
    Image = None

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
STATIC = ROOT / "static"
DIST = ROOT / "dist"
MEDIA = ROOT / "media"
TODAY = datetime.date.today()

esc = html.escape

STAGES = {
    "seedling": ("Seedling", "Rough first thoughts"),
    "budding": ("Budding", "Taking shape"),
    "evergreen": ("Evergreen", "Kept up to date"),
}
BOOK_STATUS = {"reading": "Reading", "finished": "Finished", "want": "Want to read"}
BOOK_COLORS = ["#167A3C", "#121A16", "#2F4A44", "#9DB8A6", "#55625B", "#0F5A2B", "#C9D3CC"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
FONTS = (
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600"
    "&family=JetBrains+Mono:wght@400;500&family=Space+Grotesk:wght@500;600;700&display=swap"
)
# [[note-name]] or [[note-name|label]]; editors sometimes escape the brackets with backslashes
WIKI = re.compile(r"\\?\[\\?\[([^\]\\|]+)(?:\|([^\]\\]+))?\\?\]\\?\]")
FRONT = re.compile(r"\A---[ \t]*\r?\n(.*?)^---[ \t]*\r?\n?(.*)\Z", re.S | re.M)


# ---------- Helpers ----------

def fmt_date(value, short=False):
    try:
        d = datetime.date.fromisoformat(str(value))
    except ValueError:
        return str(value or "")
    base = f"{MONTHS[d.month - 1]} {d.day}"
    return base if short else f"{base}, {d.year}"


def tag_slug(tag):
    slug = re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")
    return slug or f"tag-{zlib.crc32(tag.encode('utf-8')) % 100000}"


def write(rel_path, text):
    target = DIST / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def load_json(name, default):
    path = CONTENT / name if (CONTENT / name).exists() else ROOT / name
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


# ---------- Photos ----------
# Photos live in the media/ folder. Each one is resized once into dist/media/
# so that phone photos (often 4 MB or more) do not slow the site down.

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_variants = {}


def media_url(ref, root, width):
    """Return the URL of a resized copy of a photo from media/, or None if it is missing."""
    if not ref:
        return None
    rel = str(ref).strip().lstrip("./").lstrip("/")
    if rel.startswith("media/"):
        rel = rel[len("media/"):]
    src = (MEDIA / rel).resolve()
    if MEDIA.resolve() not in src.parents or not src.is_file():
        print(f"warning: photo not found, skipped: {ref}")
        return None
    key = (rel, width)
    if key not in _variants:
        ext = src.suffix.lower()
        if Image is not None and ext in IMAGE_EXTS:
            out_rel = f"media/_w{width}/{rel}"
            out = DIST / out_rel
            out.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(src) as opened:
                im = ImageOps.exif_transpose(opened)
                if im.width > width:
                    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
                if ext in (".jpg", ".jpeg"):
                    im.convert("RGB").save(out, "JPEG", quality=82, optimize=True, progressive=True)
                elif ext == ".png":
                    im.save(out, "PNG", optimize=True)
                else:
                    im.save(out, "WEBP", quality=82)
        else:
            out_rel = f"media/{rel}"
            out = DIST / out_rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, out)
        _variants[key] = out_rel
    return root + quote(_variants[key])


def cover_html(book, index, root=""):
    """A book cover: the photo if the book has one, otherwise a coloured block."""
    color = esc(book.get("color") or BOOK_COLORS[index % len(BOOK_COLORS)], quote=True)
    url = media_url(book.get("cover"), root, 360)
    img = ""
    if url:
        alt = esc("Cover of " + book["title"], quote=True)
        img = f'<img src="{esc(url, quote=True)}" alt="{alt}" loading="lazy" decoding="async">'
    return f'<div class="cover" style="background:{color}">{img}</div>'


IMG_SRC = re.compile(r'(<img\b[^>]*?\bsrc=")([^"]+)(")')


def fix_images(html_text, root, width=1400):
    """Point photos inside Markdown text at their resized copies."""
    def repl(m):
        src = m.group(2)
        if re.match(r"^(?:[a-z][a-z0-9+.-]*:|//)", src, re.I):
            return m.group(0)
        url = media_url(src, root, width)
        return f"{m.group(1)}{esc(url, quote=True)}{m.group(3)}" if url else m.group(0)
    return IMG_SRC.sub(repl, html_text).replace("<img ", '<img loading="lazy" ')


def render_markdown(text):
    md = markdown.Markdown(
        extensions=["fenced_code", "tables", "toc", "sane_lists"],
        extension_configs={"toc": {"toc_depth": "2-2"}},
    )
    out = md.convert(text)
    headings = [(t["id"], t["name"]) for t in md.toc_tokens if t["level"] == 2]
    return out, headings


def split_front_matter(text, name=""):
    """Split a Markdown file into its front matter (a dict) and its body."""
    m = FRONT.match(text)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as err:
        print(f"warning: could not read the front matter of {name}: {err}")
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return {str(k).lower(): v for k, v in meta.items()}, m.group(2)


def stage_chip(stage):
    return f'<span class="stage stage-{stage}">{STAGES[stage][0]}</span>'


# ---------- Notes ----------

def load_notes():
    notes = {}
    for path in sorted((CONTENT / "notes").glob("*.md")):
        meta, body = split_front_matter(path.read_text(encoding="utf-8"), path.name)
        stage = str(meta.get("stage") or "seedling").lower()
        raw_tags = meta.get("tags") or []
        if isinstance(raw_tags, str):
            raw_tags = raw_tags.split(",")
        notes[path.stem] = {
            "slug": path.stem,
            "title": str(meta.get("title") or path.stem.replace("-", " ").title()),
            "stage": stage if stage in STAGES else "seedling",
            "tags": [str(t).strip() for t in raw_tags if str(t).strip()],
            "date": str(meta.get("date") or "")[:10],
            "summary": str(meta.get("summary") or ""),
            "body": body,
            "links_to": set(),
            "backlinks": [],
        }
    for note in notes.values():
        def repl(m, note=note):
            target = notes.get(m.group(1).strip())
            label = m.group(2)
            if not target:
                return label or m.group(1)
            note["links_to"].add(target["slug"])
            return f"[{label or target['title']}]({target['slug']}.html)"
        note["body"] = WIKI.sub(repl, note["body"])
    for note in notes.values():
        for slug in note["links_to"]:
            if slug != note["slug"]:
                notes[slug]["backlinks"].append(note["slug"])
    return sorted(notes.values(), key=lambda n: (n["date"], n["title"]), reverse=True)


# ---------- Shared page shell ----------

def layout(site, title, body, root, current="", description=""):
    nav = [("Home", "index.html", "home"), ("Books", "books.html", "books"),
           ("Notes", "notes.html", "notes"), ("Projects", "projects.html", "projects"),
           ("About", "about.html", "about")]
    items = ""
    for label, href, key in nav:
        aria = ' aria-current="page"' if key == current else ""
        items += f'<a href="{root}{href}"{aria}>{label}</a>'
    name = site["name"]
    full_title = name if title == name else f"{title} · {name}"
    desc = esc(description or site.get("description", ""), quote=True)
    mark = esc(name[:1].upper())
    icon = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
            "%3Crect width='32' height='32' rx='7' fill='%23167A3C'/%3E%3Ctext x='16' y='23' "
            "font-size='20' font-family='sans-serif' font-weight='700' text-anchor='middle' "
            f"fill='white'%3E{mark}%3C/text%3E%3C/svg%3E")
    links = "".join(
        f'<a href="{esc(l["url"], quote=True)}">{esc(l["label"])}</a>'
        for l in site.get("links", []) if l.get("url")
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{esc(full_title, quote=True)}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<link rel="icon" href="{icon}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="{root}style.css">
</head>
<body>
<header class="site-header band"><div class="wrap">
<a class="brand" href="{root}index.html"><span class="brand-mark">{mark}</span>{esc(name)}</a>
<nav class="nav" aria-label="Main">{items}</nav>
</div></header>
<main>
{body}
</main>
<footer class="site-footer band"><div class="wrap">
<span>Built {fmt_date(TODAY.isoformat())}</span>
<span>{links}</span>
</div></footer>
</body>
</html>
"""


def note_row(note, root=""):
    tags = " · ".join(esc(t) for t in note["tags"])
    return (f'<a class="note-row" href="{root}notes/{note["slug"]}.html">'
            f'{stage_chip(note["stage"])}'
            f'<span class="note-title">{esc(note["title"])}</span>'
            f'<span class="note-tags">{tags}</span>'
            f'<span class="note-date">{esc(fmt_date(note["date"], short=True))}</span></a>')


# ---------- Pages ----------

def home_page(site, books, notes):
    now_rows = "".join(
        f'<div class="now-row"><span class="label">{esc(r["label"])}</span>'
        f'<span class="now-text">{esc(r["text"])}</span></div>'
        for r in site.get("now", [])
    )
    updated = fmt_date(site.get("now_updated", TODAY.isoformat()))
    who = ""
    photo = media_url(site.get("photo"), "", 640)
    if photo:
        alt = esc(site.get("photo_alt") or f"Photo of {site['name']}", quote=True)
        tagline = f'<span class="meta">{esc(site["tagline"])}</span>' if site.get("tagline") else ""
        who = (f'<div class="who"><img class="avatar" src="{esc(photo, quote=True)}" alt="{alt}">'
               f'<div><strong>{esc(site["name"])}</strong>{tagline}</div></div>')
    hero = f"""<section class="hero band"><div class="wrap hero-grid">
<div class="hero-copy">
<h1>{esc(site["headline"])}</h1>
<p class="lede">{esc(site["intro"])}</p>
<div class="btns"><a class="btn btn-primary" href="notes.html">Read the notes</a><a class="btn btn-ghost" href="books.html">See the bookshelf</a></div>
</div>
<aside class="card now">{who}<div class="now-head"><span class="label label-strong">Now</span><span class="meta">Updated {updated}</span></div>{now_rows}</aside>
</div></section>"""

    cards_top = ""
    reading = next((b for b in books if b.get("status") == "reading"), None)
    if reading:
        index = books.index(reading)
        progress = ""
        p = reading.get("progress")
        if p and p.get("total"):
            total, cur = int(p["total"]), int(p.get("current") or 0)
            segs = "".join(
                f'<span class="seg{" seg-done" if i < cur else " seg-now" if i == cur else ""}"></span>'
                for i in range(1, total + 1)
            )
            progress = (f'<div class="segs">{segs}</div>'
                        f'<span class="meta">Chapter {cur} of {total} · {esc(p.get("label", ""))}</span>')
        link = ""
        if reading.get("note"):
            link = f'<a class="textlink" href="notes/{esc(reading["note"])}.html">Read my notes →</a>'
        cards_top += f"""<div class="card">
<span class="label">Currently reading</span>
<div class="reading">{cover_html(reading, index)}
<div><h3>{esc(reading["title"])}</h3><span class="byline">{esc(reading.get("author", ""))}</span>
<p style="margin-top:8px">{esc(reading.get("takeaway", ""))}</p></div></div>
{progress}{link}</div>"""

    counts = [0] * 12
    for b in books:
        try:
            d = datetime.date.fromisoformat(str(b.get("finished", "")))
        except ValueError:
            continue
        if d.year == TODAY.year:
            counts[d.month - 1] += 1
    if sum(counts):
        top = max(counts)
        cols = "".join(
            f'<div class="col"><span class="val">{c or ""}</span>'
            f'<span class="bar" style="height:{round(c / top * 112) if c else 2}px"></span></div>'
            for c in counts
        )
        month_labels = "".join(f"<span>{m}</span>" for m in MONTHS)
        cards_top += f"""<div class="card">
<span class="label">Books finished per month, {TODAY.year}</span>
<div class="chart">{cols}</div><div class="months">{month_labels}</div></div>"""
    top_row = f'<div class="row row-wide">{cards_top}</div>' if cards_top else ""

    info = ""
    for c in site.get("cards", []):
        body = ""
        if c.get("text"):
            body += f'<p>{esc(c["text"])}</p>'
        if c.get("steps"):
            cur = int(c.get("current", 0))
            steps = "".join(
                f'<div class="step"><span class="dot{" dot-on" if i <= cur else ""}">{i}</span>{esc(s)}</div>'
                for i, s in enumerate(c["steps"], 1)
            )
            body += f'<div class="steps">{steps}</div>'
        if c.get("tags"):
            body += '<div class="tags">' + "".join(f'<span class="tag">{esc(t)}</span>' for t in c["tags"]) + "</div>"
        info += f'<div class="card"><span class="label">{esc(c["label"])}</span><h3>{esc(c["title"])}</h3>{body}</div>'
    info_row = f'<div class="row">{info}</div>' if info else ""

    recent = "".join(note_row(n) for n in notes[:4])
    notes_section = f"""<section class="section band"><div class="wrap">
<div class="section-head"><h2>Recently tended notes</h2><a class="textlink" href="notes.html">All notes →</a></div>
<div class="note-list">{recent}</div>
<p class="hint">Seedlings are rough first thoughts. Budding notes are taking shape. Evergreen notes are ones I stand behind and keep up to date.</p>
</div></section>"""

    tiles = "".join(
        f'<a class="tile" href="{esc(t["href"], quote=True)}"><strong>{esc(t["name"])}</strong><span>{esc(t["desc"])}</span></a>'
        for t in site.get("tiles", [])
    )
    tiles_section = f"""<section class="section band"><div class="wrap">
<div class="section-head"><h2>Everything else</h2></div><div class="tiles">{tiles}</div></div></section>"""

    body = f'{hero}<section class="dash band"><div class="wrap">{top_row}{info_row}</div></section>{notes_section}{tiles_section}'
    return layout(site, site["name"], body, "", "home")


def books_page(site, books):
    counts = {"all": len(books)}
    for key in BOOK_STATUS:
        counts[key] = sum(1 for b in books if b.get("status") == key)
    chip_defs = [("all", "All")] + list(BOOK_STATUS.items())
    chips = "".join(
        f'<button type="button" class="chip" data-filter="{key}" aria-pressed="{"true" if key == "all" else "false"}">'
        f'{label}<small>{counts.get(key, 0)}</small></button>'
        for key, label in chip_defs
    )

    heights = [150, 120, 172, 136, 160, 112, 146, 176, 126, 156]
    widths = [26, 34, 30, 40, 28, 36, 24, 32, 38, 28]
    spines = ""
    for i, b in enumerate(books):
        color = b.get("color") or BOOK_COLORS[i % len(BOOK_COLORS)]
        cover = media_url(b.get("cover"), "", 360)
        if cover:
            spines += f'<img class="shelf-cover" src="{esc(cover, quote=True)}" alt="" loading="lazy" decoding="async">'
        else:
            spines += f'<div class="spine" style="width:{widths[i % 10]}px;height:{heights[i % 10]}px;background:{esc(color)}"></div>'
    for j in range(len(books), max(len(books), 10)):
        spines += f'<div class="slot" style="width:{widths[j % 10]}px;height:{heights[j % 10]}px"></div>'

    rows = ""
    for i, b in enumerate(books):
        status = b.get("status", "want")
        if status not in BOOK_STATUS:
            status = "want"
        title = esc(b["title"])
        if b.get("note"):
            title_html = f'<a class="btitle" href="notes/{esc(b["note"])}.html">{title}</a>'
        else:
            title_html = f'<span class="btitle">{title}</span>'
        take = f'<span class="btake">{esc(b["takeaway"])}</span>' if b.get("takeaway") else ""
        rows += (f'<div class="brow" data-status="{status}">{cover_html(b, i)}'
                 f'<div class="binfo">{title_html}<span class="byline">{esc(b.get("author", ""))}</span>{take}</div>'
                 f'<span class="status status-{status}">{BOOK_STATUS[status]}</span></div>')

    script = """<script>
document.querySelectorAll('[data-filter]').forEach(function (btn) {
  btn.addEventListener('click', function () {
    var f = btn.getAttribute('data-filter');
    document.querySelectorAll('[data-filter]').forEach(function (b) {
      b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
    });
    document.querySelectorAll('.brow').forEach(function (r) {
      r.hidden = !(f === 'all' || r.getAttribute('data-status') === f);
    });
  });
});
</script>"""
    body = f"""<section class="page-head band"><div class="wrap"><h1>Bookshelf</h1>
<p>What I'm reading, what I've finished, and the one thing I kept from each.</p></div></section>
<section class="band"><div class="wrap">
<div class="shelf-scroll"><div class="shelf"><div class="spines" aria-hidden="true">{spines}</div><div class="plank"></div></div></div>
<div class="chips" style="margin-top:32px">{chips}</div>
<div class="book-list">{rows}</div>
</div></section>{script}"""
    return layout(site, "Books", body, "", "books", "What I'm reading and what I took from each book.")


def notes_index(site, notes, tags):
    stage_legend = "".join(
        f'<div class="legend">{stage_chip(k)}<span>{v[1]}</span></div>' for k, v in STAGES.items()
    )
    tag_links = "".join(
        f'<a class="tag" href="tags/{tag_slug(t)}.html">{esc(t)} · {len(ns)}</a>' for t, ns in sorted(tags.items())
    )
    rows = "".join(note_row(n) for n in notes) or '<p class="hint">No notes yet. Add a Markdown file to content/notes/.</p>'
    body = f"""<section class="page-head band"><div class="wrap"><h1>Notes</h1>
<p>A garden of notes that I keep editing. Each one shows how far along it is.</p></div></section>
<section class="band"><div class="wrap">
<div class="tags" style="margin-bottom:24px">{tag_links}</div>
<div class="note-list">{rows}</div>
<div class="side-block" style="margin-top:32px;max-width:420px"><span class="label">Growth stages</span>{stage_legend}</div>
</div></section>"""
    return layout(site, "Notes", body, "", "notes", "Notes I keep editing as I learn.")


def tag_page(site, tag, notes):
    rows = "".join(note_row(n, "../") for n in notes)
    body = f"""<section class="page-head band"><div class="wrap"><h1>{esc(tag)}</h1>
<p>{len(notes)} note{"s" if len(notes) != 1 else ""} tagged "{esc(tag)}".</p></div></section>
<section class="band"><div class="wrap"><div class="note-list">{rows}</div>
<p class="hint"><a class="textlink" href="../notes.html">← All notes</a></p></div></section>"""
    return layout(site, tag, body, "../", "notes")


def note_page(site, note, by_slug):
    content, headings = render_markdown(note["body"])
    content = fix_images(content, "../")
    words = len(re.findall(r"\w+", note["body"]))
    minutes = max(1, round(words / 200))
    toc = ""
    if len(headings) > 1:
        links = "".join(f'<a href="#{i}">{esc(n)}</a>' for i, n in headings)
        toc = f'<div class="side-block"><span class="label">On this page</span>{links}</div>'
    back = ""
    if note["backlinks"]:
        links = "".join(f'<a href="{s}.html">{esc(by_slug[s]["title"])}</a>' for s in note["backlinks"])
        back = f'<div class="side-block"><span class="label">Linked from</span>{links}</div>'
    tags = ""
    if note["tags"]:
        links = "".join(f'<a class="tag" href="../tags/{tag_slug(t)}.html">{esc(t)}</a>' for t in note["tags"])
        tags = f'<div class="side-block"><span class="label">Tags</span><div class="tags">{links}</div></div>'
    legend = "".join(f'<div class="legend">{stage_chip(k)}<span>{v[1]}</span></div>' for k, v in STAGES.items())
    summary = f'<p class="summary">{esc(note["summary"])}</p>' if note["summary"] else ""
    body = f"""<div class="band"><div class="wrap note-layout">
<article class="note-main">
<div class="crumbs"><a href="../notes.html">Notes</a><span>/</span><span>{esc(note["title"])}</span></div>
<div class="note-meta">{stage_chip(note["stage"])}<span class="meta">Last tended {esc(fmt_date(note["date"]))} · {minutes} min read</span></div>
<h1>{esc(note["title"])}</h1>
{summary}
<div class="prose">{content}</div>
</article>
<aside class="side">{toc}{back}{tags}<div class="side-block"><span class="label">Growth stages</span>{legend}</div></aside>
</div></div>"""
    return layout(site, note["title"], body, "../", "notes", note["summary"])


def projects_page(site, projects):
    cards = ""
    for p in projects:
        tags = ""
        if p.get("tags"):
            tags = '<div class="tags">' + "".join(f'<span class="tag">{esc(t)}</span>' for t in p["tags"]) + "</div>"
        link = f'<a class="textlink" href="{esc(p["url"], quote=True)}">View project →</a>' if p.get("url") else ""
        cards += f'<div class="card"><h3>{esc(p["title"])}</h3><p>{esc(p.get("description", ""))}</p>{tags}{link}</div>'
    body = f"""<section class="page-head band"><div class="wrap"><h1>Projects</h1>
<p>Things I've built and am still building.</p></div></section>
<section class="band"><div class="wrap"><div class="proj-grid">{cards}</div></div></section>"""
    return layout(site, "Projects", body, "", "projects", "Projects I've built.")


def about_page(site):
    path = CONTENT / "about.md"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    _, text = split_front_matter(text, "about.md")
    content, _ = render_markdown(text)
    content = fix_images(content, "")
    photo = media_url(site.get("photo"), "", 640)
    img = ""
    if photo:
        alt = esc(site.get("photo_alt") or f"Photo of {site['name']}", quote=True)
        img = f'<img class="about-photo" src="{esc(photo, quote=True)}" alt="{alt}">'
    body = f"""<section class="page-head band"><div class="wrap"><h1>About</h1></div></section>
<section class="band"><div class="wrap about-grid">{img}<div class="prose prose-narrow">{content}</div></div></section>"""
    return layout(site, "About", body, "", "about", "About " + site["name"])


def not_found(site):
    body = """<section class="page-head band"><div class="wrap"><h1>Page not found</h1>
<p>That page doesn't exist. Use the menu to find your way back.</p></div></section>"""
    return layout(site, "Not found", body, "", "")


# ---------- Build ----------

def main():
    site = load_json("site.json", {})
    # Editors may save empty fields as "" or null; treat those as not set.
    def clean(items):
        return [{k: v for k, v in item.items() if v not in (None, "")} for item in items]

    books = clean(load_json("books.json", []))
    projects = clean(load_json("projects.json", []))
    notes = load_notes()
    by_slug = {n["slug"]: n for n in notes}
    tags = {}
    for n in notes:
        for t in n["tags"]:
            tags.setdefault(t, []).append(n)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    shutil.copy(STATIC / "style.css", DIST / "style.css")
    write(".nojekyll", "")

    write("index.html", home_page(site, books, notes))
    write("books.html", books_page(site, books))
    write("notes.html", notes_index(site, notes, tags))
    write("projects.html", projects_page(site, projects))
    write("about.html", about_page(site))
    write("404.html", not_found(site))
    for n in notes:
        write(f"notes/{n['slug']}.html", note_page(site, n, by_slug))
    for t, ns in tags.items():
        write(f"tags/{tag_slug(t)}.html", tag_page(site, t, ns))

    pages = sum(1 for _ in DIST.rglob("*.html"))
    print(f"Built {pages} pages into {DIST.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
