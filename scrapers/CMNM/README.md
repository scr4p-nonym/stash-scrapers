# CMNM.net member scraper

Supports individual CMNM.net scene parts from both the older archive and the current Now Showing player, plus clear individual subject references from the archive. Each part remains a separate scene. Uses Python's standard library only.

Install **CMNM.net (custom)** from the existing source:

```text
https://scr4p-nonym.github.io/stash-scrapers/main/index.yml
```

## Member login

A valid CMNM membership is required. Keep the login in a private file **outside the scraper directory**:

```text
/root/.stash/cmnm-credentials.json
```

Its JSON fields are `username` and `password`. Create it through your private configuration process, restrict its permissions to the Stash user (`0600` on Linux), and never upload it to GitHub or place it in the catalog's web folder. `CMNM_CREDENTIALS_FILE` can select a different path. Source-manager updates do not overwrite this file.

The helper uses CMNM's normal HTTPS login form, including its current hidden validation fields. It keeps session cookies in process memory and does not require a browser service, pip packages, or a local Stash API key. Credentials are sent only to the CMNM member login endpoint. Private member-listing titles can be cached for one hour in `cmnm-cache` beside the credential file; the cache contains no passwords or cookies.

## Scene URLs

Older parts have direct links, for example:

```text
https://members.cmnm.net/membersarea/men/session2/part1.php
https://members.cmnm.net/membersarea/men/session2/part2.php
https://members.cmnm.net/membersarea/men/session2/part3.php
```

Newer scene parts share a single player address and are selected through a form. Use **Copy URL** in the catalog to get an unambiguous scraper selector, for example:

```text
https://members.cmnm.net/membersarea/oandccms/episode-player.php?partToPlay=session195%2Fpart4
```

The scraper submits the selected scene identity using the site's normal form method. This selector is supported by the scraper; opening it directly in a browser does not select a video because the website ignores the parameter on ordinary GET requests. The catalog's **Open listing** link therefore opens Now Showing so you can select the part there. The bare player URL is rejected because it does not identify a part.

Tracking parameters are removed. The alphanumeric session identities explicitly used by the site's AI section are supported without conflating them with numbered live-action sessions. The scraper never enumerates guessed parts or fetches video downloads.

## Returned metadata

- Full scene title where supplied, with an explicit part number. Older entries that only name the subject use `Name — Part N`. Now Showing titles take priority when available for the same archived part.
- The chosen part's complete description, excluding download controls, gallery captions and site navigation. Optional year estimates append a clearly labeled source note.
- Studio **CMNM.net**, with its official site URL. The corresponding [StashDB studio](https://stashdb.org/studios/676de83f-55d2-4025-9602-6f7c3c1d93df) should be linked to your local studio record through StashDB as usual.
- Canonical scene/scraper-selector URL.
- The exact part's declared video poster, embedded for reliable saving. If unavailable, the first explicitly linked full-size gallery still is tried. Image failures do not discard the other metadata.

The inspected listings and parts supply no reliable release dates. Dates labeled **UNTIL** or **AVAILABLE UNTIL** are access-expiry dates and are never returned as release dates. Server Last-Modified headers, local file timestamps and image paths are not used to invent dates.

### Optional estimated years

To use available JPEG EXIF dates, create `cmnm-options.json` beside the private credential file:

```json
{"image_year_mode":"date"}
```

Modes are `none` (default), `notes` (append image-year evidence to the description only), and `date` (also return the estimated year in Date). The helper prefers EXIF DateTimeOriginal, falling back to the image's EXIF editing DateTime. Both remain explicitly unverified as release dates. Editing timestamps can be much later than the original filming or release; the note identifies the actual tag and timestamp used. Images without usable EXIF leave Date empty.

Date estimates use **year precision**, not an invented January 1 release date. This requires a Stash version that supports year-only dates; saving and reading back that precision was verified in the official test container. The estimate comes from the selected scene cover, before any performer portrait is downloaded.

When Date contains only a year, the scene also returns the **Missing Date** tag. Stash matches it to the existing tag by name; no installation-specific tag ID is embedded in this package. The tag marks the missing full release date, while the description retains the estimate's provenance. A full date is not given this tag by the year-estimate helper.

### Performer creation despite blank profile pages

The inspected `fullinfo.php` pages return blank responses, but their identifiers still link to named archive cards. Direct performer scraping looks up the selected card instead of relying on the blank page. Clear individual site-subject names can therefore return **name, Male gender, CMNM.net disambiguation, source reference URL**, and an optional declared archive portrait. Missing biographical facts remain empty.

Scene scraping includes an individual subject only when the card has a clear person-like name and that name is not duplicated across archived session identifiers. Group/story labels are omitted. Names in story descriptions are never used to add other actors, so this is not a complete cast list or a StashDB identity claim. Direct scraping of an explicitly selected individual reference can still work when the name is repeated.

Stash may match common first names to existing local performers. Review its proposed match; disambiguation and the reference URL alone do not guarantee a correct match. The scraper does not query your local Stash API.

## Catalog scope

The 4 November 2026 private catalog snapshot contains **283 unique parts**: 262 parts from 78 archived sessions plus 21 additional Now Showing parts. The 59 archive links also repeated on Now Showing are deduplicated. Two entries explicitly shown in the site's AI section are included. Each part is separately searchable. The snapshot covers explicitly linked parts; individual availability of every archived part has not been checked. Expiry dates are excluded, and unlinked historical material may be absent.

The catalog contains factual titles and source links, not credentials, cookies, signed media-download links, or the member-only descriptions and galleries. Catalog metadata and authenticated page caches are not distributed with this scraper package. Continuous catalog hosting does not schedule refreshes.

## Verification

Tested on 4 November 2026 in an isolated official Stash Docker container on the user's NAS. The test covers all three Todd archive parts, two distinct Jealous Footballer parts, a weekly bonus part, and an explicitly labeled AI-section part. It verifies separate titles and descriptions, fixed studio matching, omitted expiry dates and guessed cast, canonical URLs, and saving/retrieving every returned cover through Stash.

The follow-up tests created Todd from his archive reference with a saved portrait, then verified the nested subject credit and native matching to that local performer. Todd Part 1 and Jealous Footballer Part 4 returned image-year estimates with explicit EXIF source notes. Both were saved and returned with year-only precision; the database precision was also checked. Story/group names were rejected as performers.

Controlled checks cover optional image failure and rejection of unsupported, listing, bare-player, external, malformed and ambiguous URLs. Private credentials and options are mounted read-only in the test containers and are absent from the public package.

AGPL-3.0, consistent with the repository license.
