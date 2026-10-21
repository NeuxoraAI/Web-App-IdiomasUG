// Solicitantes tab (admin): upload the applicants Excel, download the generated
// access keys, and list everyone registered.

import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { apiPersonal } from './apiPersonal';
import type { Carga, NuevaClave, Solicitante } from '../../api/types';
import { ESTADOS, fecha, Filtros, useFiltro } from './Filtros';

const XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

function descargar(base64: string, nombre: string) {
  const blob = new Blob([Uint8Array.from(atob(base64), (c) => c.charCodeAt(0))], { type: XLSX });
  const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: nombre });
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000); // revoking at once can cancel the download
}

function CargaExcel({ onCargado }: { onCargado: () => void }) {
  const [convocatoria, setConvocatoria] = useState('');
  const [archivo, setArchivo] = useState<File | null>(null);
  const [carga, setCarga] = useState<(Carga & { nombre: string }) | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!archivo) return;
    setBusy(true);
    setError(null);
    setCarga(null);
    try {
      const conv = convocatoria.trim().toUpperCase();
      const r = await apiPersonal<Carga>('POST', `/personal/solicitantes/carga?convocatoria=${encodeURIComponent(conv)}`,
        archivo);
      const nombre = `codigos_acceso_${conv}.xlsx`;
      setCarga({ ...r, nombre });
      descargar(r.excel, nombre);
      onCargado();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card panel-carga" onSubmit={submit}>
      <h2 className="card-title">Cargar solicitantes</h2>
      <p className="panel-ayuda">Excel (.xlsx) con columnas CURP, Nombre e Idioma (Correo opcional).
        Se genera un Excel con el folio y la clave de acceso de cada solicitante.</p>
      <div className="panel-campos">
        <label className="panel-label">Convocatoria
          <input className="panel-input" value={convocatoria} required pattern="\d{4}[A-Za-z]" placeholder="2026B"
            onChange={(e) => setConvocatoria(e.target.value)} />
        </label>
        <label className="panel-label">Archivo
          <input type="file" className="panel-input" required accept=".xlsx"
            onChange={(e) => setArchivo(e.target.files?.[0] ?? null)} />
        </label>
        <button type="submit" className="btn-primary" disabled={busy}>{busy ? 'Cargando…' : 'Cargar y generar claves'}</button>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {carga && (
        <div role="status">
          <p><strong>{carga.registrados}</strong> registrados · <strong>{carga.errores.length}</strong> con error.</p>
          <p className="panel-ayuda">Este Excel es la única copia de las claves en texto plano: guárdalo en un lugar seguro.</p>
          <button type="button" className="btn-outline" onClick={() => descargar(carga.excel, carga.nombre)}>
            Descargar Excel de claves
          </button>
          {carga.errores.length > 0 && (
            <ul className="panel-errores">
              {carga.errores.map((f) => (
                <li key={f.fila}>Fila {f.fila}: {f.curp || '(sin CURP)'} · {f.nombre || '(sin nombre)'} · {f.idioma || '(sin idioma)'} → {f.error}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </form>
  );
}

export function Solicitantes() {
  const [filas, setFilas] = useState<Solicitante[]>([]);
  const [error, setError] = useState<string | null>(null);
  // Regenerated keys, shown once per session of this tab; the DB only keeps their hash.
  const [claves, setClaves] = useState<Record<string, string>>({});
  const filtro = useFiltro(filas);

  async function regenerar(f: Solicitante) {
    if (!confirm(`¿Generar una clave nueva para ${f.nombre} (${f.folio})? La clave anterior dejará de funcionar.`)) return;
    try {
      const r = await apiPersonal<NuevaClave>('POST', `/personal/solicitantes/${encodeURIComponent(f.folio)}/clave`);
      setClaves((c) => ({ ...c, [f.folio]: r.clave }));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const cargar = useCallback(() => {
    apiPersonal<Solicitante[]>('GET', '/personal/solicitantes')
      .then(setFilas)
      .catch((err) => setError((err as Error).message));
  }, []);
  useEffect(cargar, [cargar]);

  return (
    <div className="panel-solicitantes">
      <CargaExcel onCargado={cargar} />
      <div className="panel-lista">
      <Filtros {...filtro} total={filas.length} visibles={filtro.visibles.length} />
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="panel-tabla">
        <table>
          <thead>
            <tr>
              <th>Folio</th><th>Nombre</th><th>CURP</th><th>Correo</th><th>Idioma</th>
              <th>Convocatoria</th><th>Estado</th><th>Registrado</th><th>Clave de acceso</th>
            </tr>
          </thead>
          <tbody>
            {filtro.visibles.map((f) => (
              <tr key={f.folio}>
                <td>{f.folio}</td><td>{f.nombre}</td><td>{f.curp}</td><td>{f.correo ?? '—'}</td>
                <td>{f.idioma}</td><td>{f.convocatoria}</td><td>{ESTADOS[f.estado]}</td><td>{fecha(f.creada_en)}</td>
                <td>
                  {claves[f.folio] ? <code className="panel-clave">{claves[f.folio]}</code>
                    : f.estado === 'pendiente'
                      ? <button type="button" className="btn-outline panel-btn-sm" onClick={() => regenerar(f)}>Regenerar clave</button>
                      : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtro.visibles.length === 0 && <p className="panel-vacio">Sin solicitantes que mostrar.</p>}
      </div>
      </div>
    </div>
  );
}
