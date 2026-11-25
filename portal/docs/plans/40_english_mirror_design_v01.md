# English mirror design

The English mirror covers the portal and all three domains: navigation, definitions, measurements, figure captions, sources, validation and search. Korean URLs remain at their present locations; corresponding English URLs begin with `/en/`. The language selector preserves the current page, query and fragment. Original provider images, filenames, numerical results, clinical claim boundaries and licensing provenance are shared unchanged.

## Approaches

A separately copied English site would drift from the atlas. Browser translation would depend on an external service at reading time and would not provide reproducible English pages. The selected approach uses the existing Flask applications, checked-in English translation catalogs, and the same static exporter. Existing English medical names are reused. The full-site scope and `/en/` architecture were proposed in conversation and accepted by the user's clarification to translate the entire site.

## Architecture

The portal owns bilingual routing and the translation implementation. English domain instances receive a localization callback for search fields; response text is translated after canonical content is rendered. A response localizer handles interface text, accessible attributes and inline viewer data, preserving code and provider bytes. English search operates on localized content. Browser-created measurement/viewer labels use a small local dictionary. Both language trees are exported together; image and code resources stay linked to their existing canonical files where possible. No runtime translation service, keys or new dependency is required.

## Validation

Test English deep routes, Korean behavior, same-page switching with filters, English search, redirects, static links under a project path, and asset byte equality. Crawl the entire bilingual site, check all links and audit visible English text for untranslated Korean. Report any source-language text intentionally retained in code, original credits or provider images. Do not change clinical data or publish until the implementation has been verified.
