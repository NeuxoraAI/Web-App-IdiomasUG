// App entry point: screen navigation and wiring of all screen modules.

import { START_SCREEN, TIMER_MINUTES } from './config.js';
import { state, resetExam } from './state.js';
import { $ } from './lib/dom.js';
import * as login from './screens/login.js';
import * as profile from './screens/profile.js';
import * as instructions from './screens/instructions.js';
import * as exam from './screens/exam.js';
import * as results from './screens/results.js';
import * as certificate from './screens/certificate.js';

const SCREENS = {
  login: '#screen-login',
  profile: '#screen-profile',
  intro: '#screen-instructions',
  test: '#screen-exam',
  results: '#screen-results',
};

function show(screen) {
  const previous = state.screen;
  state.screen = screen;

  if (previous === 'login' && screen !== 'login') login.leave();

  $('#screen-login').hidden = screen !== 'login';
  $('#app-shell').hidden = screen === 'login';
  ['profile', 'intro', 'test', 'results'].forEach((s) => {
    $(SCREENS[s]).hidden = screen !== s;
  });

  // Header: timer during the test, nav everywhere else in the app
  $('#header-timer').hidden = screen !== 'test';
  $('#header-nav').hidden = screen === 'test' || screen === 'login';
  $('#nav-profile').classList.toggle('is-active', screen === 'profile');
  $('#nav-test').classList.toggle('is-active', screen === 'intro' || screen === 'results');

  if (screen === 'login') login.enter();
  if (screen === 'profile') profile.enter();
}

const nav = {
  showLogin() {
    exam.stop();
    results.stop();
    certificate.close();
    state.email = '';
    $('#login-code').value = '';
    show('login');
  },
  showProfile() {
    exam.stop();
    results.stop();
    show('profile');
  },
  showIntro() {
    show('intro');
  },
  startTest() {
    resetExam();
    state.totalSeconds = TIMER_MINUTES * 60;
    show('test');
    exam.start();
  },
  finishTest() {
    exam.stop();
    show('results');
    results.enter();
  },
  logout() {
    this.showLogin();
  },
};

login.init(nav);
profile.init(nav);
instructions.init(nav);
exam.init(nav);
results.init(nav);
certificate.init();

$('#nav-profile').addEventListener('click', () => nav.showProfile());
$('#nav-test').addEventListener('click', () => nav.showIntro());
$('#nav-logout').addEventListener('click', () => nav.logout());

// Boot on the configured start screen
if (START_SCREEN === 'test') {
  nav.startTest();
} else if (START_SCREEN === 'profile' || START_SCREEN === 'intro') {
  show(START_SCREEN);
} else {
  show('login');
}
