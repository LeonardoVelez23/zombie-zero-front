import { useState } from 'react';
import type { Plan, Resultado } from './api';
import { nombrePlan, num } from './textos';

const W = 640;
const H = 260;
const M = { arriba: 14, derecha: 16, abajo: 30, izquierda: 52 };

export const COLOR_RECOMENDADO = '#ff9900';
const COLOR: Record<string, string> = { azar: '#a78bfa', ninguna: '#f87171' };

interface Props {
  res: Resultado;
  dia: number;   // día que muestra el mapa, marcado con una línea vertical
}

/** Zombies activos por día: media (línea) y rango p5–p95 (banda) de cada plan. */
export function Grafica({ res, dia }: Props) {
  const [hover, setHover] = useState<number | null>(null);
  const planes = ['ninguna', 'azar', res.recomendado]
    .map(id => res.planes.find(p => p.id === id))
    .filter((p): p is Plan => !!p);
  const color = (p: Plan) => (p.id === res.recomendado ? COLOR_RECOMENDADO : COLOR[p.id]);

  const dias = res.escenario.dias;
  const maxY = Math.max(1, ...planes.flatMap(p => p.curva_zombies.p95));
  const x = (d: number) => M.izquierda + (d / dias) * (W - M.izquierda - M.derecha);
  const y = (v: number) => M.arriba + (1 - v / maxY) * (H - M.arriba - M.abajo);
  const punto = (d: number, v: number) => `${x(d).toFixed(1)},${y(v).toFixed(1)}`;
  const linea = (valores: number[]) => valores.map((v, d) => `${d ? 'L' : 'M'}${punto(d, v)}`).join('');
  const banda = (p: Plan) => {
    const { p5, p95 } = p.curva_zombies;
    const vuelta = p5.map((_, i) => p5.length - 1 - i).map(d => `L${punto(d, p5[d])}`).join('');
    return `${linea(p95)}${vuelta}Z`;
  };

  const marcasY = [0, 0.25, 0.5, 0.75, 1].map(f => Math.round(maxY * f));
  const marcasX = Array.from({ length: Math.floor(dias / 30) + 1 }, (_, i) => i * 30);

  const alMover = (e: React.PointerEvent<SVGSVGElement>) => {
    const caja = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - caja.left) / caja.width) * W;
    const d = Math.round(((px - M.izquierda) / (W - M.izquierda - M.derecha)) * dias);
    setHover(Math.max(0, Math.min(dias, d)));
  };

  return (
    <figure className="grafica">
      <ul className="leyenda">
        {planes.map(p => (
          <li key={p.id}>
            <span className={`muestra ${p.id === 'ninguna' ? 'punteada' : ''}`} style={{ borderColor: color(p) }} />
            {p.id === res.recomendado ? `Recomendado: ${nombrePlan(p)}` : nombrePlan(p)}
          </li>
        ))}
      </ul>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" onPointerMove={alMover} onPointerLeave={() => setHover(null)}
        aria-label="Zombies activos por día con cada plan; las bandas muestran el rango del 90 % de los brotes simulados">
        {marcasY.map(v => (
          <g key={v}>
            <line x1={M.izquierda} x2={W - M.derecha} y1={y(v)} y2={y(v)} className="rejilla" />
            <text x={M.izquierda - 8} y={y(v) + 4} textAnchor="end" className="eje">{num(v)}</text>
          </g>
        ))}
        {marcasX.map(d => (
          <text key={d} x={x(d)} y={H - 10} textAnchor="middle" className="eje">día {d}</text>
        ))}
        {planes.map(p => <path key={`b-${p.id}`} d={banda(p)} fill={color(p)} opacity={0.14} />)}
        {planes.map(p => (
          <path key={`l-${p.id}`} d={linea(p.curva_zombies.media)} fill="none" stroke={color(p)}
            strokeWidth={p.id === res.recomendado ? 2.6 : 1.8} strokeDasharray={p.id === 'ninguna' ? '6 4' : undefined} />
        ))}
        <line x1={x(dia)} x2={x(dia)} y1={M.arriba} y2={H - M.abajo} className="marca-dia" />
        {hover !== null && <line x1={x(hover)} x2={x(hover)} y1={M.arriba} y2={H - M.abajo} className="marca-hover" />}
      </svg>
      <figcaption aria-live="polite">
        {hover === null
          ? 'Pasa el cursor por la gráfica para ver cada día.'
          : `Día ${hover}: ` + planes.map(p => `${nombrePlan(p)} ${num(p.curva_zombies.media[hover])}`).join(' · ') + ' zombies activos'}
      </figcaption>
    </figure>
  );
}
