#!/usr/bin/env python3
"""Arsip file ROM dari satu topik forum grup Telegram publik -> archive JSON.

  python3 tools/tgtopic.py https://t.me/mengpoi/32904            # scan semua sampai pesan terbaru
  python3 tools/tgtopic.py https://t.me/mengpoi/32904 --from 39000 # lanjut dari id tertentu
  opsi: --out content/marble/02-cusrom/_archive.json

Telegram web tidak punya daftar per topik, jadi semua pesan sesudah id topik
di-scan lewat embed, lalu diambil yang reply ke topik tsb & berisi file.
Hasil digabung (merge) dengan file yang sudah ada, berdasarkan id pesan.
"""
import html, json, re, sys, time, urllib.request
import netcache  # noqa: F401
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0"}


def fetch(ch, i, tries=8):
    """None = gagal jaringan (dicatat & diulang), "" = tidak ada."""
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(f"https://t.me/{ch}/{i}?embed=1&mode=tme", headers=UA), timeout=25) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(min(2 ** n, 30))
    return None


def exists(ch, i):
    s = fetch(ch, i)
    while s is None:
        s = fetch(ch, i)
    return "Post not found" not in s


def last_id(ch, lo):
    """Cari id pesan terakhir (toleran terhadap id yang dihapus)."""
    alive = lambda m: any(exists(ch, m + d) for d in range(6))
    hi = lo + 1000
    while alive(hi):
        lo, hi = hi, hi * 2 - lo
    while hi - lo > 6:
        m = (lo + hi) // 2
        lo, hi = (m, hi) if alive(m) else (lo, m)
    return hi + 6


def parse_file(name, text):
    stem = re.sub(r"\.(zip|img|7z|tgz)$", "", name, flags=re.I)
    tok = [t for t in re.split(r"[-_ ]+", stem) if t]
    low = [t.lower() for t in tok]
    tags = re.findall(r"#(\w+)", text)
    a = next((t for t in tags if re.fullmatch(r"A\d{2}", t, re.I)), "")
    status = next((t.upper() for t in tok if t.lower() in ("official", "unofficial", "community")), "")
    variant = next((t.title().replace("Gapps", "GApps").replace("Gms", "GMS") for t in tok
                    if t.lower() in ("gapps", "vanilla", "gms", "core", "full", "lite", "pifgapps", "mgapps")), "")
    date = ""
    for t in tok:
        if re.fullmatch(r"20\d{6}", t):
            date = f"{t[:4]}-{t[4:6]}-{t[6:]}"
            break
    if not date:
        m = re.search(r"(20\d{2})(\d{2})(\d{2})", stem)
        if m and 1 <= int(m.group(2)) <= 12:
            date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    name_t, ver = [], ""
    for t, l in zip(tok, low):
        if l in ("marble", "marblein", "official", "unofficial", "community") or re.fullmatch(r"20\d{6,}", t):
            break
        if re.fullmatch(r"v?\d+(\.\d+)*[a-z]?", t, re.I):
            if not ver:
                ver = t
            continue
        if ver:  # codename after version (Andromeda, Uli...) -> stop
            break
        name_t.append(t)
    rom = " ".join(name_t) or tok[0]
    if not a and ver:
        major = int(re.match(r"v?(\d+)", ver).group(1))
        if 11 <= major <= 17 and rom.lower() not in ("mistos", "axion", "crdroid", "evolution", "pixelos"):
            a = f"A{major}"
    return {"rom": rom, "version": ver, "android": a.upper(), "status": status, "variant": variant, "date": date,
            "tags": [t for t in tags if not re.fullmatch(r"A\d{2}", t, re.I)]}


def main(argv):
    if not argv:
        print(__doc__); sys.exit(1)
    m = re.search(r"t\.me/(\w+)/(\d+)", argv[0])
    ch, topic = m.group(1), m.group(2)
    out = ROOT / "content/marble/02-cusrom/_archive.json"
    start = int(topic) + 1
    if "--out" in argv: out = (ROOT / argv[argv.index("--out") + 1]).resolve()
    if "--from" in argv: start = int(argv[argv.index("--from") + 1])
    data = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"source": f"https://t.me/{ch}/{topic}", "files": []}
    have = {f["id"] for f in data["files"]}
    end = int(argv[argv.index("--to") + 1]) if "--to" in argv else last_id(ch, start)
    print(f"scan {ch}/{start}..{end} (topik {topic})", flush=True)
    found = 0
    todo = sorted(set(range(start, end + 1)) | set(data.get("failed", [])))

    def handle(i, s):
        nonlocal found
        rep = re.search(r'tgme_widget_message_reply[^>]*href="https://t\.me/[^/]+/(\d+)"', s)
        if not rep or rep.group(1) != topic:
            return
        docs = [html.unescape(x).strip() for x in re.findall(r"tgme_widget_message_document_title[^>]*>([^<]+)", s)]
        sizes = re.findall(r"tgme_widget_message_document_extra[^>]*>([^<]+)", s)
        t = re.search(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', s, re.S)
        text = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<br\s*/?>", "\n", t.group(1)))).strip() if t else ""
        d = re.search(r'<time[^>]*datetime="([^"]+)"', s)
        for n, (fn, sz) in enumerate(zip(docs, sizes)):
            fid = i if n == 0 else f"{i}.{n}"
            if fid in have or not re.search(r"\.(zip|img|7z)$", fn, re.I):
                continue
            note = re.sub(r"\s*#\w+", "", text).strip()
            data["files"].append(dict(id=fid, url=f"https://t.me/{ch}/{topic}/{i}", file=fn, size=sz.strip(),
                                      posted=d.group(1)[:10] if d else "", note=note, **parse_file(fn, text)))
            have.add(fid)
            found += 1
            print(f"  + {i} {fn} ({sz.strip()})", flush=True)

    def save():
        data["files"].sort(key=lambda f: (f["rom"].lower(), f["date"]))
        out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    failed = []
    with ThreadPoolExecutor(8) as ex:
        for k, (i, s) in enumerate(ex.map(lambda i: (i, fetch(ch, i)), todo)):
            if s is None:
                failed.append(i)
            elif "Post not found" not in s:
                handle(i, s)
            if k % 250 == 249:
                data["failed"] = failed + [x for x in todo[k + 1:]]
                save()
                print(f"  .. {i}  file:{len(data['files'])}  gagal:{len(failed)}", flush=True)
    data["failed"] = failed
    data["scanned_to"] = max(end, data.get("scanned_to", 0))
    save()
    print(f"OK +{found} file, total {len(data['files'])}, gagal {len(failed)} (jalankan ulang utk retry) -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
