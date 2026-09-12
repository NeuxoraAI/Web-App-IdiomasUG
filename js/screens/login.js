// Login screen: rotating multilingual hero texts, access form, Bee bot help chat.

import { state } from '../state.js';
import { $, esc } from '../lib/dom.js';
import { typewriter } from '../lib/typewriter.js';
import { LANGS, T, TYPED, THINK, FAQS, CHIPS } from '../data/copy.js';

let nav;
let lang = 0;
let prevLang = null;
let rotateId = null;

// Chat internals
let thinking = false;
let thinkWordId = null;
let replyId = null;
let cancelTypers = [];

export function init(navigation) {
  nav = navigation;

  $('#login-form').addEventListener('submit', (e) => {
    e.preventDefault();
    closeHelp();
    nav.showProfile();
  });
  $('#login-code').addEventListener('input', (e) => { state.email = e.target.value; });

  $('#help-toggle').addEventListener('click', toggleHelp);
  $('#chat-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const input = $('#chat-input');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    ask('faq_ai', text);
  });

  renderQuickReplies();
}

export function enter() {
  lang = 0;
  prevLang = null;
  renderFlips();
  clearInterval(rotateId);
  rotateId = setInterval(() => {
    prevLang = lang;
    lang = (lang + 1) % LANGS.length;
    renderFlips();
  }, 4200);
}

export function leave() {
  clearInterval(rotateId);
  rotateId = null;
}

/* ---- Language flip ---- */

function flipHTML(texts, wrap) {
  const fwd = lang % 2 === 0;
  let faces = '';
  if (prevLang != null && prevLang !== lang) {
    faces += `<span class="flip-face flip-face--out-${fwd ? 'f' : 'b'}">${esc(texts[prevLang])}</span>`;
  }
  const inCls = prevLang != null ? ` flip-face--in-${fwd ? 'f' : 'b'}` : '';
  faces += `<span class="flip-face${inCls}">${esc(texts[lang])}</span>`;
  return `<span class="flip${wrap ? ' flip--wrap' : ''}">${faces}</span>`;
}

function renderFlips() {
  $('#login-center').innerHTML = flipHTML(T.center, true);
  $('#login-tagline').innerHTML = flipHTML(T.tagline);
  $('#login-welcome').innerHTML = flipHTML(T.welcome);
  $('#login-title').innerHTML = flipHTML(T.title);
  $('#login-button').innerHTML = flipHTML(T.button);
  $('#login-chips').innerHTML = CHIPS.map(([es, native, code]) => {
    const active = LANGS[lang] === code;
    const texts = LANGS.map((_, k) => (k % 2 ? native : es));
    return `<span class="login-chip${active ? ' is-active' : ''}">${flipHTML(texts)}</span>`;
  }).join('');
}

/* ---- Bee bot chat ---- */

function toggleHelp() {
  const panel = $('#help-panel');
  if (panel.hidden) {
    panel.hidden = false;
    openChat();
  } else {
    closeHelp();
  }
}

function closeHelp() {
  $('#help-panel').hidden = true;
  stopThinking();
  $('#chat-input').value = '';
}

function stopThinking() {
  thinking = false;
  clearInterval(thinkWordId);
  clearTimeout(replyId);
  setQuickVisible(true);
}

function openChat() {
  stopThinking();
  cancelTypers.forEach((c) => c());
  cancelTypers = [];
  const box = $('#chat-messages');
  box.innerHTML = '';
  addBotTyped('help');
}

function scrollChat() {
  const el = $('#chat-messages');
  requestAnimationFrame(() => { el.scrollTop = el.scrollHeight; });
}

function addBotTyped(key) {
  const box = $('#chat-messages');
  const el = document.createElement('div');
  el.className = 'chat-msg-bot';
  box.appendChild(el);
  cancelTypers.push(typewriter(el, TYPED[key], { onTick: scrollChat }));
  scrollChat();
}

function setQuickVisible(visible) {
  $('#chat-quick').style.display = visible ? '' : 'none';
}

function ask(key, question) {
  if (thinking) return;
  thinking = true;
  setQuickVisible(false);

  const box = $('#chat-messages');
  const user = document.createElement('div');
  user.className = 'chat-msg-user';
  user.textContent = question;
  box.appendChild(user);

  const think = document.createElement('div');
  think.className = 'chat-msg-thinking';
  think.innerHTML = '<span class="chat-thinking-dot"></span><span class="chat-thinking-word"></span>';
  box.appendChild(think);
  const word = think.querySelector('.chat-thinking-word');
  const pickWord = () => THINK[Math.floor(Math.random() * THINK.length)];
  word.textContent = pickWord();
  scrollChat();

  thinkWordId = setInterval(() => { word.textContent = pickWord(); }, 420);
  replyId = setTimeout(() => {
    clearInterval(thinkWordId);
    thinking = false;
    setQuickVisible(true);
    think.remove();
    addBotTyped(key);
  }, 1400 + Math.random() * 900);
}

function renderQuickReplies() {
  const wrap = $('#chat-quick');
  wrap.innerHTML = '';
  FAQS.filter((f) => f.key !== 'faq_human').forEach((f) => {
    const btn = document.createElement('button');
    btn.className = 'chat-quick-btn';
    btn.textContent = f.q;
    btn.addEventListener('click', () => ask(f.key, f.q));
    wrap.appendChild(btn);
  });
  const human = document.createElement('button');
  human.className = 'chat-quick-btn chat-quick-btn--human';
  human.textContent = 'Hablar con una persona';
  human.addEventListener('click', () => ask('faq_human', 'Quiero hablar con una persona de servicios'));
  wrap.appendChild(human);
}
