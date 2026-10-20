// Request/response shapes of backend/api/main.py

export type EstadoAsignacion = 'pendiente' | 'en_curso' | 'finalizado' | 'cancelado';

export interface ExamenResumen {
  titulo: string;
  duracion_min: number;
  preguntas: number;
  disponible_hasta: string | null;
}

// GET /api/perfil
export interface Perfil {
  nombre: string;
  correo: string | null;
  folio: string;
  convocatoria: string;
  idioma: string;
  estado: EstadoAsignacion;
  examen: ExamenResumen | null;
}

// POST /api/sesion
export interface SesionRequest {
  curp: string;
  clave: string;
}

export interface SesionResponse {
  token: string;
  perfil: Perfil;
}

export type TipoPregunta =
  | 'choice' | 'tf' | 'listen' | 'notice' | 'select' | 'drag' | 'order' | 'match' | 'short' | 'essay';

// Exam question as sent to the browser: the `respuesta` field is projected out.
export interface PreguntaApi {
  id: string;
  parte: number;
  tipo: TipoPregunta;
  instruccion: string;
  enunciado: string;
  opciones?: string[];
  media?: { tipo: 'audio' | 'imagen'; url: string | null };
  segmentos?: (string | { hueco: number })[];
  opciones_hueco?: string[][];
  banco?: string[];
  izquierdas?: string[];
  derechas?: string[];
  palabras?: { min: number; max: number };
}

// Stored answer: option index, text, or one entry per gap / row / word.
export type Valor = number | string | (number | string | null)[];

// POST|GET /api/intento
export interface Examen {
  intento_id: string;
  titulo: string;
  partes: { numero: number; nombre: string }[];
  preguntas: PreguntaApi[];
  segundos_restantes: number;
  respuestas: Record<string, Valor>;
}

// PUT /api/intento/respuestas/{pregunta_id}
export interface RespuestaRequest {
  valor: Valor | null;
}

// POST /api/intento/incidencias
export interface IncidenciaRequest {
  tipo: string;
}

// POST /api/intento/finalizar
export interface Resultado {
  aciertos: number;
  calificables: number;
  mcer: string;
  nivel: string;
  por_parte: { parte: number; nombre: string; aciertos: number; total: number; porcentaje: number }[];
  pendientes_revision: string[];
  segundos_usados: number;
}
