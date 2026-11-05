# Gentlemen's Closet

Public scene and model metadata for Stash. Python standard library only; no login, browser service, pip packages or local Stash API configuration.

Install **Gentlemen's Closet (custom)** from the existing scr4p-nonym source:

```text
https://scr4p-nonym.github.io/stash-scrapers/main/index.yml
```

## Supported URLs

- Individual scenes: `https://gentlemenscloset.com/videos/all-dressed-up-1`
- Individual models: `https://gentlemenscloset.com/models/michael-delray`

The www alias, ordinary trailing slash and tracking parameters are normalized. Listing pages, member URLs and unrelated hosts are rejected. Returned scene identity is checked against the requested slug and the publisher's Gentlemen's Closet brand. Other Ducati Studios network brands are not silently assigned this studio.

## Returned metadata

Scenes return the exact published title, canonical URL, source publication date when available, description when supplied, **Gentlemen's Closet** studio with its public URL, and explicitly credited models with their source profile URLs. Scene credits use Male and site disambiguation as the configured workflow for this site. Cast is never inferred from recommendations, navigation or title words.

The declared trailer cover is preferred, with the declared scene thumbnail as an alternative. Images are downloaded and embedded before returning, so saving does not depend on Stash fetching the CDN later. Only declared JPEG, PNG or WebP images are used. Preview videos, HLS streams, galleries and paid media are never downloaded. An image failure leaves the other metadata available.

Direct model scraping returns the published name and gender, the profile URL and site disambiguation. Biographical text is included only when actually provided. The source currently sometimes places another named model's portrait in a profile's extra images. Portraits are therefore included only when their declared filename agrees with the requested profile slug. Otherwise the photo stays empty; no replacement portrait is guessed.

**Date means publication on the current website, not independently verified original production or release.** In particular, older material may have a recent current-site publication date. Missing dates stay empty; source modification timestamps and image upload paths are not used as release dates.

Existing local studios and performers use Stash's normal matching. No installation-specific IDs, StashDB associations or API lookups are embedded. Review proposed common-name performer matches before saving.

## Catalog and matching

The private catalog collects public listing metadata at a paced interval, validates pagination and deduplicates scene identities. Titles, source dates, explicitly named cast, runtimes and canonical URLs can be used for file matching. A matching title alone is a candidate; runtime and available filename evidence are checked before ambiguous links are applied. Numbered parts and similarly named editions remain distinct.

The user's library filenames, match receipts and catalog caches are not part of this public scraper package.

AGPL-3.0, consistent with the repository license.

## Verification

Tested on 5 November 2026 in an isolated official Stash Docker container. Three live scenes (All Dressed up, In Control 4 Part 1, Gents Club Part III) returned correct individual identities, source dates and declared covers; all covers were saved and retrieved through Stash. Named credits were checked where supplied, and a scene without credits kept cast empty. Michael DelRay returned the published Male gender; an unrelated named portrait was omitted. Controlled checks reject wrong-studio records, malformed/external/listing URLs and invalid dates. The public catalog collected all 39 linked listing pages, with 687 unique identities matching the reported total.
