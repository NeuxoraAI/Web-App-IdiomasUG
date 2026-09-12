// Instructions screen shown before the exam starts.

import { $ } from '../lib/dom.js';
import { Q } from '../data/questions.js';
import { TIMER_MINUTES } from '../config.js';

export function init(nav) {
  $('#instructions-totalq').textContent = Q.length;
  $('#instructions-minutes').textContent = TIMER_MINUTES;
  $('#instructions-start').addEventListener('click', () => nav.startTest());
  $('#instructions-back').addEventListener('click', () => nav.showProfile());
}
