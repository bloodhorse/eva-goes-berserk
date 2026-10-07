import glob
import os

from store import read_jsonl


def table(source):
    out = {}
    for path in sorted(glob.glob(str(source.ledger))) if source.ledger else []:
        for record in read_jsonl(path):
            for key in (record.get("slug"), os.path.splitext(os.path.basename(record.get("file") or ""))[0],
                        record.get("dir"), str(record.get("id", ""))):
                if key:
                    out.setdefault(str(key), record)
    return out


def find(found, path):
    stem = os.path.splitext(os.path.basename(path))[0]
    return found.get(stem) or found.get(path.rpartition("#")[2])


def rough(record):
    if not record:
        return False
    said = " ".join(str(record.get(k) or "") for k in ("format", "status"))
    said += " " + " ".join(str(w) for w in record.get("warnings") or [])
    return "pdf" in said.casefold()
