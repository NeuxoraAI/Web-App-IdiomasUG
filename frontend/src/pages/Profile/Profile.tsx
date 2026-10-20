// Profile screen: applicant data and exam summary from the API, Bee bot typed hint.

import './profile.css';
import beeBot from '../../assets/bee-bot.webp';
import { AppShell } from '../../components/layout/AppShell';
import { TypedText } from '../../components/ui/TypedText';
import { usePerfil, useSession } from '../../context/SessionContext';
import { TYPED } from '../../data/copy';
import { initials } from '../../utils/format';

const STATUS: Record<string, string> = { pendiente: 'Disponible', en_curso: 'En curso', finalizado: 'Finalizado', cancelado: 'Cancelado' };

export function Profile() {
  const { profileNotice, showIntro } = useSession();
  const p = usePerfil();
  const ex = p.examen;

  return (
    <AppShell>
      <main className="page page--wide">
        <h1 className="page-title">Mi perfil</h1>
        <div className="profile-grid">
          <section className="card profile-card">
            <div className="profile-identity">
              <div className="profile-avatar">{initials(p.nombre)}</div>
              <div className="profile-names">
                <div className="profile-name">{p.nombre}</div>
                <div className="profile-role">Sustentante · EXAUBI {p.convocatoria}</div>
              </div>
            </div>
            <div className="profile-divider"></div>
            <dl className="profile-facts">
              <dt>Folio</dt><dd className="profile-folio">{p.folio}</dd>
              <dt>Campus</dt><dd>León</dd>
              <dt>Idioma</dt><dd>{p.idioma}</dd>
              <dt>Correo</dt><dd>{p.correo || '—'}</dd>
            </dl>
          </section>
          <section className="card card--accent profile-exam-card">
            <div className="profile-exam-head">
              <div className="profile-exam-titles">
                <div className="eyebrow">Examen asignado</div>
                <h2 className="card-title">{ex ? ex.titulo : `EXAUBI · ${p.idioma}`}</h2>
              </div>
              <span className="profile-exam-status">{ex ? STATUS[p.estado] || p.estado : 'No disponible'}</span>
            </div>
            <div className="profile-stats">
              <div className="profile-stat"><span className="profile-stat-label">Duración</span><span className="profile-stat-value">{ex ? ex.duracion_min : '—'} min</span></div>
              <div className="profile-stat"><span className="profile-stat-label">Preguntas</span><span className="profile-stat-value">{ex ? ex.preguntas : '—'}</span></div>
              <div className="profile-stat"><span className="profile-stat-label">Intento</span><span className="profile-stat-value">Único</span></div>
              <div className="profile-stat">
                <span className="profile-stat-label">Fecha límite</span>
                <span className="profile-stat-value">
                  {ex?.disponible_hasta
                    ? new Date(ex.disponible_hasta).toLocaleDateString('es-MX', { day: 'numeric', month: 'short' })
                    : 'Sin límite'}
                </span>
              </div>
            </div>
            <div className="bee-row">
              <img src={beeBot} width="144" height="144" loading="lazy" decoding="async" alt="" className="profile-bee" />
              <div className="speech-bubble speech-bubble--cream">
                {/* Bee bot bubble: the usual hint, or a plain message (e.g. an API error) */}
                <span><TypedText key={profileNotice ?? ''} parts={profileNotice ? [[profileNotice]] : TYPED.profile} /></span>
              </div>
            </div>
            <button className="btn-primary profile-start" disabled={!ex || p.estado === 'finalizado'} onClick={showIntro}>Iniciar examen</button>
          </section>
        </div>
      </main>
    </AppShell>
  );
}
