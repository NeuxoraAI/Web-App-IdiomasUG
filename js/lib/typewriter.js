// Character-by-character typing effect over segmented text.
// parts: array of [text, bold?]; bold segments render as <strong>.
// Returns a cancel function.

import { esc } from './dom.js';

export function typewriter(el, parts, { onTick } = {}) {
  const total = parts.reduce((a, p) => a + p[0].length, 0);
  let n = 0;
  render(0);
  const id = setInterval(() => {
    n++;
    render(n);
    if (onTick) onTick();
    if (n >= total) clearInterval(id);
  }, 18);

  function render(count) {
    let left = count;
    let html = '';
    for (const p of parts) {
      if (left <= 0) break;
      const t = p[0].slice(0, left);
      left -= p[0].length;
      html += p[1] ? `<strong class="typed-strong">${esc(t)}</strong>` : esc(t);
    }
    if (count < total) html += '<span class="typed-caret"></span>';
    el.innerHTML = html;
  }

  return () => clearInterval(id);
}
