/* Acronym quick links. hooks/acronym_links.py wraps every acronym in a link
   to its glossary entry; this script adds what a plain link can't:
   - touch: the first tap shows the expansion (Material's tooltip) with a
     "tap again" hint, and a second tap on the same acronym opens the glossary;
   - glossary: the entry you arrived at is highlighted, and a "← Back to …"
     button returns you to the exact spot you left. */
(() => {
  const RETURN_KEY = "sdd-acr-return";   // where the reader came from
  const RESTORE_KEY = "sdd-acr-restore"; // scroll position to restore there
  const FRESH_MS = 30 * 60 * 1000;
  const HINT = "  ·  tap again for the glossary";

  let pointer = "mouse";
  let armed = null;

  const isGlossary = () => /\/reference\/glossary\/(index\.html)?$/.test(location.pathname);
  const here = () => location.pathname + location.search;
  const load = (key) => {
    try { return JSON.parse(sessionStorage.getItem(key)); } catch (e) { return null; }
  };
  const save = (key, value) => {
    try {
      if (value == null) sessionStorage.removeItem(key);
      else sessionStorage.setItem(key, JSON.stringify(value));
    } catch (e) { /* storage blocked: links still work, just no Back button */ }
  };

  document.addEventListener("pointerdown", (ev) => {
    pointer = ev.pointerType || "mouse";
    if (pointer !== "touch") return;
    const abbr = ev.target.closest?.("a.sdd-acr")?.querySelector("abbr");
    if (abbr && abbr.title && !abbr.dataset.sddHint) {
      abbr.dataset.sddHint = "1";
      abbr.title += HINT;
    }
  }, true);

  document.addEventListener("click", (ev) => {
    const link = ev.target.closest?.("a.sdd-acr");
    if (!link) { armed = null; return; }
    if (pointer === "touch" && armed !== link) {
      ev.preventDefault();       // first tap: show the expansion only
      ev.stopPropagation();      // keep instant navigation from following it
      armed = link;
      return;
    }
    armed = null;
    if (!isGlossary()) {
      const title = document.title.replace(/\s+-\s+[^-]+$/, "");
      save(RETURN_KEY, { href: here(), y: Math.round(scrollY), title, t: Date.now() });
    }
  }, true);

  function showBack() {
    document.querySelectorAll(".sdd-back").forEach((el) => el.remove());
    const back = load(RETURN_KEY);
    if (!isGlossary() || !back || Date.now() - back.t > FRESH_MS) return;
    const a = document.createElement("a");
    a.className = "sdd-back";
    a.href = back.href;
    a.textContent = `← Back to ${back.title}`;
    a.addEventListener("click", () => {
      save(RESTORE_KEY, { href: back.href, y: back.y });
      save(RETURN_KEY, null);
    });
    (document.querySelector(".md-content") || document.body).append(a);
  }

  function restoreScroll() {
    const spot = load(RESTORE_KEY);
    if (!spot || spot.href !== here()) return;
    save(RESTORE_KEY, null);
    // after Material's own post-navigation scroll
    setTimeout(() => window.scrollTo({ top: spot.y, behavior: "instant" }), 60);
  }

  function highlightTarget() {
    if (!isGlossary() || location.hash.length < 2) return;
    const el = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (!el) return;
    document.querySelectorAll(".sdd-hit").forEach((x) => x.classList.remove("sdd-hit"));
    el.classList.add("sdd-hit");
    setTimeout(() => el.classList.remove("sdd-hit"), 4000);
  }

  window.addEventListener("hashchange", highlightTarget);
  document$.subscribe(() => {
    armed = null;
    showBack();
    restoreScroll();
    highlightTarget();
  });
})();
