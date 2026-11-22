#!/usr/bin/env python3
"""Meng Pedia static site builder — no dependencies, Python 3.8+.

  python3 build.py           build ke ./build
  python3 build.py --serve   build + preview di http://localhost:8000<base>/
"""
import html, json, math, os, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT, STATIC, THEME, OUT = ROOT / "content", ROOT / "static", ROOT / "theme", ROOT / "build"
SITE = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
BASE = SITE.get("base", "").rstrip("/")
DEVICES = json.loads((CONTENT / "devices.json").read_text(encoding="utf-8")) if (CONTENT / "devices.json").exists() else {}
ICON = lambda n, cls="": f'<span class="ms {cls}" aria-hidden="true">{n}</span>'
esc = lambda s: html.escape(str(s), quote=True)


def url(p):
    """Site-absolute path -> path with base."""
    if p.startswith("/") and not p.startswith("//"):
        return BASE + p
    return p


def strip_num(name):
    return re.sub(r"^\d+[-_]", "", name)


def slugify(text):
    t = re.sub(r"<[^>]+>", "", text).strip().lower()
    t = re.sub(r"[^\w\s-]", "", t, flags=re.U)
    return re.sub(r"\s+", "-", t).strip("-") or "section"


# ---------------------------------------------------------------- markdown
class Md:
    """Small markdown dialect: headings, paragraphs, lists, fences, images,
    links, buttons {.btn}, :::admonitions, {{device id}}, tables, quotes."""

    def __init__(self, src_dir, media):
        self.src_dir, self.media = src_dir, media
        self.toc, self.title, self.ids = [], None, {}

    # -- inline
    def media_url(self, src):
        if re.match(r"^(https?:)?//|^data:", src):
            return src
        if src.startswith("/"):
            return url(src)
        f = (self.src_dir / src).resolve()
        rel = f.relative_to(CONTENT).as_posix()
        self.media.add(rel)
        return f"{BASE}/_media/{rel}"

    def inline(self, s):
        stash = []

        def keep(h):
            stash.append(h)
            return f"\x00{len(stash) - 1}\x00"

        s = re.sub(r"`([^`]+)`", lambda m: keep(f"<code>{esc(m.group(1))}</code>"), s)
        s = esc(s).replace("&#x27;", "'")
        s = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)",
                   lambda m: keep(f'<img src="{esc(self.media_url(html.unescape(m.group(2))))}" alt="{m.group(1)}" loading="lazy">'), s)

        def link(m):
            text, href, cls = m.group(1), html.unescape(m.group(2)), m.group(3)
            ext = re.match(r"^https?://", href)
            attrs = ' target="_blank" rel="noopener"' if ext else ""
            if cls:
                kind = cls[1:]
                icon = ICON("open_in_new" if ext else "arrow_forward")
                return keep(f'<a class="{kind}" href="{esc(url(href))}"{attrs}><span>{text}</span>{icon}</a>')
            return keep(f'<a href="{esc(url(href))}"{attrs}>{text}</a>')

        s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)(?:\{(\.[\w-]+)\})?", link, s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
        s = re.sub(r"~~(.+?)~~", r"<del>\1</del>", s)
        s = re.sub(r"(?<![\"=>])(https?://[^\s<]+[^\s<.,)])", r'<a href="\1" target="_blank" rel="noopener">\1</a>', s)
        while "\x00" in s:
            s = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], s)
        return s

    # -- blocks
    RE_FENCE = re.compile(r"^(\s*)(`{3,})\s*([\w+-]*)")
    RE_HEAD = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
    RE_IMG = re.compile(r"^\s*!\[[^\]]*\]\([^)]+\)\s*$")
    RE_BTN = re.compile(r"^\s*\[[^\]]+\]\([^)]+\)\{\.btn[\w-]*\}\s*$")
    RE_LIST = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)")
    RE_DEV = re.compile(r"^\s*\{\{\s*device\s+([\w-]+)\s*\}\}\s*$")

    def heading(self, level, raw):
        inner = self.inline(raw)
        if level == 1 and self.title is None:
            self.title = inner
            return ""
        base = slugify(inner)
        n = self.ids.get(base, 0)
        self.ids[base] = n + 1
        hid = base if n == 0 else f"{base}-{n}"
        if level in (2, 3):
            self.toc.append((level, hid, re.sub(r"<[^>]+>", "", inner)))
        return f'<h{level} id="{hid}"><a class="anchor" href="#{hid}" aria-label="Tautan">#</a>{inner}</h{level}>'

    def render(self, text):
        lines = text.split("\n")
        out, para, i = [], [], 0

        def flush():
            if para:
                body = "\n".join(para)
                body = re.sub(r"( {2,}|\\)\n", "\x01\n", body)
                m = re.match(r"^\s*(\d+)\ufe0f?\u20e3\s*", body)
                inner = self.inline(body[m.end():] if m else body).replace("\x01", "<br>")
                if m:
                    out.append(f'<p class="step"><span class="step-n">{m.group(1)}</span><span>{inner}</span></p>')
                else:
                    out.append(f"<p>{inner}</p>")
                para.clear()

        while i < len(lines):
            ln = lines[i]
            st = ln.strip()
            m = self.RE_FENCE.match(ln)
            if m:
                flush()
                ind, ticks, lang = len(m.group(1)), m.group(2), m.group(3)
                code, i = [], i + 1
                while i < len(lines) and not re.match(r"^\s*`{%d,}\s*$" % len(ticks), lines[i]):
                    code.append(lines[i][ind:] if lines[i][:ind].strip() == "" else lines[i])
                    i += 1
                i += 1
                cls = f' class="lang-{lang}"' if lang else ""
                out.append(f'<div class="code"><pre><code{cls}>{esc(chr(10).join(code))}</code></pre>'
                           f'<button class="copy" type="button" aria-label="Salin">{ICON("content_copy")}</button></div>')
                continue
            if not st:
                flush(); i += 1; continue
            if st.startswith(":::") and len(st) > 3:
                flush()
                kind, _, label = st[3:].strip().partition(" ")
                depth, body, i = 1, [], i + 1
                while i < len(lines):
                    s2 = lines[i].strip()
                    if s2.startswith(":::") and len(s2) > 3:
                        depth += 1
                    elif s2 == ":::":
                        depth -= 1
                        if depth == 0:
                            break
                    body.append(lines[i]); i += 1
                i += 1
                icons = {"tip": "lightbulb", "note": "edit_note", "info": "info", "warning": "warning", "danger": "report", "caution": "warning"}
                sub = Md(self.src_dir, self.media); sub.title = ""
                out.append(f'<aside class="callout callout-{esc(kind)}"><div class="callout-head">{ICON(icons.get(kind, "info"))}'
                           f'<span>{self.inline(label or kind.capitalize())}</span></div>{sub.render(chr(10).join(body))}</aside>')
                continue
            m = self.RE_DEV.match(ln)
            if m:
                flush(); out.append(device_card(m.group(1))); i += 1; continue
            m = self.RE_HEAD.match(ln)
            if m:
                flush(); out.append(self.heading(len(m.group(1)), m.group(2))); i += 1; continue
            if re.match(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$", ln):
                flush(); out.append("<hr>"); i += 1; continue
            if self.RE_IMG.match(ln):
                flush(); out.append(f"<figure>{self.inline(st)}</figure>"); i += 1; continue
            if self.RE_BTN.match(ln):
                flush()
                btns = []
                while i < len(lines) and (self.RE_BTN.match(lines[i]) or (not lines[i].strip() and i + 1 < len(lines) and self.RE_BTN.match(lines[i + 1]))):
                    if lines[i].strip():
                        btns.append(self.inline(lines[i].strip()))
                    i += 1
                out.append(f'<div class="btn-row">{"".join(btns)}</div>')
                continue
            if st.startswith(">"):
                flush()
                q = []
                while i < len(lines) and lines[i].strip().startswith(">"):
                    q.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
                sub = Md(self.src_dir, self.media); sub.title = ""
                out.append(f"<blockquote>{sub.render(chr(10).join(q))}</blockquote>")
                continue
            if st.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-+", lines[i + 1]):
                flush()
                row = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
                head = row(ln); i += 2
                rows = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    rows.append(row(lines[i])); i += 1
                th = "".join(f"<th>{self.inline(c)}</th>" for c in head)
                tb = "".join("<tr>" + "".join(f"<td>{self.inline(c)}</td>" for c in r) + "</tr>" for r in rows)
                out.append(f'<div class="table"><table><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>')
                continue
            m = self.RE_LIST.match(ln)
            if m:
                flush()
                ordered = m.group(2)[0].isdigit()
                items = []
                while i < len(lines):
                    m2 = self.RE_LIST.match(lines[i])
                    if m2 and len(m2.group(1)) <= len(m.group(1)) + 1:
                        items.append([m2.group(3)]); i += 1
                    elif lines[i].strip() and lines[i].startswith((" ", "\t")) and not self.RE_BTN.match(lines[i]) and items:
                        items[-1].append(lines[i].strip()); i += 1
                    else:
                        break
                tag = "ol" if ordered else "ul"
                lis = "".join(f"<li>{self.inline(chr(10).join(it))}</li>" for it in items)
                out.append(f"<{tag}>{lis}</{tag}>")
                continue
            if re.match(r"^\s*<(/?)(details|summary|div|iframe|video|table|br|center)\b", ln):
                flush()
                while i < len(lines) and lines[i].strip():
                    out.append(lines[i]); i += 1
                continue
            para.append(ln.rstrip("\n") if not ln.endswith("  ") else ln)
            i += 1
        flush()
        return "\n".join(o for o in out if o)


def device_card(did):
    d = DEVICES.get(did)
    if not d:
        return f'<p class="muted">Device <code>{esc(did)}</code> tidak ditemukan di devices.json.</p>'
    bar = d.get("storageBar", [])
    segs = "".join(f'<i class="seg seg{n}" style="width:{v}%"></i>' for n, v in enumerate(bar))
    specs = "".join(f'<li><span>{esc(k)}</span><b>{esc(v)}</b></li>' for k, v in d.get("specs", []))
    used = sum(bar)
    return f'''<section class="device">
  <div class="device-top">
    <div class="device-name tile">{ICON("smartphone", "lg")}<div><small>Nama perangkat</small><strong>{esc(d["name"])}</strong>{f"<em>{esc(d['alias'])}</em>" if d.get("alias") else ""}</div></div>
    <div class="device-storage tile">{ICON("hard_drive", "lg")}<div><small>Penyimpanan · {used}% terpakai</small><strong>{esc(d.get("storage", ""))}</strong><div class="bar">{segs}</div></div></div>
  </div>
  <ul class="spec">{specs}</ul>
</section>'''


# ---------------------------------------------------------------- content tree
def frontmatter(text):
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for ln in text[3:end].strip().splitlines():
                k, _, v = ln.partition(":")
                if k.strip():
                    meta[k.strip()] = v.strip().strip('"').strip("'")
            text = text[end + 4:]
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"^import .+$", "", text, flags=re.M)
    return meta, text


