# Textbook v2 — the big fix (plan)

> Status: **Phases 0–1 done; Phase 2 under way, with Ch 1–4 done (23 Nov 2026).** Work is
> committed and pushed on the `textbook-v2` branch; fast-forwarding `main` to it publishes the live
> site (last published after the Ch 1 pilot). Next: the rest of Phase 2, then Phases 3 and 4.

## Context

A review of the site (Nov 2026) found that the writing is strong, but four things hold it back as a
textbook for someone new to SSDs:

- **Phones:** 10 of the 13 animations render their labels at 3–4.5 px on a 375 px phone.
- **Visuals:** there is not one still diagram in the 12 pages. The 24 animation embeds are all
  collapsed, and Supplements B–E have only ASCII art.
- **Beginners:** acronyms are never expanded (ASIC, MOSFET, AXI, PLL, MSI-X, FUA); DMA is used
  four chapters before it is defined. There is no start-here page and no prerequisites. 199 of
  322 glossary entries are translations with no meaning, and none of the 137 quiz questions has
  an answer.
- **Coverage:** these topics are missing: security and sanitize, the firmware lifecycle, the host
  software stack, data-center drives, and board-level hardware. The history and market sections
  stop at 2016–2018, and 3D XPoint is still described as current.

You asked for real fixes rather than workarounds. These decisions are made:

| Decision | Choice |
|---|---|
| Quiz answers | A hidden answer under every question (reverses the "no answer key" backlog rule) |
| New topics | All four, as Supplements F, G, H, I |
| 中文 terms | The book's term plus the Taiwan industry term where it differs, written 閃存（台：快閃記憶體） |
| Animations | Edited for phone layout and light mode. This relaxes the CLAUDE.md rule "never modify an animation", replacing the wrapper-only workaround. |

**Outcome:**

- A reader can start from zero (Chapter 0).
- Every key idea has a picture, and every term has a definition.
- Every question has an answer.
- Every animation works on a phone in both themes.
- The missing topics exist.

## Order of work

0. **Quick fixes** ✅
1. **Shared foundations** ✅ Everything after this depends on it.
2. **Page passes** (Phase 2), **new pages** (Phase 3) and **animations** (Phase 4) form three
   independent tracks. They touch separate files, so once Phase 1 lands they can run as parallel
   sessions.
5. **Integration and verification**.

Shared files (`mkdocs.yml`, `extra.css`, `includes/abbreviations.md`, `reference/*`, `index.md`) are
edited only in Phases 0, 1 and 5. Page sessions report anything those files need instead of editing
them.

## Phase 0 — Quick fixes ✅ done

Results:

- **Theme**: the site follows an OS switch after a reload, and the toggle cycles system → light → dark.
- **Glossary search**: the preview for 磨損平衡 / 垃圾回收 is now 235–385 px (it was about
  7,800 px), and Ch 4 ranks first.
- **Atlas**: it moved under Reference and got a *full* voice pass, not just the intro. It still held
  personal, mentor-to-intern references to the author's own work, which are now gone.
- **Acronyms**: 253 entries, all of them in tooltips. They work on hover, and on tap at phone width.
  The underline is kept faint because Ch 2 alone has 338 of them.
- **Home page**: all 9 learning-path steps show on a phone.
- `mkdocs build --strict` is clean. CLAUDE.md and AGENTS.md are updated.

| # | Fix | Files |
|---|---|---|
| 0.1 | The theme follows the OS on every visit: a three-state toggle (auto → light → dark) | `mkdocs.yml` |
| 0.2 | Glossary has one entry per term. The generator emits A–Z sections, each term an `###` entry with its own anchor, a letter jump bar, no TOC, and no search boost, so a search previews one term instead of about 7,800 px. It also accepts the new 3-column vocabulary tables, so Phase 2 can fill them in. | `scripts/build_glossary.py` |
| 0.3 | Atlas moves from a top-level tab into Reference, and its mentor-voice intro and headings are rewritten | `mkdocs.yml`, `docs/atlas/…` |
| 0.4 | Acronym tooltips on every page: `abbr`, plus `pymdownx.snippets` auto-append of `includes/abbreviations.md`, plus `content.tooltips` | `mkdocs.yml`, `includes/` |
| 0.5 | Home page on phones: the learning path shows all steps as a vertical list, and the hero's empty band is removed | `docs/assets/extra.css` |

