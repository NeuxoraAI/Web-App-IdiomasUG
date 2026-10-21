import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './assets/styles/tokens.css';
import './assets/styles/base.css';
import { App } from './App';
import { SessionProvider } from './context/SessionContext';
import { Panel } from './pages/Panel/Panel';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* /panel is the staff app: no applicant session around it. Read once; no router. */}
    {location.pathname.startsWith('/panel') ? <Panel /> : (
      <SessionProvider>
        <App />
      </SessionProvider>
    )}
  </StrictMode>,
);
