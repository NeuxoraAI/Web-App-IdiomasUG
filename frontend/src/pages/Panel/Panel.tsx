// Staff panel (/panel): own login and session, separate from the applicant flow.

import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import './panel.css';
import { api, KEY_PERSONAL, setToken } from '../../api/client';
import type { SesionPersonalRequest, SesionPersonalResponse, UsuarioPersonal } from '../../api/types';
import { apiStaff, SESSION_EXPIRED } from './apiStaff';
import { Applicants } from './Applicants';
import { Exams } from './Exams';

const TABS: Record<UsuarioPersonal['rol'], [string, () => ReactNode][]> = {
  admin: [['Exámenes', Exams], ['Solicitantes', Applicants]],
  profesor: [['Exámenes', Exams]],
};

const logout = () => setToken(null, KEY_PERSONAL);

function StaffLogin({ onLogin }: { onLogin: (u: UsuarioPersonal) => void }) {
  const [correo, setCorreo] = useState('');
  const [clave, setClave] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body: SesionPersonalRequest = { correo, clave };
      const r = await api<SesionPersonalResponse>('POST', '/personal/sesion', body, KEY_PERSONAL);
      setToken(r.token, KEY_PERSONAL);
      onLogin(r.usuario);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="panel-login">
      <form className="card card--accent panel-form" onSubmit={submit}>
        <h1 className="card-title">Panel del Centro</h1>
        <label className="panel-label">Correo
          <input type="email" className="panel-input" value={correo} required autoComplete="username"
            onChange={(e) => setCorreo(e.target.value)} />
        </label>
        <label className="panel-label">Contraseña
          <input type="password" className="panel-input" value={clave} required autoComplete="current-password"
            onChange={(e) => setClave(e.target.value)} />
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button type="submit" className="btn-primary" disabled={busy}>Iniciar sesión</button>
      </form>
    </main>
  );
}

export function Panel() {
  const [user, setUser] = useState<UsuarioPersonal | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState(0);

  useEffect(() => {
    const close = () => { logout(); setUser(null); setTab(0); };
    window.addEventListener(SESSION_EXPIRED, close);
    apiStaff<UsuarioPersonal>('GET', '/personal/yo')
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
    return () => window.removeEventListener(SESSION_EXPIRED, close);
  }, []);

  if (loading) return null;
  if (!user) return <StaffLogin onLogin={setUser} />;

  const tabs = TABS[user.rol];
  const Tab = tabs[tab][1];
  return (
    <div className="panel">
      <header className="panel-header">
        <span className="panel-user"><strong>{user.nombre}</strong> · {user.rol}</span>
        <button type="button" className="btn-outline" onClick={() => { logout(); setUser(null); setTab(0); }}>
          Cerrar sesión
        </button>
      </header>
      <div className="panel-tabs" role="tablist" aria-label="Secciones del panel">
        {tabs.map(([t], i) => (
          <button key={t} type="button" role="tab" id={`tab-${i}`} aria-selected={i === tab}
            aria-controls="panel-content" className="panel-tab" onClick={() => setTab(i)}>{t}</button>
        ))}
      </div>
      <section id="panel-content" role="tabpanel" aria-labelledby={`tab-${tab}`} className="panel-body">
        <Tab key={tab} />
      </section>
    </div>
  );
}
