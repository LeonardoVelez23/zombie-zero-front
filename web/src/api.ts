// Tipos y cliente de la API (ver docs/api.md).

export interface Rango { media: number; p5: number; p95: number }
export interface Serie { media: number[]; p5: number[]; p95: number[] }

export interface Plaga { r0: number; dias_latencia: number; dias_infeccioso: number; deteccion: number }
export interface Recursos {
  presupuesto: number; costo_vacuna: number; vacunas_disponibles: number; vacunas_por_dia: number;
  dia_inicio: number; eficacia: number; dias_cierre: number; cumplimiento_cierre: number;
  costo_cierre_mercado: number; costo_cierre_colegio: number;
}
export interface Escenario {
  n_personas: number; dias: number; semilla: number; inicio: string; casos_iniciales: number;
  plaga: Plaga; recursos: Recursos;
}

export interface Plan {
  id: string; nombre: string; tipo: 'linea_base' | 'candidato'; descripcion: string;
  vacunacion: string; cierres: string[]; vacunas: number; costo: number;
  infectados: Rango; pico: Rango; dia_pico: number; curva_zombies: Serie;
  mapa: number[][]; vacunas_perdidas: number;
  salvados_vs_ninguna?: Rango; salvados_vs_azar?: Rango;
  gana_a_ninguna?: number; gana_a_azar?: number;
}

export interface Veredicto {
  nivel: 'solida' | 'debil' | 'insuficiente';
  gana_a_azar: number; salvados_vs_ninguna: number; salvados_vs_azar: number;
}

export interface Resultado {
  escenario: Escenario; repeticiones: number; r0: number; beta: number;
  barrios: string[]; poblacion_barrio: number[];
  planes: Plan[]; recomendado: string | null; veredicto: Veredicto | null;
}

type Limites = Record<string, [number, number]>;
export interface Parametros {
  por_defecto: Escenario;
  limites: { escenario: Limites; plaga: Limites; recursos: Limites };
  inicios: string[];
  repeticiones: { por_defecto: number; limites: [number, number] };
}

const API_URL = ((import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000').replace(/\/$/, '');

async function pedir<T>(ruta: string, init?: RequestInit): Promise<T> {
  const respuesta = await fetch(`${API_URL}${ruta}`, init);
  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) throw new Error(datos.error ?? `La API respondió ${respuesta.status}`);
  return datos as T;
}

export const obtenerParametros = () => pedir<Parametros>('/api/parametros');

export const simular = (escenario: Escenario, repeticiones: number, signal?: AbortSignal) =>
  pedir<Resultado>('/api/simular', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ escenario, repeticiones }),
    signal
  });
