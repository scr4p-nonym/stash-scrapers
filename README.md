# Stash scrapers

Custom URL metadata scrapers for [Stash](https://github.com/stashapp/stash).

## Install

In Stash, open **Settings → Metadata Providers**, add a scraper source named **scr4p-nonym** with this URL, and install **CumClub (custom)** from that source:

```text
https://scr4p-nonym.github.io/stash-scrapers/main/index.yml
```

Scraper updates are distributed through the same source. No extra Docker container, Python installation, or browser service is needed.

## CumClub

Paste a scene URL from `cumclub.com/cc/` into a Stash scene's URL field and click the URL scrape button. Review the returned fields before applying and saving them.

The scraper extracts:

- Title and canonical source URL.
- Full description with paragraph breaks, excluding the gallery and sharing widgets.
- The actual backdrop image, retaining its existing resolution suffix.
- Publication date from `article:published_time`, falling back to a semantic publication `<time>` element.

Modification timestamps are ignored. Publication date means the site's page publication date; it does not independently establish an original scene release date. The calendar date is retained as written in the selected timestamp.

If no publication date exists, the date stays empty. An optional approximate fallback can be enabled by setting `allowApproximateImageDate = true` in the YAML. It converts an image upload path such as `/wp-content/uploads/2019/01/` to `2019-01-01`. The day is assumed and the upload month may differ from release month. Updates from the source can overwrite local edits.

### Verification

Tested on 2026-10-17 in an isolated official Stash v0.31.1 Docker container. Three live scene pages passed checks for the complete description, title, canonical URL, publication date, and exact backdrop image bytes:

| Page slug | Publication date | Description paragraphs | Description characters |
| --- | --- | --- | --- |
| `thick-cock-thick-load-swallowed` | 2019-01-13 | 8 | 1,640 |
| `pov-service` | 2019-01-08 | 9 | 1,462 |
| `big-cock-fucker` | 2019-01-18 | 9 | 1,546 |

The optional approximate-date branch is disabled by default and was not exercised by these three live-page tests.

## Development

Scrapers live in `scrapers/`. The publishing workflow builds the source index and ZIP packages with the official [scrapers-repo-template](https://github.com/stashapp/scrapers-repo-template) build script, then deploys to GitHub Pages. Contributions to the official [CommunityScrapers](https://github.com/stashapp/CommunityScrapers) repository are reviewed separately by its maintainers.

## License

AGPL-3.0. See [LICENCE](LICENCE). The source publishing script and workflow originate from the official Stash scraper repository template.
