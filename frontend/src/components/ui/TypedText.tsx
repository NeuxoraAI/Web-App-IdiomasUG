// Character-by-character typing effect over segmented text; bold segments render as <strong>.

import { useEffect } from 'react';
import type { Segment } from '../../data/copy';
import { useTypewriter } from '../../hooks/useTypewriter';

export function TypedText({ parts, onTick }: { parts: Segment[]; onTick?: () => void }) {
  const total = parts.reduce((a, p) => a + p[0].length, 0);
  const count = useTypewriter(total);
  useEffect(() => { onTick?.(); }, [count, onTick]);

  let left = count;
  const shown = [];
  for (const [i, p] of parts.entries()) {
    if (left <= 0) break;
    const t = p[0].slice(0, left);
    left -= p[0].length;
    shown.push(p[1] ? <strong key={i} className="typed-strong">{t}</strong> : t);
  }
  return (
    <>
      {shown}
      {count < total && <span className="typed-caret" />}
    </>
  );
}
