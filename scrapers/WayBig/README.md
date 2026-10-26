# WayBig

Install **WayBig (custom)** from your existing scraper source, then scrape an individual WayBig blog post URL in a Stash scene. Example:

`https://www.waybig.com/blog/2007/05/17/dex-mcgregor-returns-randyblue/`

It returns:

- The original post title.
- Main post text with paragraphs, quotations and headings preserved.
- The blog publication date, ignoring later modification timestamps and sidebar dates.
- The canonical post URL, without tracking parameters or comment fragments.
- An optional embedded still image: the declared social cover, falling back to the largest declared version of the first article image.

**The Date field is the WayBig post date, not a verified original scene release date.** The Dex McGregor example returns **2007-05-17**; its 2010 modification timestamp is ignored. Missing publication dates remain empty. Dates are not inferred from image paths or recent/recommended posts.

Studio and performer fields are not assigned. Names in a headline, blog authors, category tags and advertisements do not create studio or cast credits. Keep or select your existing studio and performers when reviewing the scrape.

The main description excludes advertising widgets, related posts, navigation and link-only “Watch/Visit/Join” prompts. Quoted producer descriptions remain intact, including the attribution when present. Embedded video players and affiliate destinations are not fetched.

## Installation and Docker

Update your existing source in **Settings → Metadata Providers**, install **WayBig (custom)**, and reload scrapers if needed. The source remains:

`https://scr4p-nonym.github.io/stash-scrapers/main/index.yml`

No login, extra Docker container, pip packages, browser service or local API configuration is needed. The helper uses the Python standard library included in the tested official Stash Docker image. For manual installation, copy this whole folder into Stash's configured scraper directory and reload scrapers.

## Verification

Tested on 26 October 2026 in a temporary, isolated official **Stash v0.31.1** Docker container with a separate database:

| Post | Publication date | Main text blocks |
| --- | --- | --- |
| RandyBlue: Dex McGregor Returns | 2007-05-17 | 2 |
| Freshmen.net: Newcomer Asher Masters Bottoms for Hudson Malone | 2026-10-01 | 6 |

Both live posts returned complete main text, correct dates, clean URLs and valid covers with no studio/cast assignment. The Dex result's text, date and 500×669 cover were saved to an existing test scene while retaining its studio; Stash successfully served the persisted image.

Controlled checks cover missing images/dates, ignored modification/sidebar dates, structured and published-time date fallbacks, quoted text, excluded ads/CTAs, image-download failure and fallback to the largest declared article image, and rejection of category/archive/external URLs. Image failure does not discard the other metadata. AGPL-3.0.
