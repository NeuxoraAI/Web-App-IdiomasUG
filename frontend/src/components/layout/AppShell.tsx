// App shell for every screen after the login: header with the timer during
// the test (pass secondsLeft) and the navigation everywhere else.

import type { ReactNode } from 'react';
import escudo from '../../assets/escudo-ug.webp';
import { usePerfil, useSession } from '../../context/SessionContext';
import { fmt, initials } from '../../utils/format';

export function AppShell({ secondsLeft, children }: { secondsLeft?: number; children: ReactNode }) {
  const { screen, showProfile, showIntro, logout } = useSession();
  const perfil = usePerfil();
  const testing = secondsLeft !== undefined;

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-brand">
          <div className="app-header-shield"><img src={escudo} width="150" height="128" loading="lazy" decoding="async" alt="" /></div>
          <div className="app-header-names">
            <div className="app-header-university">Universidad de Guanajuato</div>
            <div className="app-header-center">Centro de Servicios de Lenguas Extranjeras · EXAUBI</div>
          </div>
        </div>
        {testing ? (
          <div className="header-timer">
            <span className="header-timer-label">Tiempo restante</span>
            <div className={`timer-badge${secondsLeft < 300 ? ' is-low' : ''}`}>{fmt(secondsLeft)}</div>
          </div>
        ) : (
          <nav className="app-nav">
            <button className={`app-nav-link${screen === 'profile' ? ' is-active' : ''}`} onClick={showProfile}>Perfil</button>
            <button className={`app-nav-link${screen === 'intro' || screen === 'results' ? ' is-active' : ''}`} onClick={showIntro}>Examen</button>
            <div className="app-nav-user">
              <div className="app-nav-avatar">{initials(perfil.nombre)}</div>
              <button className="app-nav-logout" onClick={logout}>Cerrar sesión</button>
            </div>
          </nav>
        )}
      </header>
      {children}
    </div>
  );
}
