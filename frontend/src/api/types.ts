// Data contract with the backend. schema.ts is generated from the FastAPI
// response models (npm run gen:api); never edit it by hand.

import type { components } from './schema';

type S = components['schemas'];

export type Perfil = S['Perfil'];
export type EstadoAsignacion = Perfil['estado'];
export type ExamenResumen = S['ExamenResumen'];
export type SesionRequest = S['Login'];
export type SesionResponse = S['Sesion'];
export type PreguntaApi = S['Pregunta'];
export type TipoPregunta = PreguntaApi['tipo'];
export type Examen = S['Examen'];
export type Valor = NonNullable<Examen['respuestas'][string]>;
export type RespuestaRequest = S['Respuesta'];
export type IncidenciaRequest = S['Incidencia'];
export type PosicionRequest = S['Posicion'];
export type Resultado = S['Resultado'];
export type UsuarioPersonal = S['Usuario'];
export type SesionPersonalRequest = S['LoginPersonal'];
export type SesionPersonalResponse = S['SesionPersonal'];
