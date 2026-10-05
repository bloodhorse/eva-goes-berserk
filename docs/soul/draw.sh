#!/bin/sh
curl -s -m 120 "$URL/completion" -H "Content-Type: application/json" -d "$(jq -n --arg p "$PROMPT" --argjson s "$1" --argjson n "${N:-60}" '{prompt:$p,n_predict:$n,temperature:1.0,top_k:0,top_p:1.0,min_p:0,repeat_penalty:1.0,seed:$s,cache_prompt:false}')" | jq -r .content > "$OUT/$1.txt"
