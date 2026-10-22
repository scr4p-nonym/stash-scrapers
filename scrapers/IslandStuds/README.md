# Island Studs scraper

Refresh the existing scraper source under **Settings → Metadata Providers** and install **Island Studs (custom)**:

```text
https://scr4p-nonym.github.io/stash-scrapers/main/index.yml
```

Python 3 is included in the official Stash Docker image tested here. The scraper uses its standard library only: no pip packages, browser service, login, or local Stash API configuration is required.

## Scenes

Scrape individual `/tour/scenes/...html` URLs from a scene's URL field. Review the metadata, select fields to apply, and save the scene.

Returned fields include the scene title, full description with paragraph breaks, publication date, main cover from the page's Open Graph metadata, source URL, and fixed **Island Studs** studio.

Performers come only from the main scene's explicit **Featuring** links. Model links on recommended scenes are excluded. Each credited performer includes the site name, profile URL, **Male** gender, **Island Studs** disambiguation, and an optional embedded portrait. A profile fetch failure preserves the credited performer's basic metadata.

The displayed date is parsed as month/day/year. Dates are never inferred from a copyright year, image filename, or image expiry timestamp.

## Models and photos

Individual `/tour/models/...html` URLs can be scraped directly in a performer editor. The scraper reads the model heading and the site's lazy-loaded portrait attributes, choosing the largest declared `src0_Nx` image. Portraits are downloaded immediately and returned as embedded image data. An image error, including HTTP 403, leaves the remaining performer fields available.

A biography is included only when the profile actually provides one. Ratings and review widgets are excluded; Eli Daddy's tested profile has a portrait but no biography.

Names and profile URLs are supplied for Stash's normal local matching. The scraper does not identify StashDB performers or look up local performer IDs. Review ambiguous matches and use the scene dialog's editable Performers selector when linking an existing record.

The [Island Studs StashDB studio](https://stashdb.org/studios/8579c4ee-54da-4024-a309-33776c7a0cc4) can be imported/linked once on your local studio record. This scraper returns the studio name and website; it does not create the external StashDB association.

## Verification

Tested through the official Stash v0.31.1 Docker image on 2026-10-23:

| Scene | Publication date | Credited performer |
| --- | --- | --- |
| Eli Daddy 2 | 2022-10-19 | Eli Daddy |
| Eli Daddy | 2021-05-05 | Eli Daddy |
| Hal 2 - Anal | 2021-12-15 | Hal |

All three tests checked the title, full description, exact cover image bytes, date, studio, cast scope, model URL, gender, and disambiguation. Further tests checked Eli's direct portrait scrape, omission of a nonexistent biography, matching to an existing local studio associated with the supplied StashDB ID, and graceful handling of an HTTP 403 portrait failure.

## Manual installation

Keep `IslandStuds.yml` and `islandstuds.py` together in an `IslandStuds` folder under Stash's configured scraper directory, then reload scrapers. Source-manager installation handles both files together and is recommended.

AGPL-3.0, consistent with the repository license.
