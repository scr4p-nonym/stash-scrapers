# BG East

Standard-library-only Stash scraper for public individual matches and wrestler profiles on bgeast.com. Install **BG East (custom)** from the custom source, or copy this entire directory into Stash's scraper directory and reload scrapers.

## Entry confirmation

BG East requires confirmation that the visitor is 21+ and accepts its cookie/privacy statement. Review that statement on the website first. Only if you agree, create bgeast-options.json beside your Stash configuration file containing:

    {"accept_entry": true}

This per-installation choice is not in the public package. The default path is ~/.stash/bgeast-options.json; BGEAST_OPTIONS_FILE can override it. No account, membership, browser-cookie export or local Stash API key is required. The scraper uses an in-memory entry session and submits the site's entry form only when this option is explicitly enabled. It does not enter the paid Arena.

## Scenes

Use an individual URL containing **both pid and match**, such as https://www.bgeast.com/catalog.php?pid=1542&match=3. Product-only URLs are rejected. The returned page's selected match must agree with the requested URL.

Scenes return product/match title, the selected match's story heading and description, studio **BG East Wrestling**, explicit wrestler credits with Male gender and BG East disambiguation, and a declared action still. For named opponents without a direct link, the scraper checks the publisher's wrestler directory for a unique exact name match. Unmatched or ambiguous credits are returned without a URL. Action images are preferred over the first portrait in a caption column. A declared publisher code/VOD URL is included only when its match-number suffix agrees with the selected match.

The public match pages inspected omit release dates. The scraper estimates the year for 46 releases from eight catalog batches using BG East's product IDs and dated launch evidence.

| Catalog | Estimated year | Evidence |
| --- | --- | --- |
| 73 | 2008 | BG East's [August homepage](https://web.archive.org/web/20080804223105id_/http://www.bgeast.com:80/home.php) shows the preceding catalog and its [September homepage](https://web.archive.org/web/20080901093915id_/http://www.bgeast.com:80/home.php) features Catalog 73, including Motel Madness 8. The [match was listed in August](https://web.archive.org/web/20080821040700id_/http://www.bgeast.com:80/catalog.php?pid=1131&match=1). |
| 87 | 2011 | [BG East launch page](https://www.bgeast.com/gallery/home/home_cat87.php) and [May 2011 coverage](https://sidelineland.com/2011/05/25/precisely-my-kink/). |
| 97 | 2013 | [BG East launch page](https://www.bgeast.com/gallery/home_archives.php?pg=cat97) and [January 2013 coverage](https://sidelineland.com/2013/01/28/still-frame-fantasies-3/). |
| 104.1 and 105 | 2014 | [June 2014 launch coverage](https://sidelineland.com/2014/06/16/hot-off-the-presses/) and [October 2014 release roundup](https://sidelineland.com/tag/lorenzo-lowe/). |
| 107 | 2015 | BG East's [January homepage](https://web.archive.org/web/20150111114543id_/http://bgeast.com:80/home.php) features the preceding catalog and the [February homepage](https://web.archive.org/web/20150208113539id_/http://www.bgeast.com:80/home.php) lists the new Catalog 107 releases. |
| 109.2 | 2015 | BG East's [catalog listing](https://www.bgeast.com/gallery/home_archives.php?pg=cat109.2) and [2015 coverage](https://sidelineland.com/2015/) of its Undagear 23 release. |
| 172 | 2023 | [BG East launch page](https://www.bgeast.com/gallery/home_archives.php?pg=cat172) and [November 2023 coverage](https://sidelineland.com/tag/bryan/). |

The **Missing Date** tag is returned for year-only estimates and for matches without a supported year. Dates outside the reviewed catalogs stay blank. The description contains the publisher's match text.

## Wrestler profiles

Direct performer scraping accepts name-based and numeric profile URLs, including /profiles/index.php?wr_id=757, and discards navigation parameters. It returns the declared name, Male gender, BG East disambiguation, URL, explicitly labeled height and weight where present, and an optional declared profile portrait. For name-based URLs, the profile heading must match the requested name.

Image failures are optional. Only bounded public HTML and declared first-party still images are fetched. No videos, purchases, galleries or membership credentials are involved. This scraper does not establish StashDB submission eligibility.

Verified with real public fixtures and isolated official Stash Docker checks covering Undagear 23, an older Classic Spotlight match, wrestler profiles, studio/tag matching, cover/portrait persistence, optional image failure and rejection of product-only or mismatched pages. No consent file, session cookie or installation-specific IDs are distributed.

AGPL-3.0.