These earlier quick fixes are dropped because the real fixes replace them:

- Wrapper-only animation scaling: Phase 4 fixes the animations themselves.
- "Open the key animations by default": decided page by page in Phase 2, once each animation has a
  still figure next to it.
- Clipped ASCII art: replaced by figures in Phase 2.

## Phase 1 — Shared foundations ✅ done

Results:

- **Acronym → glossary links** (added at your request):
  - Every acronym links to its glossary entry, about 330 a page in Ch 2.
  - Desktop: hover shows the expansion; a click opens the entry.
  - Touch: the first tap shows the expansion with a "tap again" hint; the second tap opens the
    entry.
  - The glossary highlights the entry you landed on, and a "← Back to …" button returns you to the
    exact scroll position.
  - The glossary now has an entry for every acronym: 457 entries. 60 acronyms join the term that
    names them, and the rest get entries of their own.
  - The strict build validates every acronym link. A deliberately broken anchor failed the build
    as it should.
- **Figure system**:
  - The Vt-bells prototype is live in Ch 3 §3.1.2 and switches with the theme.
  - Labels are 11.1 px on a 375 px phone.
  - The diagram labels are kept out of search; the numbered caption stays searchable.
- **Reading time** appears under every chapter and supplement title.
- **Animation contract**:
  - Embeds receive `data-theme`.
  - All 37 iframes use the `.sdd-anim` class.
  - `ingest.py` no longer overwrites edited animations.
- **`scripts/check_content.py`** runs in CI. It is clean today, and its report is the to-do list
  for Phase 2.
- **Docs**: README "Authoring rules", CLAUDE.md and AGENTS.md (kept in sync), and amendments in
  SITE_SPECIFICATION.md.

What was planned:

1. **Figure system.**
   - Original SVGs go in `docs/assets/figures/<page>/<name>.svg`. They are drawn from the concept
     and the site's own text, never traced from the scans.
   - Author them as `![alt](../assets/figures/ch3/vt-bells.svg){ .sdd-fig }`, followed by a
     `/// caption` block (`pymdownx.blocks.caption` is installed, v11.0.1).
   - Hook `hooks/inline_svg.py` (`on_page_content`) inlines the SVG. That way:
     - it takes its colours from theme tokens in `extra.css` and switches with the toggle;
     - it gets `role="img"` with `<title>`/`<desc>`;
     - its labels stay out of the search index.
   - SVG files contain no `<style>`, because inline SVG styles leak site-wide. They use
     presentation attributes as fallbacks plus classes (`.f-ink`, `.f-line`, `.f-cyan`, …).
   - Phone-first legibility rule:
     - Portrait figures: viewBox 400 wide with labels ≥ 13 units, so text is ≥ 11 px on a 375 px
       phone; capped at about 520 px wide on desktop.
     - Wide figures: ≤ 720 wide with labels ≥ 16 units, and a 560 px minimum width that scrolls
       sideways on phones.
   - **Prototype first:** build Ch 3's Vt-bells figure end to end (both themes, phone, search,
     strict build) before any other figure.
2. **Authoring rules**, written into README so that parallel sessions match:
   - **Vocabulary** tables become `| Term | 中文 | Meaning |`. Each Meaning is one sentence ending in
     a link to the explaining section, e.g. `→ [§4.3.2](#432-write-amplification)`. The 中文 cell
     gives the book term, plus the Taiwan term where it differs.
   - **Answers**: an indented `??? success "Answer"` under each Check-yourself item, 2–6
     sentences, with worked numbers for calculations and the section link.
   - **Acronyms** are expanded at first use on every page, because each page must stand alone.
   - **New sections** are appended with the next free number, so existing anchors and
     `formulas.md` links never break.
   - **Dated facts** say "as of 2026". They are checked against a primary source (spec revision,
     standards body, vendor) while writing, and cited in the page's provenance note. Nothing is
     rehosted.
3. **Reading-time hook**: adds "≈ N min read" under each chapter title.
4. **Animation contract** (the animations themselves are not edited yet):
   - `iframe-resize.js` sets `data-theme="light|dark"` on each embedded animation's `<html>` from
     Material's scheme, and updates it when the reader toggles.
   - The inline `style="…background:#0b1020"` on all 24 embeds and the wrapper pages becomes a
     theme-aware `.sdd-anim` class. The embed template in `scripts/ingest.py` changes to match.
   - **`ingest.py` stops overwriting `docs/animations/files/*.html`.** Today it copies
     `incoming/animations/` over them on every run, which would silently undo Phase 4.
     Overwriting becomes opt-in (`--overwrite-animations`), like authored docs.
