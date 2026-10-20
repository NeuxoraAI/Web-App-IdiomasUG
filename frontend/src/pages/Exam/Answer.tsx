// Answer area of the current question, one layout per question type.

import type { Valor } from '../../api/types';
import { LETTERS, isChoiceType, type Question } from '../../services/questions';

type Slots = (number | string | null)[];

interface Props {
  cur: Question;
  a: Valor | undefined;
  setAns: (fn: (prev: Valor | undefined) => Valor) => void;
  pick: number | null;            // drag: currently picked word-bank index
  setPick: (i: number | null) => void;
  pickL: number | null;           // match: currently selected left tile index
  setPickL: (i: number | null) => void;
}

const copy = (x: Valor | undefined): Slots => (Array.isArray(x) ? [...x] : []);

export function Answer({ cur, a, setAns, pick, setPick, pickL, setPickL }: Props) {
  if (isChoiceType(cur.type)) {
    return (
      <div className="exam-options">
        {(cur.o || []).map((text, i) => (
          <button key={i} className={`exam-option${a === i ? ' is-selected' : ''}`} onClick={() => setAns(() => i)}>
            <span className="exam-option-badge">{LETTERS[i]}</span>
            <span className="exam-option-text">{text}</span>
          </button>
        ))}
      </div>
    );
  }

  if (cur.type === 'short') {
    return (
      <input
        type="text" className="exam-short-input" value={typeof a === 'string' ? a : ''}
        placeholder="Escribe tu respuesta" autoComplete="off" onChange={(e) => setAns(() => e.target.value)}
      />
    );
  }

  if (cur.type === 'essay') {
    const text = typeof a === 'string' ? a : '';
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    return (
      <div className="exam-essay">
        <textarea rows={8} placeholder="Escribe aquí tu texto…" value={text} onChange={(e) => setAns(() => e.target.value)} />
        <div className="exam-essay-meta"><span>{words} palabras · mínimo 50</span><span>Se califica manualmente</span></div>
      </div>
    );
  }

  const segs = cur.segs || [];
  const bank = cur.bank || [];
  const arr: Slots = Array.isArray(a) ? a : [];

  if (cur.type === 'select') {
    return (
      <div className="exam-sentence">
        {segs.map((seg, k) => {
          if (typeof seg === 'string') return <span key={k}>{seg}</span>;
          const gi = seg.g;
          return (
            <select
              key={k} className="exam-gap-select" value={(arr[gi] as string) || ''}
              onChange={(e) => setAns((x) => { const n = copy(x); n[gi] = e.target.value; return n; })}
            >
              {['', ...(cur.opts?.[gi] || [])].map((v, j) => <option key={j} value={v}>{v === '' ? '—' : v}</option>)}
            </select>
          );
        })}
      </div>
    );
  }

  if (cur.type === 'drag') {
    const placeWord = (gi: number, wi: number) => {
      setAns((x) => {
        const n = copy(x);
        for (let k = 0; k < n.length; k++) if (n[k] === wi) n[k] = null;
        n[gi] = wi;
        return n;
      });
      setPick(null);
    };
    return (
      <div className="exam-order">
        <div className="exam-sentence">
          {segs.map((seg, k) => {
            if (typeof seg === 'string') return <span key={k}>{seg}</span>;
            const gi = seg.g;
            const wi = arr[gi];
            const filled = wi != null;
            const cls = filled ? ' is-filled' : pick != null ? ' is-target' : '';
            return (
              <button
                key={k} className={`exam-tile exam-gap${cls}`}
                onClick={() => {
                  if (filled) setAns((x) => { const n = copy(x); n[gi] = null; return n; });
                  else if (pick != null) placeWord(gi, pick);
                }}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  const w = Number(e.dataTransfer.getData('text/plain'));
                  if (!Number.isNaN(w)) placeWord(gi, w);
                }}
              >
                {filled ? bank[wi as number] : '        '}
              </button>
            );
          })}
        </div>
        <div className="exam-bank">
          {bank.map((text, i) => {
            const used = arr.includes(i);
            const cls = used ? ' is-used' : pick === i ? ' is-picked' : ' is-grab';
            // A used tile keeps its slot but its text is hidden (color: transparent),
            // so take it out of the tab order and the accessibility tree until it is freed.
            return (
              <button
                key={i} className={`exam-tile${cls}`} draggable={!used} disabled={used} aria-hidden={used || undefined}
                onDragStart={(e) => e.dataTransfer.setData('text/plain', String(i))}
                onClick={() => setPick(pick === i ? null : i)}
              >
                {text}
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  if (cur.type === 'order') {
    return (
      <div className="exam-order">
        <div className="exam-sequence">
          {arr.map((wi, k) => (
            <button key={k} className="exam-sequence-word" onClick={() => setAns((x) => copy(x).filter((_, j) => j !== k))}>
              {bank[wi as number]}
            </button>
          ))}
          {arr.length === 0 && <span className="exam-sequence-hint">Selecciona las palabras en orden…</span>}
        </div>
        <div className="exam-bank exam-bank--plain">
          {bank.map((text, i) => {
            const used = arr.includes(i);
            return (
              <button
                key={i} className={`exam-tile${used ? ' is-used' : ''}`} disabled={used} aria-hidden={used || undefined}
                onClick={() => setAns((x) => [...copy(x), i])}
              >
                {text}
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  if (cur.type === 'match') {
    return (
      <div className="exam-match">
        <div className="exam-match-col">
          {(cur.lefts || []).map((text, i) => {
            const paired = arr[i] != null && arr[i] !== '';
            const cls = pickL === i ? ' is-selected' : paired ? ' is-paired' : '';
            return (
              <button
                key={i} className={`exam-tile exam-tile--left${cls}`}
                onClick={() => {
                  if (paired) setAns((x) => { const n = copy(x); n[i] = ''; return n; });
                  else setPickL(pickL === i ? null : i);
                }}
              >
                {text}
              </button>
            );
          })}
        </div>
        <div className="exam-match-col">
          {(cur.rights || []).map((text) => {
            const li = arr.indexOf(text);
            const cls = li >= 0 ? ' is-paired' : pickL != null ? ' is-open' : '';
            return (
              <button
                key={text} className={`exam-tile exam-tile--right${cls}`}
                onClick={() => {
                  if (li >= 0) {
                    setAns((x) => { const n = copy(x); n[li] = ''; return n; });
                  } else if (pickL != null) {
                    setAns((x) => {
                      const n = copy(x);
                      for (let k = 0; k < n.length; k++) if (n[k] === text) n[k] = '';
                      n[pickL] = text;
                      return n;
                    });
                    setPickL(null);
                  }
                }}
              >
                {text}
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  return null;
}
