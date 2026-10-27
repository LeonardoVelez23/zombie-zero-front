// Todo lo que convierte números en frases para quien decide (el alcalde).
import type { Plan, Resultado } from './api';

export const num = (n: number) => Math.round(n).toLocaleString('es-EC');
export const usd = (n: number) => `$${num(n)}`;
export const pct = (x: number) => `${Math.round(x * 100)} %`;

const VACUNACION: Record<string, string> = {
  ninguna: 'No hacer nada',
  azar: 'Vacunar al azar',
  centralidad: 'Vacunar primero a quienes tienen más contactos',
  anillo: 'Vacunar a los contactos de cada zombie detectado'
};
const LUGAR: Record<string, string> = { mercado: 'el Mercado Central', colegio: 'los colegios' };

export const INICIOS: Record<string, string> = {
  aleatorio: 'Cualquier lugar',
  mercado: 'Mercado Central',
  colegio: 'Un colegio'
};

export function nombrePlan(plan: Plan): string {
  const base = VACUNACION[plan.vacunacion] ?? plan.vacunacion;
  if (plan.cierres.length === 0) return base;
  return `${base} y cerrar ${plan.cierres.map(c => LUGAR[c] ?? c).join(' y ')}`;
}

export interface Informe {
  nivel: 'solida' | 'debil' | 'insuficiente';
  titulo: string;
  parrafos: string[];
}

export function informe(res: Resultado): Informe | null {
  const rec = res.planes.find(p => p.id === res.recomendado);
  const nada = res.planes.find(p => p.id === 'ninguna');
  const azar = res.planes.find(p => p.id === 'azar');
  const v = res.veredicto;
  if (!rec || !nada || !azar || !v) return null;

  const { n_personas: n, recursos } = res.escenario;
  const brotes = `${res.repeticiones} brotes simulados`;
  const sinHacerNada =
    `Si no hacemos nada, en promedio ${num(nada.infectados.media)} de ${num(n)} personas ` +
    `(${pct(nada.infectados.media / n)}) terminan mordidas.`;

  if (v.nivel === 'insuficiente') {
    return {
      nivel: v.nivel,
      titulo: 'Con estos recursos no se puede frenar la plaga',
      parrafos: [
        sinHacerNada,
        `El mejor plan (${nombrePlan(rec).toLowerCase()}) salva en promedio ${num(v.salvados_vs_ninguna)} personas, ` +
        `pero solo le gana a repartir los recursos al azar en ${pct(v.gana_a_azar)} de los ${brotes}: el resultado depende de la suerte.`,
        'Para cambiar el resultado hace falta más: más vacunas, actuar antes o detectar más casos.'
      ]
    };
  }

  const cierres = rec.cierres.length
    ? ` y el cierre de ${rec.cierres.map(c => LUGAR[c] ?? c).join(' y ')} durante ${recursos.dias_cierre} días`
    : '';
  return {
    nivel: v.nivel,
    titulo: `${v.nivel === 'debil' ? 'Recomendación con reservas' : 'Recomendación'}: ${nombrePlan(rec)}`,
    parrafos: [
      sinHacerNada,
      `Con este plan serían ${num(rec.infectados.media)} (entre ${num(rec.infectados.p5)} y ${num(rec.infectados.p95)} ` +
      `en 9 de cada 10 brotes). Se salvan en promedio ${num(v.salvados_vs_ninguna)} personas.`,
      `Repartir lo mismo al azar salvaría solo ${num(nada.infectados.media - azar.infectados.media)}. ` +
      `Este plan le gana al azar en ${pct(v.gana_a_azar)} de los ${brotes}` +
      (v.nivel === 'debil' ? ', así que conviene tomarlo con cautela.' : '.'),
      `Costo: ${usd(rec.costo)} de ${usd(recursos.presupuesto)} (${num(rec.vacunas)} vacunas${cierres}), ` +
      `empezando el día ${recursos.dia_inicio}.`
    ]
  };
}
