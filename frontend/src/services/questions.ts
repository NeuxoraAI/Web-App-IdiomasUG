// Exam questions (loaded from the API) and per-type helpers.
// Answer keys never reach the browser, so scoring happens on the server.

import type { Examen, PreguntaApi, TipoPregunta, Valor } from '../api/types';

// Compact shape the exam screen renders: p = part (1-3), ins = instruction,
// t = prompt text, o = options, segs = sentence segments ({ g: n } marks gap n).
export interface Question {
  id: string;
  p: number;
  type: TipoPregunta;
  ins: string;
  t: string;
  o?: string[];
  media?: NonNullable<PreguntaApi['media']>;
  segs?: (string | { g: number })[];
  opts?: string[][];
  bank?: string[];
  lefts?: string[];
  rights?: string[];
}

export interface LoadedExam {
  questions: Question[];
  parts: string[];
  answers: Record<number, Valor>;   // question index -> saved answer
  secondsLeft: number;
}

// API question (Spanish schema) -> the compact shape the exam screen renders.
// The API sends null for fields a question type doesn't use.
const toQ = (p: PreguntaApi): Question => ({
  id: p.id,
  p: p.parte,
  type: p.tipo,
  ins: p.instruccion,
  t: p.enunciado,
  o: p.opciones ?? undefined,
  media: p.media ?? undefined,
  segs: p.segmentos?.map((s) => (typeof s === 'string' ? s : { g: s.hueco })),
  opts: p.opciones_hueco ?? undefined,
  bank: p.banco ?? undefined,
  lefts: p.izquierdas ?? undefined,
  rights: p.derechas ?? undefined,
});

export function loadExam(examen: Examen): LoadedExam {
  const questions = examen.preguntas.map(toQ);
  const answers: Record<number, Valor> = {};
  questions.forEach((x, i) => {
    const v = examen.respuestas[x.id];
    if (v != null) answers[i] = v;
  });
  return {
    questions,
    parts: examen.partes.map((x) => x.nombre),
    answers,
    secondsLeft: examen.segundos_restantes,
  };
}

export const TYPE_LABEL: Record<TipoPregunta, string> = {
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

export const isChoiceType = (t: TipoPregunta) => t === 'choice' || t === 'tf' || t === 'listen' || t === 'notice';

export function isAnswered(x: Question, a: Valor | undefined): boolean {
  if (a == null) return false;
  if (typeof a === 'string') return a.trim().length > 0;
  if (Array.isArray(a)) {
    if (x.type === 'order') return a.length > 0;
    const need = x.type === 'match' ? (x.lefts || []).length : (x.segs || []).filter((s) => typeof s !== 'string').length;
    let n = 0;
    for (let i = 0; i < need; i++) if (a[i] != null && a[i] !== '') n++;
    return n === need;
  }
  return true;
}
