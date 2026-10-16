// Certificate overlay: fills the printable sheet and drives the print flow.

import { state, folio } from '../state.js';
import { $ } from '../lib/dom.js';
import { computeResults } from '../data/questions.js';

export function init() {
  $('#cert-print').addEventListener('click', () => window.print());
  $('#cert-close').addEventListener('click', close);
}

export function open() {
  const r = computeResults(state.answers);
  $('#cert-mcer').textContent = r.mcer;
  $('#cert-level').textContent = r.levelName;
  $('#cert-folio').textContent = folio();
  $('#cert-score').textContent = `${r.correct} / ${r.scoredCount}`;
  $('#cert-date').textContent = new Date().toLocaleDateString('es-MX', { day: 'numeric', month: 'long', year: 'numeric' });
  state.certOpen = true;
  $('#certificate-overlay').hidden = false;
}

export function close() {
  state.certOpen = false;
  $('#certificate-overlay').hidden = true;
}
