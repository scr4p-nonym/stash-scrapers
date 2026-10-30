# See Him Solo performer companion

Install **See Him Solo (performers)** from the scr4p-nonym source:

```text
https://scr4p-nonym.github.io/stash-scrapers/main/index.yml
```

For scenes, install **MojoHost** from Community (stable). MojoHost already supports `seehimsolo.com/trailers/`; this companion only handles individual performer profiles and adds no scene scraper, so both can be installed together.

## Use

On a performer, scrape an individual profile URL such as:

```text
https://seehimsolo.com/models/NadeNasty.html
```

The helper returns the published name, Male gender, See Him Solo disambiguation, birthdate, ethnicity, metric height/weight/penis length, circumcision status, tattoos, piercings, and hair/eye colour when explicitly supplied. It adds the profile URL and explicit external profile/social links. Additional biography, birthplace, shoe size, girth and fun facts are retained in Details when present. No attributes are estimated from pictures, names, or ages. Empty or unknown fields stay empty.

The actual profile portrait is downloaded using the largest declared version, with smaller declared versions as fallbacks. Older `src` portraits respect the page's base URL. A validated image is embedded in the scrape result; an unavailable portrait does not prevent other metadata from being returned. Logos and scene previews are not substituted for missing portraits.

`https://seehimsolo.com/models/1/latest/?g=m` is a model directory for browsing. Open an individual profile before scraping; directory pages are intentionally rejected. Profile spelling and case are preserved, and tracking queries/fragments are removed.

The standard-library Python helper needs no pip packages, login, browser service, or local Stash API configuration. Python is included in the official Stash Docker image used for testing. Disambiguation does not force Stash to distinguish same-name performers; review existing matches before saving.

## Scene dates

The existing MojoHost scene scraper returns the site's current Date Added. For the supplied `see-nade-nasty-solo.html` page, it returns **2023-08-04**, while the description explicitly says **Re-release from 2020-05-08**. The performer companion does not change that scene behavior. Choose the date appropriate to the scene version being catalogued.

## Verification

Tested 2026-10-30 with the official Stash v0.31.1 Docker image in an isolated temporary instance:

- Nade Nasty: published stats, five explicit profile URLs, complete fun facts, Male gender, disambiguation, and 1875 x 2490 portrait. Fields and portrait persisted through performer creation.
- Billy Raw: published stats including Uncut status and 1875 x 2490 portrait.
- Charles Neptune: genuine 625 x 830 `src` portrait and name; unavailable stats and biography remained empty.
- Original MojoHost scene scraper still selected for the supplied trailer; title, date, description, performer and studio returned; cover saved successfully.
- Directory, scene, and external URLs rejected; controlled image failure left metadata usable; hair/eye colour absent in the inspected profiles remained unset.

Runtime code is AGPL-3.0, following the existing custom scraper helpers.
