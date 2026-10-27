import { useEffect, useRef, useState } from 'react';
import { obtenerParametros, simular, type Escenario, type Parametros, type Resultado } from './api';
import { Grafica } from './Grafica';
import { Mapa } from './Mapa';
import { INICIOS, informe, nombrePlan, num, pct, usd } from './textos';

interface Control {
  grupo: 'plaga' | 'recursos';
  clave: string;
  etiqueta: string;
  ayuda: string;
  paso: number;
  max?: (e: Escenario) => number;   // tope del deslizador si el límite de la API es demasiado amplio
  formato?: (v: number) => string;
}

const CONTROLES: Control[] = [
  { grupo: 'plaga', clave: 'r0', etiqueta: 'Contagio (R0)', ayuda: 'A cuántas personas muerde cada zombie en una ciudad sana.', paso: 0.1 },
  { grupo: 'plaga', clave: 'deteccion', etiqueta: 'Zombies que se detectan', ayuda: 'Si no se detecta un zombie, no se puede vacunar a su alrededor.', paso: 0.05, formato: pct },
  { grupo: 'recursos', clave: 'presupuesto', etiqueta: 'Presupuesto', ayuda: 'Para vacunas y cierres.', paso: 1000, max: () => 100_000, formato: usd },
  { grupo: 'recursos', clave: 'vacunas_disponibles', etiqueta: 'Vacunas disponibles', ayuda: 'Stock máximo, aunque sobre dinero.', paso: 50, max: e => e.n_personas, formato: num },
  { grupo: 'recursos', clave: 'vacunas_por_dia', etiqueta: 'Vacunas por día', ayuda: 'Capacidad de las brigadas.', paso: 10, max: () => 1000, formato: num },
  { grupo: 'recursos', clave: 'eficacia', etiqueta: 'Eficacia de la vacuna', ayuda: 'Una variante puede bajarla.', paso: 0.05, formato: pct },
  { grupo: 'recursos', clave: 'dia_inicio', etiqueta: 'Día en que se empieza a actuar', ayuda: 'Cuánto tarda en detectarse el brote.', paso: 1, max: () => 60 },
  { grupo: 'recursos', clave: 'dias_cierre', etiqueta: 'Días de cada cierre', ayuda: 'Del mercado o de los colegios.', paso: 1, max: () => 90 }
];

// Cambios típicos del Brote Sorpresa: se aplican sobre lo que ya está en pantalla.
const SORPRESAS: { etiqueta: string; aplicar: (e: Escenario) => Escenario }[] = [
  { etiqueta: 'El doble de contagiosa', aplicar: e => ({ ...e, plaga: { ...e.plaga, r0: Math.min(10, Math.round(e.plaga.r0 * 20) / 10) } }) },
  { etiqueta: 'La mitad de las vacunas', aplicar: e => ({ ...e, recursos: { ...e.recursos, vacunas_disponibles: Math.floor(e.recursos.vacunas_disponibles / 2) } }) },
  { etiqueta: 'Empieza en el mercado', aplicar: e => ({ ...e, inicio: 'mercado' }) },
  { etiqueta: 'Variante: vacuna a medias', aplicar: e => ({ ...e, recursos: { ...e.recursos, eficacia: Math.round(e.recursos.eficacia * 50) / 100 } }) }
];

const leer = (e: Escenario, c: Control) => (e[c.grupo] as unknown as Record<string, number>)[c.clave];
const cambiar = (e: Escenario, c: Control, v: number): Escenario => ({ ...e, [c.grupo]: { ...e[c.grupo], [c.clave]: v } });

