// Results screen: score summary, per-part breakdown, and auto-logout countdown.

import { state } from '../state.js';
import { $, esc, fmt } from '../lib/dom.js';
import * as certificate from './certificate.js';

let nav;
let countdownId = null;

export function init(navigation) {
  nav = navigation;
  $('#results-cert').addEventListener('click', () => certificate.open());
  $('#results-logout').addEventListener('click', () => nav.logout());
}

export function enter() {
  const r = state.resultado;

  $('#results-mcer').textContent = r.mcer;
  $('#results-level').textContent = r.nivel;
  $('#results-summary').textContent =
    `${r.aciertos} de ${r.calificables} respuestas correctas · ${fmt(r.segundos_usados)} utilizados`;

  $('#results-sections').innerHTML = r.por_parte.map((s) => `
    <div class="results-section">
      <div class="results-section-head"><span>${esc(s.nombre)}</span><span class="results-section-score">${s.aciertos} / ${s.total}</span></div>
      <div class="results-section-track"><div class="results-section-fill" style="width:${s.porcentaje}%"></div></div>
    </div>`).join('');

  state.closeIn = 20;
  $('#results-closein').textContent = state.closeIn;
  clearInterval(countdownId);
  countdownId = setInterval(() => {
    if (state.certOpen) return; // paused while the certificate is open
    if (state.closeIn <= 1) {
      stop();
      nav.logout();
      return;
    }
    state.closeIn--;
    $('#results-closein').textContent = state.closeIn;
  }, 1000);
}

export function stop() {
  clearInterval(countdownId);
  countdownId = null;
}