5. **`scripts/check_content.py`**, run locally and in CI after the glossary step:
   - Fails if any Check-yourself item has no answer.
   - Fails if any vocabulary row is missing 中文 or Meaning.
   - Fails if any SVG lacks `<title>`/`<desc>`, contains `<style>`, or breaks the size rule.
   - Warns about acronyms not expanded at first use.
6. **Rules docs**: update CLAUDE.md and AGENTS.md (kept in sync), README, and
   SITE_SPECIFICATION.md §6.2, §6.3 and §6.5 to cover:
   - the animation edit rule;
   - quiz answers removed from the backlog;
   - the 3-column vocabulary format;
   - the figure system and checker.

## Phase 2 — Page passes (12 pages, one commit per page)

Each page pass touches only that page and its figures folder, plus the page's new acronyms in
`includes/abbreviations.md`. The passes run one at a time, so the shared-file rule in "Order of
work" matters only for parallel sessions. Done: Ch 1–4. For every page:

1. Add figures from the table below, replacing every ASCII diagram.
2. Expand acronyms at first use, and fix forward references (DMA in Ch 2, "interrupt", SMART and
   ONFI in Ch 1).
3. Convert the vocabulary table to 3 columns:
   - chapters gain Meanings (199 terms);
   - supplements gain 中文 (123 terms);
   - every row gets the Taiwan term where it differs, and a "→ §" link.
4. Add hidden answers for every Check-yourself question.
5. Choose which animation blocks open by default (`???+`): only where the animation *is* the
   explanation.
6. Normalize term spellings across pages so the glossary merges them. Today, for example,
   "write amplification" (Ch 3) and "write amplification (WA)" (Ch 1, Ch 4) are separate entries.
