// Search box + language filter shared by the panel tables. Filtering is
// client-side over the full list.
// ponytail: client-side filter; move it to the API if a convocatoria grows past a few thousand rows.

import { useMemo, useState } from 'react';

type Fila = { nombre: string; curp: string; folio: string; idioma: string };

const normalizar = (s: string) => s.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();

export function useFiltro<T extends Fila>(filas: T[]) {
  const [q, setQ] = useState('');
  const [idioma, setIdioma] = useState('');
  const idiomas = useMemo(() => [...new Set(filas.map((f) => f.idioma))].sort(), [filas]);
  const visibles = useMemo(() => {
    const t = normalizar(q.trim());
    return filas.filter((f) => (!idioma || f.idioma === idioma)
      && (!t || normalizar(`${f.nombre} ${f.curp} ${f.folio}`).includes(t)));
  }, [filas, q, idioma]);
  return { q, setQ, idioma, setIdioma, idiomas, visibles };
}

export function Filtros({ q, setQ, idioma, setIdioma, idiomas, total, visibles }:
  Omit<ReturnType<typeof useFiltro>, 'visibles'> & { total: number; visibles: number }) {
  return (
    <div className="panel-filtros">
      <input type="search" className="panel-input" placeholder="Buscar por nombre, CURP o folio"
        aria-label="Buscar" value={q} onChange={(e) => setQ(e.target.value)} />
      <select className="panel-input" aria-label="Idioma" value={idioma} onChange={(e) => setIdioma(e.target.value)}>
        <option value="">Todos los idiomas</option>
        {idiomas.map((i) => <option key={i} value={i}>{i}</option>)}
      </select>
      <span className="panel-conteo">{visibles} de {total}</span>
    </div>
  );
}

export const ESTADOS: Record<string, string> = {
  pendiente: 'Pendiente', en_curso: 'En curso', finalizado: 'Finalizado', cancelado: 'Cancelado',
};

export const fecha = (iso?: string | null) => (iso ? new Date(iso).toLocaleString('es-MX') : '—');