def order_key(p, meta=None):
    pos = (meta or {}).get("sidebar_position") or (meta or {}).get("position")
    m = re.match(r"^(\d+)", p.name)
    return (float(pos) if pos else float(m.group(1)) if m else 999, p.name.lower())


class Page:
    def __init__(self, path, section, route, media):
        raw = path.read_text(encoding="utf-8")
        self.meta, text = frontmatter(raw)
        md = Md(path.parent, media)
        self.body = md.render(text)
        self.title = self.meta.get("title") or md.title or strip_num(path.stem).replace("-", " ")
        self.plain_title = re.sub(r"<[^>]+>", "", self.title)
        self.toc, self.section, self.route = md.toc, section, route
        plain = re.sub(r"<[^>]+>", " ", self.body)
        plain = html.unescape(re.sub(r"\s+", " ", plain)).strip()
        self.text = plain
        self.desc = self.meta.get("description") or (plain[:150] + "…" if len(plain) > 150 else plain)
        self.order = order_key(path, self.meta)


def load_section(sid, media):
    root = CONTENT / sid
    tree = []  # list of ("page", Page) | ("group", dict)

    def walk(d, prefix):
        items = []
        for p in d.iterdir():
            if p.is_file() and p.suffix == ".md":
                slug = strip_num(p.stem)
                route = f"/{sid}{prefix}/{slug}"
                pg = Page(p, sid, route, media)
                items.append((pg.order, ("page", pg)))
            elif p.is_dir() and p.name not in ("img", "images", "assets", "roms") and not p.name.startswith(("_", ".")):
                cat = {}
                cf = p / "_category_.json"
                if cf.exists():
                    cat = json.loads(cf.read_text(encoding="utf-8"))
                slug = strip_num(p.name)
                grp = {
                    "label": cat.get("label") or slug.replace("-", " ").title(),
                    "desc": (cat.get("link") or {}).get("description") or cat.get("description", ""),
                    "route": f"/{sid}{prefix}/{slug}",
                    "items": walk(p, f"{prefix}/{slug}"),
                }
                pos = cat.get("position")
                items.append(((float(pos) if pos is not None else order_key(p)[0], p.name.lower()), ("group", grp)))
        if (d / "_archive.json").exists():
            ap = ArchivePage(d / "_archive.json", sid, prefix)
            items.append(((800.0, "arsip"), ("page", ap)))
        if (d / "roms").is_dir():
            roms = [RomPage(f, sid, prefix, media) for f in (d / "roms").glob("*.json")]
            roms.sort(key=lambda r: (r.rom.get("posted", ""), r.rom.get("source", "")), reverse=True)
            for n, r in enumerate(roms):
                items.append(((900.0 + n, r.slug), ("page", r)))
        return [it for _, it in sorted(items, key=lambda x: x[0])]

    tree = walk(root, "")
    return tree


BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def tanggal(iso):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso or "")
    return f"{int(m.group(3))} {BULAN[int(m.group(2)) - 1]} {m.group(1)}" if m else esc(iso or "")


class RomPage:
    """ROM post from content/<...>/roms/<slug>.json (made by tools/tgrom.py)."""

    def __init__(self, path, section, prefix, media):
        self.rom = r = json.loads(path.read_text(encoding="utf-8"))
        self.slug = path.stem
        self.section, self.route = section, f"/{section}{prefix}/{self.slug}"
        self.md = Md(path.parent, media)
        self.md.title = ""
        self.meta, self.toc = {}, []
        self.plain_title = r["name"]
        self.title = esc(r["name"])
        self.banner = self.md.media_url(r["banner"]) if r.get("banner") else ""
        self.builder = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", r.get("by", ""))
        self.desc = f'{r["name"]} · Android {r.get("android", "?")} · {r.get("status") or "ROM"} · by {self.builder}'
        self.text = " ".join([self.desc] + r.get("notes", []) + r.get("changelog", []) + r.get("credits", []))
        self.order = (999, self.slug)
        self.body = self.render()

    def chips(self, big=False):
        r = self.rom
        st = (r.get("status") or "").upper()
        cls = {"OFFICIAL": "ok", "UNOFFICIAL": "un", "PORT": "port"}.get(st, "un")
        c = []
        if r.get("android"):
            c.append(f'<span class="rchip a">{ICON("android")}Android {esc(r["android"])}</span>')
        if st:
            c.append(f'<span class="rchip {cls}">{esc(st.title())}</span>')
        if big:
            c += [f'<span class="rchip">{esc(x)}</span>' for x in r.get("extra", [])]
        return "".join(c)

    def render(self):
        r, il = self.rom, self.md.inline
        btn = lambda cls, lab, href, ic: f'<a class="{cls}" href="{esc(href)}" target="_blank" rel="noopener">{ICON(ic)}<span>{esc(lab)}</span></a>'
        h = []
        if self.banner:
            h.append(f'<figure class="rom-banner"><img src="{esc(self.banner)}" alt="{esc(r["name"])}"></figure>')
        h.append(f'<div class="rom-chips">{self.chips(True)}</div>')
        meta = [("event", "Update", tanggal(r.get("updated") or r.get("posted"))),
                ("person", "Builder", il(r.get("by") or "-"))]
        h.append('<div class="rom-meta">' + "".join(
            f'<div class="rm">{ICON(i)}<div><small>{k}</small><span>{v}</span></div></div>' for i, k, v in meta) + "</div>")
        if r.get("downloads"):
            dls = []
            for lab, href, *rest in r["downloads"]:
                if r.get("archived") and not rest:
                    dls.append(f'<a class="dl dead" href="{esc(href)}" target="_blank" rel="noopener">{ICON("link_off")}<span>{esc(lab)}<small>link lama, mungkin mati</small></span></a>')
                else:
                    sub = f"<small>{esc(rest[0])} · Telegram</small>" if rest else ""
                    dls.append(f'<a class="dl" href="{esc(href)}" target="_blank" rel="noopener">{ICON("download")}<span>{esc(lab)}{sub}</span></a>')
            note = '<p class="muted rom-arc">File diarsipkan di grup MARBLE, perlu join grup untuk mengunduh.</p>' if r.get("archived") else ""
            h.append('<h2 id="download">Download</h2><div class="rom-dl">' + "".join(dls) + "</div>" + note)
        quick = []
        if r.get("changelog_url"):
            quick.append(btn("btn-tonal", "Changelog", r["changelog_url"], "history"))
        quick += [btn("btn-tonal", s[0], s[1], "forum") for s in r.get("support", [])]
        quick += [btn("btn-donate", s[0], s[1], "volunteer_activism") for s in r.get("donate", [])]
        quick += [btn("btn-outline", s[0], s[1], "link") for s in r.get("links", [])]
        if quick:
            h.append(f'<div class="btn-row rom-quick">{"".join(quick)}</div>')
        note_extra = [s[2] for s in r.get("donate", []) if len(s) > 2 and s[2]]
        secs = [("changelog", "Changelog", "history", "", []), ("important", "Penting", "warning", "warn", []),
                ("notes", "Notes", "sticky_note_2", "", note_extra), ("credits", "Credit", "favorite", "cred", [])]
        for key, title, ic, cls, extra in secs:
            items = r.get(key, []) + (["Donate: " + e for e in extra] if extra else [])
            if items:
                lis = "".join(f"<li>{il(x)}</li>" for x in items)
                h.append(f'<section class="rom-sec {cls}"><h2 id="{key}">{ICON(ic)}{title}</h2><ul>{lis}</ul></section>')
                self.toc.append((2, key, title))
        h.append(f'<p class="rom-src">{ICON("send")}Sumber: <a href="{esc(r["source"])}" target="_blank" rel="noopener">{esc(r["source"].replace("https://", ""))}</a></p>')
        if r.get("downloads"):
            self.toc.insert(0, (2, "download", "Download"))
        return "\n".join(h)

    def card(self):
        img = f'<img src="{esc(self.banner)}" alt="" loading="lazy">' if self.banner else shape_svg("cookie9", "rc-ph")
        r = self.rom
        return (f'<a class="rom-card" href="{url(self.route)}"><div class="rc-img">{img}</div><div class="rc-body">'
                f'<div class="rc-chips">{self.chips()}</div><h3>{esc(r["name"])}</h3>'
                f'<p>{ICON("person")}<span>{esc(self.builder)}</span></p><p>{ICON("event")}<span>{tanggal(r.get("updated") or r.get("posted"))}</span></p></div></a>')


