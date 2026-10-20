// Instructions screen shown before the exam starts.

import './instructions.css';
import abejaLentes from '../../assets/abeja-lentes.webp';
import { AppShell } from '../../components/layout/AppShell';
import { usePerfil, useSession } from '../../context/SessionContext';

export function Instructions() {
  const { startTest, showProfile } = useSession();
  const ex = usePerfil().examen;

  return (
    <AppShell>
      <main className="page">
        <div className="bee-row">
          <img src={abejaLentes} width="177" height="340" loading="lazy" decoding="async" alt="" className="instructions-bee" />
          <div className="speech-bubble">
            <div className="eyebrow instructions-eyebrow">Antes de comenzar</div>
            <p>Hola, soy tu guía. El examen tiene <strong>{ex ? ex.preguntas : '—'} preguntas</strong> de distinto tipo: opción múltiple, verdadero/falso, comprensión auditiva, palabras faltantes, completar arrastrando, traducir con fichas, relacionar, respuesta corta, imagen y un texto breve. Tienes <strong>{ex ? ex.duracion_min : '—'} minutos</strong>.</p>
          </div>
        </div>
        <section className="card instructions-rules">
          <ul>
            <li>Responde y pulsa <strong>Siguiente</strong>. Puedes omitir una pregunta si lo necesitas; no es posible regresar.</li>
            <li>Al agotarse el tiempo, el examen se envía automáticamente.</li>
            <li>No uses diccionarios ni traductores. Usa audífonos para la parte auditiva.</li>
            <li><strong>No está permitido el uso de inteligencia artificial.</strong> El texto del examen está protegido: si lo copias a un asistente de IA, este no podrá responder.</li>
          </ul>
        </section>
        <div className="actions">
          <button className="btn-primary" onClick={startTest}>Comenzar examen</button>
          <button className="btn-outline" onClick={showProfile}>Volver</button>
        </div>
      </main>
    </AppShell>
  );
}
