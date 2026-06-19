#!/usr/bin/env python3
"""
build_data.py - runs in GitHub Actions (server-side, so no CORS).
Reads config.json, fetches active feeds, applies filter rules, dedupes against
existing data.json (accumulates), writes data.json for index.html.

A listing is KEPT only if ALL pass (matching is case-insensitive):
  1. require_any : whole-word match of at least one (e.g. phd / doctoral).
                   Word-boundary => "doctoral" does NOT match "postdoctoral".
  2. anchor_any  : whole-word match of at least one animal/livestock term.
                   Word-boundary => "pig" does NOT match "epigenetic".
  3. exclude     : whole-word match of any => drop.
  4. include     : substring match of at least one topical/field term
                   (kept as substring so "genomic" catches "genomics").
"""
import json, re, socket, datetime as dt, pathlib
import feedparser

HERE = pathlib.Path(__file__).parent
CONFIG = HERE / "config.json"
DATA = HERE / "data.json"
socket.setdefaulttimeout(25)
UA = "Mozilla/5.0 (compatible; PositionTracker/1.0)"


def norm_link(u):
    u = (u or "").strip().lower().split("?")[0].rstrip("/")
    return re.sub(r"^https?://(www\.)?", "", u)


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def has_word(term, text):
    # whole word, tolerant of a trailing plural 's' (animal/animals, pig/pigs)
    return re.search(r"\b" + re.escape(term) + r"s?\b", text) is not None


def matches(text, inc, req, anc, exc):
    t = text.lower()
    if req and not any(has_word(r, t) for r in req):
        return False
    if anc and not any(has_word(a, t) for a in anc):
        return False
    if any(has_word(x, t) for x in exc):
        return False
    if inc and not any(k in t for k in inc):
        return False
    return True


def main():
    cfg = json.loads(CONFIG.read_text())
    inc = [k.lower() for k in cfg.get("keywords_include", [])]
    req = [k.lower() for k in cfg.get("keywords_require_any", [])]
    anc = [k.lower() for k in cfg.get("keywords_anchor_any", [])]
    exc = [k.lower() for k in cfg.get("keywords_exclude", [])]

    existing = []
    if DATA.exists():
        try:
            existing = json.loads(DATA.read_text()).get("items", [])
        except Exception:
            existing = []
    seen_links = {norm_link(i["link"]) for i in existing}
    seen_titles = {norm_title(i["title"]) for i in existing}

    today = dt.date.today().isoformat()
    items = list(existing)
    new_count, ok, failed = 0, 0, 0

    for f in cfg.get("feeds", []):
        if not f.get("active") or "PASTE" in str(f.get("url", "")).upper():
            continue
        try:
            parsed = feedparser.parse(f["url"], agent=UA)
            if parsed.bozo and not parsed.entries:
                raise ValueError(getattr(parsed, "bozo_exception", "parse error"))
            ok += 1
        except Exception as e:
            failed += 1
            print(f"  ! {f.get('label')}: {e}")
            continue

        for e in parsed.entries:
            title = (e.get("title") or "").strip()
            link = (e.get("link") or "").strip()
            summary = e.get("summary", "") or e.get("description", "")
            if not title or not link:
                continue
            if not matches(title + " " + summary, inc, req, anc, exc):
                continue
            nl, nt = norm_link(link), norm_title(title)
            if nl in seen_links or (nt and nt in seen_titles):
                continue
            seen_links.add(nl); seen_titles.add(nt)
            items.append({"found": today, "region": f.get("region", ""),
                          "country": f.get("country", ""), "source": f.get("label", ""),
                          "title": title, "link": link})
            new_count += 1

    items.sort(key=lambda i: i.get("found", ""), reverse=True)
    DATA.write_text(json.dumps(
        {"updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
         "count": len(items), "items": items}, indent=2, ensure_ascii=False))
    print(f"{new_count} new ({len(items)} total). Feeds ok={ok} failed={failed}.")


if __name__ == "__main__":
    main()
