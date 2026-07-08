# incoming/ — ingestion staging area

Drop raw study material here; it is **not** committed (only this README is
tracked). The ingestion pipeline consumes it:

- `incoming/*.md` — study guides / supplements / the figure atlas.
- `incoming/animations/*.html` — self-contained single-file animations.

Then run:

```bash
python scripts/ingest.py
```

The script copies each file to its destination under `docs/`, adds YAML front
matter (title, tags, source anchor) to markdown files, and generates a wrapper
page for each new animation. It is re-runnable: existing animation wrapper
pages are left untouched so hand-edited descriptions survive, and markdown
guides are re-normalized from the fresh drop.

After ingesting animations, add the new wrapper page to `nav:` in `mkdocs.yml`
and a card to `docs/animations/index.md` (the script prints a reminder).
