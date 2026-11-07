# BG East

Standard-library-only Stash scraper for public individual matches and wrestler profiles on bgeast.com. Install **BG East (custom)** from the custom source, or copy this entire directory into Stash's scraper directory and reload scrapers.

## Entry confirmation

BG East requires confirmation that the visitor is 21+ and accepts its cookie/privacy statement. Review that statement on the website first. Only if you agree, create bgeast-options.json beside your Stash configuration file containing:

    {"accept_entry": true}

This per-installation choice is not in the public package. The default path is ~/.stash/bgeast-options.json; BGEAST_OPTIONS_FILE can override it. No account, membership, browser-cookie export or local Stash API key is required. The scraper uses an in-memory entry session and submits the site's entry form only when this option is explicitly enabled. It does not enter the paid Arena.

## Scenes

Use an individual URL containing **both pid and match**, such as https://www.bgeast.com/catalog.php?pid=1542&match=3. Product-only URLs are rejected. The returned page's selected match must agree with the requested URL.

Scenes return product/match title, the selected match's story heading and description, studio **BG East**, explicit wrestler credits with Male gender and BG East disambiguation, and a declared action still. For named opponents without a direct link, the scraper checks the publisher's wrestler directory for a unique exact name match. Unmatched or ambiguous credits are returned without a URL. Action images are preferred over the first portrait in a caption column. A declared publisher code/VOD URL is included only when its match-number suffix agrees with the selected match.

The public match pages inspected omit release dates. The scraper returns an estimated year of **2013** for the seven releases listed as new in BG East's Catalog 97, including Motel Madness 12. This uses the publisher's archived launch page for the product IDs and a contemporary account dated January 28, 2013 for the year. [BG East Catalog 97](https://www.bgeast.com/gallery/home_archives.php?pg=cat97) · [Still-Frame Fantasies](https://sidelineland.com/2013/01/28/still-frame-fantasies-3/)

The **Missing Date** tag is returned for year-only estimates and for matches without a supported year. Dates outside the reviewed catalog stay blank. The description contains the publisher's match text.

## Wrestler profiles

Direct performer scraping accepts name-based and numeric profile URLs, including /profiles/index.php?wr_id=757, and discards navigation parameters. It returns the declared name, Male gender, BG East disambiguation, URL, explicitly labeled height and weight where present, and an optional declared profile portrait. For name-based URLs, the profile heading must match the requested name.

Image failures are optional. Only bounded public HTML and declared first-party still images are fetched. No videos, purchases, galleries or membership credentials are involved. This scraper does not establish StashDB submission eligibility.

Verified with real public fixtures and isolated official Stash Docker checks covering Undagear 23, an older Classic Spotlight match, wrestler profiles, studio/tag matching, cover/portrait persistence, optional image failure and rejection of product-only or mismatched pages. No consent file, session cookie or installation-specific IDs are distributed.

AGPL-3.0.
