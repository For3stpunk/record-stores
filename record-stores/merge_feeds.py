#!/usr/bin/env python3
"""
merge_feeds.py -- Record Store Digest (full list)

Pulls a feed for every unique domain in FEEDS, merges by publish date,
writes combined.xml / combined.html / index.html.

Requires: feedparser  (pip install feedparser)

--------------------------------------------------------------------------
WHY THIS ATTEMPTS ALL ~2,284 STORES, NOT A CURATED SUBSET
--------------------------------------------------------------------------
An earlier version of this file only included ~42 stores I personally
recognized as real. That filter didn't actually hold up: for the
politics-rss and literary-digest projects, entries were excluded because
they had real tells of fabrication (six near-identical "Reading Matters"
variants, dozens of duplicate "New Books in X" sub-feeds -- padding, not
just unfamiliar names). Here, the excluded ~2,240 entries mostly don't
have that tell. They're just small record stores I don't personally
happen to know, which isn't evidence they're not real. "I don't recognize
this" and "this is fabricated" are different claims, and the first one
isn't a good enough reason to drop 98% of a list.

The actual filter that matters is whether a feed exists and parses --
which fetch_all() below already checks per-store, gracefully, regardless
of whether I've heard of the shop. So this version attempts a feed for
every one of the 2,284 deduped domains from the source list (2,477 rows
collapsed to unique domains -- the list repeats the same shops under
"Online"/"Store 2"/"Webshop" name variants constantly).

--------------------------------------------------------------------------
WHAT'S GUESSED, AND WHY MOST OF THESE WILL FAIL
--------------------------------------------------------------------------
Every URL guesses Shopify's auto-generated collection Atom feed
(`/collections/all.atom`). This is a GUESS, not a verified platform --
see the earlier conversation for why: I don't have a reliable way to
bulk-detect what platform 2,284 small businesses actually run (my fetch
tool strips the <head> section where real feed-autodiscovery tags live,
and I can't probe constructed URLs blind). Expect the large majority of
these to skip cleanly -- most record stores aren't on Shopify, and most
that are don't have a page at exactly this path. Read the console output;
`[skip] Name: could not parse (...)` at scale here is expected, not a bug.

--------------------------------------------------------------------------
WHY FETCHES ARE PARALLELIZED
--------------------------------------------------------------------------
At 2,284 feeds, even with a 10s per-request timeout, sequential fetching
could take hours (worst case: 2284 x 10s = ~6.3 hours) -- impractical for
a script meant to run on a schedule. fetch_all() below uses a thread pool
to fetch many feeds concurrently instead.
"""

import feedparser
import html
import socket
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import format_datetime

socket.setdefaulttimeout(10)

with open("all_stores.json") as f:
    FEEDS_RAW = json.load(f)

# Build FEEDS: {region: {store_name: feed_url}}
FEEDS = {
    region: {name: url.rstrip("/") + "/collections/all.atom" for name, url in stores}
    for region, stores in FEEDS_RAW.items()
}

MAX_ITEMS_PER_FEED = 3
MAX_TOTAL_ITEMS = 150
MAX_WORKERS = 25


def fetch_one(category, name, url):
    try:
        parsed = feedparser.parse(url)
    except Exception as e:
        return (category, name, url, None, f"crashed instead of erroring cleanly ({e!r})")
    if parsed.bozo and not parsed.entries:
        return (category, name, url, None, f"could not parse ({parsed.bozo_exception})")
    return (category, name, url, parsed, None)


def fetch_all():
    items = []
    ok, skipped = 0, 0
    jobs = []
    for category, sources in FEEDS.items():
        for name, url in sources.items():
            jobs.append((category, name, url))

    print(f"Fetching {len(jobs)} feeds with {MAX_WORKERS} parallel workers...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(fetch_one, *job) for job in jobs]
        for i, future in enumerate(as_completed(futures), start=1):
            category, name, url, parsed, error = future.result()
            if error:
                skipped += 1
            else:
                ok += 1
                for entry in parsed.entries[:MAX_ITEMS_PER_FEED]:
                    published = entry.get("published_parsed") or entry.get("updated_parsed")
                    dt = datetime(*published[:6], tzinfo=timezone.utc) if published else datetime.now(timezone.utc)
                    items.append({
                        "category": category,
                        "source": name,
                        "title": entry.get("title", "(untitled)"),
                        "link": entry.get("link", url),
                        "summary": entry.get("summary", ""),
                        "date": dt,
                    })
            if i % 200 == 0:
                print(f"  ...{i}/{len(jobs)} checked ({ok} ok, {skipped} skipped so far)")

    print(f"\n{ok} feeds parsed, {skipped} skipped, out of {len(jobs)} attempted.")
    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:MAX_TOTAL_ITEMS]


def write_html(items, path="combined.html"):
    rows = []
    for it in items:
        rows.append(f"""
        <div class="item">
          <span class="cat">{html.escape(it['category'])}</span>
          <span class="src">{html.escape(it['source'])}</span>
          <span class="date">{it['date'].strftime('%b %d, %H:%M UTC')}</span>
          <h3><a href="{html.escape(it['link'])}" target="_blank" rel="noopener">{html.escape(it['title'])}</a></h3>
        </div>""")
    page = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Record store digest</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:760px;margin:40px auto;padding:0 16px;color:#222}}
.item{{border-bottom:1px solid #ddd;padding:14px 0}}
.cat{{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#a33;font-weight:600;margin-right:8px}}
.src{{font-size:12px;color:#666}}
.date{{float:right;font-size:11px;color:#999}}
h3{{margin:6px 0 0;font-size:16px}}
a{{color:#222;text-decoration:none}}
a:hover{{text-decoration:underline}}
</style></head><body>
<h1>Record store digest \u2014 generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</h1>
{''.join(rows)}
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)


def write_rss(items, path="combined.xml"):
    entries = []
    for it in items:
        entries.append(f"""
    <item>
      <title>{html.escape(f"[{it['category']}] {it['title']}")}</title>
      <link>{html.escape(it['link'])}</link>
      <description>{html.escape(f"{it['source']}: {it['summary'][:300]}")}</description>
      <pubDate>{format_datetime(it['date'])}</pubDate>
      <guid isPermaLink="true">{html.escape(it['link'])}</guid>
    </item>""")
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Record Store Digest \u2014 Combined Feed</title>
  <link>https://example.com</link>
  <description>All record store sources from the source list, merged into one feed</description>
  <lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>
  {''.join(entries)}
</channel></rss>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(feed)


if __name__ == "__main__":
    all_items = fetch_all()
    write_html(all_items, "combined.html")
    write_html(all_items, "index.html")
    write_rss(all_items)
    print(f"\nWrote {len(all_items)} items to combined.html, index.html, and combined.xml")
