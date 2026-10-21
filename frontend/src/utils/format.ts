// mm:ss
export const fmt = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

import type { EstadoAsignacion } from '../api/types';

export const ESTADOS: Record<EstadoAsignacion, string> = {
  pendiente: 'Pendiente', en_curso: 'En curso', finalizado: 'Finalizado', cancelado: 'Cancelado',
};

export const fecha = (iso?: string | null) => (iso ? new Date(iso).toLocaleString('es-MX') : '—');

export const initials = (name: string) => name.split(/\s+/).slice(0, 2).map((w) => w[0] || '').join('').toUpperCase();
