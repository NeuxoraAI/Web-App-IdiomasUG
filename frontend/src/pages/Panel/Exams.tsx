// Exámenes tab (admin and profesor): every started or finished exam with its grade.

import { useEffect, useState } from 'react';
import type { ExamenPresentado } from '../../api/types';
import { ESTADOS, fecha } from '../../utils/format';
import { apiStaff } from './apiStaff';
import { Filters, useFilter } from './Filters';

export function Exams() {
  const [rows, setRows] = useState<ExamenPresentado[]>([]);
  const [error, setError] = useState<string | null>(null);
  const filter = useFilter(rows);

  useEffect(() => {
    apiStaff<ExamenPresentado[]>('GET', '/personal/examenes')
      .then(setRows)
      .catch((err) => setError((err as Error).message));
  }, []);

  return (
    <div className="panel-list">
      <Filters {...filter} total={rows.length} visible={filter.visible.length} />
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="panel-table">
        <table>
          <thead>
            <tr>
              <th>Folio</th><th>Nombre</th><th>CURP</th><th>Idioma</th><th>Estado</th>
              <th>Aciertos</th><th>Nivel</th><th>Terminado</th>
            </tr>
          </thead>
          <tbody>
            {filter.visible.map((r) => (
              <tr key={r.folio}>
                <td>{r.folio}</td><td>{r.nombre}</td><td>{r.curp}</td><td>{r.idioma}</td>
                <td>{ESTADOS[r.estado]}</td>
                <td>{r.aciertos != null ? `${r.aciertos} / ${r.calificables}` : '—'}</td>
                <td>{r.mcer ? `${r.mcer} · ${r.nivel}` : '—'}</td>
                <td>{fecha(r.finalizado_en)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {filter.visible.length === 0 && <p className="panel-empty">Sin exámenes que mostrar.</p>}
      </div>
    </div>
  );
}
