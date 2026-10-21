// Session state and screen navigation shared by every page.

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { ApiError, api, getProgreso, getToken, setProgreso, setToken } from '../api/client';
import type { Examen, Perfil, Resultado, SesionRequest, SesionResponse } from '../api/types';
import { loadExam, type LoadedExam } from '../services/questions';

export type Screen = 'login' | 'profile' | 'intro' | 'test' | 'results';

interface Session {
  screen: Screen | null;          // null while a stored token is being checked
  curp: string;
  setCurp: (curp: string) => void;
  perfil: Perfil | null;
  resultado: Resultado | null;
  exam: LoadedExam | null;
  loginError: string | null;      // shown on the login form after a 401
  profileNotice: string | null;   // Bee bot says this on the profile instead of the usual hint
  login: (curp: string, clave: string) => Promise<void>;
  logout: () => void;
  showProfile: () => void;
  showIntro: () => void;
  startTest: () => Promise<void>;
  finishTest: () => Promise<void>;
  fail: (err: unknown) => void;
}

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [screen, setScreen] = useState<Screen | null>(() => (getToken() ? null : 'login'));
  const [curp, setCurp] = useState('');
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [exam, setExam] = useState<LoadedExam | null>(null);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [profileNotice, setProfileNotice] = useState<string | null>(null);

  const showLogin = useCallback((error: string | null = null) => {
    setToken(null);
    setPerfil(null);
    setResultado(null);
    setExam(null);
    setProgreso(null);
    setLoginError(error);
    setScreen('login');
  }, []);

  const showProfile = useCallback((notice: string | null = null) => {
    setProfileNotice(notice);
    setScreen('profile');
  }, []);

  // Expired session -> back to login with the server message; otherwise show it on the profile.
  const fail = useCallback((err: unknown) => {
    const e = err instanceof ApiError ? err : new ApiError(0, String(err));
    if (e.status === 401) showLogin(e.message);
    else showProfile(e.message);
  }, [showLogin, showProfile]);

  const login = useCallback(async (curp: string, clave: string) => {
    const r = await api<SesionResponse>('POST', '/sesion', { curp, clave } satisfies SesionRequest);
    setToken(r.token);
    setPerfil(r.perfil);
    showProfile();
  }, [showProfile]);

  const startTest = useCallback(async () => {
    try {
      const examen = await api<Examen>('POST', '/intento');
      // Resume where the applicant was: the server knows it across devices,
      // this tab's copy covers a position save that didn't arrive.
      setProgreso(Math.max(getProgreso(), examen.pregunta_actual));
      setExam(loadExam(examen));
      setPerfil((p) => p && { ...p, estado: 'en_curso' });
      setScreen('test');
    } catch (err) {
      fail(err);
    }
  }, [fail]);

  const finishTest = useCallback(async () => {
    try {
      const r = await api<Resultado>('POST', '/intento/finalizar');
      setResultado(r);
      setProgreso(null);
      setPerfil((p) => p && { ...p, estado: 'finalizado' });
      setScreen('results');
    } catch (err) {
      fail(err);
    }
  }, [fail]);

  // Boot: a stored token (page reload) resumes an exam in progress, otherwise shows the profile.
  useEffect(() => {
    if (!getToken()) return;
    api<Perfil>('GET', '/perfil')
      .then((p) => {
        setPerfil(p);
        if (p.estado === 'en_curso') startTest();
        else setScreen('profile');
      })
      .catch(() => showLogin());
  }, [showLogin, startTest]);

  const value = useMemo<Session>(() => ({
    screen, curp, setCurp, perfil, resultado, exam, loginError, profileNotice,
    login,
    logout: () => showLogin(),
    showProfile: () => showProfile(),
    showIntro: () => setScreen('intro'),
    startTest, finishTest, fail,
  }), [screen, curp, perfil, resultado, exam, loginError, profileNotice, login, showLogin, showProfile, startTest, finishTest, fail]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const s = useContext(SessionContext);
  if (!s) throw new Error('useSession must be used inside SessionProvider');
  return s;
}

// Pages below the login only render once the profile is loaded.
export function usePerfil() {
  const { perfil } = useSession();
  if (!perfil) throw new Error('No profile loaded');
  return perfil;
}
