#!/usr/bin/env python3
"""Resumable magazine shelf collector. No corpus validation or deduplication.

Run with: uv run --no-project --python .venv/bin/python python collect.py --help
All persistent output is relative to this file unless --root is supplied.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sqlite3
import subprocess
import threading
import time
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup, Comment, NavigableString, Tag

VERSION = "2"
SITES = {
    "clarkesworld": ("https://clarkesworldmagazine.com", ["/category/text/"]),
    "lightspeed": ("https://www.lightspeedmagazine.com", ["/fiction/"]),
    "nightmare": ("https://www.nightmare-magazine.com", ["/fiction/"]),
    "uncanny": ("https://www.uncannymagazine.com", ["/type/fiction/", "/type/reprints/"]),
    "bcs": ("https://beneath-ceaseless-skies.com", [f"/issues/{y}/" for y in range(2008, dt.datetime.now().year + 1)]),
    "infinityplus": ("https://www.infinityplus.co.uk", [f"/stories/index{x}.htm" for x in ("af", "gm", "nz")]),
    "escapepod": ("https://escapepod.org", ["/"]),
    "podcastle": ("https://podcastle.org", ["/"]),
    "pseudopod": ("https://pseudopod.org", ["/"]),
    "giganotosaurus": ("https://giganotosaurus.org", ["/category/fiction/"]),
    "thedark": ("https://www.thedarkmagazine.com", ["/category/fiction/"]),
    "fireside": ("https://firesidefiction.com", ["/magazine"]),
    "fantasy": ("https://psychopomp.com", ["/fantasy/category/fiction/"]),
    "deadlands": ("https://psychopomp.com", ["/deadlands/"]),
    "apex": ("https://www.apexbookcompany.com", ["/sitemap_articles_1.xml", "/sitemap_articles_2.xml"]),
    "katalepsis": ("https://katalepsis.net", ["/table-of-contents/"]),
    "necroepilogos": ("https://necroepilogos.net", ["/table-of-contents/"]),
    "pale": ("https://palewebserial.wordpress.com", ["/table-of-contents/"]),
    "pact": ("https://pactwebserial.wordpress.com", ["/table-of-contents/"]),
    "worm": ("https://parahumans.wordpress.com", ["/table-of-contents/"]),
    "ward": ("https://www.parahumans.net", ["/table-of-contents/"]),
    "twig": ("https://twigserial.wordpress.com", ["/"]),
    "wanderinginn": ("https://wanderinginn.com", ["/table-of-contents/"]),
}
NEW_SITES = {"escapepod", "podcastle", "pseudopod", "giganotosaurus", "thedark", "fireside", "fantasy", "deadlands", "apex"}
PODCASTS = {"escapepod", "podcastle", "pseudopod"}
SERIALS = {"katalepsis", "necroepilogos", "pale", "pact", "worm", "ward", "twig", "wanderinginn"}
DEFAULT_SITES = [source for source in SITES if source != "wanderinginn"]
STOP = threading.Event()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def tag(path: Path):
    if os.uname().sysname == "Darwin":
        try:
            subprocess.run(["xattr", "-w", "com.apple.metadata:_kMDItemUserTags", "(claude)", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        except OSError:
            pass


def write(path: Path, data: bytes | str):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
    os.replace(temp, path)
    tag(path)


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False)


def normalized_url(base, href):
    p = urlsplit(urljoin(base, href))
    host = p.netloc.lower()
    if host == "www.beneath-ceaseless-skies.com":
        host = "beneath-ceaseless-skies.com"
    if host == "www.clarkesworldmagazine.com":
        host = "clarkesworldmagazine.com"
    return urlunsplit((p.scheme, host, p.path or "/", p.query, ""))


def text(node):
    return node.get_text(" ", strip=True) if node else ""


def soup_of(data):
    # BeautifulSoup/UnicodeDammit reads BOM/meta charset and legacy encodings.
    return BeautifulSoup(data, "lxml")


def same_site(source, url):
    target = urlsplit(url)
    return target.scheme in ("http", "https") and (target.hostname or "").removeprefix("www.") == urlsplit(SITES[source][0]).hostname.removeprefix("www.")


def index_entries(source, url, soup):
    """Return story metadata and linked index pages, not text excerpts as stories."""
    if source in SERIALS:
        return serial_index_entries(source, url, soup)
    if source in NEW_SITES:
        return new_index_entries(source, url, soup)
    if source == "clarkesworld":
        links = soup.select("article h2.entry-title a")
    elif source in ("lightspeed", "nightmare"):
        links = soup.select("#content h2.posttitle a")
    elif source == "uncanny":
        links = soup.select("article.type-article .article_title a")
    elif source == "bcs":
        links = soup.select(".issue-story-title a")
    else:
        links = []
        for a in soup.select("td li a[href]"):
            target = normalized_url(url, a["href"])
            path = urlsplit(target).path
            if same_site(source, target) and path.endswith((".htm", ".html")) and not re.search(r"/(?:index[^/]*|home)\.html?$", path) and "/nonfiction/" not in path and "/misc/" not in path and "/books/" not in path:
                links.append(a)
    stories = []
    for a in links:
        target = normalized_url(url, a.get("href", ""))
        if not same_site(source, target):
            continue
        if source == "bcs" and not urlsplit(target).path.startswith("/stories/"):
            continue
        item = a.find_parent("article") or a.find_parent("div", id=re.compile(r"^post-")) or a.parent.parent
        meta = {"title": text(a), "discovered_from": url}
        authors = item.select(".authorname") or item.select("a[href*='/authors/'], a[href*='/author/']")
        if source == "bcs":
            sibling = a.parent.find_next_sibling("div", class_="issue-author-name")
            authors = [sibling] if sibling else []
            # Year pages contain a full issue container; do not attach every issue author.
        meta["authors"] = list(dict.fromkeys(text(n) for n in authors if text(n)))
        meta["classes"] = item.get("class", [])
        location = item.select_one(".entry-location, .byline, .issue-title")
        if location:
            meta["issue_label"] = text(location)
        if source == "infinityplus":
            li = a.find_parent("li")
            meta["index_description"] = text(li)
            meta["is_excerpt_hint"] = bool(re.search(r"\b(extract|excerpt|sample chapters?)\b", text(li), re.I))
            cell = a.find_parent("td")
            anchor = cell.select_one("a[name]") if cell else None
            if anchor:
                parent = anchor.parent
                meta["authors"] = [text(parent)] if text(parent) else []
        stories.append((target, meta))

    indexes = []
    pagination_selector = "a[href]" if source == "bcs" else "#archive_pagination a[href], .nav-links a[href]"
    for a in soup.select(pagination_selector):
        target = normalized_url(url, a["href"])
        path = urlsplit(target).path
        if same_site(source, target) and "/page/" in path and (source != "bcs" or re.match(r"^/issues/\d{4}/page/\d+/$", path)):
            indexes.append(target)
    return stories, list(dict.fromkeys(indexes))


def new_index_entries(source, url, soup):
    stories, indexes = [], []
    if source in PODCASTS:
        for article in soup.select("article"):
            a = article.select_one("h3.entry_title a[href]")
            if a and "category-podcasts" in article.get("class", []):
                stories.append((normalized_url(url, a["href"]), {"title": text(a), "discovered_from": url}))
        indexes = [normalized_url(url, a["href"]) for a in soup.select("a[href]")
                   if re.fullmatch(r"/page/\d+/", urlsplit(normalized_url(url, a["href"])).path)]
    elif source in {"giganotosaurus", "thedark", "fantasy"}:
        if source == "giganotosaurus":
            links = [a for article in soup.select("article.category-fiction")
                     for a in article.select("a[href]")
                     if re.fullmatch(r"/\d{4}/\d{2}/\d{2}/[^/]+/", urlsplit(normalized_url(url, a["href"])).path)
                     and not re.fullmatch(r"[A-Z][a-z]+ \d+,? \d{4}", text(a))]
        elif source == "thedark":
            links = soup.select("article.category-fiction h2.posttitle a[href]")
        else:
            links = soup.select("article h2.entry-title a[href]")
        stories = [(normalized_url(url, a["href"]), {"title": text(a), "discovered_from": url}) for a in links]
        prefix = {"giganotosaurus": "/category/fiction/page/", "thedark": "/category/fiction/page/", "fantasy": "/fantasy/category/fiction/page/"}[source]
        indexes = [normalized_url(url, a["href"]) for a in soup.select("a[href]")
                   if urlsplit(normalized_url(url, a["href"])).path.startswith(prefix)]
    elif source == "fireside":
        for h in soup.select("h3"):
            a = h.select_one("a[href]")
            if a and "short story" in text(h).lower():
                stories.append((normalized_url(url, a["href"]), {"title": text(a), "discovered_from": url}))
    elif source == "deadlands":
        if urlsplit(url).path == "/deadlands/":
            indexes = [normalized_url(url, a["href"]) for a in soup.select("a[href]")
                       if re.fullmatch(r"/deadlands/issue-\d+(?:-\d+)?/", urlsplit(normalized_url(url, a["href"])).path)]
        else:
            section = None
            for node in soup.select("main.dl-toc > *"):
                if node.name in {"h2", "h3"}:
                    section = text(node).lower()
                if node.name == "p" and section == "fiction":
                    for a in node.select("a[href]"):
                        target = normalized_url(url, a["href"])
                        if urlsplit(target).path.startswith(urlsplit(url).path):
                            stories.append((target, {"title": text(a), "discovered_from": url}))
    elif source == "apex":
        stories = [(normalized_url(url, n.get_text(strip=True)), {"discovered_from": url, "discovery_kind": "publisher_sitemap"})
                   for n in soup.select("loc")
                   if "/blogs/apex-magazine/" in n.get_text(strip=True)]
    stories = [(target, meta) for target, meta in stories if same_site(source, target)]
    indexes = [target for target in indexes if same_site(source, target) and target != url]
    return list(dict((target, (target, meta)) for target, meta in stories).values()), list(dict.fromkeys(indexes))


def serial_index_entries(source, url, soup):
    if source == "twig":
        stories = [(f"{SITES[source][0]}/?cat={option['value']}",
                    {"title": text(option), "discovered_from": url, "serial": source, "category_id": option["value"]})
                   for option in soup.select("option.level-2[value]")]
        return stories, []
    container = soup.select_one(".entry-content") if source != "wanderinginn" else soup
    if container is None:
        raise ValueError("table of contents not found")
    stories = []
    for a in container.select("a[href]"):
        target = normalized_url(url, a["href"])
        if not same_site(source, target):
            continue
        path = urlsplit(target).path
        if not re.match(r"^/\d{4}/\d{2}/\d{2}/[^/]+/$", path):
            if source != "worm" or not re.match(r"^/category/stories-arcs-\d+-\d+/arc-[^/]+/[^/]+/$", path):
                continue
        label = text(a)
        if source == "wanderinginn" and ("archive" in path or "glossary" in path):
            continue
        if source == "wanderinginn" and (not label or not re.match(r"^(?:\d|interlude|epilogue|prologue)", label, re.I)):
            continue
        stories.append((target, {"title": label, "discovered_from": url, "serial": source}))
    return list(dict((target, (target, meta)) for target, meta in stories).values()), []


BLOCKS = {"p", "div", "section", "article", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "table", "tr", "pre"}


def prose(node):
    """Render paragraph boundaries without adding spaces at inline tag boundaries."""
    def visit(n):
        if isinstance(n, Comment):
            return ""
        if isinstance(n, NavigableString):
            return re.sub(r"\s+", " ", str(n))
        if not isinstance(n, Tag):
            return ""
        if n.name in {"script", "style", "noscript", "iframe", "audio", "video", "svg"}:
            return ""
        if n.name == "br":
            return "\n"
        if n.name == "hr" or set(n.get("class", [])) & {"section_break", "section-break"}:
            return "\n\n***\n\n"
        if n.name == "img":
            return ""
        if n.name == "pre":
            return "\n\n" + n.get_text() + "\n\n"
        result = "".join(visit(c) for c in n.children)
        if n.name in BLOCKS:
            return "\n\n" + result + "\n\n"
        if n.name in {"td", "th"}:
            return result + "\t"
        return result
    result = visit(node).replace("\xa0", " ")
    result = re.sub(r"[ \t]*\n[ \t]*", "\n", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip() + "\n"


def extract(source, url, data, metadata):
    if source in SERIALS:
        return serial_extract(source, url, data, metadata)
    if source in NEW_SITES:
        return new_extract(source, url, data, metadata)
    soup = soup_of(data)
    record = dict(metadata)
    record.update(source=source, url=url, extractor_version=VERSION, extracted_at=now())
    selectors = {
        "clarkesworld": (".story-text", "h1.story-title", ".authorname"),
        "lightspeed": ("#content .single_entry.entry-content", "h1.entry-title", ".postmetadata a[href*='/authors/']"),
        "nightmare": ("#content .single_entry.entry-content", "h1.entry-title", ".postmetadata a[href*='/authors/']"),
        "uncanny": ("article.type-article .entry-content", "article.type-article .entry-title", "article.type-article .byline a[href*='/authors/']"),
        "bcs": (".bcs-story-content", ".right-content .post-title", ".right-content .post-author"),
    }
    if source in selectors:
        body_sel, title_sel, author_sel = selectors[source]
        body = soup.select_one(body_sel)
        title = soup.select_one(title_sel)
        authors = [text(n) for n in soup.select(author_sel)]
        if title:
            record["title"] = (" ".join(str(n).strip() for n in title.children if isinstance(n, NavigableString)).strip() if source == "bcs" else text(title)) or record.get("title", "story")
        if authors:
            record["authors"] = list(dict.fromkeys(re.sub(r"^by\s+", "", a, flags=re.I) for a in authors))
        record["body_selector"] = body_sel
    else:
        title = soup.find("h1")
        body = title.find_parent("td") if title else None
        if body is None:
            cells = soup.find_all("td")
            # Legacy layouts often use <font>/<b> headings instead of h1.
            body = max(cells, key=lambda n: len(n.get_text()), default=None)
            record["body_selector"] = "legacy longest td (fallback)"
        else:
            record["body_selector"] = "td containing h1"
            record["title"] = text(title)
        author = soup.select_one(".author")
        if author:
            record["authors"] = [text(author)]
        record["is_excerpt_hint"] = record.get("is_excerpt_hint", False) or bool(re.search(r"\b(extract|excerpt)\b", " ".join(text(h) for h in soup.select("h1,h2")), re.I))
        expected = re.search(rb"<!--\s*(\d[\d,]*)\s+words\s*-->", data, re.I)
        if expected:
            record["declared_words"] = int(expected[1].replace(b",", b""))
        record["linked_story_pages"] = [
            {"url": normalized_url(url, a["href"]), "label": text(a)}
            for a in soup.select("a[href]")
            if same_site(source, normalized_url(url, a["href"]))
            and re.match(r"^/stories/(?!index)[^/]+\.html?$", urlsplit(normalized_url(url, a["href"])).path)
        ]
    if body is None:
        raise ValueError("story body container not found")
    canonical = soup.select_one("link[rel='canonical']")
    if canonical and canonical.get("href"):
        record["canonical_url"] = canonical["href"]
    for name in ("article:published_time", "article:modified_time"):
        m = soup.find("meta", property=name)
        if m:
            record[name.split(":")[1]] = m.get("content")
    post = body.find_parent("article") or body.find_parent("div", id=re.compile(r"^post-"))
    if post:
        record["classes"] = post.get("class", record.get("classes", []))
    notices = body.select(".author-copyright, .copyright, .editorial")
    record["publication_notes"] = list(dict.fromkeys(text(n) for n in notices if text(n)))
    # The raw page remains untouched; only the detached extraction is cleaned.
    fragment = BeautifulSoup(str(body), "lxml")
    for n in fragment.select("script,style,noscript,iframe,audio,video,svg,.mp3-player,.about_author,.author_bio,.author-bio,.aboutinfo,.m-a-box,.addtoany_share_save_container,.a2a_kit,.callout,.actions,.callouts_container,.callout_box,.author-copyright,.story-comment-link,.share-links,.display-recs,.return-to-issue"):
        n.decompose()
    if source in ("lightspeed", "nightmare"):
        first = fragment.select_one("p")
        if first and text(first).startswith("ANNOUNCEMENT:") and first.select_one("a[href*='kickstarter'], a[href*='lightspeedmagazine.com/ks']"):
            for neighbor in (first.find_previous_sibling(), first.find_next_sibling()):
                if neighbor and neighbor.name == "hr":
                    neighbor.decompose()
            first.decompose()
    if source == "infinityplus":
        for n in fragment.select(".editorial,.footer"):
            n.decompose()
        # Strip the opening title/subtitle/byline, retaining headings within prose.
        heading = fragment.find("h1")
        if heading:
            for sibling in list(heading.next_siblings):
                if isinstance(sibling, NavigableString) and not sibling.strip():
                    continue
                if isinstance(sibling, Tag) and sibling.name in ("h2", "br"):
                    sibling.decompose()
                    continue
                break
            heading.decompose()
    cleaned_html = str(fragment.body or fragment)
    content = prose(fragment.body or fragment)
    record["words"] = len(content.split())
    record["characters"] = len(content)
    return record, content, cleaned_html


def new_extract(source, url, data, metadata):
    soup = soup_of(data)
    record = dict(metadata)
    record.update(source=source, url=url, extractor_version=VERSION, extracted_at=now())
    selectors = {
        "giganotosaurus": ("article.category-fiction .entry_content", "meta[property='og:title']"),
        "thedark": ("article.category-fiction .entry-content", "article.category-fiction h2.entry-title"),
        "fireside": ("article.fiction .story-body", "article.fiction h1"),
        "fantasy": ("article.fantasy .entry-content", "article.fantasy h1.entry-title"),
        "deadlands": ("article.dl-story__body", "h1.dl-story__title"),
        "apex": ("article.apex-story__article .apex-story__body", "article.apex-story__article h1.apex-story__title"),
    }
    if source in PODCASTS:
        container = soup.select_one("article .entry_content")
        title = soup.select_one("article h2.post_title")
        if container is None:
            raise ValueError("episode text container not found")
        heading = next((n for n in container.find_all(recursive=False)
                        if n.name == "h3" and text(n).lower() not in {"show notes", "host commentary"}), None)
        if heading is None:
            raise ValueError("story heading not found in episode")
        fragment = BeautifulSoup("<div></div>", "lxml")
        body = fragment.div
        for sibling in heading.next_siblings:
            if isinstance(sibling, Tag) and sibling.name == "h3" and "commentary" in text(sibling).lower():
                break
            if isinstance(sibling, Tag) and sibling.name == "hr" and "full" in sibling.get("class", []):
                following = sibling.find_next_sibling()
                if not (following and following.name == "h3" and "commentary" not in text(following).lower()):
                    break
            if isinstance(sibling, Tag) and sibling.name in {"h3", "h4"} and re.match(r"^(about|notes|links|credits)", text(sibling), re.I):
                break
            if isinstance(sibling, Tag) and not (sibling.name == "h4" and text(sibling).lower().startswith("by ")):
                parsed = BeautifulSoup(str(sibling), "lxml")
                body.append(next((n for n in parsed.body.children if isinstance(n, Tag)), parsed.body))
        children = body.find_all(True, recursive=False)
        if children and children[0].name == "hr":
            children[0].decompose()
        children = body.find_all(True, recursive=False)
        if children and children[-1].name == "hr":
            children[-1].decompose()
        if title:
            record["title"] = text(title)
        record["story_heading"] = text(heading)
        author = soup.select_one("article header")
        if author:
            m = re.search(r"Author\s*:\s*(.+?)(?:Narrator\s*:|Host\s*:|$)", text(author))
            if m:
                record["authors"] = [m.group(1).strip()]
        m = re.search(r"\[\s*([\d,]+)\s+words\s*\]", text(soup.select_one("article header")))
        if m:
            record["declared_words"] = int(m.group(1).replace(",", ""))
        record["body_selector"] = "article .entry_content: story heading to host commentary"
    else:
        body_sel, title_sel = selectors[source]
        original = soup.select_one(body_sel)
        if original is None:
            raise ValueError(f"story body container not found: {body_sel}")
        fragment = BeautifulSoup(str(original), "lxml")
        body = next((n for n in fragment.body.children if isinstance(n, Tag)), fragment.body)
        title = soup.select_one(title_sel)
        if title:
            record["title"] = title.get("content", "") if title.name == "meta" else text(title)
        record["body_selector"] = body_sel
        if source == "fireside":
            byline = soup.select_one("article.fiction h2.byline")
            if byline:
                record["authors"] = [re.sub(r"^by\s+", "", text(byline), flags=re.I)]
        elif source == "thedark":
            byline = soup.select_one("article.category-fiction .byline")
            if byline:
                record["authors"] = [re.sub(r"^by\s+", "", text(byline), flags=re.I)]
        elif source == "apex":
            byline = soup.select_one("article.apex-story__article .apex-story__byline")
            if byline:
                record["authors"] = [re.sub(r"^by\s+", "", text(byline).split(" views", 1)[0], flags=re.I)]
            record["mixed_fiction_and_nonfiction_index"] = True
        if source == "giganotosaurus":
            for n in list(body.select("h3")):
                if text(n).lower().startswith("about the author"):
                    for sibling in list(n.next_siblings):
                        if isinstance(sibling, Tag):
                            sibling.decompose()
                    n.decompose()
            for n in body.select("a[href$='.epub'],a[href$='.mobi']"):
                n.decompose()
        if source in {"fireside", "fantasy", "deadlands"}:
            for n in list(body.find_all(recursive=False)):
                if (source == "fireside" and n.name in {"h4", "h5"} and
                    ("author" in text(n).lower() or text(n).startswith("©"))):
                    for sibling in list(n.next_siblings):
                        if isinstance(sibling, Tag):
                            sibling.decompose()
                    n.decompose()
                    break
                if source == "fantasy" and n.name == "div" and n == body.find_all(recursive=False)[-1]:
                    n.decompose()
                if source == "deadlands" and n.name == "div" and "wp-block-columns" in n.get("class", []):
                    n.decompose()
    for n in body.select("script,style,noscript,iframe,audio,video,svg,form,.sharedaddy,.jp-relatedposts,.author-bio,.author_bio,.wp-block-buttons,.wp-block-image,.dl-story__art"):
        n.decompose()
    content = prose(body)
    if len(content.split()) < 100:
        raise ValueError("extracted story is under 100 words")
    record["words"] = len(content.split())
    record["characters"] = len(content)
    canonical = soup.select_one("link[rel='canonical']")
    if canonical and canonical.get("href"):
        record["canonical_url"] = canonical["href"]
    return record, content, str(body)


def serial_extract(source, url, data, metadata):
    soup = soup_of(data)
    record = dict(metadata)
    record.update(source=source, url=url, extractor_version=VERSION, extracted_at=now())
    selector = "article.twi-article" if source == "wanderinginn" else ".entry-content"
    original = soup.select_one(selector)
    if original is None:
        raise ValueError(f"chapter body container not found: {selector}")
    fragment = BeautifulSoup(str(original), "lxml")
    body = next((n for n in fragment.body.children if isinstance(n, Tag)), fragment.body)
    for n in body.select("script,style,noscript,iframe,audio,video,svg,form,.sharedaddy,.jp-relatedposts,.wp-block-buttons"):
        n.decompose()
    for n in list(body.find_all(recursive=False)):
        if n.name == "p" and n.select_one("a[href]") and re.fullmatch(r"[.\s]*(?:(?:about|previous|next)\s*){1,3}(?:chapter)?[.\s]*", text(n), re.I):
            n.decompose()
    if source == "wanderinginn":
        for n in list(body.find_all(recursive=False))[-3:]:
            if n.name == "hr":
                n.decompose()
    heading = soup.select_one("h1.entry-title")
    if heading:
        record["title"] = text(heading)
    record["authors"] = ["pirateaba"] if source == "wanderinginn" else ["Wildbow"] if source in {"pale", "pact", "worm", "ward", "twig"} else []
    record["body_selector"] = selector
    content = prose(body)
    if len(content.split()) < 5:
        raise ValueError("extracted chapter is under 5 words")
    record["words"] = len(content.split())
    record["characters"] = len(content)
    canonical = soup.select_one("link[rel='canonical']")
    if canonical and canonical.get("href"):
        record["canonical_url"] = canonical["href"]
    return record, content, str(body)


class Collector:
    def __init__(self, root, delay=1.5):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.process_lock = (self.root / "collector.lock").open("a")
        try:
            fcntl.flock(self.process_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("Another collector is using this shelf; use monitor.py to inspect it.")
        self.delay = delay
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.root / "manifest.sqlite3", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
              id INTEGER PRIMARY KEY, source TEXT NOT NULL, url TEXT NOT NULL,
              kind TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
              metadata TEXT NOT NULL DEFAULT '{}', http_status INTEGER, final_url TEXT,
              raw_path TEXT, text_path TEXT, words INTEGER, error TEXT,
              attempts INTEGER NOT NULL DEFAULT 0, updated TEXT,
              UNIQUE(source,url));
            CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, at TEXT, source TEXT, job_id INTEGER, event TEXT, detail TEXT);
        """)
        self.db.commit()
        self.state = {}
        self.started = now()
        self.done = threading.Event()

    def add(self, source, url, kind, metadata=None):
        url = normalized_url(SITES[source][0], url)
        with self.lock:
            self.db.execute("INSERT INTO jobs(source,url,kind,metadata,updated) VALUES(?,?,?,?,?) ON CONFLICT(source,url) DO NOTHING", (source,url,kind,dumps(metadata or {}),now()))
            if metadata:
                old = self.db.execute("SELECT metadata FROM jobs WHERE source=? AND url=?", (source,url)).fetchone()
                merged = json.loads(old[0]) | metadata
                self.db.execute("UPDATE jobs SET metadata=? WHERE source=? AND url=?", (dumps(merged),source,url))
            self.db.commit()

    def event(self, source, job, event, detail=""):
        with self.lock:
            self.db.execute("INSERT INTO events(at,source,job_id,event,detail) VALUES(?,?,?,?,?)", (now(),source,job,event,detail))
            self.db.commit()
        print(dumps({"at":now(),"source":source,"job":job,"event":event,"detail":detail}), flush=True)

    def update(self, job_id, **fields):
        fields["updated"] = now()
        with self.lock:
            self.db.execute("UPDATE jobs SET " + ",".join(f"{k}=?" for k in fields) + " WHERE id=?", [*fields.values(),job_id])
            self.db.commit()

    def heartbeat(self):
        while not self.done.wait(5):
            self.write_heartbeat()
        self.write_heartbeat(finished=True)

    def write_heartbeat(self, finished=False):
        with self.lock:
            state = dict(self.state)
        write(self.root / "heartbeat.json", dumps({"pid":os.getpid(),"started_at":self.started,"heartbeat_at":now(),"finished":finished,"stop_requested":STOP.is_set(),"sources":state}) + "\n")

    def activity(self, source, **values):
        with self.lock:
            self.state.setdefault(source, {}).update(values, loop_at=now())

    def seed(self, sources):
        for source in sources:
            base, paths = SITES[source]
            for path in paths:
                self.add(source, base + path, "index")

    def process(self, job, client):
        source, url = job["source"], job["url"]
        self.activity(source, current_url=url, phase="fetching")
        raw_rel = job["raw_path"]
        if raw_rel and (self.root / raw_rel).exists() and job["http_status"] == 200:
            data = gzip.decompress((self.root / raw_rel).read_bytes())
            final_url = job["final_url"] or url
        else:
            if client is None:
                raise FileNotFoundError(f"No cached successful response for {url}; offline extraction cannot fetch it")
            response = None
            for attempt in range(3):
                if STOP.is_set():
                    self.update(job["id"], status="pending")
                    return
                self.update(job["id"], attempts=job["attempts"] + attempt + 1)
                try:
                    response = client.get(url)
                    if response.status_code not in (429,500,502,503,504):
                        break
                    wait = min(120, int(response.headers.get("retry-after", "0"))) if response.headers.get("retry-after", "0").isdigit() else 0
                    wait = max(wait, 5 * 2**attempt)
                    self.event(source, job["id"], "retry", f"HTTP {response.status_code}; wait {wait}s")
                except httpx.HTTPError as exc:
                    if attempt == 2:
                        raise
                    wait = 5 * 2**attempt
                    self.event(source, job["id"], "retry", type(exc).__name__)
                self.activity(source, phase="backoff", retry_wait_seconds=wait)
                if STOP.wait(wait):
                    self.update(job["id"], status="pending")
                    return
            if response is None:
                raise RuntimeError("no HTTP response")
            digest = hashlib.sha256(url.encode()).hexdigest()[:20]
            raw_rel = f"raw/{source}/{digest}.html.gz"
            write(self.root / raw_rel, gzip.compress(response.content, mtime=0))
            final_url = str(response.url)
            self.update(job["id"], raw_path=raw_rel, http_status=response.status_code, final_url=final_url)
            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code}")
            data = response.content
            STOP.wait(self.delay)
        self.activity(source, phase="extracting")
        if job["kind"] == "index":
            stories, indexes = index_entries(source, final_url, soup_of(data))
            for target, meta in stories:
                self.add(source, target, "story", meta)
            for target in indexes:
                self.add(source, target, "index")
            self.update(job["id"], status="done", error=None)
            self.event(source, job["id"], "index", f"{len(stories)} story links; {len(indexes)} index links")
        else:
            meta, content, fragment = extract(source, final_url, data, json.loads(job["metadata"]))
            for link in meta.get("linked_story_pages", []):
                with self.lock:
                    exists = self.db.execute("SELECT 1 FROM jobs WHERE source=? AND url=?", (source,link["url"])).fetchone()
                if not exists:
                    self.add(source, link["url"], "story", {"title":link["label"], "discovered_from":final_url, "discovery_kind":"linked_story_page"})
            digest = hashlib.sha256(url.encode()).hexdigest()[:20]
            stem = re.sub(r"[^\w.-]+", "-", meta.get("title", "story"), flags=re.U).strip("-.")[:100] or "story"
            name = f"{stem}--{digest}"
            if job["text_path"]:
                name = Path(job["text_path"]).stem
            txt_rel = f"text/{source}/{name}.txt"
            meta.update(raw_path=raw_rel, text_path=txt_rel, requested_url=url)
            write(self.root / txt_rel, content)
            write(self.root / f"metadata/{source}/{name}.json", dumps(meta) + "\n")
            write(self.root / f"fragments/{source}/{name}.html.gz", gzip.compress(fragment.encode("utf-8"), mtime=0))
            self.update(job["id"], status="done", text_path=txt_rel, words=meta["words"], error=None)
            self.event(source, job["id"], "story", f"{meta['words']} words; {meta.get('title','')}")
        self.activity(source, last_completed_at=now(), last_completed_url=url, phase="idle")

    def worker(self, source, limit=None):
        processed = 0
        blocked = 0
        with httpx.Client(follow_redirects=True, timeout=httpx.Timeout(40, connect=15), headers={"User-Agent":"HomeShelfCollector/1.0 (personal literary archive)","Accept":"text/html,application/xhtml+xml"}, limits=httpx.Limits(max_connections=1)) as client:
            while not STOP.is_set():
                self.activity(source, phase="selecting")
                with self.lock:
                    job = self.db.execute("SELECT * FROM jobs WHERE source=? AND status='pending' ORDER BY CASE kind WHEN 'index' THEN 0 ELSE 1 END,id LIMIT 1", (source,)).fetchone()
                    if job and (limit is None or processed < limit):
                        self.db.execute("UPDATE jobs SET status='running',updated=? WHERE id=?", (now(), job["id"]))
                        self.db.commit()
                if not job or (limit is not None and processed >= limit):
                    break
                try:
                    self.process(job, client)
                    blocked = 0
                except Exception as exc:
                    self.update(job["id"], status="failed", error=f"{type(exc).__name__}: {exc}")
                    self.event(source, job["id"], "failed", f"{type(exc).__name__}: {exc}")
                    blocked = blocked + 1 if re.search(r"HTTP (403|429|503)", str(exc)) else 0
                    if blocked >= 3:
                        self.event(source, job["id"], "source_stopped", "three consecutive access/rate failures")
                        self.activity(source, phase="stopped_after_access_failures")
                        return
                processed += 1
        self.activity(source, phase="finished" if not STOP.is_set() else "stopped")

    def run(self, sources, limit=None, workers_per_source=1):
        with self.lock:
            self.db.execute("UPDATE jobs SET status='pending' WHERE status='running'")
            self.db.commit()
        thread = threading.Thread(target=self.heartbeat, daemon=True)
        thread.start()
        self.write_heartbeat()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(sources) * workers_per_source) as pool:
                futures = [pool.submit(self.worker, source, limit) for source in sources for _ in range(workers_per_source)]
                for f in futures:
                    f.result()
        finally:
            self.done.set()
            thread.join()
            self.export()

    def export(self):
        with self.lock:
            rows = [dict(r) for r in self.db.execute("SELECT * FROM jobs ORDER BY source,id")]
        write(self.root / "manifest.jsonl", "".join(dumps(r) + "\n" for r in rows))
        write(self.root / "failures.jsonl", "".join(dumps(r) + "\n" for r in rows if r["status"] == "failed"))
        summary = {}
        for r in rows:
            s = summary.setdefault(r["source"], {"story_files":0,"words":0,"indexes":0,"pending":0,"failed":0,"skipped":0})
            if r["status"] == "done":
                if r["kind"] == "story":
                    s["story_files"] += 1
                    s["words"] += r["words"] or 0
                else:
                    s["indexes"] += 1
            elif r["status"] in s:
                s[r["status"]] += 1
        write(self.root / "summary.json", dumps({"generated_at":now(),"sources":summary,"corpus_validated":False,"corpus_deduplicated":False}) + "\n")
        print(dumps(summary), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    p.add_argument("--delay", type=float, default=1.5, help="seconds between network requests per source")
    p.add_argument("--workers-per-source", type=int, default=1, help="concurrent fetch workers per selected source")
    sub = p.add_subparsers(dest="command", required=True)
    crawl = sub.add_parser("crawl", help="seed indexes and resume collection")
    crawl.add_argument("--limit", type=int, help="maximum jobs per source this run")
    crawl.add_argument("--refresh-indexes", action="store_true", help="fetch known indexes again to discover newly published stories")
    fetch = sub.add_parser("fetch", help="queue supplied story URLs and resume that source")
    fetch.add_argument("source", choices=SITES)
    fetch.add_argument("urls", nargs="+")
    sub.add_parser("extract", help="re-extract cached successful story responses offline")
    sub.add_parser("retry", help="retry failed jobs using cached successful responses when available")
    sub.add_parser("export", help="refresh manifest, failures and summary exports")
    for parser in sub.choices.values():
        parser.add_argument("--sources", nargs="+", choices=SITES, default=DEFAULT_SITES)
    args = p.parse_args()
    if args.delay < 0:
        p.error("delay must be nonnegative")
    if args.workers_per_source < 1:
        p.error("workers-per-source must be positive")
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: STOP.set())
    c = Collector(args.root, args.delay)
    if args.command == "crawl":
        c.seed(args.sources)
        if args.refresh_indexes:
            with c.lock:
                for source in args.sources:
                    c.db.execute("UPDATE jobs SET status='pending', raw_path=NULL WHERE kind='index' AND source=?", (source,))
                c.db.commit()
        c.run(args.sources, args.limit, args.workers_per_source)
    elif args.command == "fetch":
        for url in args.urls:
            c.add(args.source, url, "story")
        c.run([args.source], workers_per_source=args.workers_per_source)
    elif args.command == "extract":
        with c.lock:
            placeholders = ",".join("?" for _ in args.sources)
            rows = c.db.execute(f"SELECT * FROM jobs WHERE kind='story' AND http_status=200 AND raw_path IS NOT NULL AND source IN ({placeholders})", args.sources).fetchall()
        # Do not start a fetch queue: this command must remain strictly offline.
        for job in rows:
            if STOP.is_set():
                break
            try:
                c.process(job, None)
            except Exception as exc:
                c.update(job["id"], status="failed", error=str(exc))
                c.event(job["source"], job["id"], "failed", str(exc))
        c.export()
    elif args.command == "retry":
        with c.lock:
            for source in args.sources:
                c.db.execute("UPDATE jobs SET status='pending' WHERE status='failed' AND source=?", (source,))
            c.db.commit()
        c.run(args.sources, workers_per_source=args.workers_per_source)
    else:
        c.export()


if __name__ == "__main__":
    main()
