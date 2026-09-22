# mirror — eva.x while the mac is off

The loom and llama live on the mac, so a sleeping mac used to mean a 502 at `eva.x`. The
mirror keeps the shelf readable **and harvestable** from the phone at any hour — reading and
marks (★ keep, ● good), nothing else — without ever becoming a second writer of record. It is the first stone of moving the loom to the mini: the service, the caddy block and
the read-only switch all stay when the loom itself moves; only who writes changes.

- **The mac pushes.** `push.sh`, every 60s under launchd `com.bekh.eva-mirror`, **and the moment
  anything lands**: every writer of the dream stream ends by kickstarting this job
  (`eva/stream/push.py`), so a passage, a note, a story, a plate or a name is on the mini in a
  second instead of in up to a minute. The minute stays because it is the other direction —
  marks made on the mirror come home on it, and a kick that arrives mid-push is dropped by
  launchd and carried by the next tick. First it takes
  the mirror's mark journal (`~/eva-marks.jsonl` on the mini, moved aside to `.taking`) and
  replays every line through the mac loom's own `/api/mark` — so a keep builds its artifact on
  the mac like any keep — and clears it only when all landed (400/404 = that room or branch is
  gone, dropped; anything else = stop, push nothing, retry next minute). Then rsync of
  `eva/server`, `eva/front` and `shelf/` to `bek@miniarch:~/eva-mirror/` (`--delete`, no
  `.trash`, no berserk heartbeat/state), then `touch ~/eva-mirror/.synced`. When `loom.py`
  changed, it restarts the mirror too. Log: `/tmp/eva-mirror.log`, one line only when something
  changed.
- **The mini serves read-only.** `eva-mirror.service` (system unit, user bek): the same
  `loom.py` on `127.0.0.1:8083` with `LOOM_READONLY=1` — every POST is a 403 except
  `/api/mark` and `/api/keep`, which write the mirror's copy of the room (so the page shows the
  mark) and append a line to `LOOM_MARKS`; no artifact is built there. `/api/health` says
  `"readonly": true` and `"synced"` (the stamp's mtime).
- **Caddy picks.** The `e.x, eva.x` block in `~/tower/forge/mini/minidns/etc/caddy/Caddyfile`:
  `lb_policy first` over the mac (`100.91.166.121:8082`) then the mirror, active health checks
  every 5s. Mac answers → mac. Mac doesn't → mirror within ~5s.
- **The mirror pushes too, to whoever is reading it.** `GET /api/stream/events` is a held
  connection that says which rooms changed (`loom.py`); it is a GET, so the read-only switch
  does not touch it, and `dreamshit.x` reads the stream through it from here.
- **The page follows.** It polls `/api/health` every 5s. Read-only: the composer, edit/spin,
  the menu's write buttons, the sampler, continue and fan again disappear; the marks stay and go
  out one at a time through `/api/mark` instead of a whole-room save; tapping a card doesn't
  pick; a line at the bottom says marks reach the mac when it's back and when the copy synced. Flipping back to the mac reloads
  the page, because what it holds is the mirror's copy.

Tested 2026-09-17 by stopping the mac's loom: `eva.x` answered read-only, a room save 403, a
star through `eva.x` landed in the mirror and its journal, and with the loom back one push
replayed it onto the mac's room, built the artifact and emptied the journal. **Not tested: the mac actually asleep**,
where a dial into tailscale can hang instead of being refused — `dial_timeout 3s` and the 5s
health check are what cover it. First look from the phone with the mac lid shut settles it.

## Runbook

Verdicts, from the mac:

```bash
bash ~/tower/forge/eva-goes-berserk/eva/mirror/check.sh
```

Marks still waiting on the mini (empty = all home):

```bash
ssh bek@miniarch 'cat eva-marks.jsonl eva-marks.jsonl.taking 2>/dev/null'
```

Push now instead of waiting a minute; restart the mirror:

```bash
launchctl kickstart -k gui/$(id -u)/com.bekh.eva-mirror
ssh bek@miniarch 'sudo systemctl restart eva-mirror; journalctl -u eva-mirror -n 20 --no-pager'
```

A changed `eva-mirror.service`:

```bash
scp ~/tower/forge/eva-goes-berserk/eva/mirror/eva-mirror.service bek@miniarch:/tmp/ && \
  ssh bek@miniarch 'sudo mv /tmp/eva-mirror.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl restart eva-mirror'
```

**Rollback, whole thing** — caddy back to the mac alone (the pre-mirror file is kept on the
mini), stop both halves:

```bash
ssh bek@miniarch 'sudo cp /etc/caddy/Caddyfile.bak-eva-mirror /etc/caddy/Caddyfile && sudo systemctl reload caddy && sudo systemctl disable --now eva-mirror'
launchctl bootout gui/$(id -u)/com.bekh.eva-mirror
```

(`Caddyfile.bak-eva-mirror` predates only this block; if caddy has had other edits since, put
the eva block back to a bare `reverse_proxy 100.91.166.121:8082` in the minidns repo and ship
it the minidns way instead.)
