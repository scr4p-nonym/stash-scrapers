# Beefcake Hunter

Install **Beefcake Hunter (custom)** from the existing scraper source, or place this folder inside Stash's configured scraper directory and reload scrapers. The Python helper uses the standard library included in the official Stash Docker image. No login, browser service, pip dependencies, or local API settings are required.

## Scene URLs

Paste an individual `https://beefcakehunter.com/video/<slug>/` URL into a scene and scrape it. Returned fields:

- Title and full public description, with paragraph breaks; popup notices, related videos, comments, and gallery captions are excluded.
- The publication date displayed on the scene page, falling back to publication metadata. Modification dates are ignored.
- The declared video poster, embedded immediately so Stash can save it. The structured main image is a fallback; image failure does not discard metadata.
- Studio **Beefcake Hunter** and the clean source URL.
- **Victor**, with **Beefcake Hunter** disambiguation and **Male** gender, on every scene. His official Hunter page and the supplied StashDB performer URL are included.
- Guest models explicitly credited in the site's model listings, where an exact scene URL or unique exact listing title establishes the relationship. A bundled public-listing snapshot makes these lookups efficient. For newer scenes, explicit “Beefcake Name” links in the main description are accepted only after the model's public category lists the exact scene URL. No names are inferred from the scene title alone or from recommendations. Unconfirmed guests are omitted.

The scraper reads public metadata only. If the site redirects a scene to membership or removes its public metadata, the scrape reports that it is unavailable; it does not attempt authentication.

## Model URLs

Use a model category such as `https://beefcakehunter.com/video-category/gordon/`. It returns the model's name, Male gender, Beefcake Hunter disambiguation, and category URL. A portrait from an explicitly named model-directory card is optional when present in the bundled snapshot; otherwise the image stays empty. The category pages do not provide reliable biographical fields. The fixed Victor record is also available through `https://beefcakehunter.com/about-the-hunter/`.

Some generic category URLs use the same route; these are not intended as model profiles. The known genre categories are rejected.

Stash performs its normal local name/alias matching. Profile URLs and disambiguation do not force a different match in Stash v0.31.1. Review first-name matches, especially if a name already belongs to someone else. The scraper does not access your Stash API. Import or create the intended performers once and select them when reviewing a scene scrape.

The corresponding [studio on StashDB](https://stashdb.org/studios/6c64c54a-7625-43bf-8b34-858b0ce0222b) and [Victor on StashDB](https://stashdb.org/performers/cc7e6bb9-6140-41da-a748-7d306c8a31c6) can be imported into Stash to retain those associations. External UUIDs are not used as local stored IDs.

## Docker testing

Tested in a temporary, isolated official **Stash v0.31.1** Docker container with a separate empty database; no changes to the user's container were required. Both supplied examples passed title, full-description, date, studio, verified guest, existing Victor matching, and clean-URL checks:

| Scene | Date | Performers |
| --- | --- | --- |
| Jacobo’s unexpected return | 2026-04-01 | Victor, Jacobo |
| Hung Santa Gordon | 2025-12-24 | Victor, Gordon |

The bundled snapshot covers 629 public scenes, with 620 dated entries, 626 verified guest credits, and 234 portrait sources from single-model cards. Five group scenes return two separate guests. The nine listings without dates stay undated. Both example model portraits were saved and retrieved from Stash.

Both scene covers were saved and retrieved from Stash, and both performer relationships persisted. Direct model-category scraping was also checked. Controlled checks cover missing images/dates, retaining Victor when guest verification fails, and rejecting invalid dates.

To test in your own Docker installation: update the scraper source, install this scraper, reload scrapers if needed, scrape either example, review the fields and performer matches, then save. No additional container or configuration is needed. Previously saved scenes change only when re-scraped and saved.

Fetched HTML is cached for six hours in the container's temporary directory. The bundled index is a snapshot, not a promise that the site's models or URLs will never change. Metadata and optional images come from the producer's public pages. AGPL-3.0.
