// Bee bot help chat: scripted FAQ replies with a "thinking" pause and typed answers.
// Mounted while the panel is open, so closing it cancels timers and clears the chat.

import { useCallback, useEffect, useRef, useState } from 'react';
import beeBot from '../../assets/bee-bot.webp';
import { TypedText } from '../../components/ui/TypedText';
import { FAQS, THINK, TYPED } from '../../data/copy';

type Message = { id: number; bot: boolean; text: string };   // bot: text is a TYPED key

const pickWord = () => THINK[Math.floor(Math.random() * THINK.length)];
const replyDelay = () => 1400 + Math.random() * 900;

export function HelpChat() {
  const [messages, setMessages] = useState<Message[]>([{ id: 0, bot: true, text: 'help' }]);
  const [thinkWord, setThinkWord] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const box = useRef<HTMLDivElement>(null);
  const nextId = useRef(1);
  const timers = useRef<{ word?: number; reply?: number }>({});

  useEffect(() => () => {
    clearInterval(timers.current.word);
    clearTimeout(timers.current.reply);
  }, []);

  const scrollChat = useCallback(() => {
    requestAnimationFrame(() => {
      if (box.current) box.current.scrollTop = box.current.scrollHeight;
    });
  }, []);
  useEffect(scrollChat, [messages, thinkWord, scrollChat]);

  const add = (bot: boolean, text: string) =>
    setMessages((m) => [...m, { id: nextId.current++, bot, text }]);

  function ask(key: string, question: string) {
    if (thinkWord) return;
    add(false, question);
    setThinkWord(pickWord());
    timers.current.word = setInterval(() => setThinkWord(pickWord()), 420);
    timers.current.reply = setTimeout(() => {
      clearInterval(timers.current.word);
      setThinkWord(null);
      add(true, key);
    }, replyDelay());
  }

  return (
    <div id="help-panel" className="help-panel">
      <div className="help-header">
        <img src={beeBot} width="144" height="144" loading="lazy" decoding="async" alt="" className="help-header-avatar" />
        <div className="help-header-names">
          <span className="help-header-name">Bee bot</span>
          <span className="help-header-role">Asistente de ayuda</span>
        </div>
      </div>
      <div ref={box} className="chat-messages" data-chat-scroll="true">
        {messages.map((m) => m.bot
          ? <div key={m.id} className="chat-msg-bot"><TypedText parts={TYPED[m.text]} onTick={scrollChat} /></div>
          : <div key={m.id} className="chat-msg-user">{m.text}</div>)}
        {thinkWord && (
          <div className="chat-msg-thinking">
            <span className="chat-thinking-dot" />
            <span className="chat-thinking-word">{thinkWord}</span>
          </div>
        )}
      </div>
      <div className="chat-footer">
        <div className="chat-quick" style={thinkWord ? { display: 'none' } : undefined}>
          {FAQS.filter((f) => f.key !== 'faq_human').map((f) => (
            <button key={f.key} className="chat-quick-btn" onClick={() => ask(f.key, f.q)}>{f.q}</button>
          ))}
          <button className="chat-quick-btn chat-quick-btn--human" onClick={() => ask('faq_human', 'Quiero hablar con una persona de servicios')}>
            Hablar con una persona
          </button>
        </div>
        <form
          className="chat-form"
          onSubmit={(e) => {
            e.preventDefault();
            const text = input.trim();
            if (!text) return;
            setInput('');
            ask('faq_ai', text);
          }}
        >
          <input type="text" className="chat-input" placeholder="Escribe tu pregunta…" value={input} onChange={(e) => setInput(e.target.value)} />
          <button type="submit" className="chat-send" aria-label="Enviar"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 6l6 6-6 6"></path></svg></button>
        </form>
        <div className="chat-contact">Tel. 477 267 49 00 ext. 4751 · Lun a vie, 9:00–18:00 · Powered by Neuxora</div>
      </div>
    </div>
  );
}
