# Bentley Race

Standard-library-only Stash scraper for public video/BTS posts and model references on bentleyrace.com. No account, Python dependencies or local Stash API setup is required.

Install **Bentley Race (custom)** from the custom source, or copy this entire directory into Stash's scraper directory and reload scrapers. Scene URLs use a single post slug; performer URLs use /model/<slug>. Tracking parameters are discarded.

Scenes return the post title, public description, numeric publisher post ID, declared cover, studio **Bentley Race**, and models explicitly linked by that scene. Cast includes Male gender, Bentley Race disambiguation and model reference URLs. Generic keyword tags are not interpreted as people.

The displayed header date takes precedence over machine-readable publication timestamps, which can differ by one day due to the site's timezone. If the visible date is absent, a valid explicitly declared publication timestamp is used. Missing dates return the **Missing Date** tag without adding any description note. Image paths, footer years and file timestamps are never release dates.

The cover prefers the declared desktop preview image, followed by the Open Graph image. Images are optional; failures preserve the other metadata. Videos, galleries and member pages are not fetched.

Direct model scraping returns name, Male gender, disambiguation and URL. A portrait is included only if the model page explicitly links that model's own portrait. The inspected Kell Fuller archive has none, so its photo remains empty. Scene covers and other models' pictures are never substituted.

Photo-gallery-only posts, listing pages and wrong scene identities are rejected. The current website's publication date is not independent evidence of filming date. No installation-specific IDs or StashDB identities are hardcoded.

Verified with public HTML fixtures, wrong-page/invalid-URL cases, optional image failure, and an isolated official Stash Docker instance. Integration checks cover recent and 2012 scenes, studio matching, explicit cast, model references and cover saving/retrieval.

AGPL-3.0.
