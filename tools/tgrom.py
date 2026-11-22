#!/usr/bin/env python3
"""Import ROM post dari Telegram (channel/grup publik) ke content/.../roms/*.json

  python3 tools/tgrom.py https://t.me/PocoF5IDUpdates/4444 [link lain...]
  python3 tools/tgrom.py --latest 10 PocoF5IDUpdates
  python3 tools/tgrom.py --range 304 2000 PocoF5IDUpdates --archive content/marble/02-cusrom/_archive.json
      -> import post lama, link download diarahkan ke file di arsip topik (yg cocok saja)
  opsi: --out content/marble/02-cusrom/roms   (default)   --force (timpa yg sudah ada)

Yang diambil: nama ROM, status, versi Android, tanggal update, builder, banner,
link download, changelog, support grup, donate, notes, important, credit.
"""
import html, json, re, sys, urllib.request
import netcache  # noqa: F401
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 16) AppleWebKit/537.36 Chrome/140 Mobile Safari/537.36"}


def get(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "replace")


def slugify(s):
    s = re.sub(r"[^\w\s-]", "", s.lower(), flags=re.A)
    return re.sub(r"[\s_-]+", "-", s).strip("-")


# ---------------------------------------------------------------- telegram html -> markdown-ish text
def messages(page):
    for chunk in page.split('class="tgme_widget_message_wrap')[1:] or [page]:
        m = re.search(r'data-post="([^"]+)"', chunk)
        if not m:
            continue
        t = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>\s*(?:<div class="tgme_widget_message_(?:footer|reply_markup|link_preview)|</div>)', chunk, re.S)
        if not t:
            continue
        raw = t.group(1)
        txt = re.sub(r"<br\s*/?>", "\n", raw)
        txt = re.sub(r'<a href="([^"]+)"[^>]*>(.*?)</a>',
                     lambda a: f"[{re.sub('<[^>]+>', '', a.group(2)).strip()}]({html.unescape(a.group(1))})", txt, flags=re.S)
        txt = html.unescape(re.sub(r"<[^>]+>", "", txt))
        txt = re.sub(r"\[(#\w+)\]\(\?q=[^)]*\)", r"\1", txt)  # hashtag link -> plain
        date = re.search(r'<time[^>]*datetime="([^"]+)"', chunk)
        banner = re.search(r"tgme_widget_message_(?:photo_wrap|video_thumb)[^>]*background-image:url\('([^']+)'\)", chunk)
        yield {"post": m.group(1), "posted": date.group(1) if date else "", "text": txt,
               "banner": banner.group(1) if banner else None}


# ---------------------------------------------------------------- text -> rom dict
LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
SECTIONS = [
    ("changelog", r"change ?logs?"), ("important", r"important|warning|attention"),
    ("notes", r"notes?"), ("credits", r"credits?|thanks(?: to)?|special thanks"),
]


def classify(label):
    l = label.lower()
    if re.search(r"donat|\bthr\b|paypal|saweria|trakteer|buy me|kofi|ko-fi", l): return "donate"
    if re.search(r"changelog", l): return "changelog"
    if re.search(r"support|group|chat|discuss|playground", l): return "support"
    if re.search(r"download|donwload|gapps|vanilla|fastboot|recovery|mirror|gms|core|full|lite|\.zip|sourceforge|^rom", l): return "download"
    return "link"


def normalize(text):
    text = text.replace("👉", "\n🔸").replace("\u25aa\ufe0f", "\n🔸").replace("\u25aa", "\n🔸").replace("➤", "\n🔸")
    text = re.sub(r"\)\s*(Notes?|Changelogs?|Credits?|Thanks to|Important)\s*:", r")\n\n\1:", text)
    text = re.sub(r"\)\s*•", ")\n•", text)
    text = re.sub(r"\]\(([^)]+)\)\s+I\s+\[", r"](\1) | [", text)  # "Gapps I Vanilla"
    return text


def parse(msg):
    lines = [ln.rstrip() for ln in normalize(msg["text"]).split("\n")]
    lines = [ln for ln in lines if not re.search(r"(follow|join)\s*\[?@", ln, re.I) and not re.match(r"^\s*(#\w+\s*)+$", ln)]
    lines = [ln for ln in lines if not re.match(r"^[\W\d\s]+$", ln) or LINK.search(ln)]  # drop reaction-only lines
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return None
    rom = {"source": "https://t.me/" + msg["post"], "posted": msg["posted"][:10],
           "name": "", "status": "", "android": "", "extra": [], "updated": "", "by": "",
           "banner": None, "downloads": [], "links": [], "support": [], "donate": [],
           "changelog_url": "", "changelog": [], "notes": [], "important": [], "credits": []}

    # title: "Name - UNOFFICIAL | Android 17"  /  "ColorOS 17 | TWNTY 4.0 | Global | PORT | Android 17"
    title = LINK.sub(r"\1", lines[0]).strip()
    parts = [p.strip() for p in title.split("|") if p.strip()]
    for p in list(parts):
        if re.match(r"^(android|a)\s*(dekstop|desktop)?\s*\d", p, re.I):
            v = re.search(r"\d+(\.\d+)?", p)
            rom["android"] = v.group(0) if v else p
            parts.remove(p)
    name = parts.pop(0) if parts else title
    m = re.match(r"^(.*?)\s+[-–]\s+(OFFICIAL|UNOFFICIAL|COMMUNITY|BETA|STABLE|TEST)\s*$", name, re.I)
    if not m:
        m = re.match(r"^(.*?)\s+(OFFICIAL|UNOFFICIAL|COMMUNITY)\s*$", name, re.I)
    if m:
        name, rom["status"] = m.group(1), m.group(2).upper()
    for p in parts:
        if p.upper() in ("OFFICIAL", "UNOFFICIAL", "PORT", "COMMUNITY", "BETA"):
            rom["status"] = rom["status"] or p.upper()
        else:
            rom["extra"].append(p)
    rom["name"] = re.sub(r"\s{2,}", " ", name).strip()

    cur = None
    for ln in lines[1:]:
        s = ln.strip()
        if not s:
            cur = None
            continue
        m = re.match(r"^updated?\s*:?\s*(.+)$", s, re.I)
        if m and not rom["updated"]:
            d = re.search(r"(\d{1,2})[/.-](\d{1,2})[/.-]'?(\d{2,4})", m.group(1))
            if d:
                y = d.group(3); y = "20" + y if len(y) == 2 else y
                rom["updated"] = f"{y}-{int(d.group(2)):02d}-{int(d.group(1)):02d}"
            else:
                rom["updated"] = m.group(1).strip()
            continue
        m = re.match(r"^by\s*:?\s+(.+)$", s, re.I)
        if m and not rom["by"]:
            rom["by"] = m.group(1).strip()
            continue
        if s.startswith("🔸") or (s[0] in "🔹▪️➤" and LINK.search(s)):
            body = s.lstrip("🔸🔹▪️➤ ").strip()
            first = body.find("[")
            prefix = re.sub(r"[\s:–-]+$", "", body[:first]).strip() if first > 0 else ""
            tail = re.sub(r"[🔸🔹👉|]", "", LINK.sub("", body[first:])).strip() if first >= 0 else ""
            for lab, href in LINK.findall(body):
                lab = lab.strip(" 🔸🔹👉")
                if not lab or href.startswith("?q="):
                    continue
                full = f"{prefix} · {lab}" if prefix and prefix.lower() not in ("download", "downloads") else lab
                kind = classify(full if prefix.lower() not in ("download", "downloads") else "download " + full)
                if kind == "changelog" and not rom["changelog_url"]:
                    rom["changelog_url"] = href
                    continue
                if kind == "link" and re.search(r"credit", full, re.I):
                    rom["links"].append([full, href]); continue
                entry = [full, href] + ([tail] if tail and kind == "donate" else [])
                {"download": rom["downloads"], "support": rom["support"], "donate": rom["donate"]}.get(kind, rom["links"]).append(entry)
            continue
        hdr = re.match(r"^([A-Za-z ]+?)(\s*\|[^:]*)?\s*:?\s*$", s)
        if hdr:
            for key, pat in SECTIONS:
                if re.fullmatch(pat, hdr.group(1).strip(), re.I):
                    cur = key
                    break
            else:
                cur = cur
            if cur and re.fullmatch(dict(SECTIONS)[cur], hdr.group(1).strip(), re.I):
                continue
        if cur:
            item = re.sub(r"^[•\-*·]\s*", "", s).strip()
            if item:
                rom[cur].append(item)
    # changelog section that only says "[Source](...)" etc is fine; links kept inline
    return rom


# ---------------------------------------------------------------- old posts + archive
def crawl(ch, a, b):
    """Semua post channel id a..b lewat t.me/s/<ch>?before= (20 post / halaman)."""
    seen, before = {}, b + 1
    while before > a:
        page = get(f"https://t.me/s/{ch}?before={before}")
        ids = [int(x) for x in re.findall(r'data-post="[^/"]+/(\d+)"', page)]
        if not ids:
            break
        for m in messages(page):
            i = int(m["post"].rsplit("/", 1)[1])
            if a <= i <= b:
                seen[i] = m
        before = min(ids)
        print(f"  .. {before}", end="\r", flush=True)
    print()
    return [seen[i] for i in sorted(seen)]


def keyname(s):
    s = re.sub(r"\.(zip|img|7z)$", "", s.lower())
    return re.sub(r"[^a-z0-9]", "", s)


def link_file(href):
    for seg in reversed(urllib.request.unquote(href).split("?")[0].split("/")):
        if re.search(r"\.(zip|img|7z)$", seg, re.I):
            return seg
    return ""


def apply_archive(rom, arc):
    """Ganti link download dengan file di arsip topik. Return jumlah yg cocok."""
    hit = 0
    for d in rom["downloads"]:
        fn = keyname(link_file(d[1]))
        f = arc.get(fn) if fn else None
        if not f and fn:  # Telegram memotong nama file panjang -> cocokkan awalan
            cand = [v for k, v in arc.items() if len(k) >= 20 and fn.startswith(k)]
            f = max(cand, key=lambda v: len(keyname(v["file"]))) if cand else None
        if f:
            d[:] = [d[0], f["url"], f["size"]]
            hit += 1
    rom["downloads"] = [d for d in rom["downloads"] if len(d) > 2] + [d for d in rom["downloads"] if len(d) == 2]
    return hit


# ---------------------------------------------------------------- main
def fetch_post(link):
    m = re.search(r"t\.me/(?:s/)?([\w]+)/(?:\d+/)?(\d+)", link)
    if not m:
        raise SystemExit(f"link tidak valid: {link}")
    ch, pid = m.group(1), m.group(2)
    page = get(f"https://t.me/{ch}/{pid}?embed=1&mode=tme")
    msgs = list(messages(page))
    if not msgs:
        print(f"  ! {link}: isi post tidak bisa dibaca (privat / protected content?)")
    return msgs


def main(argv):
    out = ROOT / "content/marble/02-cusrom/roms"
    force, links, latest, rng, arc = False, [], None, None, None
    it = iter(argv)
    for a in it:
        if a == "--out": out = (ROOT / next(it)).resolve()
        elif a == "--force": force = True
        elif a == "--latest": latest = int(next(it))
        elif a == "--range": rng = (int(next(it)), int(next(it)))
        elif a == "--archive":
            data = json.loads((ROOT / next(it)).read_text(encoding="utf-8"))
            arc = {keyname(f["file"]): f for f in data["files"]}
        else: links.append(a)
    msgs = []
    if rng:
        for ch in links:
            msgs += crawl(re.sub(r"^.*t\.me/(s/)?", "", ch).strip("/"), *rng)
    elif latest:
        for ch in links:
            ch = re.sub(r"^.*t\.me/(s/)?", "", ch).strip("/")
            page = get(f"https://t.me/s/{ch}")
            ms = [m for m in messages(page)]
            msgs += [m for m in reversed(ms)]
    else:
        for l in links:
            msgs += fetch_post(l)
    out.mkdir(parents=True, exist_ok=True)
    (out / "img").mkdir(exist_ok=True)
    done = 0
    for msg in msgs:
        if latest and done >= latest:
            break
        rom = parse(msg)
        if not rom or not (rom["downloads"] or rom["by"]):
            continue
        if arc is not None:
            hit = apply_archive(rom, arc)
            if not hit:
                continue
            rom["archived"] = True
        slug = f'{slugify(rom["name"])}-{msg["post"].rsplit("/", 1)[1]}'
        dst = out / f"{slug}.json"
        done += 1
        if dst.exists() and not force:
            print(f"  = {slug} (sudah ada, --force untuk timpa)")
            continue
        if msg["banner"]:
            try:
                (out / "img" / f"{slug}.jpg").write_bytes(get(msg["banner"], binary=True))
                rom["banner"] = f"img/{slug}.jpg"
            except Exception as e:
                print(f"  ! banner gagal: {e}")
        dst.write_text(json.dumps(rom, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  + {slug}  ({rom['name']} · A{rom['android']} · {rom['status'] or '-'} · {len(rom['downloads'])} dl)")
    print(f"OK {done} post -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    main(sys.argv[1:])
