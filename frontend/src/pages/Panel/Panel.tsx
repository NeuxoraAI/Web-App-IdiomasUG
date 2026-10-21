// Staff panel (/panel): own login and session, separate from the applicant flow.

import { useEffect, useState, type FormEvent } from 'react';
import './panel.css';
import { api, ApiError, KEY_PERSONAL, setToken } from '../../api/client';
import type { SesionPersonalRequest, SesionPersonalResponse, UsuarioPersonal } from '../../api/types';

const TABS: Record<UsuarioPersonal['rol'], string[]> = {
  admin: ['Calificaciones', 'Solicitantes', 'Exámenes'],
  profesor: ['Calificaciones'],
};

const salir = (tokenKey = KEY_PERSONAL) => setToken(null, tokenKey);

function LoginPersonal({ onLogin }: { onLogin: (u: UsuarioPersonal) => void }) {
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
        {error && <p className="login-form-error" role="alert">{error}</p>}
        <button type="submit" className="btn-primary" disabled={busy}>Iniciar sesión</button>
      </form>
    </main>
  );
}

export function Panel() {
  const [usuario, setUsuario] = useState<UsuarioPersonal | null>(null);
  const [cargando, setCargando] = useState(true);
  const [tab, setTab] = useState(0);

  useEffect(() => {
    api<UsuarioPersonal>('GET', '/personal/yo', undefined, KEY_PERSONAL)
      .then(setUsuario)
      .catch((err) => { if (err instanceof ApiError && err.status === 401) salir(); })
      .finally(() => setCargando(false));
  }, []);

  if (cargando) return null;
  if (!usuario) return <LoginPersonal onLogin={setUsuario} />;

  const tabs = TABS[usuario.rol];
  return (
    <div className="panel">
      <header className="panel-header">
        <span className="panel-user"><strong>{usuario.nombre}</strong> · {usuario.rol}</span>
        <button type="button" className="btn-outline" onClick={() => { salir(); setUsuario(null); setTab(0); }}>
          Cerrar sesión
        </button>
      </header>
      <div className="panel-tabs" role="tablist" aria-label="Secciones del panel">
        {tabs.map((t, i) => (
          <button key={t} type="button" role="tab" id={`tab-${i}`} aria-selected={i === tab}
            aria-controls="panel-cuerpo" className="panel-tab" onClick={() => setTab(i)}>{t}</button>
        ))}
      </div>
      <section id="panel-cuerpo" role="tabpanel" aria-labelledby={`tab-${tab}`} className="panel-body">
        <p>{tabs[tab]}: próximamente.</p>
      </section>
    </div>
  );
}
