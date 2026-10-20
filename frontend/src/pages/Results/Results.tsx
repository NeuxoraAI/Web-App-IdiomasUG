// Results screen: score summary, per-part breakdown, and auto-logout countdown.

import './results.css';
import abejaLentes from '../../assets/abeja-lentes.webp';
import abejaOk from '../../assets/abeja-ok.webp';
import { AppShell } from '../../components/layout/AppShell';
import { useSession } from '../../context/SessionContext';
import { useCountdown } from '../../hooks/useCountdown';
import { fmt } from '../../utils/format';

export function Results() {
  const { resultado: r, logout } = useSession();
  const closeIn = useCountdown(20, logout);
  if (!r) return null;

  return (
    <AppShell>
      <main className="page">
        <section className="results-hero">
          <img src={abejaOk} width="229" height="400" loading="lazy" decoding="async" alt="" className="results-bee" />
          <div className="results-hero-body">
            <div className="results-badge"><span className="results-mcer">{r.mcer}</span></div>
            <div className="results-hero-text">
              <div className="results-hero-tags">
                <span className="eyebrow results-completed">¡Examen completado!</span>
                <span className="results-beta">Nivel Beta Test</span>
              </div>
              <h1 className="results-level">{r.nivel}</h1>
              <p className="results-summary">{`${r.aciertos} de ${r.calificables} respuestas correctas · ${fmt(r.segundos_usados)} utilizados`}</p>
            </div>
          </div>
        </section>
        <section className="card">
          <h2 className="card-title">Desempeño por parte</h2>
          <div id="results-sections">
            {r.por_parte.map((s) => (
              <div key={s.parte} className="results-section">
                <div className="results-section-head"><span>{s.nombre}</span><span className="results-section-score">{s.aciertos} / {s.total}</span></div>
                <div className="results-section-track"><div className="results-section-fill" style={{ width: `${s.porcentaje}%` }}></div></div>
              </div>
            ))}
          </div>
          <p className="results-note">El texto breve se revisa manualmente y no cuenta para este puntaje preliminar.</p>
        </section>
        <section className="bee-row results-farewell">
          <img src={abejaLentes} width="177" height="340" loading="lazy" decoding="async" alt="" className="results-farewell-bee" />
          <div className="speech-bubble speech-bubble--cream">
            <p className="results-farewell-title">¡Gracias por participar, abeja!</p>
            <p>Tu resultado quedó registrado y lo recibirás en tu correo institucional. Este examen permite un solo intento, así que tu sesión se cerrará en <strong>{closeIn} s</strong>.</p>
          </div>
        </section>
        <div className="actions">
          <button className="btn-primary" onClick={logout}>Cerrar sesión ahora</button>
        </div>
      </main>
    </AppShell>
  );
}
