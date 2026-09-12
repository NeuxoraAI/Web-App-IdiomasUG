// Question bank and scoring rules, extracted verbatim from the prototype.
// Question shape: p = part (1-3), type, ins = instruction, t = prompt text,
// o = options, c = correct answer (null = manually graded / unscored),
// segs = sentence segments ({g:n} marks gap n), opts/bank/pairs/rights per type.

export const Q = [
  { p: 1, type: 'choice', ins: 'Selecciona la respuesta correcta', t: 'This car is more_____than that one.', o: ['fast', 'cheap', 'slow', 'expensive'], c: 3 },
  { p: 1, type: 'tf', ins: '¿Es correcta esta oración?', t: '“She don’t like coffee.”', o: ['True', 'False'], c: 1 },
  { p: 1, type: 'listen', ins: 'Escucha y elige lo que oíste', t: 'Toca el altavoz para escuchar.', o: ['I go home at 3 o’clock.', 'I go home in 3 o’clock.', 'I go home on 3 o’clock.'], c: 0 },
  { p: 1, type: 'select', ins: 'Elige las palabras que faltan', t: 'Completa con la forma correcta del verbo “to be”.', segs: ['I ', { g: 0 }, ' a student and my brothers ', { g: 1 }, ' teachers.'], opts: [['am', 'is', 'are'], ['am', 'is', 'are']], c: ['am', 'are'] },
  { p: 2, type: 'drag', ins: 'Completa la oración', t: 'Arrastra las fichas a los espacios.', segs: ['Yesterday we ', { g: 0 }, ' to the cinema and ', { g: 1 }, ' a very good film.'], bank: ['went', 'saw', 'go', 'see'], c: ['went', 'saw'] },
  { p: 2, type: 'order', ins: 'Traduce esta oración', t: 'Nunca he estado en Londres.', bank: ['never', 'been', 'I', 'have', 'to London', 'was', 'going'], c: 'I have never been to London' },
  { p: 2, type: 'match', ins: 'Relaciona cada palabra con su significado', t: 'Toca una palabra y luego su definición.', pairs: [['reliable', 'can be trusted'], ['generous', 'gives more than expected'], ['punctual', 'arrives on time']], rights: ['arrives on time', 'can be trusted', 'gives more than expected'], c: ['can be trusted', 'gives more than expected', 'arrives on time'] },
  { p: 3, type: 'short', ins: 'Escribe la palabra que falta', t: 'He’s been working here ______ 2019.', c: 'since' },
  { p: 3, type: 'notice', ins: '¿Dónde puedes ver este aviso?', t: 'Where can you see this notice?', o: ['in a restaurant', 'in a library', 'in a police station', 'in a book'], c: null },
  { p: 3, type: 'essay', ins: 'Escribe un texto breve', t: 'Describe a place you would like to visit and explain why. Write 50–80 words.', c: null },
];

export const PARTS = ['Parte 1 · Básico', 'Parte 2 · Intermedio', 'Parte 3 · Avanzado'];

export const TYPE_LABEL = {
  choice: 'Opción múltiple',
  tf: 'Verdadero / Falso',
  listen: 'Comprensión auditiva',
  select: 'Palabras faltantes',
  drag: 'Arrastrar y soltar',
  order: 'Traducir con fichas',
  match: 'Relacionar columnas',
  short: 'Respuesta corta',
  notice: 'Pregunta con imagen',
  essay: 'Texto breve',
};

export const LETTERS = ['a', 'b', 'c', 'd'];

const norm = (s) => String(s || '').trim().toLowerCase().replace(/[.!?]$/, '');

export const scorable = (x) => x.c != null;

export const isChoiceType = (t) => t === 'choice' || t === 'tf' || t === 'listen' || t === 'notice';

export function isCorrect(x, a) {
  if (a == null) return false;
  switch (x.type) {
    case 'short': return norm(a) === norm(x.c);
    case 'select':
    case 'match': return Array.isArray(a) && x.c.every((v, i) => a[i] === v);
    case 'drag': return Array.isArray(a) && x.c.every((v, i) => a[i] != null && x.bank[a[i]] === v);
    case 'order': return Array.isArray(a) && a.map((i) => x.bank[i]).join(' ') === x.c;
    case 'essay': return false;
    default: return a === x.c;
  }
}

export function correctText(x) {
  switch (x.type) {
    case 'short': return x.c;
    case 'select':
    case 'drag': return x.c.join(', ');
    case 'order': return x.c;
    case 'match': return x.pairs.map((p) => `${p[0]} → ${p[1]}`).join(' · ');
    default: return x.c != null ? x.o[x.c] : '';
  }
}

export function isAnswered(x, a) {
  if (a == null) return false;
  if (typeof a === 'string') return a.trim().length > 0;
  if (Array.isArray(a)) {
    if (x.type === 'order') return a.length > 0;
    const need = x.type === 'match' ? x.pairs.length : (x.segs || []).filter((s) => typeof s !== 'string').length;
    let n = 0;
    for (let i = 0; i < need; i++) if (a[i] != null && a[i] !== '') n++;
    return n === need;
  }
  return true;
}

// Aggregate scoring: total correct, per-part breakdown, and MCER level.
export function computeResults(answers) {
  const scored = Q.filter(scorable);
  const correct = Q.reduce((n, x, i) => n + (scorable(x) && isCorrect(x, answers[i]) ? 1 : 0), 0);
  const lvl = correct <= 2 ? ['A1', 'Nivel 1 · Básico']
    : correct <= 4 ? ['A2', 'Nivel 1 · Básico alto']
    : correct <= 6 ? ['B1', 'Nivel 2 · Intermedio']
    : correct <= 7 ? ['B2', 'Nivel 3 · Intermedio alto']
    : ['C1', 'Nivel 3 · Avanzado'];
  const sections = PARTS.map((name, pi) => {
    const qs = Q.map((x, i) => ({ x, i })).filter(({ x }) => x.p === pi + 1 && scorable(x));
    const okn = qs.filter(({ x, i }) => isCorrect(x, answers[i])).length;
    const pct = qs.length ? Math.round((okn / qs.length) * 100) : 0;
    return { name, label: `${okn} / ${qs.length}`, pct };
  });
  return { correct, scoredCount: scored.length, mcer: lvl[0], levelName: lvl[1], sections };
}
