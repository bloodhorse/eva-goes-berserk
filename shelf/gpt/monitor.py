#!/usr/bin/env python3
"""Read-only collector monitor: probe time, worker heartbeat, durable progress."""
import argparse
import datetime as dt
import json
from pathlib import Path
import sqlite3
import time

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
p.add_argument("--watch", type=float, default=0, help="poll interval in seconds; 0 prints once")
p.add_argument("--until-finished", action="store_true", help="stop watching after the collector marks its run finished")
args = p.parse_args()

def age(value, now):
    return round((now - dt.datetime.fromisoformat(value)).total_seconds(), 1) if value else None

while True:
    now = dt.datetime.now(dt.timezone.utc)
    output = {"probe_at":now.isoformat()}
    hb_path = args.root / "heartbeat.json"
    if hb_path.exists():
        hb = json.loads(hb_path.read_text())
        output.update(pid=hb["pid"], heartbeat_age_seconds=age(hb["heartbeat_at"],now), finished=hb["finished"])
        output["workers"] = {name: {"phase":s.get("phase"), "loop_age_seconds":age(s.get("loop_at"),now), "progress_age_seconds":age(s.get("last_completed_at"),now), "current_url":s.get("current_url")} for name,s in hb.get("sources",{}).items()}
    dbpath = args.root / "manifest.sqlite3"
    if dbpath.exists():
        db = sqlite3.connect(dbpath.resolve().as_uri() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        output["counts"] = [dict(r) for r in db.execute("SELECT source,kind,status,count(*) AS count,coalesce(sum(words),0) AS words FROM jobs GROUP BY source,kind,status ORDER BY source,kind,status")]
        output["last_completion"] = dict(db.execute("SELECT at,source,event,detail FROM events WHERE event IN ('story','index') ORDER BY id DESC LIMIT 1").fetchone() or {})
        db.close()
    print(json.dumps(output,ensure_ascii=False),flush=True)
    if args.watch <= 0 or (args.until_finished and output.get("finished")):
        break
    time.sleep(args.watch)
