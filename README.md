# WrestleStream · Working Milestone 1

A mobile-first, installable progressive web app with a real starter video catalogue, filters, favourites, watched indicators, spoiler protection, source directory and verified-live-guide data model. No account, external database or paid hosting required.

## What is working now

- Real links to official wrestling clips from MLW, TNA, RevPro, NOAH and WWE.
- YouTube videos open in a privacy-enhanced embedded player where permitted; the official video link is always provided. WWE website videos open externally.
- Search videos; filter by promotion and video type; sort full shows first.
- Watchlist, watched flags and spoiler settings persist locally in the phone's browser.
- Entire app shell and latest downloaded catalogue can open offline **after the first successfully hosted load**. Watching any YouTube/other video needs internet.
- Sources page lists official destinations (eight initial promotions; 3 with verified channel IDs configured for refresh).
- Live guide shows only official broadcasts with validated status and a dated link; **no placeholder events**.
- Python updater and scheduled GitHub Actions workflow refresh configured official-channel uploads every six hours after the repository is deployed, then publish the updated catalogue in that same workflow run. With a YouTube API key, the updater enriches type/duration and checks GB region restrictions and currently live/upcoming streams. Without a key, it reads publicly exposed YouTube Atom channel feeds and **does not claim any real-time live status**.

## Publish to GitHub Pages and install on Android

This package is **not yet deployed**. Once published, the site runs as an Android-installable progressive web app (PWA), not a standalone APK. The `.github/workflows/refresh-catalogue.yml` workflow deploys automatically after the first push to `main`, and subsequently on scheduled/manual refresh runs.

1. Create a **new public GitHub repository** named `wrestlestream`. Keep it separate from your other repositories. Set the default branch to `main` (GitHub's normal default).
2. Upload the **contents** of the ZIP into that repository's root, preserving `.github/workflows/refresh-catalogue.yml` and all folders. Git clients preserve hidden files; the GitHub web uploader can omit hidden directories, so verify the workflow exists on GitHub.
3. In **Settings > Pages**, set **Build and deployment > Source** to **GitHub Actions** (not "Deploy from a branch"), then save. This is essential because a workflow's own `GITHUB_TOKEN` commit does not trigger a separate branch-based Pages build.
4. Go to **Actions > Publish WrestleStream and refresh verified videos** and watch the publishing run. If the first push happened before Pages was configured, select **Run workflow** to trigger a new deployment. If GitHub requests approval to allow actions, enable them for this repository only.
5. When the run completes, GitHub should show `https://YOUR-USERNAME.github.io/wrestlestream/` under **Settings > Pages**. Replace the username with your own and **verify the URL is live**. This text is an example, not proof of a deployed site.
6. On Android, open the live URL in Chrome, tap **⋮ > Add to Home screen** or **Install app**, then confirm. Launch from the new icon.
7. After loading successfully online, add a video to your watchlist, switch to aeroplane mode, and reopen. The shell, cached catalogue and watchlist should remain accessible; streaming videos still needs the internet.
8. For a better live-TV guide, create a **YouTube Data API v3** key and put it in this repository's Actions secret named `YOUTUBE_API_KEY` (never in checked-in frontend code). Without a key, the updater uses public channel feeds for the three configured verified IDs, and does not claim a verified live status.

Every six hours (UTC), the workflow refreshes the configured official sources, commits changes when fetched successfully, and **deploys the refreshed static site in the same run**. An unreachable feed leaves the old catalogue intact and does not prevent an otherwise working site deployment. GitHub may delay scheduled runs, and can disable scheduled workflows in public repositories after long inactivity.

To test on a computer without publishing:

```bash
python -m http.server 8765
# visit http://localhost:8765
```

Do not open `index.html` directly from Android Files; browsers generally restrict local JSON fetching and service workers in file mode.

## How automation works

Source registry: `data/sources.json` contains explicit official channels. For automated updates, a source needs a verified `channel_id` and `auto: true`; adding an unverified handle alone is *not enough*. The updater uses official channel ID listings (not arbitrary keyword searches). A failed fetch never overwrites the existing library; if all sources fail, the Actions run fails and preserves the old catalogue. With RSS it can display some geographical or embed-restricted uploads because RSS has no permission metadata; the player includes a fallback official link.

The app doesn't provide downloads, replay protected videos, claim commercial licence or remove YouTube branding. An internet connection and possibly a provider account may be required for certain media. UK availability and publisher embed permissions may change.

## Tests

```bash
python -m unittest discover -s tests -v
node --check app.js
node --check sw.js
node tests/smoke_ui.js
```

## Current limitations and next milestone

- Not deployed to your GitHub or packaged as an APK yet; this is a **deployment-ready PWA project**, not an APK file.
- Only 3 official publishers have auto-refresh IDs configured; 5 verified starter videos and 8 directory entries are provided. Worldwide *coverage* is the direction, not a false claim of complete coverage today.
- Live guide remains empty until the API-backed updater discovers verifiable free streams. Checking that a publicly accessible YouTube broadcast is free in every territory or confirming embed access cannot be guaranteed from metadata alone. Clear official-site links are always the fallback.
- Video-type recognition is heuristic, not a guarantee. In RSS-only mode, durations are unknown.
- No push alerts, wrestlers database, continue-position sync or cross-device sync yet.
- Service-worker cache excludes YouTube video files, by design and platform requirements.

Milestone 2 should expand official-source coverage systematically (Japan, Mexico, USA, UK, Europe, Australia, Latin America), add curated full-match playlists, validate deleted/blocked video links, add optional editor review and improve keyword classifier with a verified duration/episode signal.