export function App() {
  const [parametros, setParametros] = useState<Parametros | null>(null);
  const [escenario, setEscenario] = useState<Escenario | null>(null);
  const [repeticiones, setRepeticiones] = useState(50);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [simulado, setSimulado] = useState<string>('');
  const [cargando, setCargando] = useState(false);
  const [segundos, setSegundos] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [dia, setDia] = useState(0);
  const [reproduciendo, setReproduciendo] = useState(false);
  const [verPlan, setVerPlan] = useState<'recomendado' | 'ninguna'>('recomendado');
  const peticion = useRef<AbortController | null>(null);

  const ejecutar = async (esc: Escenario, reps: number) => {
    peticion.current?.abort();
    const control = new AbortController();
    peticion.current = control;
    setCargando(true);
    setError(null);
    setSegundos(0);
    const inicio = Date.now();
    const reloj = setInterval(() => setSegundos(Math.round((Date.now() - inicio) / 1000)), 500);
    try {
      const res = await simular(esc, reps, control.signal);
      setResultado(res);
      setSimulado(JSON.stringify([esc, reps]));
      setReproduciendo(false);
      setDia(Math.round(res.planes.find(p => p.id === 'ninguna')?.dia_pico ?? 0));
    } catch (e) {
      if (!control.signal.aborted) setError(e instanceof Error ? e.message : String(e));
    } finally {
      clearInterval(reloj);
      if (peticion.current === control) setCargando(false);
    }
  };

  useEffect(() => {
    obtenerParametros()
      .then(p => {
        setParametros(p);
        setEscenario(p.por_defecto);
        setRepeticiones(p.repeticiones.por_defecto);
        ejecutar(p.por_defecto, p.repeticiones.por_defecto);
      })
      .catch(() => setError('No se pudo conectar con la API. En local, corre: PYTHONPATH=src python -m zombie.servidor'));
    return () => peticion.current?.abort();
  }, []);

  const diasTotales = resultado?.escenario.dias ?? 0;
  useEffect(() => {
    if (!reproduciendo) return;
    const t = setInterval(() => setDia(d => Math.min(d + 1, diasTotales)), 60);
    return () => clearInterval(t);
  }, [reproduciendo, diasTotales]);
  useEffect(() => {
    if (reproduciendo && dia >= diasTotales) setReproduciendo(false);
  }, [dia, diasTotales, reproduciendo]);

  if (!escenario || !parametros) {
    return (
      <main className="cargando-app">
        <h1 className="titulo">Zombie Zero</h1>
        <p role="status">{error ?? 'Conectando con el simulador…'}</p>
      </main>
    );
  }

  const desactualizado = !!resultado && simulado !== JSON.stringify([escenario, repeticiones]);
  const reporte = resultado && informe(resultado);
  const planes = resultado ? [...resultado.planes].sort((a, b) => a.infectados.media - b.infectados.media) : [];
  const planMapa = resultado?.planes.find(p => p.id === (verPlan === 'recomendado' ? resultado.recomendado : 'ninguna'));

  return (
    <div className="app">
      <header className="cabecera">
        <h1 className="titulo">🧟 Zombie Zero</h1>
        <p>Comité de Contención de Manta · qué hacer, dónde y cuándo para que la plaga alcance a la menor cantidad de gente</p>
      </header>

      <aside className="panel controles">
        <h2>Escenario</h2>
        <label className="campo">
          <span>Dónde empieza el brote</span>
          <select value={escenario.inicio} onChange={e => setEscenario({ ...escenario, inicio: e.target.value })}>
            {parametros.inicios.map(i => <option key={i} value={i}>{INICIOS[i] ?? `Parroquia ${i}`}</option>)}
          </select>
        </label>

        {CONTROLES.map(c => {
          const [min, maxApi] = parametros.limites[c.grupo][c.clave];
          const max = Math.min(maxApi, c.max?.(escenario) ?? maxApi);
          const v = leer(escenario, c);
          return (
            <label key={c.clave} className="campo">
              <span>{c.etiqueta} <output>{c.formato ? c.formato(v) : v}</output></span>
              <input type="range" min={min} max={max} step={c.paso} value={v}
                onChange={e => setEscenario(cambiar(escenario, c, Number(e.target.value)))} />
              <small>{c.ayuda}</small>
            </label>
          );
        })}

        <div className="campo fila">
          <label>
            <span>Semilla</span>
            <input type="number" min={0} value={escenario.semilla}
              onChange={e => setEscenario({ ...escenario, semilla: Math.max(0, Math.floor(Number(e.target.value))) })} />
          </label>
          <label>
            <span>Brotes a simular</span>
            <select value={repeticiones} onChange={e => setRepeticiones(Number(e.target.value))}>
              {[20, 50, 100, 200].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
        </div>

        <h3>🎃 Brote Sorpresa</h3>
        <div className="sorpresas">
          {SORPRESAS.map(s => (
            <button key={s.etiqueta} type="button" className="boton-secundario" onClick={() => setEscenario(s.aplicar(escenario))}>
              {s.etiqueta}
            </button>
          ))}
        </div>

        <button type="button" className="boton-principal" disabled={cargando} onClick={() => ejecutar(escenario, repeticiones)}>
          {cargando ? `Simulando ${repeticiones} brotes… ${segundos} s` : 'Simular'}
        </button>
        <button type="button" className="boton-texto" onClick={() => setEscenario(parametros.por_defecto)}>
          Volver a los valores por defecto
        </button>
      </aside>

      <main className="resultados">
        {error && <p className="error" role="alert">{error}</p>}
        {desactualizado && !cargando && <p className="aviso">Cambiaste el escenario: pulsa <b>Simular</b> para actualizar los resultados.</p>}

        {reporte && (
          <section className={`panel informe nivel-${reporte.nivel}`} aria-live="polite">
            <h2>{reporte.titulo}</h2>
            {reporte.parrafos.map(p => <p key={p}>{p}</p>)}
          </section>
        )}

        {resultado && (
          <>
            <section className="panel">
              <h2>Zombies activos por día</h2>
              <Grafica res={resultado} dia={dia} />
            </section>

            <section className="panel">
              <div className="encabezado-mapa">
                <h2>Avance por parroquia · día {dia}</h2>
                <div className="interruptor" role="group" aria-label="Plan que muestra el mapa">
                  <button type="button" aria-pressed={verPlan === 'recomendado'} onClick={() => setVerPlan('recomendado')}>Con el plan</button>
                  <button type="button" aria-pressed={verPlan === 'ninguna'} onClick={() => setVerPlan('ninguna')}>Sin hacer nada</button>
                </div>
              </div>
              <div className="linea-tiempo">
                <button type="button" className="boton-secundario" onClick={() => {
                  if (dia >= diasTotales) setDia(0);
                  setReproduciendo(!reproduciendo);
                }}>
                  {reproduciendo ? '⏸ Pausa' : '▶ Reproducir'}
                </button>
                <input type="range" min={0} max={diasTotales} value={dia} aria-label="Día"
                  onChange={e => { setReproduciendo(false); setDia(Number(e.target.value)); }} />
              </div>
              {planMapa && <Mapa res={resultado} plan={planMapa} dia={dia} />}
            </section>

            <section className="panel">
              <h2>Todos los planes comparados</h2>
              <div className="tabla-scroll">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Plan</th>
                      <th scope="col">Vacunas</th>
                      <th scope="col">Costo</th>
                      <th scope="col">Mordidos (promedio)</th>
                      <th scope="col">Rango 90 %</th>
                      <th scope="col">Salvados vs. nada</th>
                      <th scope="col">Gana al azar</th>
                    </tr>
                  </thead>
                  <tbody>
                    {planes.map(p => (
                      <tr key={p.id} className={p.id === resultado.recomendado ? 'fila-recomendada' : undefined}>
                        <th scope="row">
                          {nombrePlan(p)}
                          {p.tipo === 'linea_base' && <span className="etiqueta">línea base</span>}
                          {p.id === resultado.recomendado && <span className="etiqueta recomendada">recomendado</span>}
                        </th>
                        <td>{num(p.vacunas)}</td>
                        <td>{usd(p.costo)}</td>
                        <td>{num(p.infectados.media)}</td>
                        <td>{num(p.infectados.p5)} – {num(p.infectados.p95)}</td>
                        <td>{p.salvados_vs_ninguna ? num(p.salvados_vs_ninguna.media) : '—'}</td>
                        <td>{p.gana_a_azar !== undefined ? pct(p.gana_a_azar) : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <p className="pie">
              R0 {resultado.r0} · {resultado.repeticiones} brotes simulados · semilla {resultado.escenario.semilla} ·
              misma configuración y semilla, mismo resultado.
            </p>
          </>
        )}
      </main>
    </div>
  );
}
