# SPECIFICATION — "SSD Deep Dive" Study Site
## A searchable, indexed GitHub Pages knowledge base for my SSD study materials

**Audience of this document:** Claude Code. Implement this spec top to bottom. Where a decision is marked *(decided)*, do not revisit it; where marked *(your call)*, use judgment. Ask before deviating from any **MUST**.

---

## 1. Goal

Build a static documentation site, deployed on GitHub Pages, that hosts my complete SSD study corpus so I can re-read, search, and navigate it by topic, subtopic, and keyword. The corpus:

- **7 chapter study guides** (`SSD_Book_Ch1..Ch7_Study_Guide.md`) — English companions to the book 《深入淺出SSD》, each with section-by-section notes, worked examples, Chinese↔English vocabulary tables, self-quizzes, "Modern developments" sections, and (Ch3/Ch6/Ch7) "2nd-Edition Addendum" sections.
- **5 supplements** (`SSD_Book_Supplement_A..E_*.md`) — ECC coding theory, UFS, flash file systems, power management, aerospace storage.
- **1 figure atlas** (`SSD_Book_Figure_Atlas_Animation_Roadmap.md`) — catalog of all 359 book figures, tiered, with 10 animation-cluster build specs.
- **Interactive animations** — self-contained single-file HTML visualizations I've already built (currently: a NAND page/block/erase/write-amplification animation, a Hamming(12,8) visualizer, a tabbed BCH(15,7)+LDPC visualizer), with ~10 more planned per the atlas roadmap. Each is fully self-contained (inline SVG/CSS/JS, Google Fonts CDN only, no localStorage, respects `prefers-reduced-motion`).

Success = I can type "write amplification" or "phase tag" or "磨損平衡" into a search box and land on the right section in two clicks; I can browse Topics → FTL → Garbage Collection; and every animation runs embedded in the site looking native.

## 2. Hard constraints — read first

1. **MUST NOT commit the book's scanned pages** (the per-page `.jpeg` files or the original chapter archives) to the repository, ever. They are copyrighted material and GitHub Pages is public. The repo includes a `private/` directory in `.gitignore` where I will keep scans locally; the site references figures only as "CH4 p.22, Fig 4-19" pointers (the guides already do this).
2. **MUST NOT** hotlink, embed, or reproduce the book's figures as images. Original SVG/HTML recreations (my animations) are mine and welcome.
3. Everything else in `docs/` will be public — assume it will be read by strangers.
4. Animations **MUST** remain single-file and untouched functionally; the site wraps them, it does not refactor them.

## 3. Stack *(decided)*

**MkDocs + Material for MkDocs**, deployed via GitHub Actions to GitHub Pages.

Rationale (for the record): the corpus is already Markdown; Material ships client-side search that deep-links into page *sections* (so long guides stay searchable without splitting); the built-in `tags` plugin gives keyword indexing for free; dark theming is first-class and matches my animation design system; zero server, zero build complexity beyond `pip install`. (Considered: Docusaurus — heavier, React build for no benefit; Jekyll — weaker search; Astro Starlight — fine but more setup for the same outcome.)

Plugins/extensions to enable:
- `search` with `lang: [en, zh]` (the vocabulary tables contain Traditional Chinese terms; they must be findable — verify a search for 垃圾回收 returns the Ch4 guide; if zh tokenization proves unreliable, fall back to `separator: '[\s\-,:!=\[\]()"/]+|(?!\b)(?=[A-Z][a-z])|\.(?!\d)|&[lg]t;'` and confirm CJK terms still match as whole strings).
- `tags` (Material built-in) with a tags index page.
- `git-revision-date-localized` — "last updated" per page.
- Markdown extensions: `admonition`, `pymdownx.details`, `pymdownx.superfences`, `pymdownx.highlight`, `pymdownx.arithmatex` (KaTeX — the ECC supplement and Ch4/Ch7 have formulas; keep them rendering), `tables`, `toc` with `permalink: true`.
- `navigation.instant`, `navigation.tabs`, `navigation.sections`, `navigation.top`, `search.highlight`, `search.suggest`, `content.code.copy` features.

## 4. Repository layout *(decided)*