7. Page-specific content:
   - **Ch 1**:
     - §1.3 history extended from 2016 to 2026;
     - §1.7 market rewritten as of 2026, replacing the "As of 2018" lists;
     - §1.6 gets a short EDSFF note.
   - **Ch 2**:
     - §2.2 vendor landscape refreshed;
     - **new §2.8 "The board around the controller"**: PMIC and power rails, DRAM (DDR4/LPDDR,
       ECC), power-loss capacitors, SPI-NOR boot flash, thermal sensors and throttling, sideband
       signals (PERST#, CLKREQ#, PEWAKE#), SMBus.
   - **Ch 3**:
     - §3.1.7 states that Intel wound down Optane in 2022;
     - layer counts updated to 2026.

**Figures** (about 52 here and about 12 on the new pages):

| Page | Figures |
|---|---|
| Ch 1 | HDD vs SSD anatomy · inside an SSD (front end, FTL, back end, NAND, DRAM, power) · form factors to scale |
| Ch 2 | controller SoC block diagram · channels × dies in parallel · the board (§2.8) · AFA write path |
| Ch 3 | floating-gate cell · **Vt bells SLC/MLC/TLC (prototype)** · cell → page → block → plane → die · 2D vs 3D string · failure modes as bell shifts · data-integrity ladder · CMOS beside / under / bonded |
| Ch 4 | out-of-place write and the L2P map · map placement: DRAM, DRAM-less, HMB · GC before/after · OP vs WA curve (computed from a model, not copied) · power-loss rebuild · SLC cache fill and fold |
| Ch 5 | topology tree · a TLP dressed layer by layer · TLP header fields · where the bandwidth goes · NRZ vs PAM4 |
| Ch 6 | AHCI vs NVMe queues · the 8-step command flow · SQ/CQ ring with head/tail · PRP vs SGL · ZNS zone states |
| Ch 7 | verification vs validation · test rig (host, analyzer, jammer) · SNIA phases, FOB → steady state · power-loss test loop |
| Supp A | channel model · soft-read strobes and LLRs · decode escalation ladder (all three replace ASCII) |
| Supp B | UFS stack (replaces ASCII) · HPB |
| Supp C | EXT4 layout · F2FS layout (both replace ASCII) · log-on-log vs ZNS |
| Supp D | power-state layers (replaces ASCII) · link-state exit-latency ladder · APST timeline |
| Supp E | radiation effects map · mitigation stack |

Cross-links into the new pages are added in Phase 5, because links to pages that don't exist yet
fail the strict build. Examples: Ch 7's Sanitize → Supp F; Ch 7 §7.11 tools → Supp H.

## Phase 3 — New pages (one commit each)

Every new page uses the existing skeleton:

- front matter (`source_anchor: "original — no book chapter"`);
- intro, then an "In this chapter" box with "Short on time?";
- numbered sections, each with figures;
- takeaways, a 3-column Key vocabulary table, and Check yourself with answers;
- a provenance note citing exact spec revisions.

| Page | Contents |
|---|---|
| **Ch 0 — Foundations** `core/ch0-foundations.md` | units (KB vs KiB, and why "1 TB" ≠ 1 TiB matters for OP) · binary and hex · how a computer is wired (CPU, caches, DRAM, PCIe slots) · storage as a block device (sectors, LBAs, files → blocks) · latency vs throughput vs IOPS, with the latency ladder · the transistor as a switch (sets up the flash cell) · volatile vs non-volatile memory (SRAM, DRAM, NOR, NAND) · firmware vs software · interrupts vs polling · DMA · queues and ring buffers · error rates and big exponents (10⁻¹⁵). Figures: storage path, latency ladder, transistor, interrupt + DMA, ring buffer. |
| **Start here** (home page block) | who the book is for, prerequisites, three reading paths (newcomer / firmware / validation), and what ⭐, ⭐⭐ and 🎬 mean |
| **Supp F — Security & sanitization** | threat model · self-encrypting drives (AES-XTS, MEK/KEK) · TCG Opal / Pyrite / Ruby, locking ranges, crypto erase · NVMe Sanitize vs Format vs Trim, and why "deleted" data lingers in OP space · secure boot, root of trust, signed firmware, anti-rollback · attestation (SPDM, Caliptra) · RPMB recap (→ Supp B) · FIPS 140-3, IEEE 2883 |
| **Supp G — Firmware: boot, update & debug** | firmware architecture recap (→ Ch 2 §2.1.2) · boot chain: Boot ROM → bootloader (SPI-NOR or NAND) → main image, redundant copies · Firmware Image Download / Commit, slots, activation with and without reset, power-loss safety · SMART/Health, Error, Persistent Event and Telemetry logs · UART, JTAG/SWD, asserts and crash dumps · factory flow (bad-block scan, burn-in) · the field-return analysis loop |
| **Supp H — The host side: OS stack & tools** | one read traced from app to flash: syscall → VFS → filesystem → blk-mq → NVMe driver → doorbell → MSI-X → completion · per-CPU queues · interrupts vs polling, io_uring, SPDK · hands-on `nvme-cli` (id-ctrl, smart-log, error-log, fw-log, telemetry), `smartctl`, `lspci -vv` (link speed/width, ASPM), sysfs queue settings, `iostat`/`blktrace`, each with annotated example output labelled as illustrative |
| **Supp I — Data-center SSDs** | tail-latency QoS (99.99%) · U.2/U.3 and EDSFF E1.S/E1.L/E3.S/E3.L, hot-swap, thermals · the OCP Datacenter NVMe SSD spec · power-loss protection · dual-port and multipath (ANA) · NVMe-MI out-of-band management · endurance classes · very large QLC + FDP · NVMe-oF recap (→ Ch 6 §6.8) · CXL |

New tags (the taxonomy may only grow): `foundations`, `security`, `sanitize`, `firmware`, `debug`,
`host-stack`, `tools`, `data-center`, `form-factors`, `cxl`, `ocp`. New spec pointers go in
`reference/specs.md` (links and revisions only).

## Phase 4 — Animations (13 files; four groups that can run in parallel)

Each animation stays a single self-contained file with the same behaviour, Google Fonts only, and
`prefers-reduced-motion` respected. For each one:

1. **Light theme.**
   - Move the 18–63 hard-coded colours into the file's existing `:root` tokens.
   - Add a light token set for `:root[data-theme="light"]`, plus an
     `@media (prefers-color-scheme: light)` fallback for full-screen viewing.
2. **Phone layout.** Below about 600 px:
   - controls wrap into full-width rows and panels stack;
   - touch targets are ≥ 40 px;
   - SVG scenes use a portrait arrangement or larger type, so labels are ≥ 11 px at 375 px;
   - nothing overflows sideways (fixes `enum_routing`).
3. **Known defects**: the low-contrast "free" legend in the Toy SSD sandbox.

Groups:

| Group | Animations |
|---|---|
| Ch 3 | `vt_playground`, `flash_timing_lab`, `nand-flash-animation`, `stripe_raid` |
| Ch 4 | `toy_ssd_sandbox`, `mapping_paths`, `power_loss_rebuild` |
| PCIe / NVMe | `nvme_ring_machine`, `packet_dresser`, `enum_routing`, `ssd_calculators` |
| ECC | `ecc_bit_correction`, `ecc_bch_ldpc` (already responsive, so light theme only) |

The 13 wrapper pages will lead with "what you'll learn / try this". The "Book anchor: Realizes
Figs…" line moves into a provenance note.

## Phase 5 — Integration

- **Nav**:
  - Ch 0 goes first under Core Chapters, and Supplements F–I are added;
  - the home learning path is updated (00 → 07, then A–I);
  - the "Start here" block is added;
  - the tile counts are refreshed.
- **Cross-links** from existing pages to F–I. Both Codas (end of Ch 7 and of Supp E) are updated to
  cover the new pages.
- **Reference**:
  - regenerate the glossary;
  - update the quizzes index intro ("answers are hidden under each question");
  - add any new formulas;
  - add spec pointers;
  - add **a generated Visual index**, every figure and animation by page and concept, built by
    `scripts/build_visual_index.py` in CI. Once that exists, the atlas becomes "production notes".
- `check_content.py` is added to `.github/workflows/deploy.yml`.
- **Animation gallery in search**: today the gallery page's cards form one section, so a search such
  as "doorbell" previews it at about 1,600 px. Give each card its own heading so each hit previews
  one card.
- **Acronym list**: add the new pages' acronyms (OCP, CXL, SPDM, …) to
  `includes/abbreviations.md`. Ch 2's pass already added the board-level ones (PLP, PMIC, SMBus,
  NVMe-MI and others).
