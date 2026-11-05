# UCW public archive

Initial metadata scraper for UCW products on Underground Wrestler. Standard library only; no login, browser service, pip packages or local Stash API configuration.

Example: `https://undergroundwrestler.com/products/589`.

## Initial coverage and current site limit

The first public collection response supplied 250 products on 5 November 2026. Further collection, including a later normal product-page check, returned **HTTP 429**. Live collection was stopped. This initial release uses a bundled factual snapshot of those 250 product identities rather than repeatedly requesting a rate-limited store. **It does not cover all UCW releases.** A URL absent from the snapshot fails clearly and never receives guessed metadata.

The index contains public product identity, exact title, declared match number, rounded runtime where supplied, declared image URLs, and cast tags that exactly match named links in the source's wrestler roster. It contains no purchased files, video URLs, store credentials, local filenames or private library metadata. It includes no copied product descriptions or prices.

Scenes return the published title, canonical product URL, match number as Code when supplied, **UCW** studio, and explicitly tagged performers linked through the public roster. Those performer URLs are filmography collections rather than detailed biographies. Cast names are not inferred from generic product tags, recommendations or title fragments. Scene credits use Male and UCW disambiguation as the configured workflow for this site.

The first available declared product image is embedded for reliable saving. Image failure leaves other metadata available. Only public image CDN requests are made; video previews and paid media are never fetched.

**Release dates stay empty.** The store's published/import/modified timestamps do not reliably establish original match release dates. Rounded title runtimes aid matching but are not used to fabricate dates. Descriptions absent from this factual snapshot remain empty.

Known source URLs are matched exactly. Tracking parameters and the www alias are normalized; collection pages, external hosts and malformed paths are rejected. Source updates can later expand the bundled catalog. There is no automatic live crawl on each scrape.

Install **UCW (public archive)** from the existing scr4p-nonym scraper source. Keep `UCW.yml`, `ucw.py`, `public_index.json` and this README together when installing manually.

AGPL-3.0, consistent with the repository license.

## Verification

Tested on 5 November 2026 in an isolated official Stash Docker container. Products 589 and 200 returned exact match codes, canonical URLs, roster-confirmed cast and no invented release dates. Both declared covers were saved and retrieved through Stash. The tests used the factual bundled snapshot and image CDN only, with no requests to the rate-limited store. Controlled checks cover image failure, unknown products, generic non-performer tags, malformed/external/listing URLs and tracking normalization.
