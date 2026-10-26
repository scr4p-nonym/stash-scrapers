# Stash scrapers

Custom URL metadata scrapers for [Stash](https://github.com/stashapp/stash).

## Install

In Stash, open **Settings → Metadata Providers**, add a scraper source named **scr4p-nonym** with this URL, and install the desired scrapers from that source:

```text
https://scr4p-nonym.github.io/stash-scrapers/main/index.yml
```

Scraper updates are distributed through the same source. No extra Docker container, Python installation, or browser service is needed.

## CumClub

Paste a scene URL from `cumclub.com/cc/` into a Stash scene's URL field and click the URL scrape button. Review the returned fields before applying and saving them.

The scraper extracts:

- Title and canonical source URL.
- Studio: **CumClub**, with its official site URL.
- Full description with paragraph breaks, excluding the gallery and sharing widgets.
- The actual backdrop image, retaining its existing resolution suffix.
- Publication date from `article:published_time`, falling back to a semantic publication `<time>` element.

Modification timestamps are ignored. Publication date means the site's page publication date; it does not independently establish an original scene release date. The calendar date is retained as written in the selected timestamp.

### Studio matching

The scraper returns the studio name **CumClub**. Stash matches that to an existing local studio by name or alias. If no local entry exists, create or import the studio once and select it when applying the scrape.

The corresponding [StashDB studio](https://stashdb.org/studios/28c633bf-a45e-4643-a26d-a25558a430eb) has ID `28c633bf-a45e-4643-a26d-a25558a430eb`. That external ID belongs on the local studio record as a StashDB association; the YAML scraper does not set it. Importing the studio from StashDB is the usual way to establish the association. Performer extraction is intentionally omitted.

If no publication date exists, the date stays empty. An optional approximate fallback can be enabled by setting `allowApproximateImageDate = true` in the YAML. It converts an image upload path such as `/wp-content/uploads/2019/01/` to `2019-01-01`. The day is assumed and the upload month may differ from release month. Updates from the source can overwrite local edits.

### Verification

Tested on 2026-10-17 in an isolated official Stash v0.31.1 Docker container. Three live scene pages passed checks for the complete description, title, canonical URL, publication date, and exact backdrop image bytes:

| Page slug | Publication date | Description paragraphs | Description characters |
| --- | --- | --- | --- |
| `thick-cock-thick-load-swallowed` | 2019-01-13 | 8 | 1,640 |
| `pov-service` | 2019-01-08 | 9 | 1,462 |
| `big-cock-fucker` | 2019-01-18 | 9 | 1,546 |

The optional approximate-date branch is disabled by default and was not exercised by these three live-page tests.

Studio assignment was also verified on all three pages, and a further test confirmed automatic matching to an existing local CumClub studio carrying the StashDB ID above.

## The Full English

Scene URL scraping and direct model-profile scraping are available in **The Full English (custom)**. It returns the scene description, cover image, publication date when available, fixed studio, and site performers whose profiles explicitly list the requested scene URL. No StashDB performer identities are guessed.

The helper uses Python's standard library only. Python is included in the official Stash Docker image tested here; no pip packages, browser service, or login are needed. See the [scraper instructions and test results](scrapers/TheFullEnglish/README.md) for matching limitations, caching, and installation details.

## My Best Friend's Dad

**My Best Friend's Dad (custom)** supports scene URLs and direct model-profile URLs. It returns full descriptions, cover images, publication dates when available, the fixed studio, and performers whose profiles explicitly list the scene URL. Models include Male gender, site disambiguation, and optional embedded portraits. It uses Python's standard library with no local API configuration.

See the [scraper instructions and test results](scrapers/MyBestFriendsDad/README.md).

## Island Studs

**Island Studs (custom)** supports scene URLs and model-profile URLs. It returns descriptions, publication dates, covers, the fixed studio, and performers explicitly credited in the scene's Featuring section. Models include Male gender, Island Studs disambiguation, and optional embedded portraits. Recommended-scene cast links are excluded. No local API configuration is required.

See the [scraper instructions and test results](scrapers/IslandStuds/README.md).

## My Friends Feet

**My Friends Feet (custom)** supports scene URLs and individual model-directory URLs. It returns full descriptions, embedded covers, publication dates when an exact dated listing is available, the fixed studio, and performers explicitly linked in the main scene credits. Models include Male gender, site disambiguation, and optional embedded portrait choices. Affiliate tracking is removed from identity URLs. No local API configuration is required.

See the [scraper instructions and test results](scrapers/MyFriendsFeet/README.md).

## Film911

**Film911 (custom)** supports individual scene URLs with full descriptions, embedded covers, dates, and the fixed studio. Explicit purchase links are included as additional scene URLs. Alternate title layouts are supported, and display labels are removed. Performer names are not inferred from titles or fictional characters because the inspected pages have no reliable actor-profile credits.

See the [scraper instructions and test results](scrapers/Film911/README.md) for release-date handling and fallback behavior.

## Slow Teasing Hand Jobs

**Slow Teasing Hand Jobs (custom)** accepts individual members scene URLs and finds their metadata through exact links in public archives. It never requests protected scene pages. Original archive dates and descriptions are preserved; a confirmed mirror in the producer's Clips4Sale store can supply a larger public cover image. Every scene scrape also includes Richard Maturo as a user-requested fixed performer credit. An included URL-to-archive index and temporary metadata cache keep lookups efficient, while current updates and new archive links support future scenes without credentials.

See the [scraper instructions and test results](scrapers/SlowTeasingHandJobs/README.md).

## Beefcake Hunter

**Beefcake Hunter (custom)** supports individual scene URLs and public model-category URLs. It returns full public descriptions, publication dates, embedded covers, the fixed studio, and verified guest models. Every scene includes Victor with Beefcake Hunter disambiguation and Male gender. Public model cards provide an optional portrait snapshot; newer guest credits require the exact scene URL on the model's category page. No login or local API configuration is required.

See the [scraper instructions and Docker test results](scrapers/BeefcakeHunter/README.md).

## All Australian Boys

**All Australian Boys (custom)** supports individual public sex-scene/solo preview URLs and verified teaser-page URLs. It returns the main description, embedded cover, fixed studio and explicitly named model with Male gender and optional embedded portrait. Scene labels retain the exact URL identifier because the site reuses first names; model disambiguation retains that identifier too. Missing release dates stay empty. The catalog covers linked public previews; older join-only directory thumbnails are excluded.

See the [scraper instructions and Docker test results](scrapers/AllAustralianBoys/README.md).

## QueerClick

**QueerClick (custom)** transfers metadata from individual dated QueerClick posts: the original title, main description, canonical source URL, optional embedded article image, and the blog's publication date. It assigns a studio only from an explicit, unambiguous producer link and does not guess performers. The post date is not proof of the scene's original release date; modification timestamps are ignored. No login or local API configuration is required.

See the [scraper instructions and Docker test results](scrapers/QueerClick/README.md).

## Development

Scrapers live in `scrapers/`. The publishing workflow builds the source index and ZIP packages with the official [scrapers-repo-template](https://github.com/stashapp/scrapers-repo-template) build script, then deploys to GitHub Pages. Contributions to the official [CommunityScrapers](https://github.com/stashapp/CommunityScrapers) repository are reviewed separately by its maintainers.

## License

AGPL-3.0. See [LICENCE](LICENCE). The source publishing script and workflow originate from the official Stash scraper repository template.
