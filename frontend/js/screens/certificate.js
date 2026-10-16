// Certificate overlay: fills the printable sheet from GET /api/nivel and drives the print flow.

import { state } from '../state.js';
import { $ } from '../lib/dom.js';
import { api } from '../api.js';

let nav;

export function init(navigation) {
  nav = navigation;
  $('#cert-print').addEventListener('click', () => window.print());
  $('#cert-close').addEventListener('click', close);
}

export async function open() {
  let n;
  try {
    n = await api('GET', '/nivel');
  } catch (err) {
    nav.fail(err);
    return;
  }
  $('#cert-name').textContent = n.nombre;
  $('#cert-mcer').textContent = n.mcer;
  $('#cert-level').textContent = n.nivel;
  $('#cert-folio').textContent = n.folio;
  $('#cert-idioma').textContent = n.idioma;
  $('#cert-reason-idioma').textContent = n.idioma.toLowerCase();
  $('#cert-score').textContent = `${n.aciertos} / ${n.calificables}`;
  $('#cert-date').textContent = new Date(n.fecha).toLocaleDateString('es-MX', { day: 'numeric', month: 'long', year: 'numeric' });
  state.certOpen = true;
  $('#certificate-overlay').hidden = false;
}

export function close() {
  state.certOpen = false;
  $('#certificate-overlay').hidden = true;
}
