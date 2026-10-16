// Instructions screen shown before the exam starts.

import { state } from '../state.js';
import { $ } from '../lib/dom.js';

export function init(nav) {
  $('#instructions-start').addEventListener('click', () => nav.startTest());
  $('#instructions-back').addEventListener('click', () => nav.showProfile());
}

export function enter() {
  const ex = state.perfil.examen;
  $('#instructions-totalq').textContent = ex ? ex.preguntas : '—';
  $('#instructions-minutes').textContent = ex ? ex.duracion_min : '—';
}