```
ssd-deep-dive/                      # suggested repo name; my call at creation
├── mkdocs.yml
├── requirements.txt                # mkdocs-material, plugins, pinned
├── .gitignore                      # includes: private/, site/
├── .github/workflows/deploy.yml    # build & deploy on push to main
├── private/                        # NEVER committed — book scans live here locally
│   └── README.md                   # (committed) explains what goes here and why it's ignored
├── incoming/                       # staging: I drop raw .md and .html here; ingestion consumes it
└── docs/
    ├── index.md                    # home: what this is, learning path, quick links
    ├── assets/
    │   ├── extra.css               # design-system theming (see §7)
    │   └── logo.svg                # simple original mark (generate something minimal)
    ├── core/                       # the 7 chapter guides
    │   ├── ch1-overview.md
    │   ├── ch2-controllers-afa.md
    │   ├── ch3-nand-flash.md
    │   ├── ch4-ftl.md
    │   ├── ch5-pcie.md
    │   ├── ch6-nvme.md
    │   └── ch7-testing.md
    ├── supplements/
    │   ├── a-ecc-coding-theory.md
    │   ├── b-ufs.md
    │   ├── c-flash-file-systems.md
    │   ├── d-power-management.md
    │   └── e-aerospace-storage.md
    ├── atlas/
    │   └── figure-atlas-animation-roadmap.md
    ├── animations/
    │   ├── index.md                # gallery page: card per animation
    │   ├── files/                  # the untouched self-contained .html files
    │   └── <one wrapper .md per animation>
    └── reference/
        ├── glossary.md             # AUTO-GENERATED master glossary (see §6.3)
        ├── formulas.md             # AUTO-EXTRACTED key formulas cheat sheet (see §6.4)
        ├── quizzes.md              # index linking every guide's self-quiz section
        └── tags.md                 # tags index page (Material tags plugin target)
```

## 5. Navigation & information architecture *(decided)*

Top-level tabs: **Home · Core Chapters · Supplements · Animations · Atlas · Reference**.

- One page per guide *(decided — do not split the guides into subtopic pages)*. Rationale: each guide is a coherent narrative; Material's right-hand TOC + section-level search results give subtopic access without fragmenting the reading flow. The guides' existing `##`/`###` heading structure becomes the in-page navigation — preserve it exactly.
- Home page contains: a one-paragraph description, the **learning path** (Ch1 → Ch2 → Ch3 → Ch4 → [A] → Ch5 → Ch6 → Ch7 → B–E, with the atlas as a companion), and "If you're looking for…" quick links (glossary, formulas, animations, quizzes).

## 6. Content ingestion — the real work

### 6.1 Normalize the source files
For each `.md` dropped in `incoming/`:
1. Copy to its destination path per §4 (filenames as listed).
2. Prepend YAML front matter: `title` (short form, e.g., "Ch 4 — FTL"), `tags` (per the taxonomy in §6.2), and `source_anchor` (e.g., `"CH4 file, pp. 1–72"`) as custom metadata.
3. **Do not rewrite prose.** Permitted mechanical fixes only: ensure exactly one H1; demote a stray second H1 if present; fix relative links between documents (e.g., mentions of "Chapter 4 §4.3" in one guide may optionally become intra-site links — nice-to-have, not required in v1); ensure tables render (the vocab tables are pipe tables already).
4. The emoji markers (⭐, 🏆, 📌, 📘, 🔬) are intentional signposting — keep them.

### 6.2 Tag taxonomy *(decided — apply exactly; you may ADD tags, not remove)*

Controlled vocabulary (kebab-case): `ssd-basics`, `controllers`, `all-flash-array`, `flash-physics`, `3d-nand`, `charge-trap`, `threshold-voltage`, `reliability`, `read-disturb`, `data-retention`, `endurance`, `ftl`, `mapping`, `garbage-collection`, `write-amplification`, `over-provisioning`, `trim`, `wear-leveling`, `power-loss-recovery`, `bad-blocks`, `slc-cache`, `pcie`, `tlp`, `link-layer`, `nvme`, `queues`, `prp-sgl`, `namespaces`, `nvme-of`, `zns`, `fdp`, `testing`, `fio`, `jedec`, `snia`, `ecc`, `bch`, `ldpc`, `soft-decision`, `ufs`, `writebooster`, `hpb`, `filesystems`, `f2fs`, `ext4`, `power-management`, `aspm`, `apst`, `aerospace`, `radiation`, `patents`, `bics8`, `animations`.

