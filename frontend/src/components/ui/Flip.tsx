// Language flip (3D cube): every translation is stacked in the same grid cell;
// the hidden ones only reserve space, so the box always fits the longest text
// and never resizes. Keyed by `lang` so the faces remount and replay the turn.

interface Props {
  texts: string[];
  lang: number;
  prevLang: number | null;
  wrap?: boolean;
}

export function Flip({ texts, lang, prevLang, wrap }: Props) {
  const cur = texts[lang];
  const prev = prevLang != null ? texts[prevLang] : null;
  return (
    <span key={lang} className={`flip${wrap ? ' flip--wrap' : ''}`}>
      {[...new Set(texts)].map((t) => {
        let cls = 'flip-face flip-face--ghost';
        if (t === cur) cls = prev != null && prev !== cur ? 'flip-face flip-face--in' : 'flip-face';
        else if (t === prev) cls = 'flip-face flip-face--out';
        const hidden = cls.includes('ghost') || t === prev;
        return <span key={t} className={cls} aria-hidden={hidden || undefined}>{t}</span>;
      })}
    </span>
  );
}
