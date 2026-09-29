"""
Download the raw Stats NZ sources into data/raw/ and record provenance in
data/raw/MANIFEST.csv (file, URL, SHA-256, UTC download date). Files are
saved exactly as served; nothing is edited.

    python data/fetch_sources.py consents july-2026   # Building consents issued: July 2026
    python data/fetch_sources.py datainfo-occupancy     # DataInfo+ page cited for N1/F1

Large archives are git-ignored; MANIFEST.csv and the derived inputs built from
them (data/derived/) are committed, so a re-download can be checked against
the recorded SHA-256.
"""
import csv
import datetime as dt
import hashlib
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
MANIFEST = os.path.join(RAW, 'MANIFEST.csv')
CONSENTS = ('https://www.stats.govt.nz/assets/Uploads/Building-consents-issued/'
            'Building-consents-issued-{Month}-{year}/Download-data/building-consents-issued-{month}-{year}.{ext}')
SOURCES = {
    'datainfo-occupancy': [('datainfo_dwelling_occupancy_status.html',
                            'https://datainfoplus.stats.govt.nz/Item/nz.govt.stats/9b4c0bf9-2b8c-4b54-aa6d-fa51e07bd4d5')],
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def fetch(name, url):
    os.makedirs(RAW, exist_ok=True)
    path = os.path.join(RAW, name)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (research data download)'})
    with urllib.request.urlopen(req, timeout=300) as r, open(path, 'wb') as f:
        f.write(r.read())
    row = dict(file=name, url=url, sha256=sha256(path),
               downloaded_utc=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d'))
    rows = []
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            rows = [r for r in csv.DictReader(f) if r['file'] != name]
    rows.append(row)
    with open(MANIFEST, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r['file']))
    print(f"{name}: {os.path.getsize(path):,} bytes, sha256 {row['sha256'][:16]}...")


def main():
    what = sys.argv[1]
    if what == 'consents':
        month, year = sys.argv[2].split('-')
        for ext in ('xlsx', 'zip'):
            url = CONSENTS.format(Month=month.capitalize(), month=month.lower(), year=year, ext=ext)
            fetch(f'building-consents-issued-{month.lower()}-{year}.{ext}', url)
    else:
        for name, url in SOURCES[what]:
            fetch(name, url)


if __name__ == '__main__':
    main()
