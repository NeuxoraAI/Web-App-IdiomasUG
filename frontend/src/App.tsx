// Screens are a plain state switch (no router).

import { useSession } from './context/SessionContext';
// Import order is the stylesheet cascade order: login, profile, instructions, exam, results.
import { Login } from './pages/Login/Login';
import { Profile } from './pages/Profile/Profile';
import { Instructions } from './pages/Instructions/Instructions';
import { Exam } from './pages/Exam/Exam';
import { Results } from './pages/Results/Results';
import { Panel } from './pages/Panel/Panel';

export function App() {
  const enPanel = location.pathname.startsWith('/panel'); // read once; no router
  const { screen, perfil, exam } = useSession();
  if (enPanel) return <Panel />;
  if (screen === 'login') return <Login />;
  if (!perfil) return null;
  if (screen === 'profile') return <Profile />;
  if (screen === 'intro') return <Instructions />;
  if (screen === 'test' && exam) return <Exam exam={exam} />;
  if (screen === 'results') return <Results />;
  return null;
}