class ArchivePage:
    """Arsip file ROM dari topik Telegram (content/<...>/_archive.json, dibuat tools/tgtopic.py)."""

    def __init__(self, path, section, prefix):
        self.data = json.loads(path.read_text(encoding="utf-8"))
        files = self.data.get("files", [])
        self.section, self.route, self.slug = section, f"/{section}{prefix}/arsip", "arsip"
        self.meta, self.toc, self.order = {}, [], (800, "arsip")
        self.plain_title = self.data.get("title", "Arsip ROM")
        self.title = esc(self.plain_title)
        self.desc = f"{len(files)} file ROM lama, langsung ke file di Telegram."
        self.text = " ".join(f'{f["rom"]} {f.get("version", "")} {f["file"]}' for f in files)
        self.body = self.render(files)

    def render(self, files):
        groups = {}
        for f in files:
            groups.setdefault(f.get("android") or "Lainnya", []).append(f)
        keys = sorted(groups, key=lambda k: (k == "Lainnya", -int(k[1:]) if k[1:].isdigit() else 0))
        chips = "".join(f'<button class="fchip" type="button" data-a="{esc(k)}">{esc(k.replace("A", "Android ", 1) if k != "Lainnya" else k)}<b>{len(groups[k])}</b></button>' for k in keys)
        h = [f'<p class="lead">{esc(self.desc)} Ketuk salah satu untuk membuka filenya di Telegram (perlu join grup).</p>',
             f'<div class="arc-tools"><label class="arc-search">{ICON("search")}<input type="search" placeholder="Cari ROM…" autocomplete="off"></label>'
             f'<div class="fchips"><button class="fchip on" type="button" data-a="">Semua<b>{len(files)}</b></button>{chips}</div></div>']
        for k in keys:
            fs = sorted(groups[k], key=lambda f: (f["rom"].lower(), f.get("date", "")))
            rows = []
            for f in fs:
                st = (f.get("status") or "").upper()
                cls = {"OFFICIAL": "ok", "UNOFFICIAL": "un", "COMMUNITY": "port"}.get(st, "un")
                c = (f'<span class="rchip {cls}">{esc(st.title())}</span>' if st else "") + \
                    (f'<span class="rchip">{esc(f["variant"])}</span>' if f.get("variant") else "") + \
                    "".join(f'<span class="rchip">{esc(t)}</span>' for t in f.get("tags", [])[:2])
                q = f'{f["rom"]} {f.get("version", "")} {f["file"]} {st} {f.get("variant", "")}'.lower()
                rows.append(
                    f'<a class="arc-item" href="{esc(f["url"])}" target="_blank" rel="noopener" data-q="{esc(q)}" data-a="{esc(k)}">'
                    f'<span class="arc-ic">{esc(f["rom"][:1].upper())}</span>'
                    f'<div class="arc-main"><strong>{esc(f["rom"])} <em>{esc(f.get("version", ""))}</em></strong>'
                    f'<div class="arc-chips">{c}</div><small>{esc(f["file"])}</small></div>'
                    f'<div class="arc-side"><span>{esc(f.get("size", ""))}</span><small>{tanggal(f.get("date") or f.get("posted"))}</small></div>'
                    f'{ICON("download", "arc-dl")}</a>')
            title = k.replace("A", "Android ", 1) if k != "Lainnya" else k
            h.append(f'<section class="arc-group" data-a="{esc(k)}"><h2 id="{esc(k.lower())}">{esc(title)}<span>{len(fs)}</span></h2><div class="arc-list">{"".join(rows)}</div></section>')
            self.toc.append((2, k.lower(), title))
        h.append('<div class="arc-empty" hidden>Tidak ada ROM yang cocok.</div>')
        if self.data.get("source"):
            h.append(f'<p class="rom-src">{ICON("send")}Sumber: <a href="{esc(self.data["source"])}" target="_blank" rel="noopener">{esc(self.data["source"].replace("https://", ""))}</a></p>')
        return "\n".join(h)