- **Formula sheet**: add the power-loss-protection energy rule from Ch 2 §2.8.3.

## Verification (at the end of every phase, and in full at the end)

- `python scripts/build_glossary.py`, then `python scripts/check_content.py`, then
  `mkdocs build --strict`, all clean.
- In the built-in browser, at 375×812 and on desktop, in both themes:
  - no page scrolls sideways;
  - every figure and animation label is ≥ 11 px (the same measuring script as the review);
  - animations follow the theme toggle, and full-screen pages follow the OS.
- **Search**:
  - The spec's six queries still land on the right section: "write amplification", "phase tag",
    "doorbell", "LLR", 垃圾回收, 磨損平衡.
  - So do the new ones: Opal, sanitize, nvme-cli, firmware commit, E3.S, CXL, interrupt, KiB.
  - Glossary hits preview a single entry.
- **Counts**: every question has an answer; no vocabulary row is missing 中文 or Meaning; no
  acronym is flagged as unexplained.
- **`private/` audit**: `git ls-files private` lists only the README; no scans are tracked; every
  figure is original.
- **Not covered by me**: real phones. I test with emulated viewports, so a look on your own phone
  is still worthwhile.

## Size and housekeeping

- **Size**:
  - about 64 figures;
  - about 35k words of new text (Ch 0 ≈ 5k, F–I ≈ 4k each, §2.8 ≈ 1.5k, refreshes ≈ 2k, answers ≈
    10k, glossary meanings and terms ≈ 5k);
  - 13 animation retrofits.

  This spans many sittings; Phases 0 and 1 take one each.
- **Commits**: one commit per phase on the `textbook-v2` branch, pushed to GitHub, as you asked on
  23 Nov 2026. Parallel sessions branch from it, and their work merges back into it. Merging
  `textbook-v2` into `main` deploys the live site.
- **Uncommitted work already in the tree**:
  - Your `specs.md` nav entry in `mkdocs.yml` will ride along with the first `mkdocs.yml` commit.
  - `private/README.md` is left alone.
  - CLAUDE.md and AGENTS.md are untracked; they will be edited but not committed unless you say so.
