"""Land a list of dosed pages into the stream: each page is landed, read and told before the
next lands (the reader and the sleeper take only the newest page they have not seen), then the
painter works through the backlog once and the mirror is pushed once.

    uv run --python 3.12 land_batch.py <list file>

One landing per line, `<page file> <vector> <dose> <rng> <tokens> <seed id>`; blank and `#`
lines ignored. LAND_UNFLAG applies to every line.
"""
import sys
import land

rows = [l.split() for l in open(sys.argv[1], encoding="utf-8")
        if l.strip() and not l.lstrip().startswith("#")]
for row in rows:
    land.land(*row)
    land.voices("reader", "sleeper")
if rows:
    land.voices("painter", "mirror")
print(f"land_batch · landed {len(rows)}", file=sys.stderr, flush=True)
