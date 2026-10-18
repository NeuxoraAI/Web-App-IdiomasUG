// App entry point: screen navigation and wiring of all screen modules.

import { state, resetExam } from './state.js';
import { $ } from './lib/dom.js';
import { api, getToken, setToken } from './api.js';
import { loadExam } from './data/questions.js';
import * as login from './screens/login.js';
import * as profile from './screens/profile.js';
import * as instructions from './screens/instructions.js';
import * as exam from './screens/exam.js';
import * as results from './screens/results.js';

const SCREENS = {
  login: '#screen-login',
  profile: '#screen-profile',
  intro: '#screen-instructions',
  test: '#screen-exam',
  results: '#screen-results',
};

let finishing = false;

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

// Expired session -> back to login with the server message; otherwise show it on the profile.
function fail(err) {
  if (err.status === 401) {
    nav.showLogin();
    login.showError(err.message);
  } else {
    nav.showProfile();
    profile.say(err.message);
  }
}

const nav = {
  async login(curp, clave) {
    const r = await api('POST', '/sesion', { curp, clave });
    setToken(r.token);
    state.perfil = r.perfil;
    show('profile');
  },
  showLogin() {
    exam.stop();
    results.stop();
    setToken(null);
    state.perfil = null;
    state.resultado = null;
    state.code = '';
    $('#login-code').value = '';
    show('login');
  },
  showProfile() {
    exam.stop();
    results.stop();
    show('profile');
  },
  showIntro() {
    instructions.enter();
    show('intro');
  },
  async startTest() {
    try {
      const examen = await api('POST', '/intento');
      resetExam();
      state.answers = loadExam(examen);
      state.totalSeconds = state.perfil.examen.duracion_min * 60;
      state.secondsLeft = examen.segundos_restantes;
      state.perfil.estado = 'en_curso';
      finishing = false;
      show('test');
      exam.start();
    } catch (err) {
      fail(err);
    }
  },
  async finishTest() {
    if (finishing) return;
    finishing = true;
    exam.stop();
    try {
      await exam.flush();
      state.resultado = await api('POST', '/intento/finalizar');
      state.perfil.estado = 'finalizado';
      show('results');
      results.enter();
    } catch (err) {
      finishing = false;
      fail(err);
    }
  },
  logout() {
    this.showLogin();
  },
  fail,
};

login.init(nav);
profile.init(nav);
instructions.init(nav);
exam.init(nav);
results.init(nav);

$('#nav-profile').addEventListener('click', () => nav.showProfile());
$('#nav-test').addEventListener('click', () => nav.showIntro());
$('#nav-logout').addEventListener('click', () => nav.logout());

// Boot: a stored token (page reload) goes straight back to the profile.
if (getToken()) {
  api('GET', '/perfil')
    .then((p) => { state.perfil = p; show('profile'); })
    .catch(() => nav.showLogin());
} else {
  show('login');
}
