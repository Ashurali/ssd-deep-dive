# SSD Deep Dive

A standalone, bilingual (EN / 繁體中文) interactive textbook on solid-state
storage — 7 core chapters, 5 supplements, 13 interactive animations, original
figures, and a generated reference layer (glossary, formulas, quizzes).
It grew out of a study corpus written alongside《深入淺出SSD》. Built with
[MkDocs Material](https://squidfunk.github.io/mkdocs-material/), deployed to
GitHub Pages. The work in progress is planned in `TEXTBOOK_V2_PLAN.md`.

> **⚠️ THE `private/` RULE:** the book's scanned pages (PDFs / per-page
> `.jpeg` files) are **copyrighted and must never be committed.** They live
> only in `private/`, which is gitignored, and CI fails the build if any scan
> or `private/` file is ever tracked. The site references figures purely as
> page pointers ("CH4 p.22, Fig 4-19").

## Local development

```bash
pip install -r requirements.txt
python scripts/build_glossary.py   # regenerate the master glossary
python scripts/build_visual_index.py  # regenerate the visual index
python scripts/check_content.py    # content-rule report (see below)
mkdocs serve                       # http://127.0.0.1:8000/ssd-deep-dive/
```

`mkdocs build --strict` must pass before pushing — broken links (including
section anchors) fail the build, and CI runs the same command after
`python scripts/check_content.py --strict`.

Build-time hooks (`hooks/`, registered in `mkdocs.yml`):

- `acronym_links.py` links every acronym to its glossary entry.
- `inline_svg.py` inlines figures so they follow the light/dark theme.
- `reading_time.py` adds "≈ N min read" under each chapter title.

## Authoring rules (textbook v2)

These keep pages consistent when several people or sessions edit at once.
`scripts/check_content.py` checks the mechanical ones.

**Figures.** Original SVGs only, in `docs/assets/figures/<page>/<name>.svg`:
drawn from the concept and the site's own text, never traced from a scan.
Put one in a page like this:

```markdown
![Short alt text](../assets/figures/ch3/vt-bells.svg){ .sdd-fig }
/// figure-caption
What the figure shows, in a sentence or two.
///
```

- Colour with classes, never fixed hex, so one drawing serves both themes:
  `f-ink`, `f-mute` (text); `f-line`, `f-faint` (strokes); `f-panel` (box
  fill); `f-cyan`, `f-amber`, `f-violet`, `f-red`, `f-green` (tinted shapes),
  plus `-t` (text), `-l` (line) and `-b` (faint band) variants; `f-dash`.
  Keep the matching hex as a presentation attribute, so the file still looks
  right when opened on its own.
- Every SVG needs a `viewBox`, a `<title>` and a `<desc>` (the accessible
  name and description), an explicit `font-size`, and no `<style>` or
  `<script>` (inline styles would leak across the whole page).
- Phone first: a 400-unit-wide viewBox with labels of 13 units or more renders
  at least 11 px on a 375 px phone. Wider drawings take `.sdd-fig--wide`
  (they scroll sideways on phones) and need proportionally larger labels.
  The checker computes the exact floor.
- If a figure is generated, keep its generator in `scripts/figures/`, as
  `vt_bells.py` is.
- The caption's first sentence names the figure in the
  [visual index](docs/reference/visual-index.md), so make it say what the
  picture shows. Run `python scripts/build_visual_index.py` after adding or
  re-captioning a figure (CI regenerates it too).

**Key vocabulary** is a `| Term | 中文 | Meaning |` table:

- The Meaning is one sentence that ends with a link to the section that
  explains the term: `→ [§4.3.2](#432-write-amplification)`.
- The 中文 cell gives the book's term, plus the Taiwan industry term where
  they differ, as `閃存（台：快閃記憶體）`. The format uses full-width
  parentheses and 台：, because the book's own cells already put "/" between
  items (`隨機 / 順序`).
- Spell a term the same way on every page, so the glossary merges it.

**Check yourself.** Indent the answer under its question:

```markdown
3. State the map-table size rule of thumb …

    ??? success "Answer"
        2–6 sentences, with the worked numbers for calculations, ending with
        a link to the section: [§4.2.2](#422-how-mapping-works-and-the-dram-question).
```

**Acronyms** are spelled out at first use on every page, "Flash Translation
Layer (FTL)", because a reader may arrive on any page from search. Every
acronym is also listed in `includes/abbreviations.md`: one `*[FTL]: …` line
each, and nothing else, because the file is appended to every page.

**Sections and dates:**

- New sections take the next free number, so existing anchors (and the
  `formulas.md` links into them) never break.
- A dated fact says "as of 2026". It is checked against a primary source (a
  spec revision, a standards body, a vendor) while writing, and cited in the
  page's provenance note.
- When a page's v2 pass is done, add `textbook: v2` to its front matter. From
  then on, CI enforces that page's vocabulary and answers.

## Adding a new guide

1. Drop the `.md` file into `incoming/`.
2. Add an entry to the `DOCUMENTS` registry in `scripts/ingest.py`
   (destination path, short title, tags from the §6.2 taxonomy in
   `SITE_SPECIFICATION.md`, source anchor).
3. Run `python scripts/ingest.py` — it copies the file with front matter and
   demotes any stray extra H1s. Prose is never rewritten.
4. Add the page to `nav:` in `mkdocs.yml`.
5. Run `python scripts/build_glossary.py` to pick up its vocabulary table.

## Adding a new animation

1. Drop the self-contained `.html` file into `incoming/animations/`.
2. Optionally add metadata to the `ANIMATIONS` registry in
   `scripts/ingest.py` (title, tags, description, book anchor) — unknown
   files get a stub wrapper to hand-finish.
3. Run `python scripts/ingest.py`. The HTML is copied to
   `docs/animations/files/`, and a wrapper page with an embedded iframe is
   generated. Existing wrappers are never overwritten, so hand edits are
   safe. Neither are animation files already in `docs/animations/files/`:
   that copy is the one to edit, and `--overwrite-animations` replaces it
   deliberately.
   An embedded animation receives `<html data-theme="light|dark">` from the
   site (`iframe-resize.js`); define light tokens for
   `:root[data-theme="light"]` to follow the theme toggle.
4. Add the wrapper to `nav:` in `mkdocs.yml` and a card to
   `docs/animations/index.md`.

## Deployment

Pushing to `main` triggers `.github/workflows/deploy.yml`: audit → glossary →
`mkdocs build --strict` → deploy to GitHub Pages.

One-time setup after creating the GitHub repository:

1. **Settings → Pages → Source: "GitHub Actions".**
2. Update `site_url` in `mkdocs.yml` to the real Pages URL.
