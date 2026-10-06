#!/usr/bin/env bash
cd ~/tower/forge/eva-goes-berserk/school
B=ubuntu@10.4.65.34; M=bek@100.69.218.90
S="ssh -o BatchMode=yes -o ConnectTimeout=8"
log=night/archive.log
echo "$(date -u +%FT%TZ) start" >> $log
mkdir -p models/box
rsync -a --quiet -e "$S" --include='*/' --include='*.bin' --include='*.json' --exclude='*' "$B:eva-olmo/school/bins/" models/box/bins/ && echo "$(date -u +%FT%TZ) bins" >> $log
rsync -a --quiet -e "$S" --exclude='gutenberg/' --exclude='tmp/' --exclude='pd2in/' --exclude='*-flat/' "$B:eva-olmo/school/data/" models/box/data/ && echo "$(date -u +%FT%TZ) data" >> $log
rsync -a --quiet -e "$S" --include='*.jsonl' --include='*.json' --include='*.py' --include='*.sh' --exclude='*' "$B:eva-olmo/school/fanfic/" models/box/fanfic/ && echo "$(date -u +%FT%TZ) fanfic" >> $log
rsync -a --quiet -e "$S" --exclude='__pycache__/' --exclude='night/*/status.new' ./ "$M:/srv/music/school-archive/" && echo "$(date -u +%FT%TZ) mirrored to the mini" >> $log
$S $M 'du -sh /srv/music/school-archive; df -h /srv/music | tail -1' </dev/null >> $log 2>&1
echo "$(date -u +%FT%TZ) ARCHIVE-DONE" >> $log
