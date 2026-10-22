# The Full English scraper

Install **The Full English (custom)** from the existing source in **Settings → Metadata Providers**:

```text
https://scr4p-nonym.github.io/stash-scrapers/main/index.yml
```

Refresh the source to find the new scraper. The scraper requires Python 3, which is included in the official Stash Docker image tested here. It uses only the Python standard library: no pip dependencies, browser service, or login is required. If Stash cannot find Python in a custom image, configure its Python executable path under Application Paths.

## Scene URLs

Paste an individual `/updates/...` URL into a scene's URL field and click the scrape button. Review the results, select the desired fields, then apply and save them.

The scraper returns the title, full description, main scene image, canonical URL, **The Full English** studio, and verified site performers. Performers include **Male** gender and, when available, their biography and photo. The scene image's signed CDN query parameters are retained so Stash can fetch it immediately; stale image URLs are not cached.

The site does not expose cast links on the scene page. The helper considers names from its model directory, then includes a performer only if that model's public profile lists the **exact scene URL**. A name mentioned in the description alone is insufficient. This can miss performers whose names are absent from the scene metadata or whose profile listings are incomplete; it is not a guarantee of a complete cast. At most 16 candidate profiles are checked per scene.

The publication date comes from explicit page metadata when available, otherwise from the exact scene entry in a verified model profile. It uses the publication date rather than a later Updated date. Missing or conflicting profile dates are left empty. Image expiry timestamps are never used as release dates.

## Performer URLs and local matching

Individual `/models/...` URLs can also be scraped directly in a performer editor. These return the site name, profile URL, **Male** gender, biography, and optional main profile photo. Portraits are fetched immediately and returned as embedded image data, so a delayed import does not depend on an expiring URL. If the image server returns 403 or another image error, the rest of the model metadata still imports.

Site names such as **Billy** do not establish a StashDB identity. Stash may match local performers by name or alias; review first-name matches before applying them. The scraper supplies profile URLs but does not guess StashDB performer IDs or full names.

The studio name is fixed to **The Full English**. Stash matches an existing local studio by name or alias. Its [StashDB entry](https://stashdb.org/studios/c9b896ae-25b8-458f-a849-2ac0a5f6eb0f) can be imported/linked once on that local studio record; the scraper does not set that external association.

## Requests and caching

Scene pages are fetched fresh. The model directory is cached for 24 hours and parsed model filmographies for 6 hours in the system temporary directory, under `stash-thefullenglish-cache-v1`. Cached data contains no signed image URLs. A new profile or scene may therefore take time to appear in cached model lookups. If model lookups fail, the scraper still returns the main scene metadata and logs a warning to Stash's logs.

## Verification

Tested on 2026-10-22 through the official Stash v0.31.1 Docker image, including full descriptions, exact cover bytes, studio assignment, and cast:

| Scene | Date | Verified site performer |
| --- | --- | --- |
| Meet Action Hero Billy | 2018-10-20 | Billy |
| Scottie's Room | 2026-10-11 | Scottie |
| Modern Love | 2026-08-22 | Tomasz |

Billy's scene mentions Bradley, but his profile does not list that scene, so Bradley was excluded. Direct model-URL scraping was verified with Billy's name, profile URL, biography, and image. Cross-site performer identity matching and a complete multi-performer cast have not been validated.

The gender/portrait update was tested through Stash for both scene-created performers and direct performer scraping. Both returned **Male** and an embedded photo. A controlled HTTP 403 test confirmed that portrait failure preserves the name, gender, biography, and profile URL.

## Manual Docker installation

Keep `TheFullEnglish.yml` and `thefullenglish.py` together in a `TheFullEnglish` folder inside Stash's configured scraper directory, then reload scrapers. For a container named `stash` using the default path, from the folder containing this directory:

```sh
docker cp TheFullEnglish stash:/root/.stash/scrapers/TheFullEnglish
```

Adjust the container name and path to your configuration. Source-manager installation handles both files together and is recommended.

AGPL-3.0, consistent with the repository license.
