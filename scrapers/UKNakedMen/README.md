# UK Naked Men

Install **UK Naked Men (custom)** from the scr4p-nonym scraper source:

```text
https://scr4p-nonym.github.io/stash-scrapers/main/index.yml
```

## Supported links

Open an individual scene or model from the public tour, then paste its URL into the corresponding Stash scene or performer. Both the short `refstat.php` links and their resolved `showgal.php` links are supported. Directory pages such as `/tour/?models` and `/tour/?videos` are for browsing, not scraping an individual record.

Examples:

- Scene: `https://www.uknakedmen.com/tour/refstat.php?lid=37268&sid=669`
- Model: `https://www.uknakedmen.com/tour/refstat.php?lid=34943&sid=670`

Scene results contain the published title, full public description, canonical short source URL, fixed **UK Naked Men** studio name and an optional embedded cover. The main player's declared still poster is tried first; if it is unavailable, the page's explicitly marked `scene_faceimage` supplies the scene thumbnail. Trailer/video files are never downloaded. The inspected public pages supply no release dates or explicit scene cast profile links, so no release dates or performers are guessed from names, filenames or titles.

Performer results contain the published model name, Male gender, **UK Naked Men** disambiguation, source URL, optional public biography, and the actual model portrait. Ratings, recommendations and filmography titles are excluded from the biography. Missing fields stay empty. Profile identity is not inferred from a scene title; scrape the model's own page separately.

Identity is the site's numeric content ID. Affiliate/tracking parameters are discarded; the short link retains the required `sid` navigation context. Redirects must stay within individual public tour pages and retain the same content ID. Membership, directory, unrelated-domain and wrong-page-type inputs are rejected. Protected member pages and trailer playback are not used.

The Python helper uses only the standard library. It needs no pip packages, login, browser service, or local Stash API configuration. No additional Docker container is required. Images are validated JPEG/PNG/GIF/WebP data URLs, limited to 8 MB; unavailable covers or portraits leave the remaining metadata usable.

Stash matches studios and performers using its normal matching rules. Site disambiguation does not force unique same-name matches; review the selection before saving.

## Catalog

UK Naked Men is included in the local combined scene catalog. Its public All Videos listing supplies scene titles and links, but no release dates or explicit cast links. The catalog preserves those omissions. Names present in titles remain searchable. Entries are deduplicated by content ID. The collection uses cached public listing pages and serial requests 6–9 seconds apart, stopping on HTTP 403/429; it does not fetch media or private pages.

## Verification

Tested 2026-10-30 in an isolated official Stash v0.31.1 Docker container:

- **Ivan Kolos and Max Royse**, ID 37268: full 556-character description, studio, cleaned identity URL and saved 500 x 333 cover. The site's main poster URL returned 404; its own scene thumbnail was used successfully. Date and cast remained empty.
- **Sam Wallis**, ID 34943: name, Male gender, site disambiguation and saved 500 x 692 portrait. Empty biography stayed empty; rating controls and scene titles were excluded.
- Long and short identity URLs normalize consistently. Directory, member, unrelated-domain and wrong-page-type inputs were rejected. Controlled cover failure retained the rest of the metadata.

Runtime code is AGPL-3.0, following the existing custom scraper helpers.
