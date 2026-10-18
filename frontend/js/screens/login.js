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

  $('#login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    closeHelp();
    const button = $('#login-button');
    button.disabled = true;
    $('#login-error').hidden = true;
    try {
      await nav.login(state.curp, state.code);
    } catch (err) {
      showError(err.message);
    } finally {
      button.disabled = false;
    }
  });
  $('#login-code').addEventListener('input', (e) => { state.code = e.target.value; });
  $('#login-curp').addEventListener('input', (e) => { state.curp = e.target.value.toUpperCase(); });

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
  // Flags are built once; renderFlips only swaps the names and the active tile
  $('#login-flags').innerHTML = CHIPS.map(([, , code, flag]) =>
    `<li class="login-flag" data-lang="${code}"><img src="./assets/flags/${flag}.svg" width="56" height="42" alt=""><span class="login-flag-name"></span></li>`).join('');
}

export function showError(message) {
  const el = $('#login-error');
  el.textContent = message;
  el.hidden = false;
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

// Every translation is stacked in the same grid cell; the hidden ones only
// reserve space, so the box always fits the longest text and never resizes.
function flipHTML(texts, wrap) {
  const cur = texts[lang];
  const prev = prevLang != null ? texts[prevLang] : null;
  const faces = [...new Set(texts)].map((t) => {
    let cls = 'flip-face flip-face--ghost';
    if (t === cur) cls = prev != null && prev !== cur ? 'flip-face flip-face--in' : 'flip-face';
    else if (t === prev) cls = 'flip-face flip-face--out';
    return `<span class="${cls}"${cls.includes('ghost') || t === prev ? ' aria-hidden="true"' : ''}>${esc(t)}</span>`;
  });
  return `<span class="flip${wrap ? ' flip--wrap' : ''}">${faces.join('')}</span>`;
}

function renderFlips() {
  $('#login-center').innerHTML = flipHTML(T.center, true);
  $('#login-tagline').innerHTML = flipHTML(T.tagline);
  $('#login-welcome').innerHTML = flipHTML(T.welcome);
  $('#login-title').innerHTML = flipHTML(T.title);
  $('#login-button').innerHTML = flipHTML(T.button);
  document.querySelectorAll('.login-flag').forEach((tile, i) => {
    const [es, native, code] = CHIPS[i];
    tile.classList.toggle('is-active', LANGS[lang] === code);
    tile.querySelector('.login-flag-name').innerHTML = flipHTML(LANGS.map((_, k) => (k % 2 ? native : es)));
  });
}

/* ---- Bee bot chat ---- */

function toggleHelp() {
  const panel = $('#help-panel');
  if (panel.hidden) {
    panel.hidden = false;
    $('#help-toggle').setAttribute('aria-expanded', 'true');
    openChat();
  } else {
    closeHelp();
  }
}

function closeHelp() {
  $('#help-panel').hidden = true;
  $('#help-toggle').setAttribute('aria-expanded', 'false');
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
