#!/usr/bin/env bash
set -u
cd ~/eva-olmo/school/fanfic
job=$1
par=${2:-6}
list=${3:-shards.txt}
py=~/eva-olmo/.venv-train/bin/python
echo $$ > "$job.pid"
nice -n 10 xargs -a "$list" -n ${4:-8} -P "$par" "$py" "$job.py"
echo "exit $?"
rm -f "$job.pid"
