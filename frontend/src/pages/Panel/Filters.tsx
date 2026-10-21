// Search box + language and status filters shared by the panel tables. Filtering is
// client-side over the full list.
// ponytail: client-side filter; move it to the API if a convocatoria grows past a few thousand rows.

import { useMemo, useState } from 'react';
import type { EstadoAsignacion } from '../../api/types';
import { ESTADOS } from '../../utils/format';

type Row = { nombre: string; curp: string; folio: string; idioma: string; estado: EstadoAsignacion };

const normalize = (s: string) => s.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();

export function useFilter<T extends Row>(rows: T[]) {
  const [q, setQ] = useState('');
  const [language, setLanguage] = useState('');
  const [status, setStatus] = useState('');
  const languages = useMemo(() => [...new Set(rows.map((r) => r.idioma))].sort(), [rows]);
  const statuses = useMemo(
    () => (Object.keys(ESTADOS) as EstadoAsignacion[]).filter((e) => rows.some((r) => r.estado === e)),
    [rows],
  );
  const visible = useMemo(() => {
    const t = normalize(q.trim());
    return rows.filter((r) => (!language || r.idioma === language) && (!status || r.estado === status)
      && (!t || normalize(`${r.nombre} ${r.curp} ${r.folio}`).includes(t)));
  }, [rows, q, language, status]);
  return { q, setQ, language, setLanguage, status, setStatus, languages, statuses, visible };
}

export function Filters({ q, setQ, language, setLanguage, status, setStatus, languages, statuses, total, visible }:
  Omit<ReturnType<typeof useFilter>, 'visible'> & { total: number; visible: number }) {
  return (
    <div className="panel-filters">
      <input type="search" className="panel-input" placeholder="Buscar por nombre, CURP o folio"
        aria-label="Buscar" value={q} onChange={(e) => setQ(e.target.value)} />
      <select className="panel-input" aria-label="Idioma" value={language} onChange={(e) => setLanguage(e.target.value)}>
        <option value="">Todos los idiomas</option>
        {languages.map((l) => <option key={l} value={l}>{l}</option>)}
      </select>
      <select className="panel-input" aria-label="Estado" value={status} onChange={(e) => setStatus(e.target.value)}>
        <option value="">Todos los estados</option>
        {statuses.map((e) => <option key={e} value={e}>{ESTADOS[e]}</option>)}
      </select>
      <span className="panel-count">{visible} de {total}</span>
    </div>
  );
}
