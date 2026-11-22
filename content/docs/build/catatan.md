---
sidebar_position: 1
description: Cara menulis halaman di Meng Pedia tanpa Docusaurus.
---

# Catatan saya

Web ini sekarang dibangun pakai `build.py` (Python murni, tanpa Node / npm). Semua halaman ditulis di folder `content/` sebagai file Markdown biasa.

## Build & preview

```
python3 build.py          # hasil ke folder build/
python3 build.py --serve  # preview di http://localhost:8000/mengpoi/
```

Setiap push ke `main`, GitHub Actions otomatis build dan deploy ke GitHub Pages.

## Struktur

```
content/
  docs/                 -> /docs/...
  marble/               -> /marble/...
    01-recovery/        -> /marble/recovery/
      _category_.json   -> judul & deskripsi grup
      01-download.md    -> /marble/recovery/download
  devices.json          -> data kartu device
site.json               -> judul, menu, beranda, footer
static/                 -> disalin apa adanya (favicon, gambar)
```

Angka di depan nama file/folder (`01-`) hanya untuk urutan dan tidak ikut di URL.

## Tombol

```
[Solid](https://contoh.com){.btn}
[Tonal](https://contoh.com){.btn-tonal}
[Outline](https://contoh.com){.btn-outline}
```

[Solid](#tombol){.btn}
[Tonal](#tombol){.btn-tonal}
[Outline](#tombol){.btn-outline}

Link yang diawali `/` otomatis ditambah base `/mengpoi`, jadi cukup tulis `/marble/recovery/download`.

## Kotak info

```
:::tip Judul
Isi kotak.
:::
```

:::tip Tip
Jenis lain: `note`, `info`, `warning`, `danger`.
:::

:::warning Perhatian
Contoh kotak warning.
:::

## Kartu device

```
{{device note12turbo}}
```

Datanya diambil dari `content/devices.json`.

## Post ROM dari Telegram

```
python3 tools/tgrom.py https://t.me/PocoF5IDUpdates/4444   # satu / beberapa link
python3 tools/tgrom.py --latest 10 PocoF5IDUpdates          # N post terbaru channel
```

Hasilnya `content/marble/02-cusrom/roms/<nama>-<id>.json` + banner di `roms/img/`. File JSON boleh diedit manual (nama, notes, link, dll). Tambah `--force` untuk menimpa yang sudah ada.
