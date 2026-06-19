# Livestock Genomics Position Tracker (free, self-hosting)

A static site that lists open PhD/research positions in livestock genomics.
GitHub Actions fetches RSS feeds on a schedule (server-side, so no CORS),
writes `data.json`, and GitHub Pages serves `index.html` — **$0, no server**.

## One-time setup (~10 min)

1. **Create a new GitHub repo** (make it **Public** so Pages + Actions are free) and upload these files:
   `index.html`, `build_data.py`, `config.json`, `.github/workflows/refresh.yml`, `README.md`.
2. **Edit `config.json`** (pencil icon, right in GitHub): paste your verified feed URLs.
   The big one is **Google Alerts → Deliver to = RSS feed** → paste that URL. Make several
   (one per region/query) for maximum coverage. Set `"active": false` to mute a feed.
3. **Enable Pages:** Settings → Pages → Source = *Deploy from a branch* → `main` / `root`.
   Your site appears at `https://<username>.github.io/<repo>/`.
4. **Enable Actions:** Settings → Actions → allow workflows. Then open the **Actions** tab →
   *refresh-positions* → **Run workflow** to do the first fetch now (otherwise it waits for Monday).
5. Open your Pages URL. New finds (≤7 days) get a **NEW** badge. Search, filter by region, sort by any column.

## How it stays current
The workflow runs every Monday and on demand. It commits `data.json`, which redeploys Pages
automatically and keeps the repo active so the schedule never sleeps. Listings accumulate over
time (deduped by link + title).

## To control it from anywhere
`config.json` is your control panel — edit it in the GitHub web UI from any device to add feeds
or keywords. No code changes needed.

## Scope note
The site is **read-only discovery**. Your personal triage (Applied / Notes) lives in your local
Excel tracker. If you later want status tracking + user accounts on the web, that needs a small
backend/database (e.g. a free tier on Render/Railway, or Supabase) — a later upgrade.

## Run locally to preview
```bash
pip install feedparser
python build_data.py          # writes data.json
python -m http.server 8000    # open http://localhost:8000
```
