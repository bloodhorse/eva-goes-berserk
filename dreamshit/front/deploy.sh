#!/bin/sh
# push the front to the mini → https://dreamshit.x (and d.x)
# caddy serves these files from /srv/dreamshit and forwards /api/* and the plates to eva itself,
# so only the page goes up — serve.py and eva-root.crt are for running it locally.
set -e
cd "$(dirname "$0")"
ssh bek@miniarch 'test -d /srv/dreamshit || (sudo mkdir -p /srv/dreamshit && sudo chown bek:bek /srv/dreamshit)'
rsync -a --delete index.html style.css app.js looks.js fonts.js analyst.jpg bek@miniarch:/srv/dreamshit/
curl -s -o /dev/null -w 'dreamshit.x %{http_code}\n' https://dreamshit.x/
