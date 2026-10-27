import { useEffect, useMemo, useRef, useState } from 'react';
import maplibregl, { type ExpressionSpecification } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { Plan, Resultado } from './api';

// Mapa base gratuito y sin API key; se puede cambiar con VITE_MAP_STYLE_URL.
const ESTILO = (import.meta.env.VITE_MAP_STYLE_URL as string | undefined)
  ?? 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

// Centro aproximado de cada parroquia de Manta (verificar). "Rural" agrupa San Lorenzo y Santa Marianita.
const UBICACION: Record<string, [number, number]> = {
  Tarqui: [-80.7142, -0.9639],
  Manta: [-80.7300, -0.9480],
  'Los Esteros': [-80.6914, -0.9623],
  'Eloy Alfaro': [-80.7080, -0.9790],
  'San Mateo': [-80.8112, -0.9595],
  Rural: [-80.8650, -1.0350]
};

// Fracción de zombies activos en el barrio: verde (nada) → rojo oscuro (12 % o más).
const ESCALA: [number, string][] = [[0, '#34d399'], [0.01, '#fbbf24'], [0.05, '#f87171'], [0.12, '#b91c1c']];
const COLOR_CIRCULO: ExpressionSpecification = ['interpolate', ['linear'], ['get', 'fraccion'], ...ESCALA.flat()];
const colorBarra = (f: number) => [...ESCALA].reverse().find(([umbral]) => f >= umbral)?.[1] ?? ESCALA[0][1];

const fracciones = (res: Resultado, plan: Plan, dia: number) =>
  res.barrios.map((_, b) => plan.mapa[dia][b] / Math.max(1, res.poblacion_barrio[b]));

function geojson(res: Resultado, plan: Plan, dia: number): GeoJSON.FeatureCollection {
  const f = fracciones(res, plan, dia);
  return {
    type: 'FeatureCollection',
    features: res.barrios.map((nombre, b) => ({
      type: 'Feature',
      properties: { nombre, fraccion: f[b], poblacion: res.poblacion_barrio[b] },
      geometry: { type: 'Point', coordinates: UBICACION[nombre] ?? [-80.73, -0.96] }
    }))
  };
}

interface Props { res: Resultado; plan: Plan; dia: number }

/** Avance de la plaga por parroquia el día `dia`, en el mapa real y en barras (respaldo accesible). */
export function Mapa({ res, plan, dia }: Props) {
  const contenedor = useRef<HTMLDivElement>(null);
  const mapa = useRef<maplibregl.Map | null>(null);
  const [listo, setListo] = useState(false);
  const [falla, setFalla] = useState<string | null>(null);
  const datos = useMemo(() => geojson(res, plan, dia), [res, plan, dia]);
  const ultimos = useRef(datos);
  ultimos.current = datos;

  useEffect(() => {
    if (!contenedor.current) return;
    let cargado = false;
    let m: maplibregl.Map;
    try {
      m = new maplibregl.Map({
        container: contenedor.current, style: ESTILO,
        center: [-80.76, -0.985], zoom: 10.6, attributionControl: { compact: true }
      });
    } catch {
      setFalla('Este navegador no puede mostrar el mapa (sin WebGL)');
      return;
    }
    mapa.current = m;
    const espera = setTimeout(() => { if (!cargado) setFalla('El mapa base no respondió (¿sin Internet?)'); }, 12000);
    m.on('load', () => {
      cargado = true;
      clearTimeout(espera);
      m.addSource('barrios', { type: 'geojson', data: ultimos.current });
      m.addLayer({
        id: 'barrios', type: 'circle', source: 'barrios',
        paint: {
          'circle-color': COLOR_CIRCULO,
          'circle-radius': ['interpolate', ['linear'], ['get', 'poblacion'], 300, 12, 3000, 30],
          'circle-opacity': 0.8,
          'circle-stroke-color': '#0a0514',
          'circle-stroke-width': 2
        }
      });
      for (const nombre of Object.keys(UBICACION)) {
        const etiqueta = document.createElement('span');
        etiqueta.className = 'etiqueta-barrio';
        etiqueta.textContent = nombre;
        new maplibregl.Marker({ element: etiqueta, anchor: 'top', offset: [0, 18] }).setLngLat(UBICACION[nombre]).addTo(m);
      }
      setListo(true);
    });
    return () => {
      clearTimeout(espera);
      m.remove();
      mapa.current = null;
    };
  }, []);

  useEffect(() => {
    if (!listo) return;
    (mapa.current?.getSource('barrios') as maplibregl.GeoJSONSource | undefined)?.setData(datos);
  }, [datos, listo]);

  const f = fracciones(res, plan, dia);
  return (
    <div className="mapa-plaga">
      <div ref={contenedor} className="mapa" hidden={!!falla} aria-hidden="true" />
      {falla && <p className="aviso">{falla}. Las barras muestran la misma información.</p>}
      <ul className="barras" aria-label={`Zombies activos por parroquia el día ${dia}`}>
        {res.barrios.map((nombre, b) => (
          <li key={nombre}>
            <span className="barra-nombre">{nombre}</span>
            <span className="barra-fondo">
              <span className="barra" style={{ width: `${Math.min(100, (f[b] / 0.15) * 100)}%`, background: colorBarra(f[b]) }} />
            </span>
            <span className="barra-valor">{(f[b] * 100).toFixed(1)} %</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
