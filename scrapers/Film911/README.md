# Film911 scraper

Refresh the existing source under **Settings → Metadata Providers** and install **Film911 (custom)**:

```text
https://scr4p-nonym.github.io/stash-scrapers/main/index.yml
```

Uses Python's standard library only. Python is included in the official Stash Docker image tested here. No pip packages, browser service, site login, or local Stash API setup is needed.

## Scenes and purchase links

Scrape the individual Film911 scene page URL. Returned fields include the scene title, full description with paragraph/list breaks, date when available, embedded cover, fixed **Film911** studio, and scene URLs.

The original Film911 URL is always first. Explicit purchase buttons and links to clip marketplaces such as WatchFighters are added as additional scene URLs. Product query parameters are preserved. The scraper reads the links on the Film911 page; it does not visit purchase destinations, submit checkout forms, or require a store login. Navigation, support, social, and direct media-download links are excluded.

Titles come from the scene heading, with support for alternate WordPress headings and structured-data fallbacks. Trailing display labels such as “ALL NEW,” “(review),” and “(demo available)” are removed. Character names in the story are not used to identify actors. The main description is preserved; header promotions, categories, and purchasing-support widgets are excluded.

The cover uses the scene video player's declared poster first, then Open Graph metadata, then the first description/gallery image. Gallery fallbacks try declared `srcset` sizes from largest to smallest. A known migrated `film911.net-content` image-host error is corrected to the site's `film911.net/wp-content` path. No video files are downloaded. The cover is downloaded immediately and embedded so Stash can save it without another remote request. An image failure leaves the remaining metadata available.

Some pages initially show the site's public entry screen. The helper follows its normal `ao_confirm` view once; this parameter is excluded from the returned identity URL. Category, recruitment, and information pages are rejected as scene inputs.

## Dates

An explicitly announced **full date including year**, after “coming” in the title or scene URL, takes precedence. Otherwise, the site's original `datePublished` metadata is used. Modification dates, copyright years, image upload dates, and partial announcements without a year are not used to infer a release date.

This distinction matters for migrated posts. **Brax falls in love** advertises **2021-07-07** in its URL but now reports a **2024-04-16** post-publication timestamp. The scraper returns the explicitly announced 2021 date. Announced dates reflect the site's advertised schedule; they do not independently prove the actual release date. When no full announcement exists, the fallback is a page-publication date, which can differ from a video's release date.

## Performers and studio

The inspected site's `/model/` page is a recruitment form, not an actor directory. The tested scenes do not provide reliable individual performer-profile credits. Performer scraping is therefore omitted. WordPress's `Person` entry identifies the site administrator and is never returned as cast. Names are not guessed from titles, descriptions, fictional character names, or image filenames.

The scraper returns the studio name **Film911** and its official website. Import or link the [Film911 studio on StashDB](https://stashdb.org/studios/2be1f8ca-40b9-4443-94b3-700ca9a4cf14) once on your local studio record. Returning the studio name does not create its external StashDB association.

## Verification

Tested on 2026-10-26 through an isolated official Stash v0.31.1 Docker container:

| Scene | Returned date |
| --- | --- |
| Brax falls in love | 2021-07-07 |
| Damien Kyle has anger issues | 2026-10-23 |
| Daniel”s travels | 2026-10-10 |
| Jordan King with Mr. Latcher 2 | 2026-09-16 |
| Damien Kyle asks for to much | 2026-10-22 |

All five tests checked titles, complete descriptions, exact declared poster bytes, purchase URLs, clean identity URLs, studio matching, and omission of guessed cast. Brax's scene cover was actually saved and retrieved from Stash.

Controlled tests also checked alternate heading/content layouts, structured-title fallback, status-label cleanup, preserved list formatting, generic purchase buttons with query parameters, missing purchase links, publication-versus-modification dates, image fallbacks, malformed image paths, and rejection of recruitment pages and invalid or partial release announcements.

## Manual installation

Keep `Film911.yml` and `film911.py` together in a `Film911` folder under Stash's configured scraper directory, then reload scrapers. Source-manager installation handles both files together and is recommended.

AGPL-3.0, consistent with the repository license.
