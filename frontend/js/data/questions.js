// Exam questions (loaded from the API) and per-type helpers.
// Question shape: id, p = part (1-3), type, ins = instruction, t = prompt text,
// o = options, media, segs = sentence segments ({g:n} marks gap n),
// opts/bank/pairs/rights per type.

// Filled from POST/GET /api/intento by loadExam(). Answer keys never reach
// the browser, so `c` is always undefined and scoring happens on the server.
export const Q = [];
export const PARTS = [];

// API question (Spanish schema) -> the compact shape the exam screen renders.
const toQ = (p) => ({
  id: p.id,
  p: p.parte,
  type: p.tipo,
  ins: p.instruccion,
  t: p.enunciado,
  o: p.opciones,
  media: p.media,
  segs: p.segmentos?.map((s) => (typeof s === 'string' ? s : { g: s.hueco })),
  opts: p.opciones_hueco,
  bank: p.banco,
  pairs: p.izquierdas?.map((l) => [l]),
  rights: p.derechas,
});

// Loads the exam payload and returns saved answers keyed by question index.
export function loadExam(examen) {
  Q.splice(0, Q.length, ...examen.preguntas.map(toQ));
  PARTS.splice(0, PARTS.length, ...examen.partes.map((x) => x.nombre));
  const answers = {};
  Q.forEach((x, i) => {
    if (x.id in examen.respuestas) answers[i] = examen.respuestas[x.id];
  });
  return answers;
}

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