def rom_grid(roms):
    return '<div class="rom-grid">' + "".join(r.card() for r in roms) + "</div>"


def flatten(tree):
    for kind, it in tree:
        if kind == "page":
            yield it
        else:
            yield from flatten(it["items"])


def groups(tree):
    for kind, it in tree:
        if kind == "group":
            yield it
            yield from groups(it["items"])


# ---------------------------------------------------------------- shapes (M3 Expressive)
def cookie(n=9, depth=0.09, r=50, steps=360):
    pts = []
    for k in range(steps):
        a = 2 * math.pi * k / steps
        rr = r * (1 - depth + depth * math.cos(n * a))
        pts.append(f"{50 + rr * math.cos(a - math.pi / 2):.2f},{50 + rr * math.sin(a - math.pi / 2):.2f}")
    return "M" + " L".join(pts) + "Z"


SHAPES = {
    "cookie9": cookie(9, 0.08),
    "cookie12": cookie(12, 0.06),
    "sunny": cookie(8, 0.12),
    "flower": cookie(5, 0.16),
    "clover": cookie(4, 0.2),
}


def shape_svg(name, cls):
    return f'<svg class="{cls}" viewBox="0 0 100 100" aria-hidden="true"><path d="{SHAPES[name]}"/></svg>'


# ---------------------------------------------------------------- layout
FONTS = ("https://fonts.googleapis.com/css2?family=Google+Sans+Flex:opsz,wdth,wght,ROND@6..144,25..151,1..1000,0..100"
         "&family=Google+Sans+Code:wght@300..800"
         "&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap")


