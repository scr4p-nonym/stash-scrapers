# Slow Teasing Hand Jobs scraper

Refresh the existing source under **Settings → Metadata Providers** and install **Slow Teasing Hand Jobs (custom)**:

```text
https://scr4p-nonym.github.io/stash-scrapers/main/index.yml
```

Uses Python's standard library only. Python is included in the official Stash Docker image tested here. No pip packages, site login, browser service, or local Stash API configuration is needed.

## Paste the members scene URL

Use the individual `https://slowteasinghandjobs.com/members_sthj/.../scene.htm` URL in the scene editor, even though opening that URL normally requires signing in. The scraper treats it as an exact lookup key and **does not request the protected scene page**.

The public archives already link each members URL to its title, description, date, and collage. `archive_index.json` maps public members links to the correct archive. It contains URL mappings and year-range search hints, not member content, credentials, or copied scene descriptions. The initial index covers 47 public archive pages and the current updates page, with 1,654 distinct scene links as of 2026-10-26.

Known scenes require one public archive lookup. Previously unindexed scenes are checked against the current updates and newly linked archives, so new releases can work without an index update. When needed, the remaining public archives are searched with likely years first; the scene URL must still match exactly. Percent-encoded and literal spaces are normalized. Matching is never based only on a title or a filename fragment.

The archive's title, complete description, and date are returned with the fixed **Slow Teasing Hand Jobs** studio. The original members URL is first in the scene URLs; its public archive is also included for reference. Preview links and navigation are excluded from the description. Wrapped text is joined into readable paragraphs. Old Windows-1252 pages are decoded correctly.

## Higher-resolution covers from Clips4Sale

The scraper searches only the producer's public Clips4Sale store **1336**. A normalized title match, ignoring trailing resolution labels such as “High Def,” must be confirmed against the clip's description. Descriptions must match after punctuation/spacing normalization, or share the same first 200 normalized characters. Short or unrelated descriptions are rejected. At most three matching clip candidates are inspected.

For a confirmed mirror, the matched Clips4Sale URL is added to the scene URLs. The larger declared public `previewlg` image is preferred, with the declared large rectangle as an alternative. Small store thumbnails are not used. No original full-size image is invented from a filename, and no video is downloaded.

If matching or downloading fails, the original public archive collage is used. For the supplied **Luke - A Ruined Orgasm on the Cross** example, the confirmed public Clips4Sale image is **720 × 405**, compared with the archive collage's **340 × 287**. This is the larger publicly available preview found on the clip page, not a guarantee of the producer's original master image.

**The archive date and description remain authoritative.** Clips4Sale's upload date never replaces the original site date. For Luke, the returned date is **2025-12-19**.

Covers are downloaded and embedded before returning the result, so saving does not depend on another remote fetch. If neither source supplies a working image, the rest of the metadata remains available.

## Dates, caching, and matching limits

Dates come only from the archive's date headings. A folder named “2008 Sets,” an image upload year, or a Clips4Sale upload timestamp is never used to invent a date. Some early archives have no visible dates; their date field stays empty.

Parsed public metadata is cached under the container's temporary directory: current updates for one hour, archives for one day. No login cookies or images are cached. If a page temporarily fails, previously cached metadata may be reused. Cache write failures do not prevent scraping. A previously unknown URL may take longer on its first lookup; a URL absent from the public archives fails explicitly rather than receiving a guessed match.

An archive page contains many scenes, so an archive URL alone cannot identify which scene you want. Paste the linked members scene URL. This scraper does not scrape Clips4Sale URLs directly.

## Fixed performer

Every scene scrape includes **Richard Maturo**, with **Male** gender, as a user-requested fixed credit. This is a site-wide rule configured for this scraper rather than a claim extracted from each archive entry. Stash uses its normal name matching to link an existing Richard Maturo record; otherwise the scrape dialog can create one. No profile URL, StashDB identity, or local performer ID is invented. Additional performers are not inferred from titles or descriptions.

## Studio

The scraper returns **Slow Teasing Hand Jobs** and its official website. Import or link the [studio on StashDB](https://stashdb.org/studios/750d51af-3061-461c-8a93-364b1e93ade0) once on your local studio record. Returning the studio name does not create its external StashDB association.

## Verification

Tested on 2026-10-26 through an isolated official Stash v0.31.1 Docker container:

| Scene | Source | Returned date |
| --- | --- | --- |
| Luke - A Ruined Orgasm on the Cross | Archive 47 | 2025-12-19 |
| Sage Tied to the Bed | Archive 46 | 2024-12-27 |
| Peter Racked, Edged and Milked | Archive 24 | 2013-03-15 |
| Buff Straight Boy Forced to Cum Again | Archive 1 | Empty: no visible date |
| Muscular Tanner Bound and Jerked | Current updates | 2026-10-23 |

Checks covered exact scene links, original descriptions and dates, image bytes, studio matching, encoded spaces, and omission of guessed performers. Luke's returned cover was checked against the public 720 × 405 Clips4Sale preview, actually saved, and retrieved from Stash. The fixed Richard Maturo credit was subsequently checked through Stash for matching an existing performer and saving the scene relationship.

Controlled checks covered one-page indexed lookup, cache reuse, discovery of an unindexed scene on a newly linked archive, explicit failure for an unknown URL, rejection of member-page requests before networking, title-and-description verification of Clips4Sale matches, rejection of unrelated clips, and collage fallback during a store outage.

## Manual installation

Keep `SlowTeasingHandJobs.yml`, `slowteasinghandjobs.py`, and `archive_index.json` together in a `SlowTeasingHandJobs` folder under Stash's configured scraper directory, then reload scrapers. Source-manager installation handles these together and is recommended.

AGPL-3.0, consistent with the repository license.
