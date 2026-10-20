import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './assets/styles/tokens.css';
import './assets/styles/base.css';
import { App } from './App';
import { SessionProvider } from './context/SessionContext';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <SessionProvider>
      <App />
    </SessionProvider>
  </StrictMode>,
);