def layout(title, body, sections, active_sec=None, desc="", page_cls=""):
    nav_top = "".join(
        f'<a class="tab{" on" if s["id"] == active_sec else ""}" href="{url(s["first"])}">{ICON(s.get("icon", "article"))}<span>{esc(s["label"])}</span></a>'
        for s in sections)
    full_title = f"{title} · {SITE['title']}" if title != SITE["title"] else SITE["title"]
    foot = "".join(
        f'<div><h4>{esc(c["title"])}</h4>' + "".join(f'<a href="{esc(h)}" target="_blank" rel="noopener">{esc(t)}</a>' for t, h in c["links"]) + "</div>"
        for c in SITE.get("footer", []))
    return f'''<!doctype html>
<html lang="{SITE.get("lang", "id")}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(desc or SITE["tagline"])}">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(desc or SITE["tagline"])}">
<meta name="theme-color" content="#f5fafd" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0f1416" media="(prefers-color-scheme: dark)">
<link rel="icon" href="{BASE}/img/favicon.ico">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="{BASE}/_theme/style.css?v={VER}">
<script>try{{var t=localStorage.getItem("theme");if(t)document.documentElement.dataset.theme=t}}catch(e){{}}</script>
</head>
<body class="{page_cls}" data-base="{BASE}">
<header class="appbar">
  <button class="icon-btn menu" type="button" aria-label="Menu">{ICON("menu")}</button>
  <a class="brand" href="{BASE}/">{shape_svg("cookie9", "brand-shape")}<span class="brand-m">M</span><span class="brand-t">{esc(SITE["title"])}</span></a>
  <nav class="tabs">{nav_top}</nav>
  <div class="actions">
    <button class="icon-btn search-open" type="button" aria-label="Cari">{ICON("search")}</button>
    <button class="icon-btn theme" type="button" aria-label="Tema">{ICON("dark_mode", "t-dark")}{ICON("light_mode", "t-light")}</button>
  </div>
</header>
{body}
<footer class="foot">
  <div class="foot-in">
    <div class="foot-brand">{shape_svg("flower", "foot-shape")}<div><strong>{esc(SITE["title"])}</strong><p>{esc(SITE["tagline"])}</p></div></div>
    <div class="foot-cols">{foot}</div>
  </div>
  <p class="copy-r">© {YEAR} {esc(SITE["title"])} · Material 3 Expressive</p>
</footer>
<dialog class="search"><div class="search-box">
  <div class="search-field">{ICON("search")}<input type="search" placeholder="Cari catatan…" autocomplete="off"><button class="icon-btn search-close" type="button" aria-label="Tutup">{ICON("close")}</button></div>
  <div class="search-res"></div>
</div></dialog>
<dialog class="lightbox"><img alt=""><button class="icon-btn lb-close" type="button" aria-label="Tutup">{ICON("close")}</button></dialog>
<script src="{BASE}/_theme/app.js?v={VER}" defer></script>
</body>
</html>'''


def side_nav(sec, tree, current):
    def render(items, depth=0):
        h = []
        for kind, it in items:
            if kind == "page":
                on = " on" if it.route == current else ""
                h.append(f'<a class="nav-item{on}" href="{url(it.route)}"><span>{it.plain_title}</span></a>')
            else:
                inside = current.startswith(it["route"] + "/") or current == it["route"]
                h.append(f'<details class="nav-group"{" open" if inside or depth == 0 else ""}><summary>{ICON("expand_more", "chev")}'
                         f'<span>{esc(it["label"])}</span></summary><div class="nav-sub">'
                         f'<a class="nav-item{" on" if current == it["route"] else ""}" href="{url(it["route"])}/"><span>Ringkasan</span></a>'
                         f'{render(it["items"], depth + 1)}</div></details>')
        return "".join(h)
    others = "".join(f'<a class="nav-sec" href="{url(s["first"])}">{ICON(s.get("icon", "article"))}<span>{esc(s.get("long", s["label"]))}</span></a>'
                     for s in SECTIONS if s["id"] != sec["id"])
    return f'''<aside class="drawer"><div class="drawer-in">
  <div class="drawer-head">{ICON(sec.get("icon", "article"))}<span>{esc(sec.get("long", sec["label"]))}</span></div>
  <nav class="nav">{render(tree)}</nav>
  <div class="drawer-foot">{others}</div>
</div></aside><div class="scrim"></div>'''


