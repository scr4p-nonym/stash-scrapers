# My Friends Feet scraper

Refresh the existing source under **Settings → Metadata Providers** and install **My Friends Feet (custom)**:

```text
https://scr4p-nonym.github.io/stash-scrapers/main/index.yml
```

The helper uses Python's standard library only. Python is included in the official Stash Docker image tested here. No pip packages, browser service, site login, or local API configuration is required.

## Scenes

Scrape individual `https://www.myfriendsfeet.com/scenes/<id>/<slug>` URLs from the scene editor. Affiliate `nats` parameters can be present in the input; tracking and other query parameters are removed from the returned identity URL.

Returned fields include title, full description, source URL, optional embedded cover, fixed **My Friends Feet** studio, and the models explicitly linked in the scene's model-directory credits. Sidebar promotions, live webcams, and recommended-scene performers are excluded. Names are not inferred from titles or descriptions. If a profile cannot be fetched, the explicitly credited name and profile URL are retained.

The date comes from publication metadata when present, or an exact scene-ID match on a dated related-scene listing. Some public scene pages omit their own date, so the scraper checks at most two related pages for a matching listing. Unrelated dates, image filenames, and copyright years are never used. If a reliable date is unavailable, the field stays empty.

Scene covers use the first working Open Graph image, preserving the declared resolution. Duplicate or broken image declarations are skipped. Covers and portraits are downloaded immediately and embedded in the result so saving does not depend on a later remote download. Image failures leave the other metadata available. Temporary server errors on HTML pages are retried once.

## Models

Individual `/directory/<id>/all/<name>` URLs support direct performer scraping. The model name comes from the profile's structured data or heading. Returned fields include the clean profile URL, **Male** gender, and **My Friends Feet** disambiguation. No biography or other personal attributes are guessed.

Direct performer scrapes offer up to eight distinct public directory pictures, where available. Use the image selector in the performer scrape dialog to choose one. Scene scrapes return one default picture for each model. The site's malformed triple-slash CDN image URLs are normalized before downloading. Public preview resolution varies; no member-only media is accessed.

The scraper supplies names and profile URLs for Stash's normal matching. Stash may match an unrelated existing performer with the same name; review ambiguous results. The scraper does not look up local performer IDs or guess StashDB performer identities.

## Studio

The scraper returns **My Friends Feet** and its official website. Import or link the [My Friends Feet studio on StashDB](https://stashdb.org/studios/95dd1286-4c4d-4445-b18d-0f85c0df72f4) once on your local studio record. Returning the studio name does not create its external StashDB association.

## Verification

Tested on 2026-10-26 through an isolated official Stash v0.31.1 Docker container:

- Nito Loves Foot Worship: exact full description and cover bytes, Nito credit, clean URLs, studio matching, and publication date **2014-05-14** from an exact related-scene listing.
- Nito Tickled Until He Cums: metadata, portrait, and publication date **2026-10-01**.
- Nito Dominates Dev With His Socked & Bare Feet: both explicitly credited models, **Dev** and **Nito**, with their own profile URLs and portraits.
- Direct Nito profile: multiple distinct embedded picture choices, gender, disambiguation, and no invented biography.
- Actual saving and retrieval of a selected alternative portrait and scene cover.
- Unrelated/missing dates, malformed CDN URLs, failed image requests, and HTML masquerading as images.

## Manual installation

Keep `MyFriendsFeet.yml` and `myfriendsfeet.py` together in a `MyFriendsFeet` folder under Stash's configured scraper directory, then reload scrapers. Source-manager installation handles both files together and is recommended.

AGPL-3.0, consistent with the repository license.
