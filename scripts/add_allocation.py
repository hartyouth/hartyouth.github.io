#!/usr/bin/env python3
"""Add or update one row in weekly-pitch-allocations.csv for a fixture listed in upcoming-fixtures.csv."""
import csv
import os
import re
import sys

ALLOCATIONS = 'weekly-pitch-allocations.csv'
UPCOMING = 'upcoming-fixtures.csv'


def main():
    fixture = os.environ['INPUT_FIXTURE'].strip().lower()
    date = os.environ.get('INPUT_DATE', '').strip()
    venue = os.environ['INPUT_VENUE'].strip()
    kickoff = os.environ['INPUT_KICKOFF'].strip()

    m = re.fullmatch(r'(\d{1,2})[:.](\d{2})', kickoff)
    if not m or int(m[1]) > 23 or int(m[2]) > 59:
        sys.exit('Kick-off must be a time such as 09:15')
    kickoff = f'{int(m[1]):02d}:{m[2]}'

    if date:
        m = re.fullmatch(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})', date)
        if not m:
            sys.exit('Date must be dd/mm/yyyy')
        date = f'{int(m[1]):02d}/{int(m[2]):02d}/{m[3]}'

    with open(UPCOMING, newline='') as f:
        upcoming = list(csv.DictReader(f))
    matches = [r for r in upcoming
               if fixture in r['Fixture'].lower() and (not date or r['Date'] == date)]
    if len(matches) != 1:
        options = '\n'.join(f"  {r['Date']}  {r['Fixture']}" for r in upcoming) or '  (none)'
        reason = 'No fixture matched' if not matches else 'More than one fixture matched (add a date)'
        sys.exit(f'{reason}. Fixtures for the coming week:\n{options}')
    chosen = matches[0]

    with open(ALLOCATIONS, newline='') as f:
        rows = list(csv.reader(f))
    new_row = [chosen['Date'], venue, kickoff, chosen['Fixture']]
    key = (chosen['Date'], chosen['Fixture'].lower())
    for i, r in enumerate(rows[1:], start=1):
        if len(r) >= 4 and (r[0].strip(), r[3].strip().lower()) == key:
            rows[i] = new_row
            break
    else:
        rows.append(new_row)

    with open(ALLOCATIONS, 'w', newline='') as f:
        csv.writer(f, lineterminator='\n').writerows(rows)
    print('Saved:', ', '.join(new_row))


if __name__ == '__main__':
    main()
