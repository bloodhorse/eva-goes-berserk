#!/bin/zsh
cd "${0:A:h}"
UA="Mozilla/5.0 (pd2 corpus; one request at a time)"
mkdir -p raw/pgau/txt raw/pgau/html
fails=0
while IFS=$'\t' read -r shelf author title base num; do
  id=${base:t}
  [[ -s raw/pgau/txt/$id.txt || -s raw/pgau/html/${id}h.html ]] && continue
  if curl -sS -f -L --max-time 120 -A "$UA" -o raw/pgau/txt/$id.txt.part "$base.txt" 2>/dev/null; then
    mv raw/pgau/txt/$id.txt.part raw/pgau/txt/$id.txt; fails=0; echo "ok txt $id $title"
  else
    rm -f raw/pgau/txt/$id.txt.part
    sleep 2
    if curl -sS -f -L --max-time 120 -A "$UA" -o raw/pgau/html/${id}h.html.part "${base}h.html"; then
      mv raw/pgau/html/${id}h.html.part raw/pgau/html/${id}h.html; fails=0; echo "ok html $id $title"
    else
      rm -f raw/pgau/html/${id}h.html.part; fails=$((fails+1)); echo "FAIL $id $title"
      (( fails >= 3 )) && { echo STOP; exit 1; }
    fi
  fi
  sleep 2.5
done < "$1"
echo FETCH-DONE