def doc_layout(sec, tree, route, title, inner, toc=(), crumbs=(), prev=None, nxt=None):
    toc_html = ""
    if len(toc) > 1:
        toc_html = '<aside class="toc"><div class="toc-in"><h5>Di halaman ini</h5>' + "".join(
            f'<a class="l{lvl}" href="#{hid}">{esc(t)}</a>' for lvl, hid, t in toc) + "</div></aside>"
    pn = ""
    if prev or nxt:
        a = lambda p, cls, lab, ic: (f'<a class="pn {cls}" href="{url(p.route)}">{ICON(ic)}<div><small>{lab}</small><span>{p.plain_title}</span></div></a>' if p else "<span></span>")
        pn = f'<nav class="prevnext">{a(prev, "prev", "Sebelumnya", "arrow_back")}{a(nxt, "next", "Berikutnya", "arrow_forward")}</nav>'
    bc = "".join(f'<a href="{url(h)}">{esc(t)}</a>{ICON("chevron_right")}' for t, h in crumbs)
    return f'''<div class="shell">
{side_nav(sec, tree, route)}
<main class="doc">
  <div class="crumbs">{bc}</div>
  <h1 class="doc-title">{title}</h1>
  <article class="prose">{inner}</article>
  {pn}
</main>
{toc_html}
</div>'''


def home_page():
    h = SITE["home"]
    feats = "".join(
        f'<article class="feat f{n}"><div class="feat-img">{shape_svg(["cookie12", "sunny", "clover"][n % 3], "feat-shape")}'
        f'<img src="{BASE}/{esc(f["image"])}" alt="" loading="lazy"></div><h3>{esc(f["title"])}</h3><p>{esc(f["text"])}</p></article>'
        for n, f in enumerate(h.get("features", [])))
    devs = "".join(
        f'<a class="dev-card" href="{url(d["href"])}"><div class="dev-img">{shape_svg("cookie9", "dev-shape")}<img src="{BASE}/{esc(d["image"])}" alt=""></div>'
        f'<div class="dev-txt"><h3>{esc(d["title"])}</h3><p>{esc(d["text"])}</p></div><span class="dev-go">{ICON("arrow_forward")}</span></a>'
        for d in h.get("devices", []))
    latest = sorted(ALL_PAGES, key=lambda p: p.route)
    recent = "".join(f'<a class="list-item" href="{url(p.route)}">{ICON("article")}<div><strong>{p.plain_title}</strong><small>{esc(p.desc)}</small></div>{ICON("chevron_right", "end")}</a>'
                     for p in latest if not isinstance(p, RomPage) and (p.section != "docs" or "intro" in p.route))
    roms = sorted([p for p in ALL_PAGES if isinstance(p, RomPage)], key=lambda r: r.rom.get("posted", ""), reverse=True)[:6]
    cus = "/".join(roms[0].route.split("/")[:-1]) + "/" if roms else ""
    rom_block = (f'''<section class="block">
    <div class="block-head"><h2>ROM terbaru</h2><a class="btn-tonal" href="{url(cus)}"><span>Semua ROM</span>{ICON("arrow_forward")}</a></div>
    {rom_grid(roms)}
  </section>''') if roms else ""
    cta = h.get("cta")
    body = f'''<main class="home">
  <section class="hero">
    {shape_svg("sunny", "hs hs1")}{shape_svg("flower", "hs hs2")}{shape_svg("clover", "hs hs3")}
    <div class="hero-in">
      <span class="chip">{ICON("android")}Catatan oprek Android</span>
      <h1>{esc(SITE["title"])}</h1>
      <p>{esc(SITE["tagline"])}</p>
      <div class="btn-row">
        {f'<a class="btn btn-lg" href="{url(cta["href"])}"><span>{esc(cta["label"])}</span>{ICON("arrow_forward")}</a>' if cta else ""}
        <a class="btn-tonal btn-lg" href="{url(SECTIONS[-1]["first"])}"><span>{esc(SECTIONS[-1]["label"])}</span>{ICON("smartphone")}</a>
      </div>
    </div>
  </section>
  <section class="feats">{feats}</section>
  <section class="block">
    <div class="block-head"><h2>Perangkat</h2><p>Dokumentasi per device.</p></div>
    <div class="devs">{devs}</div>
  </section>
  {rom_block}
  <section class="block">
    <div class="block-head"><h2>Semua catatan</h2></div>
    <div class="list">{recent}</div>
  </section>
</main>'''
    return layout(SITE["title"], body, SECTIONS, page_cls="is-home")


# ---------------------------------------------------------------- build
import datetime
YEAR = datetime.date.today().year
VER = datetime.datetime.now().strftime("%y%m%d%H%M")
SECTIONS, ALL_PAGES = [], []


