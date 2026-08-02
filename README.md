# record-store-digest

Merges feeds from record store domains (see `sites_list.md`) into one
combined feed, on a schedule, for free. Same pattern as `politics-rss`
and `literary-digest`.

## This is the full list, not a curated subset

**2,284 unique domains** (the source list's 2,477 rows collapsed by
domain -- it repeats the same shops under "Online"/"Store 2"/"Webshop"
name variants constantly). An earlier version of this project only
included ~42 stores I personally recognized as real, which turned out to
be the wrong filter here -- see the note at the top of `merge_feeds.py`
for the full reasoning. The short version: not recognizing a store's name
isn't evidence it's fake, so this version attempts a feed for every
domain and lets the script's own skip-on-failure logic be the real filter.

## Setup

```
pip install -r requirements.txt
python merge_feeds.py
```

`all_stores.json` (the full domain list, bucketed by region) needs to sit
next to `merge_feeds.py` -- it's read at import time.

Fetching is parallelized (25 concurrent workers) since sequential
fetching across 2,284 feeds could take hours even with a 10s timeout.
Expect the run to still take several minutes.

## Sharing the combined feed for free (GitHub Pages)

1. Push this repo to GitHub (public, for the free Pages tier).
2. **Settings → Pages → Deploy from a branch → `main` / root** → Save.
3. Your feed: `https://<username>.github.io/<repo>/combined.xml`
   Your browsable page: `https://<username>.github.io/<repo>/`
4. Drop the `combined.xml` URL into Feedly, Inoreader, Flipboard, etc.

`.github/workflows/update.yml` is at the correct path and `.nojekyll` is
included from the start.

## What this tracks, and why most of these will skip

The goal is new stock, not blog posts -- every URL guesses Shopify's
auto-generated collection Atom feed (`/collections/all.atom`). This is a
guess, not a verified platform: most record stores likely aren't on
Shopify at all, and expect the large majority of the 2,284 to skip
cleanly in the console output. That's the honest baseline given the tools
available to build this -- see `merge_feeds.py`'s docstring for what
would make a store's feed URL more reliable (checking its real
`<link rel="alternate">` autodiscovery tag), which isn't something this
script can currently do at this scale.

## Why only ~42 sources

The source list was 2,477 rows / 2,284 unique domains. Beyond the first
~150-200 recognizable flagship stores (Amoeba, Rough Trade, Third Man,
Spillers, etc.), it turns into thousands of plausible-sounding
"[Adjective] Records, [City]" entries with no way to verify they're real
businesses. This file keeps only the stores I actually recognize as
established, real shops -- see the note at the top of `merge_feeds.py`
for the full reasoning.
