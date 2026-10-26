# All Australian Boys

Install **All Australian Boys (custom)** from the existing scraper source, or place this folder inside Stash's scraper directory and reload scrapers. It uses Python's standard library, included in the official Stash Docker image; no login, extra container, pip dependency, or local API configuration is needed.

## Supported URLs and naming

Individual public previews such as `https://www.allaustralianboys.com/sex-scenes_blake8.php` and `https://www.allaustralianboys.com/solos_luke12.php` work for scene scraping and performer scraping. Linked `video-*.php` teaser URLs also work for scenes when a single preview explicitly links to that exact teaser. Directory pages such as `boys.php` are not individual scenes.

The site often calls a preview only “Blake,” while its URL distinguishes him as `blake8`. The scraper therefore labels that scene **Blake [blake8] — Sex Scene**. Solo previews use **Solo** instead. The bracketed value is the site's URL identifier, not part of the performer's name or a guessed sequence number. Spelling and numeric identifiers are retained as published; different URL identifiers are not merged just because the displayed names match.

The known malformed Kane heading (a missing `>` delimiter) is repaired from the name actually present in the HTML. Join buttons and statistics are rejected as names rather than being imported as a performer.

Returned scene fields:

- A consistent label containing the displayed name and exact URL identifier.
- Full description from the main preview article, excluding join buttons, statistics, recommendations, and generic site copy.
- The public preview image, embedded so Stash can save it.
- Studio **All Australian Boys**, the individual preview URL, and explicitly linked, unambiguous teaser-page URLs. Direct media files and generic join links are excluded.
- The model named in that preview, with **Male** gender, the individual URL, and disambiguation such as **All Australian Boys (blake8)**. An optional embedded headshot comes from a directory card linking to that exact preview, with the main preview image as fallback.

Direct performer scraping also returns the main description and explicitly labeled height in centimetres and weight in kilograms when available. A stated shoot age is not converted into a birthdate. Two models explicitly named together in a heading are returned separately in a scene scrape; shared portraits, measurements and prose are not assigned to either model individually. A group preview is rejected as a direct single-performer scrape. Additional partners are not inferred from fictional text, thumbnails, or recommendations.

The inspected public previews provide no reliable release date. Dates remain empty; image timestamps, model ages, HTTP modification dates, and the site's copyright year are not treated as release dates.

## Matching and scope

The [StashDB studio](https://stashdb.org/studios/9b304557-0ef2-49b1-bde1-6e833c94aad2) has ID `9b304557-0ef2-49b1-bde1-6e833c94aad2`. Importing it into Stash establishes that association. The scraper returns the studio name and official URL; it does not use an external UUID as a local stored ID.

Stash v0.31.1 normally matches performers by name/alias, not by a scraper's profile URL or disambiguation. Review common-name matches before saving. Numeric identifiers help identify the right public preview but do not force Stash to create a different performer. No local API workaround is required or included.

The bundled index records public preview identities, exact teaser-to-preview links, and optional headshot URLs. New previews still scrape directly. Many older thumbnails on `boys-more.php` lead only to Join; the scraper does not invent public scene URLs from their filenames or request member content. A teaser's internal code is used only to identify candidate previews, and its exact player link must be verified before accepting one.

The site reuses some teaser URLs for different solo and sex-scene previews, including Blake, Jack and Chris. Those previews retain their separate descriptions and catalog entries. Known shared teasers are omitted from scraped scene URLs and rejected as scrape inputs; use the individual preview URL to choose the intended scene.

The 26 October 2026 public catalog snapshot checked 228 linked preview URLs: 211 valid entries and 17 unavailable links. Four shared teaser URLs are excluded from the reverse lookup. Older join-only thumbnails remain outside this public-preview catalog. Legacy pages mixing UTF-8 and Windows-1252 punctuation are decoded without losing the valid UTF-8 text.

## Testing in Docker

Live checks passed for Blake, Luke R, Kane, the separate Blake solo, the KYLE & ANDRES group, and the legacy Archer page.

The scraper is tested in an isolated official Stash v0.31.1 Docker container, with a separate database. Verification covers both sex-scene and solo preview routes, full main descriptions, original names and URL identifiers, fixed studio assignment, Male gender, model disambiguation, image persistence, teaser-to-preview resolution, missing dates, and excluding unrelated page content. Image failure is optional and does not discard the other fields.

To test in your own Docker installation, update your existing scraper source, install **All Australian Boys (custom)**, reload scrapers if needed, scrape an individual preview URL, review the performer match, and save. Saved scenes are not changed until you re-scrape and save them.

Public HTML is cached for six hours in the container's temporary directory. Optional images are validated as JPEG, PNG, GIF, or WebP and embedded immediately. AGPL-3.0.
