#!/bin/zsh
cd "${0:A:h}"
JAR=$(mktemp)
UA="eva-shelf/1.0 (private corpus; one request at a time)"
SHOW=raw/show
TXT=raw/txt
mkdir -p $SHOW $TXT
SKIP=${SKIP:-'non-fiction|nonfiction|poetry|poems|essay|biography|autobiography|memoir|drama|play|juvenile|children|travel'}
fails=0
done_n=0

tags_of() { sed -n "s/.*Tags:<\/td><td[^>]*>\(.*\)/\1/p" "$1" | sed 's/<\/td>.*//' | grep -oE 'tags=[^"]+' | sed 's/tags=//' | tr '\n' ',' }

beat() { echo "$(date +%s) $done_n" > heartbeat }

get_show() {
  curl -sS -f -L --max-time 60 -c $JAR -b $JAR -A "$UA" -o "$SHOW/$1.html" "https://www.fadedpage.com/showbook.php?pid=$1"
}

tail -n +2 "$1" | while IFS=$'\t' read -r pid author title rest; do
  [[ -z "$pid" ]] && continue
  done_n=$((done_n+1)); beat
  [[ -s "$TXT/$pid.txt" || -s "$TXT/$pid.html.gz" ]] && continue
  get_show $pid || { fails=$((fails+1)); echo "FAIL show $pid"; (( fails >= 3 )) && { echo STOP; exit 1; }; sleep 3; continue; }
  sleep 1.5
  tags=$(tags_of "$SHOW/$pid.html")
  if echo "$tags" | grep -qiE "$SKIP"; then
    echo "skip $pid [$tags] $author | $title"
    continue
  fi
  ext=txt
  grep -q "file=$pid.txt'" "$SHOW/$pid.html" || ext=html
  out="$TXT/$pid.$ext"
  if curl -sS -f -L --max-time 120 -c $JAR -b $JAR -e "https://www.fadedpage.com/showbook.php?pid=$pid" -A "$UA" -o "$out.part" "https://www.fadedpage.com/link.php?file=$pid.$ext" && ! grep -q 'Book Details' "$out.part"; then
    mv "$out.part" "$out"; fails=0
    [[ $ext == html ]] && gzip -f "$out"
    echo "ok $pid.$ext [$tags] $author | $title"
  else
    rm -f "$out.part"; fails=$((fails+1)); echo "FAIL file $pid.$ext"
    (( fails >= 3 )) && { echo "STOP"; exit 1; }
  fi
  sleep 2.5
done
beat
rm -f $JAR
echo FETCH-DONE
