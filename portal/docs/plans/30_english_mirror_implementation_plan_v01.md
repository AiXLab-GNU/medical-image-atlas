# English Mirror Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. Track checked steps below; translate independent catalogs in parallel under superpowers:dispatching-parallel-agents.

**Goal:** Mirror the whole atlas in English at `/en/` while retaining Korean pages and shared source artifacts.
**Architecture:** Portal-owned localization, localized domain content and bilingual static export.
**Tech Stack:** Existing Python/Flask/Jinja, standard-library HTML parser, JSON catalogs and JavaScript.
**Spec:** [English mirror design](40_english_mirror_design_v01.md)

## Global Constraints

- Shared provider bytes, numerical results, source citations and license restrictions remain canonical.
- English is generated deterministically from checked-in translations; no runtime external translator.
- Follow repository ownership and file naming; plans belong in `portal/docs/`.
- Work in the requested checkout. Do not create commits or deploy during feature implementation.

## Review Focus

- Two app instances must not share mutable mounted-language state.
- English deep-link switches retain query strings and anchors.
- English definition searches and browser-created labels remain English.
- Static English pages work below a GitHub Pages project prefix.
- Code downloads and provider-image bytes must not be translated.

## Tasks

- [x] 1. Write tests for English routes, language switches, redirects, search and asset equality. Observe failure before implementing.
- [x] 2. Add portal `localization.py`, English JSON catalogs and a small client dictionary. Localize domain content through a config callback; keep existing standalone apps supported.
- [x] 3. Extend the exporter and static browser search to cover both languages; write failing static tests first.
- [x] 4. Translate all visible text, reuse English medical names and audit every page for remaining Korean prose. Independent domain catalog translation may run in parallel.
- [x] 5. Run all web/registry/measurement tests, bilingual export and complete link audit. Review the diff independently and fix demonstrated defects.
- [x] 6. Update README, STATUS and rebuild/localization documentation with exact validation evidence and remaining limits.

## Progress

Baseline: clean checkout at 5ede8b4. Existing portal/static and domain web suites: 47 tests passed in the preceding task.

Ruling: Render canonical Korean content before translating visible response text; translate search fields and inline viewer JSON separately. This avoids using translated labels as internal grouping keys and lets full-sentence translations retain their grammar. Numerical results, data identifiers and provider bytes are unchanged.

Final verification: 104 tests passed (portal 35, domain registry/catalog 30, domain web 39). Bilingual export produced 1,688 pages, with 844 English pages, zero missing links and zero untranslated visible strings including generated SVGs. Chromium QA passed six checks each for the dynamic site and the static `/site/` deployment, with no page/network errors. The independent review's proxy path, static query, SVG validator/range and HEAD findings were covered by failing regression tests and fixed; no deferred findings introduced by this feature remain. No commits or public deployment were performed.

Static error handling: added an English `en/404.html` and an English-aware GitHub Pages fallback page; static export tests cover the English error page.
