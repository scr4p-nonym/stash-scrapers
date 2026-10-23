# Island Studs scraper

Refresh the existing scraper source under **Settings → Metadata Providers** and install **Island Studs (custom)**:

```text
https://scr4p-nonym.github.io/stash-scrapers/main/index.yml
```

Python 3 is included in the official Stash Docker image tested here. The scraper uses its standard library only: no pip packages, browser service, login, or local Stash API configuration is required.

## Scenes

Scrape individual `/tour/scenes/...html` URLs from a scene's URL field. Review the metadata, select fields to apply, and save the scene.

Returned fields include the scene title, full description with paragraph breaks, publication date, main cover, source URL, and fixed **Island Studs** studio. Images are downloaded and embedded before the result is returned, so saving does not depend on fetching the remote URL again.

For covers, the scraper first looks for the exact scene's official thumbnail on its credited models' profile pages. It chooses the largest declared version, falling back to smaller versions, Open Graph metadata, the player poster, and the main scene's preview thumbnail. Invalid directory URLs and non-image responses are rejected. If all declared images fail, the other metadata remains available without a broken image URL.

Performers come only from the main scene's explicit **Featuring** links. Both modern model URLs and older `sets.php?id=...` profile links are supported, with relative links resolved against the page's declared base URL. The **Duos** collection is excluded, as are model links on recommended scenes. Each credited performer includes the site name, profile URL, **Male** gender, **Island Studs** disambiguation, and an optional embedded portrait. A profile fetch failure preserves the credited performer's basic metadata.

The displayed date is parsed as month/day/year. Dates are never inferred from a copyright year, image filename, or image expiry timestamp.

## Models and photos

Individual `/tour/models/...html` URLs can be scraped directly in a performer editor. The scraper reads the model heading and the site's lazy-loaded portrait attributes. It tries the largest declared `src0_Nx` image first, then smaller versions and older `src0`/`src` attributes. Direct performer scrapes offer up to eight distinct image choices: the original portrait first, followed by public preview pictures from scenes explicitly credited only to that model. Group-scene pictures are excluded. Each preview uses the largest available declared version, with smaller versions as fallbacks. These are public previews; their resolution varies by the site. Use the image selector in the performer scrape dialog to choose one. Scene scrapes still fetch only the default portrait for each performer.

Pictures are downloaded immediately and returned as embedded image data. An image error, including HTTP 403, leaves the remaining performer fields available.

Legacy `/tour/sets.php?id=...` model URLs also work for direct performer scraping. Numeric IDs are preserved because they distinguish individual models. Collection pages such as `Duos.html` are not treated as performers.

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

The legacy-image fix was also tested with **Logan** (`Logan_vids.html`, dated 2013-12-18). That page's Open Graph image points to a folder that returns HTTP 403; the earlier version used the player poster instead, and the model portrait is found through its legacy `src0` attribute. The current version prefers the matching scene thumbnail from the model page. Both images were actually saved to scene/performer records and successfully retrieved from Stash afterward. Controlled tests checked fallback after a missing high-resolution portrait and rejection of HTML returned in place of an image. The three earlier live-scene tests were rerun successfully.

The duo-credit fix was tested with **Duo - Dan & Kyle** (`Duo-DanKyle_vids.html`, dated 2011-09-07). It returned exactly **Dan** (`sets.php?id=102`) and **Kyle** (`sets.php?id=58`), with separate portraits. Duos and the recommended-scene performer Darren were excluded. Both legacy profile URLs also passed direct performer scraping, and the Logan image-saving checks and earlier scene tests were rerun.

The image-choice update was tested through Stash with Floyd, Eli Daddy, and the legacy Dan profile. Tests checked multiple distinct images, exclusion of group-scene previews, graceful handling of failed alternatives, and saving a selected alternative portrait. Osric's scene cover was checked byte-for-byte against the official `contentthumbs/2788.jpg` thumbnail from his model page, and the three-person cast was checked again.

## Manual installation

Keep `IslandStuds.yml` and `islandstuds.py` together in an `IslandStuds` folder under Stash's configured scraper directory, then reload scrapers. Source-manager installation handles both files together and is recommended.

AGPL-3.0, consistent with the repository license.
