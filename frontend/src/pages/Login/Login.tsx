// Login screen: rotating multilingual hero texts, access form, Bee bot help chat.

import { useEffect, useState, type FormEvent } from 'react';
import './login.css';
import abejaOk from '../../assets/abeja-ok.webp';
import beeBot from '../../assets/bee-bot.webp';
import ecosistema from '../../assets/ecosistema-vida-ug.webp';
import escudo from '../../assets/escudo-ug.webp';
import { Flip } from '../../components/ui/Flip';
import { useSession } from '../../context/SessionContext';
import { CHIPS, LANGS, T } from '../../data/copy';
import { HelpChat } from './HelpChat';

const FLAGS = import.meta.glob<string>('../../assets/flags/*.svg', { eager: true, import: 'default' });

export function Login() {
  const { curp, setCurp, login, loginError } = useSession();
  const [code, setCode] = useState('');
  const [error, setError] = useState(loginError);
  const [busy, setBusy] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [{ lang, prevLang }, setLangs] = useState<{ lang: number; prevLang: number | null }>({ lang: 0, prevLang: null });

  useEffect(() => {
    const id = setInterval(() => setLangs(({ lang }) => ({ prevLang: lang, lang: (lang + 1) % LANGS.length })), 4200);
    return () => clearInterval(id);
  }, []);

  const flip = { lang, prevLang };

  async function submit(e: FormEvent) {
    e.preventDefault();
    setHelpOpen(false);
    setBusy(true);
    setError(null);
    try {
      await login(curp, code);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="login">
      <header className="login-top">
        <img src={escudo} width="150" height="128" alt="Universidad de Guanajuato" className="login-top-ug" />
        <img src={ecosistema} width="187" height="144" decoding="async" alt="Ecosistema Vida UG · Campus León" className="login-top-vida" />
      </header>
      <div className="login-bar">
        <span className="login-bar-title">Centro de Servicios de Lenguas Extranjeras · Campus León</span>
        <span className="login-bar-exam">Examen de ubicación EXAUBI</span>
      </div>

      <div className="login-main">
        <div className="login-hero">
          <div className="login-hero-card">
            <h1 className="login-title"><Flip texts={T.center} wrap {...flip} /></h1>
            <div className="login-tagline"><Flip texts={T.tagline} {...flip} /></div>
          </div>
          <ul className="login-flags" aria-label="Idiomas del Centro">
            {CHIPS.map(([es, native, code, flag]) => (
              <li key={code} className={`login-flag${LANGS[lang] === code ? ' is-active' : ''}`} data-lang={code}>
                <img src={FLAGS[`../../assets/flags/${flag}.svg`]} width="56" height="42" alt="" />
                <span className="login-flag-name"><Flip texts={LANGS.map((_, k) => (k % 2 ? native : es))} {...flip} /></span>
              </li>
            ))}
          </ul>
          <div className="bee-row login-welcome-row">
            <img src={abejaOk} width="229" height="400" decoding="async" alt="" className="login-bee" />
            <div className="login-bee-text">
              <span className="login-welcome"><Flip texts={T.welcome} {...flip} /></span>
              <span className="login-invite">Tu examen de ubicación EXAUBI te espera. Ingresa tu código para comenzar.</span>
            </div>
          </div>
        </div>

        <div className="login-panel">
          <form className="card card--accent login-form" onSubmit={submit}>
            <div className="login-form-head">
              <div className="eyebrow">EXAUBI · Examen de ubicación</div>
              <h2 className="card-title"><Flip texts={T.title} {...flip} /></h2>
              <p className="login-form-hint">Ingresa el código de un solo uso que recibiste en tu correo institucional.</p>
            </div>
            <label className="login-code-label">CURP
              <input
                type="text" className="login-code-input login-curp-input"
                placeholder="ABCD123456HGTXYZ01" maxLength={18} required
                autoComplete="off" autoCapitalize="characters" spellCheck={false}
                pattern="[A-Za-z][AEIOUXaeioux][A-Za-z]{2}\d{6}[HMhm][A-Za-z]{2}[B-DF-HJ-NP-TV-ZÑb-df-hj-np-tv-zñ]{3}[A-Za-z\d]\d"
                title="18 caracteres con el formato oficial de la CURP."
                defaultValue={curp}
                onChange={(e) => setCurp(e.target.value.toUpperCase())}
              />
            </label>
            <label className="login-code-label">Código de acceso
              <input
                type="text" className="login-code-input" placeholder="XXXX-XXXX" maxLength={9}
                autoComplete="one-time-code" required value={code} onChange={(e) => setCode(e.target.value)}
              />
            </label>
            {error && <p className="form-error" role="alert">{error}</p>}
            <button type="submit" className="btn-primary" disabled={busy}><Flip texts={T.button} {...flip} /></button>
            <p className="login-form-note">El código es válido para un solo intento y expira al concluir el examen.</p>
          </form>
        </div>
      </div>

      <section className="login-steps" aria-labelledby="login-steps-title">
        <h2 className="login-steps-title" id="login-steps-title">¿Cómo funciona?</h2>
        <ol className="login-steps-list">
          <li className="login-step"><span className="login-step-num" aria-hidden="true">1</span><span><strong>Ingresa</strong> con tu CURP y el código de acceso que recibiste en tu correo institucional.</span></li>
          <li className="login-step"><span className="login-step-num" aria-hidden="true">2</span><span><strong>Lee las instrucciones</strong> y ten a la mano audífonos: hay una sección de comprensión auditiva.</span></li>
          <li className="login-step"><span className="login-step-num" aria-hidden="true">3</span><span><strong>Responde</strong> en un solo intento antes de que termine el tiempo. Tus respuestas se guardan solas.</span></li>
        </ol>
      </section>

      <footer className="login-foot">
        <img src={escudo} width="150" height="128" loading="lazy" decoding="async" alt="" className="login-foot-shield" />
        <p className="login-foot-address">Área de Servicios de Educación para la Vida · CE-VIDA UG-CL · Rectoría Campus León<br />Aquiles Serdán #924, Col. Obregón, León, Gto.<br />Tel. 477 267 49 00 ext. 4751 · Lunes a viernes, 9:00–18:00</p>
        <div className="login-foot-links">
          <span className="login-foot-hashtag">#SomosAbejasUG</span>
          <a href="https://www.ugto.mx/campusleon/lenguas/" target="_blank" rel="noopener">www.ugto.mx/campusleon/lenguas</a>
          <span className="login-foot-powered">Powered by <strong>Neuxora</strong></span>
        </div>
      </footer>

      <button className="help-toggle" aria-label="Ayuda" aria-controls="help-panel" aria-expanded={helpOpen} onClick={() => setHelpOpen(!helpOpen)}>
        <img src={beeBot} width="144" height="144" decoding="async" alt="" />
      </button>
      {helpOpen && <HelpChat />}
    </section>
  );
}