Assignments:
| Page | Tags |
|---|---|
| ch1 | ssd-basics, endurance, reliability, ssd form-factor topics as you see fit |
| ch2 | controllers, all-flash-array, queues, ecc |
| ch3 | flash-physics, 3d-nand, charge-trap, threshold-voltage, reliability, read-disturb, data-retention, endurance, ecc, bics8 |
| ch4 | ftl, mapping, garbage-collection, write-amplification, over-provisioning, trim, wear-leveling, power-loss-recovery, bad-blocks, slc-cache, zns, fdp |
| ch5 | pcie, tlp, link-layer |
| ch6 | nvme, queues, prp-sgl, namespaces, nvme-of, zns |
| ch7 | testing, fio, jedec, snia, power-loss-recovery |
| supp A | ecc, bch, ldpc, soft-decision, patents |
| supp B | ufs, writebooster, hpb, queues, zns |
| supp C | filesystems, f2fs, ext4, zns, garbage-collection |
| supp D | power-management, aspm, apst, pcie, nvme |
| supp E | aerospace, radiation, reliability, ecc |
| atlas | animations, plus every topic tag it touches (use judgment) |
| each animation wrapper | animations + the topics it teaches |

### 6.3 Master glossary *(build a small script — this is the keyword index the user asked for)*
Write `scripts/build_glossary.py` (run manually and in CI before build):
- Parse every guide/supplement for its "Key vocabulary" table (they all have one, consistently formatted as a two-column pipe table under a `## Key vocabulary` heading, some with 中文 column).
- Merge into `docs/reference/glossary.md`: one alphabetized table with columns **Term | 中文 (if any) | Meaning | Source page(s)** where source links to the originating guide's vocabulary section. Deduplicate identical terms; when the same term appears in multiple guides with different glosses, keep both meanings and both source links.
- This page is the site's keyword backbone: every term becomes searchable in one place, in both languages.

### 6.4 Formula sheet *(scripted or manual — your call)*
`docs/reference/formulas.md`: a one-page cheat sheet collecting the recurring formulas with one-line context and a link to the section that derives each — at minimum: WA definition, OP definition, TBW ≈ (capacity × P/E)/WA, DWPD = TBW/(365·years·capacity), map-table ≈ capacity/1000, IOPS ceiling = link BW / block size, UCL sample-size inequalities (Ch7 §7.8), Hamming/parity relations dmin↔t (Supp A). Render math with KaTeX.

### 6.5 Quiz index
`docs/reference/quizzes.md`: links to every guide's `## Check yourself` section (they all have one), grouped by chapter/supplement. No answer generation in v1.

## 7. Design *(decided)* — match my animation design system so site and animations feel like one product

Material `slate` scheme customized in `docs/assets/extra.css`:
- Background `#0b1020`; primary accent cyan `#4dd0c4`; secondary accent amber `#f2b13c`; tertiary violet `#a78bfa` (use for tags/chips).
- Fonts via Google Fonts: **Space Grotesk** for headings, **IBM Plex Sans** for body, **IBM Plex Mono** for code.
- Keep contrast accessible (WCAG AA); don't restyle Material components beyond colors/fonts/link accents; tables get subtle row striping (the vocab tables are long).
- Respect `prefers-reduced-motion` (disable `navigation.instant` prefetch animations if any conflict).

## 8. Animations integration

For every `.html` in `incoming/animations/`:
1. Copy verbatim to `docs/animations/files/<name>.html`.
2. Generate a wrapper page `docs/animations/<name>.md` from this template:

