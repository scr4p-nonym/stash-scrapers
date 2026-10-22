# My Best Friend's Dad scraper

Refresh the existing scraper source in **Settings → Metadata Providers** and install **My Best Friend's Dad (custom)**:

```text
https://scr4p-nonym.github.io/stash-scrapers/main/index.yml
```

Python 3 is included in the official Stash Docker image tested here. This scraper uses its standard library only: no pip packages, browser service, login, or local Stash API configuration is required.

## Scenes

Paste an individual `/updates/...` URL into a scene's URL field, scrape, review the returned fields, then apply and save.

Returned fields include the title, complete description, main cover image, canonical URL, publication date when available, fixed **My Best Friend's Dad** studio, and verified performers. Each model includes **Male** gender, **My Best Friend's Dad** disambiguation, a profile URL, biography, and an optional portrait.

Candidate names may come from scene titles, descriptions, or image filenames, but a performer is returned only after their profile explicitly lists the **exact scene URL**. This can miss performers where profiles or scene metadata are incomplete. At most 16 candidate profiles are checked. No full cast guarantee or StashDB performer identity inference is made.

Publication dates come from explicit page metadata or the exact scene entry in a verified model profile. Later Updated dates and signed-image expiry timestamps are not treated as publication dates. If profile dates conflict, the date remains empty.

## Models and matching

Individual `/models/...` URLs can be scraped directly in a performer editor. Model portraits are fetched immediately and embedded as image data. If a portrait request returns 403 or otherwise fails, the remaining model metadata is still returned.

Names and profile URLs are supplied to Stash for its normal matching. Review ambiguous local matches; the scraper does not look up local performer IDs or modify existing performer records. An existing model can be selected in the scene scrape dialog's editable Performers field rather than created again with the plus badge.

The studio name is fixed to **My Best Friend's Dad**. Stash can match an existing local studio by name or alias. The corresponding [StashDB studio](https://stashdb.org/studios/2f71c0e7-a04e-452e-9d45-196147c24a7b) can be imported/linked once on the local studio record; this scraper does not create that external association.

## Cache

Scene pages and portrait URLs are fetched fresh. The parsed model directory is cached for 24 hours and model filmographies for 6 hours under the system temporary directory's `stash-mybestfriendsdad-cache-v1` folder. No signed image URLs are cached. New filmography entries may therefore take time to appear in cached lookups. If model lookup fails, the main scene metadata still returns with a warning in Stash's logs.

## Verification

Tested through the official Stash v0.31.1 Docker image on 2026-10-22:

| Scene | Publication date | Verified performer |
| --- | --- | --- |
| Meet Jeremy Barrett | 2022-11-19 | Jeremy Barrett |
| Hopelessly Devoted | 2026-02-21 | Jeremy Barrett |
| Frank the Tank | 2026-09-12 | Frank Clayton |

All three tests checked titles, complete descriptions, exact cover image bytes, studio, performer name/profile URL, gender, and disambiguation. Jeremy's direct profile scrape returned his bio and portrait. A separate test confirmed matching to an existing local studio with the supplied StashDB association. A controlled portrait 403 test preserved the remaining model metadata.

## Manual installation

Keep `MyBestFriendsDad.yml` and `mybestfriendsdad.py` together inside a `MyBestFriendsDad` folder in Stash's configured scraper directory, then reload scrapers. Source-manager installation handles both files together and is recommended.

AGPL-3.0, consistent with the repository license. Ported from the self-contained The Full English scraper.
