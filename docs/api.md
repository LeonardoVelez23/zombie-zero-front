# API de Zombie Zero

La misma API corre en local (`python -m zombie.servidor`, puerto 8000) y en AWS
Lambda (`zombie.api.lambda_handler`). Todo es JSON en UTF-8.

Respuesta de ejemplo completa y real: [`docs/ejemplos/respuesta-simular.json`](ejemplos/respuesta-simular.json)
(escenario por defecto, 50 repeticiones, semilla 42).

## `GET /api/salud`

```json
{"estado": "ok"}
```

## `GET /api/parametros`

Valores por defecto y límites de cada parámetro, para armar los controles de la interfaz.

```json
{
  "por_defecto": { "n_personas": 10000, "dias": 180, "semilla": 42, "inicio": "aleatorio", "casos_iniciales": 5,
                   "plaga": {...}, "recursos": {...} },
  "limites": { "escenario": {"n_personas": [1000, 20000], ...},
               "plaga": {"r0": [0.5, 10.0], ...},
               "recursos": {...} },
  "inicios": ["aleatorio", "mercado", "colegio", "Tarqui", "Manta", "Los Esteros", "Eloy Alfaro", "San Mateo", "Rural"],
  "repeticiones": {"por_defecto": 50, "limites": [5, 200]}
}
```

## `POST /api/simular`

### Petición

Todo es opcional: lo que no se envía toma el valor por defecto.

```json
{
  "repeticiones": 50,
  "escenario": {
    "semilla": 42,
    "n_personas": 10000,
    "dias": 180,
    "inicio": "mercado",
    "casos_iniciales": 5,
    "plaga":    { "r0": 2.5, "dias_latencia": 3, "dias_infeccioso": 5, "deteccion": 0.7 },
    "recursos": { "presupuesto": 20000, "costo_vacuna": 10, "vacunas_disponibles": 1000,
                  "vacunas_por_dia": 100, "dia_inicio": 3, "eficacia": 0.9,
                  "dias_cierre": 14, "cumplimiento_cierre": 0.8,
                  "costo_cierre_mercado": 600, "costo_cierre_colegio": 800 }
  }
}
```

**Brote Sorpresa típico:** `{"escenario": {"inicio": "mercado", "plaga": {"r0": 5}, "recursos": {"vacunas_disponibles": 500, "eficacia": 0.5}}}`.

### Respuesta

```json
{
  "escenario": { ... lo que se simuló, con todos los valores ... },
  "repeticiones": 50,
  "r0": 2.5,
  "beta": 0.04626,
  "barrios": ["Tarqui", "Manta", "Los Esteros", "Eloy Alfaro", "San Mateo", "Rural"],
  "poblacion_barrio": [2990, 2511, ...],
  "recomendado": "anillo+mercado",
  "veredicto": {
    "nivel": "solida",              // "solida" | "debil" | "insuficiente"
    "gana_a_azar": 0.98,            // fracción de brotes en que el recomendado gana al azar
    "salvados_vs_ninguna": 4812.0,
    "salvados_vs_azar": 3896.0
  },
  "planes": [
    {
      "id": "anillo+mercado",
      "nombre": "anillo + cerrar mercado",
      "tipo": "candidato",          // "linea_base" (ninguna, azar) | "candidato"
      "descripcion": "Vacuna a los contactos de los zombies...",
      "vacunacion": "anillo",
      "cierres": ["mercado"],
      "vacunas": 1000,
      "costo": 18400.0,
      "infectados":      { "media": 320.0, "p5": 6.0, "p95": 1882.0 },
      "pico":            { "media": ..., "p5": ..., "p95": ... },
      "dia_pico": 21.4,
      "curva_zombies":   { "media": [dias+1 números], "p5": [...], "p95": [...] },
      "mapa": [[zombies promedio por barrio el día 0], [día 1], ...],   // (dias+1) × 6
      "vacunas_perdidas": 12.3,
      "salvados_vs_ninguna": { "media": ..., "p5": ..., "p95": ... },
      "salvados_vs_azar":    { "media": ..., "p5": ..., "p95": ... },
      "gana_a_ninguna": 0.98,
      "gana_a_azar": 0.98
    }
  ]
}
```

- `infectados`: personas que llegaron a ser mordidas en todo el brote (media y rango p5–p95 entre repeticiones).
- `curva_zombies`: zombies activos por día; sirve para la gráfica con banda de rango.
- `mapa[d][b] / poblacion_barrio[b]`: fracción de zombies en el barrio `b` el día `d`, para colorear el mapa.
- `salvados_vs_*`: diferencia pareada (misma semilla) de infectados frente a la línea base.

### Errores

| Código | Cuándo | Cuerpo |
|---|---|---|
| 400 | JSON inválido, campo desconocido o valor fuera de rango | `{"error": "r0 debe estar entre 0.5 y 10.0"}` |
| 404 | Ruta inexistente | `{"error": "No existe GET /api/otra"}` |

### Tiempo de respuesta

Unos 12 s con 50 repeticiones y 10.000 personas (10 planes × 50 brotes). Escala
lineal con `repeticiones` y con `n_personas`. En AWS conviene una Lambda Function
URL (hasta 15 min) en vez de API Gateway (corta a los 30 s).
