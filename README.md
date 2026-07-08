# SSD Deep Dive

A searchable, indexed study site for the《深入淺出SSD》corpus — 7 chapter
study guides, 5 supplements, a figure atlas, and interactive animations.
Built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/),
deployed to GitHub Pages.

> **⚠️ THE `private/` RULE:** the book's scanned pages (PDFs / per-page
> `.jpeg` files) are **copyrighted and must never be committed.** They live
> only in `private/`, which is gitignored, and CI fails the build if any scan
> or `private/` file is ever tracked. The site references figures purely as
> page pointers ("CH4 p.22, Fig 4-19").

## Local development

```bash
pip install -r requirements.txt
python scripts/build_glossary.py   # regenerate the master glossary
mkdocs serve                       # http://127.0.0.1:8000/ssd-deep-dive/
```

`mkdocs build --strict` must pass before pushing — broken links (including
section anchors) fail the build, and CI runs the same command.

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
3. Run `python scripts/ingest.py` — the HTML is copied verbatim to
   `docs/animations/files/` and a wrapper page with an embedded iframe is
   generated (existing wrappers are never overwritten, so hand edits are
   safe).
4. Add the wrapper to `nav:` in `mkdocs.yml` and a card to
   `docs/animations/index.md`.

## Deployment

Pushing to `main` triggers `.github/workflows/deploy.yml`: audit → glossary →
`mkdocs build --strict` → deploy to GitHub Pages.

One-time setup after creating the GitHub repository:

1. **Settings → Pages → Source: "GitHub Actions".**
2. Update `site_url` in `mkdocs.yml` to the real Pages URL.
