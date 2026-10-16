// Results screen: score summary, per-part breakdown, and auto-logout countdown.

import { state } from '../state.js';
import { $, fmt } from '../lib/dom.js';
import { computeResults } from '../data/questions.js';
import * as certificate from './certificate.js';

let nav;
let countdownId = null;

export function init(navigation) {
  nav = navigation;
  $('#results-cert').addEventListener('click', () => certificate.open());
  $('#results-logout').addEventListener('click', () => nav.logout());
}

export function enter() {
  const r = computeResults(state.answers);

  $('#results-mcer').textContent = r.mcer;
  $('#results-level').textContent = r.levelName;
  $('#results-summary').textContent =
    `${r.correct} de ${r.scoredCount} respuestas correctas · ${fmt(state.totalSeconds - state.secondsLeft)} utilizados`;

  $('#results-sections').innerHTML = r.sections.map((s) => `
    <div class="results-section">
      <div class="results-section-head"><span>${s.name}</span><span class="results-section-score">${s.label}</span></div>
      <div class="results-section-track"><div class="results-section-fill" style="width:${s.pct}%"></div></div>
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
