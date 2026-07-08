/* Auto-size embedded animation iframes to their content so nothing hides
   behind an inner scrollbar. Same-origin only; the height="720" attribute
   remains as the no-JS / cross-origin fallback. */
document$.subscribe(() => {
  document.querySelectorAll(".md-typeset iframe").forEach((frame) => {
    const fit = () => {
      try {
        const root = frame.contentDocument?.documentElement;
        if (!root) return;
        const h = root.scrollHeight;
        if (h > 0) frame.style.height = h + 4 + "px";
      } catch (e) {
        /* cross-origin: keep the fixed fallback height */
      }
    };
    const observe = () => {
      fit();
      try {
        new ResizeObserver(fit).observe(frame.contentDocument.documentElement);
      } catch (e) {
        /* ignore */
      }
    };
    frame.addEventListener("load", observe);
    if (frame.contentDocument?.readyState === "complete") observe();
  });
});
