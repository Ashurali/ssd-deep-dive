# private/ — local-only book material

This directory holds the **copyrighted scans of《深入淺出SSD》** (per-chapter PDFs
and any per-page `.jpeg` exports). It exists so the study guides' page
references ("CH4 p.22, Fig 4-19") can be checked against the originals locally.

**Nothing in here may ever be committed or published.** The repository's
`.gitignore` excludes everything in this directory except this README, and CI
audits `git ls-files` on every push to make sure no scan sneaks in.

If you clone this repo on a new machine, copy your local scans back into this
folder; the site itself never needs them.