def write(route, html_text):
    d = OUT / route.strip("/")
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(html_text, encoding="utf-8")


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    media = set()
    trees = {}
    SECTIONS.clear(); ALL_PAGES.clear()
    for s in SITE["sections"]:
        tree = load_section(s["id"], media)
        pages = list(flatten(tree))
        if not pages:
            continue
        sec = dict(s, first=pages[0].route)
        SECTIONS.append(sec)
        trees[s["id"]] = (sec, tree, pages)
        ALL_PAGES.extend(pages)

    for sid, (sec, tree, pages) in trees.items():
        for n, p in enumerate(pages):
            crumbs = [(sec["label"], sec["first"])]
            for g in groups(tree):
                if p.route.startswith(g["route"] + "/"):
                    crumbs.append((g["label"], g["route"] + "/"))
            body = doc_layout(sec, tree, p.route, p.title, p.body, p.toc, crumbs,
                              pages[n - 1] if n else None, pages[n + 1] if n + 1 < len(pages) else None)
            write(p.route, layout(p.plain_title, body, SECTIONS, sid, p.desc))
        for g in groups(tree):
            kids = []
            for kind, it in g["items"]:
                if kind == "page":
                    kids.append(f'<a class="list-item" href="{url(it.route)}">{ICON("article")}<div><strong>{it.plain_title}</strong><small>{esc(it.desc)}</small></div>{ICON("chevron_right", "end")}</a>')
                else:
                    kids.append(f'<a class="list-item" href="{url(it["route"])}/">{ICON("folder")}<div><strong>{esc(it["label"])}</strong><small>{esc(it["desc"])}</small></div>{ICON("chevron_right", "end")}</a>')
            roms = [it for kind, it in g["items"] if kind == "page" and isinstance(it, RomPage)]
            if roms:
                kids = [k for k, (kind, it) in zip(kids, g["items"]) if not isinstance(it, RomPage)]
                kids_html = (f'<div class="list">{"".join(kids)}</div>' if kids else "") + rom_grid(roms)
                inner = (f'<p class="lead">{esc(g["desc"])}</p>' if g["desc"] else "") + kids_html
                body = doc_layout(sec, tree, g["route"], esc(g["label"]), inner, crumbs=[(sec["label"], sec["first"])])
                write(g["route"], layout(g["label"], body, SECTIONS, sid, g["desc"]))
                continue
            inner = (f'<p class="lead">{esc(g["desc"])}</p>' if g["desc"] else "") + (
                f'<div class="list">{"".join(kids)}</div>' if kids else
                f'<div class="empty">{shape_svg("cookie12", "empty-shape")}{ICON("construction", "xl")}<p>Segera hadir.</p></div>')
            body = doc_layout(sec, tree, g["route"], esc(g["label"]), inner, crumbs=[(sec["label"], sec["first"])])
            write(g["route"], layout(g["label"], body, SECTIONS, sid, g["desc"]))
        # /docs/ and /marble/ -> first page
        write(f"/{sid}", redirect(sec["first"]))

    (OUT / "index.html").write_text(home_page(), encoding="utf-8")
    nf = f'''<main class="home"><section class="hero nf">{shape_svg("sunny", "hs hs1")}<div class="hero-in"><span class="chip">{ICON("explore_off")}404</span>
<h1>Halaman tidak ditemukan</h1><p>Mungkin sudah pindah. Coba cari atau kembali ke beranda.</p>
<div class="btn-row"><a class="btn btn-lg" href="{BASE}/"><span>Beranda</span>{ICON("home")}</a></div></div></section></main>'''
    (OUT / "404.html").write_text(layout("404", nf, SECTIONS), encoding="utf-8")

    idx = [{"t": p.plain_title, "u": url(p.route), "s": next(s["label"] for s in SECTIONS if s["id"] == p.section),
            "x": p.text[:4000]} for p in ALL_PAGES]
    (OUT / "search.json").write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")

    if STATIC.exists():
        shutil.copytree(STATIC, OUT, dirs_exist_ok=True)
    shutil.copytree(THEME, OUT / "_theme")
    for rel in sorted(media):
        src = CONTENT / rel
        if src.exists():
            dst = OUT / "_media" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        else:
            print(f"  ! gambar hilang: {rel}")
    (OUT / ".nojekyll").touch()
    print(f"OK {len(ALL_PAGES)} halaman, {len(media)} gambar -> {OUT}")


def redirect(to):
    u = url(to)
    return f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={u}"><link rel="canonical" href="{u}"><a href="{u}">{u}</a>'


def serve(port=8000):
    import http.server, functools

    class H(http.server.SimpleHTTPRequestHandler):
        def translate_path(self, path):
            if BASE and path.startswith(BASE):
                path = path[len(BASE):] or "/"
            return super().translate_path(path)

        def send_error(self, code, message=None, explain=None):
            if code == 404 and (OUT / "404.html").exists():
                b = (OUT / "404.html").read_bytes()
                self.send_response(404); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
            else:
                super().send_error(code, message, explain)

    srv = http.server.ThreadingHTTPServer(("0.0.0.0", port), functools.partial(H, directory=str(OUT)))
    print(f"Preview: http://localhost:{port}{BASE}/  (Ctrl+C stop)")
    srv.serve_forever()


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        serve(int(os.environ.get("PORT", 8000)))
