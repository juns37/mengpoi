# Meng Pedia

Catatan oprek Android — https://juns37.github.io/mengpoi/

Static site tanpa framework: `build.py` (Python 3.8+, tanpa dependency) mengubah Markdown di `content/` jadi HTML bergaya **Material 3 Expressive**.

```bash
python3 build.py           # build ke ./build
python3 build.py --serve   # preview http://localhost:8000/mengpoi/
```

Push ke `main` → GitHub Actions build & deploy otomatis ke Pages.

| Path | Isi |
|---|---|
| `content/<section>/` | halaman Markdown (`01-nama.md` → `/section/nama`) |
| `content/**/_category_.json` | label + deskripsi grup |
| `content/devices.json` | data kartu `{{device id}}` |
| `site.json` | judul, menu section, beranda, footer |
| `static/` | disalin apa adanya ke root situs |
| `theme/` | `style.css` (token M3) + `app.js` |

Sintaks tambahan: tombol `[Teks](url){.btn}` / `{.btn-tonal}` / `{.btn-outline}`, kotak `:::tip Judul … :::` (`note` `info` `warning` `danger`), kartu device `{{device note12turbo}}`, langkah `1️⃣ …` otomatis jadi badge. Detail di halaman *Catatan saya*.

Post ROM: `python3 tools/tgrom.py <link t.me>` atau `--latest 10 PocoF5IDUpdates` → `content/marble/02-cusrom/roms/*.json` + banner.
