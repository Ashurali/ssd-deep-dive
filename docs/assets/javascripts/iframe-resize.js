/* Embedded animation iframes (same-origin only):

   1. Auto-size each frame to its content so nothing hides behind an inner
      scrollbar. The height attribute remains as the no-JS / cross-origin
      fallback. Measure document.body, NOT documentElement: the html
      element's scrollHeight is clamped to the iframe viewport, which turns a
      resize observer into a positive feedback loop (the frame grows forever).

   2. Tell each animation which theme the site is showing, by setting
      <html data-theme="light|dark"> inside the frame on load and whenever the
      reader flips the toggle. An animation that defines light tokens for
      :root[data-theme="light"] follows the site; one that doesn't simply
      ignores the attribute. */
const siteTheme = () =>
  document.body.getAttribute("data-md-color-scheme") === "slate" ? "dark" : "light";

const tellTheme = (frame) => {
  try {
    frame.contentDocument?.documentElement.setAttribute("data-theme", siteTheme());
  } catch (e) {
    /* cross-origin: the animation follows the OS instead */
  }
};

new MutationObserver(() => {
  document.querySelectorAll(".md-typeset iframe").forEach(tellTheme);
}).observe(document.body, { attributes: true, attributeFilter: ["data-md-color-scheme"] });

document$.subscribe(() => {
  document.querySelectorAll(".md-typeset iframe").forEach((frame) => {
    const fit = () => {
      try {
        const body = frame.contentDocument?.body;
        if (!body) return;
        const h = Math.max(body.scrollHeight, body.offsetHeight) + 24;
        const cur = parseInt(frame.style.height, 10) || 0;
        if (h > 60 && Math.abs(h - cur) > 8) frame.style.height = h + "px";
      } catch (e) {
        /* cross-origin: keep the fixed fallback height */
      }
    };
    const observe = () => {
      tellTheme(frame);
      fit();
      try {
        new ResizeObserver(fit).observe(frame.contentDocument.body);
      } catch (e) {
        /* ignore */
      }
    };
    frame.addEventListener("load", observe);
    if (frame.contentDocument?.readyState === "complete") observe();
  });
});
