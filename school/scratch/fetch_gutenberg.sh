#!/usr/bin/env bash
cd ~/eva-olmo/school
mkdir -p gutenberg/raw
IDS="1342 84 11 1661 2701 98 1952 174 345 76 1080 5200 2542 844 219 43 1400 46 120 768 158 161 105 121 141 145 1260 35 36 5230 159 2148 1184 135 2600 996 1257 829 23 1232 730 766 580 1023 967 786 883 963 821 1399 3207 2554 28054 600 2638 4363 2591 74 55 113 514 408 2814 1497 205 16 1727 6130 3600 2160 215 910 1250 2852 863 61 4217 3825 25344 2097 1998 27827 10676 6593"
for id in $IDS; do
  f=gutenberg/raw/pg$id.txt
  [ -s "$f" ] && continue
  curl -s -L --max-time 60 -o "$f" "https://www.gutenberg.org/cache/epub/$id/pg$id.txt"
  sleep 1
done
for f in gutenberg/raw/*.txt; do
  awk 'BEGIN{p=0} /^\*\*\* *START OF/{p=1; next} /^\*\*\* *END OF/{p=0} p' "$f" | tr -d '\r' > "gutenberg/$(basename "$f")"
  [ -s "gutenberg/$(basename "$f")" ] || rm -f "gutenberg/$(basename "$f")"
done
head -c 3000000 gutenberg/pg1342.txt > gutenberg/sample.txt
cat gutenberg/pg2701.txt | head -c 3000000 >> gutenberg/sample.txt
du -sh gutenberg/raw; ls gutenberg/*.txt | wc -l; cat gutenberg/pg*.txt | wc -c
echo FETCH-DONE
