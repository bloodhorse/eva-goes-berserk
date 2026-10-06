#!/bin/zsh
cd "${0:A:h}"
JAR=$(mktemp)
UA="Mozilla/5.0 (pd2 corpus; one request at a time)"
SHOW=raw/fadedpage/show
TXT=raw/fadedpage/txt
mkdir -p $SHOW $TXT
WANT='science fiction|fantasy|horror|occult|gothic|supernatural|ghost|weird|future world|time travel|dystopia|robots|space|utopia|lost race|mytholog|legend|saga|vampire|magic|apocalyp|alien|immortal'
SKIP='western|non-fiction|Tarzan|Doc Savage|juvenile|essay|biography|poetry'
fails=0

tags_of() { sed -n "s/.*Tags:<\/td><td[^>]*>\(.*\)/\1/p" "$1" | sed 's/<\/td>.*//' | grep -oE 'tags=[^"]+' | sed 's/tags=//' | tr '\n' ',' }

get_show() {
  curl -sS -f -L --max-time 60 -c $JAR -b $JAR -A "$UA" -o "$SHOW/$1.html" "https://www.fadedpage.com/showbook.php?pid=$1"
}

while IFS=$'\t' read -r mode pid rest; do
  [[ -z "$pid" ]] && continue
  [[ -s "$TXT/$pid.txt" || -s "$TXT/$pid.html" ]] && continue
  fresh=0
  if [[ ! -s "$SHOW/$pid.html" ]]; then
    get_show $pid || { fails=$((fails+1)); echo "FAIL show $pid"; (( fails >= 3 )) && exit 1; sleep 3; continue; }
    fresh=1
    sleep 1.5
  fi
  tags=$(tags_of "$SHOW/$pid.html")
  if [[ $mode == T ]]; then
    if ! echo "$tags" | grep -qiE "$WANT" || echo "$tags" | grep -qiE "$SKIP"; then
      echo "skip $pid [$tags] $rest"
      (( fresh )) && sleep 1
      continue
    fi
  fi
  if (( ! fresh )); then
    get_show $pid || { fails=$((fails+1)); echo "FAIL show $pid"; (( fails >= 3 )) && exit 1; sleep 3; continue; }
    sleep 1.5
  fi
  ext=txt
  grep -q "file=$pid.txt'" "$SHOW/$pid.html" || ext=html
  out="$TXT/$pid.$ext"
  if curl -sS -f -L --max-time 120 -c $JAR -b $JAR -e "https://www.fadedpage.com/showbook.php?pid=$pid" -A "$UA" -o "$out.part" "https://www.fadedpage.com/link.php?file=$pid.$ext" && ! grep -q 'Book Details' "$out.part"; then
    mv "$out.part" "$out"; fails=0
    echo "ok $pid.$ext [$tags] $rest"
  else
    rm -f "$out.part"; fails=$((fails+1)); echo "FAIL file $pid.$ext"
    (( fails >= 3 )) && { echo "STOP"; exit 1; }
  fi
  sleep 2.5
done < "$1"
rm -f $JAR
echo FETCH-DONE
