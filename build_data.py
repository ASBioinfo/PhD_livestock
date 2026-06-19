#!/usr/bin/env python3
"""
build_data.py - runs in GitHub Actions (server-side, so no CORS).
Reads config.json, fetches every active feed, filters by keywords, dedupes
against the existing data.json (so the list accumulates over time), and writes
data.json for index.html to render. Read-only display: personal triage
(Status/Notes) stays in your local Excel tracker.
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


def matches(text, inc, exc):
    t = text.lower()
    if any(x in t for x in exc):
        return False
    return any(k in t for k in inc) if inc else True


def main():
    cfg = json.loads(CONFIG.read_text())
    inc = [k.lower() for k in cfg.get("keywords_include", [])]
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
            if not matches(title + " " + summary, inc, exc):
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
