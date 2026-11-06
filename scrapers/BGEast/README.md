# BG East

Standard-library-only Stash scraper for public individual matches and wrestler profiles on bgeast.com. Install **BG East (custom)** from the custom source, or copy this entire directory into Stash's scraper directory and reload scrapers.

## Entry confirmation

BG East requires confirmation that the visitor is 21+ and accepts its cookie/privacy statement. Review that statement on the website first. Only if you agree, create bgeast-options.json beside your Stash configuration file containing:

    {"accept_entry": true}

This per-installation choice is not in the public package. The default path is ~/.stash/bgeast-options.json; BGEAST_OPTIONS_FILE can override it. No account, membership, browser-cookie export or local Stash API key is required. The scraper uses an in-memory entry session and submits the site's entry form only when this option is explicitly enabled. It does not enter the paid Arena.

## Scenes

Use an individual URL containing **both pid and match**, such as https://www.bgeast.com/catalog.php?pid=1542&match=3. Product-only URLs are rejected. The returned page's selected match must agree with the requested URL.

Scenes return product/match title, the selected match's story heading and description, studio **BG East**, explicit wrestler profile links with Male gender and BG East disambiguation, and a declared action still. Opponents explicitly named in the match's A-vs.-B credit line are included even without a profile; their URLs remain empty rather than guessed. Names are never extracted from story prose or keywords. Action images are preferred over the first portrait in a caption column. A declared publisher code/VOD URL is included only when its match-number suffix agrees with the selected match.

The inspected public match pages do **not** declare release dates. The date stays blank and the **Missing Date** tag is returned. Copyright years, product IDs, runtime, file dates and image paths are not release dates. No date-source or estimate note is added to the description.

## Wrestler profiles

Direct performer scraping accepts /profiles/index.php?wrestler=<name>, discarding navigation parameters. It returns declared name, Male gender, BG East disambiguation, URL, explicitly labeled height/weight where present and an optional declared profile portrait. The profile heading must match the requested wrestler name.

Image failures are optional. Only bounded public HTML and declared first-party still images are fetched. No videos, purchases, galleries or membership credentials are involved. This scraper does not establish StashDB submission eligibility.

Verified with real public fixtures and isolated official Stash Docker checks covering Undagear 23, an older Classic Spotlight match, wrestler profiles, studio/tag matching, cover/portrait persistence, optional image failure and rejection of product-only or mismatched pages. No consent file, session cookie or installation-specific IDs are distributed.

AGPL-3.0.
