# QueerClick

Install **QueerClick (custom)** from your existing scraper source, then scrape an individual QueerClick post URL in a Stash scene. For example:

`https://www.queerclick.com/qc/2019/07/all-australian-boys-steve.php`

It returns the original post title, complete main description with paragraph breaks, QueerClick publication date, canonical post URL, and an optional embedded cover image. The article's real lazy-loaded image is preferred to its small social thumbnail. Navigation, author details, comments, related posts, advertisements and the short trailing “Head over to” affiliate prompt are excluded.

**The Date field is the QueerClick post's publication date. It does not establish the scene's original release date.** For the Steve example it is **2019-07-04**. The later 2022 modification timestamp is ignored. If no full publication date is available, the field stays empty; no day is invented from the year/month in a URL or image path.

The studio is returned only when the post has a single explicit **Visit [studio]** producer link. QueerClick is not used as a default studio. Known labels such as `AllAustralianBoys` are normalized to **All Australian Boys**, allowing Stash to match an existing local studio. Affiliate redirects are not followed or treated as official studio URLs. Multiple different studio links leave the studio field empty.

Performer names are not guessed from titles, blog authors, taxonomy tags or story characters. This is a scene metadata scraper; it does not scrape individual models.

## Installation and Docker

Update your existing source in Stash's **Settings → Metadata Providers**, install **QueerClick (custom)**, and reload scrapers if needed. The source URL remains:

`https://scr4p-nonym.github.io/stash-scrapers/main/index.yml`

The helper uses Python's standard library only, available in the tested official Stash Docker image. No additional container, pip dependencies, browser service, login, or local API configuration is required. Review the returned fields before applying and saving, especially when you already know the scene's original release date.

For a manual installation, copy this entire folder into Stash's configured scraper directory and reload scrapers.

## Verification

Tested on 26 October 2026 in a temporary, isolated official **Stash v0.31.1** Docker container with a separate database:

| Public post | Publication date | Studio | Description paragraphs |
| --- | --- | --- | --- |
| All Australian Boys: Steve | 2019-07-04 | All Australian Boys | 2 |
| Cocky Boys: Chris Loan Fucks Alam Wernik – Bareback | 2019-07-04 | CockyBoys | 4 |
| Men.com: Josh and Tiago Santana – “The Girthy Farmer” | 2026-10-26 | Men.com | 5 |

The Steve result matched an existing local All Australian Boys studio associated with StashDB. Its title, date, description and 600×1770 article cover were saved; Stash successfully served the persisted image. All three posts returned full-size article images rather than 250-pixel social thumbnails, with no guessed cast.

Controlled checks cover missing images/publication dates, ignored modification dates, structured and visible post-date fallbacks, ambiguous studios, wrapped content, paragraph breaks, exclusion of authors/tags/ads, and rejection of category/archive/external URLs.

Only the selected public post and optional still image are requested. Video embeds, original studio websites and member content are not fetched. Failed image downloads do not discard the other metadata. AGPL-3.0.
