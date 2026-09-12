// Profile screen: exam summary card and Bee bot typed hint.

import { folio } from '../state.js';
import { $ } from '../lib/dom.js';
import { typewriter } from '../lib/typewriter.js';
import { TYPED } from '../data/copy.js';
import { Q } from '../data/questions.js';
import { TIMER_MINUTES } from '../config.js';

let nav;
let cancelTyper = null;

export function init(navigation) {
  nav = navigation;
  $('#profile-start').addEventListener('click', () => nav.showIntro());
  $('#profile-duration').textContent = TIMER_MINUTES;
  $('#profile-questions').textContent = Q.length;
}

export function enter() {
  $('#profile-folio').textContent = folio();
  if (cancelTyper) cancelTyper();
  cancelTyper = typewriter($('#profile-typed'), TYPED.profile);
}
