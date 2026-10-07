#!/bin/sh
cd "$(dirname "$0")"
while kill -0 "$1" 2>/dev/null; do sleep 20; done
uv run --python 3.12 python scifiction/fetch.py classics >> scifiction/fetch.log 2>&1
date > chain.done