```markdown
---
title: "<Human title>"
tags: [animations, <topic tags>]
---
# <Human title>

<one-paragraph description: what it teaches, how to interact — infer from the HTML's own headings/UI text>

**Book anchor:** <figure numbers + chapter pages it realizes, if stated in the file or inferable; else omit>

[Open full-screen ↗](files/<name>.html){ .md-button }

<iframe src="files/<name>.html" width="100%" height="720" style="border:1px solid #26304d;border-radius:12px;background:#0b1020" loading="lazy" title="<Human title>"></iframe>
```

3. `docs/animations/index.md`: a card-grid gallery (Material grid cards) — title, one-liner, tags, thumbnail optional (skip thumbnails in v1).
4. Verify each animation actually runs inside the iframe on the built site (fonts load, no console errors from sandboxing). If an animation misbehaves in an iframe, fall back to the full-screen link as primary with a static note — do not modify the animation.
5. The pipeline must be **re-runnable**: when I drop a new animation into `incoming/animations/` later (10 more are planned per the atlas), one script/`make` target ingests it. Provide `make ingest` or `scripts/ingest.py`.

## 9. Search & findability — acceptance-critical behaviors

- Site-wide search returns **section-level** hits (Material default) — e.g., "phase tag" → Ch6 guide §6.3; "write amplification" → Ch4 §4.3.2 *and* the glossary *and* the sandbox animation wrapper.
- Chinese terms from vocab tables are findable (e.g., 磨損平衡 → Ch4 guide + glossary).
- Tags: clicking any tag chip lands on the tags index filtered to that tag; `docs/reference/tags.md` lists all tags with their pages.
- Every page shows a right-hand TOC and a last-updated date.

## 10. Deployment

- `.github/workflows/deploy.yml`: on push to `main` → set up Python → `pip install -r requirements.txt` → run `scripts/build_glossary.py` → `mkdocs build --strict` → deploy `site/` via `actions/deploy-pages` (or `mkdocs gh-deploy --force`; prefer the Pages-artifact flow). `--strict` so broken links fail CI.
- Repo Settings → Pages → GitHub Actions source. Document the two manual clicks I must do in the README.
- README: quickstart (`pip install -r requirements.txt && mkdocs serve`), how to add a new guide, how to add a new animation, the `private/` rule restated in bold.

## 11. Phased task plan (implement in this order; commit per phase)

1. **Scaffold** — repo, mkdocs.yml, theme + extra.css, CI workflow, `.gitignore` (with `private/`, `site/`, `incoming/` contents policy: `incoming/` committed empty with a README), home page stub. *Done when `mkdocs serve` shows a themed empty site.*
2. **Ingest documents** — normalize + front-matter + place all 13 markdown files; nav complete. *Done when every guide renders with working TOC, tables, math, emoji intact.*
3. **Reference layer** — glossary script + generated glossary, formulas page, quiz index, tags index. *Done when glossary has every vocab term with source links.*
4. **Animations** — ingestion script, wrappers for the 3 existing animations, gallery page. *Done when all three run embedded.*
5. **Polish & deploy** — search verification (English + Chinese test queries listed in §9), mobile pass, `--strict` build clean, deploy to Pages, README complete.

## 12. Acceptance checklist (verify each before calling it done)

- [ ] No file from `private/` or any book scan/`.jpeg` page image is tracked by git (`git ls-files` audit in CI is a plus).
- [ ] All 13 documents render correctly: headings, pipe tables (incl. CJK columns), KaTeX math, code blocks, emoji markers.
- [ ] Search: "write amplification", "phase tag", "doorbell", "LLR", "垃圾回收", "磨損平衡" each return sensible section-level results.
- [ ] Tag chips work; tags index lists all pages.
- [ ] Glossary is generated, alphabetized, deduplicated, source-linked.
- [ ] All animations run embedded AND via full-screen link; `prefers-reduced-motion` respected.
- [ ] CI deploys on push; `mkdocs build --strict` passes.
- [ ] Site is legible on a phone (I read on mobile at the office).
- [ ] README explains: local dev, adding a guide, adding an animation, the private/ rule.

## 13. Out of scope for v1 (backlog — do not build now)

Answer keys for quizzes; PDF export; per-figure thumbnail gallery; versioning (`mike`); comments; analytics; auto-cross-linking chapter references into hyperlinks (v1.1 candidate); dark/light toggle (dark only is fine).
