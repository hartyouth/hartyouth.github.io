#!/usr/bin/env python3
"""Fetch Hart Youth home fixtures for a week from the FA Full-Time feeds into upcoming-fixtures.csv."""
import argparse
import csv
import datetime as dt
import re
import sys
import urllib.request
from html.parser import HTMLParser

# Same report codes the website's results page uses.
FEEDS = ['363942307', '297000377']
FEED_URL = 'https://fulltime.thefa.com/js/cs1.html?cs={code}&random={rand}'
OUT = 'upcoming-fixtures.csv'
DAY_RE = re.compile(r'^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2}\s+\w{3}\s+\d{4})(?:\s+(\d{1,2}:\d{2}))?$', re.I)


class RowParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self._row, self._cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self._row = []
        elif tag in ('td', 'th') and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self._cell is not None:
            self._row.append(' '.join(''.join(self._cell).split()))
            self._cell = None
        elif tag == 'tr' and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def fetch(code):
    url = FEED_URL.format(code=code, rand=int(dt.datetime.now().timestamp()))
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
        'Referer': 'https://www.hyfc.uk/results.html',
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        js = resp.read().decode('utf-8', 'replace')
    m = re.search(r"innerHTML\s*=\s*'(.*)'\s*;?\s*$", js, re.S)
    if not m:
        raise RuntimeError(f'Unexpected response for feed {code}')
    return m.group(1).replace("\\'", "'").replace('\\/', '/').replace('\\"', '"')


def team_name(cell):
    m = re.match(r'Hart Youth\s+U(\d+)[A-Za-z]?\s*(.*)$', cell, re.I)
    if not m:
        return None
    return f'U{int(m.group(1))} {m.group(2)}'.strip()


def home_fixtures(html, start, end):
    parser = RowParser()
    parser.feed(html)
    day, kickoff, postponed = None, '', False
    for row in parser.rows:
        if len(row) == 1:
            m = DAY_RE.match(row[0])
            if m:
                day = dt.datetime.strptime(m.group(1), '%d %b %Y').date()
                kickoff = m.group(2) or ''
                postponed = False
            elif row[0].lower() == 'postponed':
                postponed = True
            continue
        if len(row) < 5 or day is None:
            continue
        was_postponed, postponed = postponed, False
        _, home, _, away, venue = row[:5]
        team = team_name(home)
        if was_postponed or not team or not start <= day <= end:
            continue
        yield {
            'Date': day.strftime('%d/%m/%Y'),
            'Fixture': team,
            'Opponent': away,
            'FA Kick-off': '' if kickoff == '00:00' else kickoff,
            'FA Venue': venue,
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--start', help='Monday of the week, dd/mm/yyyy (default: next Monday)')
    args = ap.parse_args()

    if args.start:
        start = dt.datetime.strptime(args.start, '%d/%m/%Y').date()
    else:
        today = dt.date.today()
        start = today + dt.timedelta(days=7 - today.weekday())
    end = start + dt.timedelta(days=6)

    rows = []
    for code in FEEDS:
        rows.extend(home_fixtures(fetch(code), start, end))
    rows.sort(key=lambda r: (dt.datetime.strptime(r['Date'], '%d/%m/%Y'), r['Fixture']))

    with open(OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['Date', 'Fixture', 'Opponent', 'FA Kick-off', 'FA Venue'], lineterminator='\n')
        w.writeheader()
        w.writerows(rows)

    print(f'{len(rows)} home fixtures for {start:%d/%m/%Y} to {end:%d/%m/%Y}')
    for r in rows:
        print(f"{r['Date']}  {r['Fixture']:<24} v {r['Opponent']}  ({r['FA Venue']})")
    if not rows:
        sys.exit('No fixtures found. The FA Full-Time feed may not have published them yet.')


if __name__ == '__main__':
    main()
