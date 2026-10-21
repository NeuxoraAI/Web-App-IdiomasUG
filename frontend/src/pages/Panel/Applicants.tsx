// Solicitantes tab (admin): upload the applicants Excel, download the generated
// access keys, and list everyone registered.

import { useCallback, useEffect, useState, type FormEvent } from 'react';
import type { Carga, NuevaClave, Solicitante } from '../../api/types';
import { ESTADOS, fecha } from '../../utils/format';
import { apiStaff } from './apiStaff';
import { Filters, useFilter } from './Filters';

const XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

function download(base64: string, filename: string) {
  const blob = new Blob([Uint8Array.from(atob(base64), (c) => c.charCodeAt(0))], { type: XLSX });
  const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: filename });
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000); // revoking at once can cancel the download
}

function ExcelUpload({ onUploaded }: { onUploaded: () => void }) {
  const [convocatoria, setConvocatoria] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [upload, setUpload] = useState<(Carga & { filename: string }) | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    setUpload(null);
    try {
      const conv = convocatoria.trim().toUpperCase();
      const r = await apiStaff<Carga>('POST', `/personal/solicitantes/carga?convocatoria=${encodeURIComponent(conv)}`, file);
      const filename = `codigos_acceso_${conv}.xlsx`;
      setUpload({ ...r, filename });
      download(r.excel, filename);
      onUploaded();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card panel-upload" onSubmit={submit}>
      <h2 className="card-title">Cargar solicitantes</h2>
      <p className="panel-help">Excel (.xlsx) con columnas CURP, Nombre e Idioma (Correo opcional).
        Se genera un Excel con el folio y la clave de acceso de cada solicitante.</p>
      <div className="panel-fields">
        <label className="panel-label">Convocatoria
          <input className="panel-input" value={convocatoria} required pattern="\d{4}[A-Za-z]" placeholder="2026B"
            onChange={(e) => setConvocatoria(e.target.value)} />
        </label>
        <label className="panel-label">Archivo
          <input type="file" className="panel-input" required accept=".xlsx"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </label>
        <button type="submit" className="btn-primary" disabled={busy}>{busy ? 'Cargando…' : 'Cargar y generar claves'}</button>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {upload && (
        <div role="status">
          <p><strong>{upload.registrados}</strong> registrados · <strong>{upload.errores.length}</strong> con error.</p>
          <p className="panel-help">Este Excel es la única copia de las claves en texto plano: guárdalo en un lugar seguro.</p>
          <button type="button" className="btn-outline" onClick={() => download(upload.excel, upload.filename)}>
            Descargar Excel de claves
          </button>
          {upload.errores.length > 0 && (
            <ul className="panel-errors">
              {upload.errores.map((f) => (
                <li key={f.fila}>Fila {f.fila}: {f.curp || '(sin CURP)'} · {f.nombre || '(sin nombre)'} · {f.idioma || '(sin idioma)'} → {f.error}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </form>
  );
}

export function Applicants() {
  const [rows, setRows] = useState<Solicitante[]>([]);
  const [error, setError] = useState<string | null>(null);
  // Regenerated keys, shown once per session of this tab; the DB only keeps their hash.
  const [keys, setKeys] = useState<Record<string, string>>({});
  const filter = useFilter(rows);

  async function regenerate(r: Solicitante) {
    if (!confirm(`¿Generar una clave nueva para ${r.nombre} (${r.folio})? La clave anterior dejará de funcionar.`)) return;
    try {
      const res = await apiStaff<NuevaClave>('POST', `/personal/solicitantes/${encodeURIComponent(r.folio)}/clave`);
      setKeys((k) => ({ ...k, [r.folio]: res.clave }));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const load = useCallback(() => {
    apiStaff<Solicitante[]>('GET', '/personal/solicitantes')
      .then(setRows)
      .catch((err) => setError((err as Error).message));
  }, []);
  useEffect(load, [load]);

  return (
    <div className="panel-applicants">
      <ExcelUpload onUploaded={load} />
      <div className="panel-list">
        <Filters {...filter} total={rows.length} visible={filter.visible.length} />
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="panel-table">
          <table>
            <thead>
              <tr>
                <th>Folio</th><th>Nombre</th><th>CURP</th><th>Correo</th><th>Idioma</th>
                <th>Convocatoria</th><th>Estado</th><th>Registrado</th><th>Clave de acceso</th>
              </tr>
            </thead>
            <tbody>
              {filter.visible.map((r) => (
                <tr key={r.folio}>
                  <td>{r.folio}</td><td>{r.nombre}</td><td>{r.curp}</td><td>{r.correo ?? '—'}</td>
                  <td>{r.idioma}</td><td>{r.convocatoria}</td><td>{ESTADOS[r.estado]}</td><td>{fecha(r.creada_en)}</td>
                  <td>
                    {keys[r.folio] ? <code className="panel-key">{keys[r.folio]}</code>
                      : r.estado === 'pendiente'
                        ? <button type="button" className="btn-outline panel-btn-sm" onClick={() => regenerate(r)}>Regenerar clave</button>
                        : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filter.visible.length === 0 && <p className="panel-empty">Sin solicitantes que mostrar.</p>}
        </div>
      </div>
    </div>
  );
}
