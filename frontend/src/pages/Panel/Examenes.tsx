// Exámenes tab (admin and profesor): every started or finished exam with its grade.

import { useEffect, useState } from 'react';
import { api, KEY_PERSONAL } from '../../api/client';
import type { ExamenPresentado } from '../../api/types';
import { ESTADOS, fecha, Filtros, useFiltro } from './Filtros';

export function Examenes() {
  const [filas, setFilas] = useState<ExamenPresentado[]>([]);
  const [error, setError] = useState<string | null>(null);
  const filtro = useFiltro(filas);

  useEffect(() => {
    api<ExamenPresentado[]>('GET', '/personal/examenes', undefined, KEY_PERSONAL)
      .then(setFilas)
      .catch((err) => setError((err as Error).message));
  }, []);

  return (
    <>
      <Filtros {...filtro} total={filas.length} visibles={filtro.visibles.length} />
      {error && <p className="login-form-error" role="alert">{error}</p>}
      <div className="panel-tabla">
        <table>
          <thead>
            <tr>
              <th>Folio</th><th>Nombre</th><th>CURP</th><th>Idioma</th><th>Estado</th>
              <th>Aciertos</th><th>Nivel</th><th>Terminado</th>
            </tr>
          </thead>
          <tbody>
            {filtro.visibles.map((f) => (
              <tr key={f.folio}>
                <td>{f.folio}</td><td>{f.nombre}</td><td>{f.curp}</td><td>{f.idioma}</td>
                <td>{ESTADOS[f.estado]}</td>
                <td>{f.aciertos != null ? `${f.aciertos} / ${f.calificables}` : '—'}</td>
                <td>{f.mcer ? `${f.mcer} · ${f.nivel}` : '—'}</td>
                <td>{fecha(f.finalizado_en)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtro.visibles.length === 0 && <p className="panel-vacio">Sin exámenes que mostrar.</p>}
      </div>
    </>
  );
}
