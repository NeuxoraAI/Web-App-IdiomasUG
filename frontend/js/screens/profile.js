// Profile screen: applicant data and exam summary from the API, Bee bot typed hint.

import { state } from '../state.js';
import { $ } from '../lib/dom.js';
import { typewriter } from '../lib/typewriter.js';
import { TYPED } from '../data/copy.js';

const STATUS = { pendiente: 'Disponible', en_curso: 'En curso', finalizado: 'Finalizado', cancelado: 'Cancelado' };

let nav;
let cancelTyper = null;

export function init(navigation) {
  nav = navigation;
  $('#profile-start').addEventListener('click', () => nav.showIntro());
}

const initials = (name) => name.split(/\s+/).slice(0, 2).map((w) => w[0] || '').join('').toUpperCase();

export function enter() {
  const p = state.perfil;
  const ex = p.examen;
  document.querySelectorAll('[data-initials]').forEach((el) => { el.textContent = initials(p.nombre); });
  $('#profile-name').textContent = p.nombre;
  $('#profile-role').textContent = `Sustentante · EXAUBI ${p.convocatoria}`;
  $('#profile-folio').textContent = p.folio;
  $('#profile-idioma').textContent = p.idioma;
  $('#profile-correo').textContent = p.correo || '—';
  $('#profile-exam-title').textContent = ex ? ex.titulo : `EXAUBI · ${p.idioma}`;
  $('#profile-status').textContent = ex ? STATUS[p.estado] || p.estado : 'No disponible';
  $('#profile-duration').textContent = ex ? ex.duracion_min : '—';
  $('#profile-questions').textContent = ex ? ex.preguntas : '—';
  $('#profile-deadline').textContent = ex?.disponible_hasta
    ? new Date(ex.disponible_hasta).toLocaleDateString('es-MX', { day: 'numeric', month: 'short' })
    : 'Sin límite';
  $('#profile-start').disabled = !ex || p.estado === 'finalizado';
  say(TYPED.profile);
}

// Bee bot bubble: typed segments, or a plain message (e.g. an API error).
export function say(content) {
  if (cancelTyper) cancelTyper();
  cancelTyper = typewriter($('#profile-typed'), typeof content === 'string' ? [[content]] : content);
}
