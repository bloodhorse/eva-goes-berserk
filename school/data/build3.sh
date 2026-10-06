#!/usr/bin/env bash
cd ~/eva-olmo/school
export HF_HOME=~/eva-olmo/hf-home
P=~/eva-olmo/.venv-train/bin/python
$P prep.py data/shelves/shelf1 --out bins/fantasy.bin --workers 12
$P prep.py data/shelves/shelf2 --out bins/scifi.bin --workers 12
$P prep.py data/wired-core --out bins/wired-core.bin --workers 12
$P prep.py data/wired-bulk --out bins/wired-bulk.bin --workers 12
echo BUILD3-DONE
