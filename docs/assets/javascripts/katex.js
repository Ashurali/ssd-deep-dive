/* KaTeX auto-render, wired to Material's instant navigation.
   Inline math uses \( ... \); blocks use $$ ... $$ or \[ ... \]. */
document$.subscribe(({ body }) => {
  renderMathInElement(body, {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "\\[", right: "\\]", display: true },
      { left: "\\(", right: "\\)", display: false }
    ],
    throwOnError: false
  });
});
