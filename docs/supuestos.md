# Supuestos y de dónde salen los números

Leyenda: **Fuente** = número tomado de literatura o datos abiertos ·
**Supuesto** = decisión del equipo, razonada. Las referencias [n] están al final.

## La plaga (inspirada en COVID-19, variante original)

| Parámetro | Valor | Tipo | Justificación |
|---|---|---|---|
| R0 | 2,5 | Fuente | La OMS y estudios de 2020 lo ubican entre 2 y 3 (Liu et al., *J Travel Med* 2020, revisión de 12 estudios). En el Brote Sorpresa, "el doble de contagiosa" equivale a R0 = 5. |
| Días de latencia (mordido → zombie) | 3 | Fuente | Incubación media de unos 5 días (Lauer et al., *Ann Intern Med* 2020) y contagio desde unos 2 días antes de los síntomas (He et al., *Nat Med* 2020). |
| Días infeccioso (zombie → exorcizado) | 5 | Fuente | La mayor parte del contagio ocurre en la primera semana (He et al., 2020). |
| Transmisión | Por contacto en la red | Supuesto | Enfermedad respiratoria, de persona a persona. No usamos el dengue porque necesita un vector (el mosquito). |
| Mortalidad | No se modela | Supuesto | El objetivo es minimizar los contagiados. Los exorcizados quedan inmunes. |
| Zombies detectados | 70 % | Supuesto | Parte de los casos no se detecta (por ejemplo, los asintomáticos). Un zombie no detectado no activa la vacunación en anillo. Ajustable en la interfaz. |

**Calibración:** el usuario elige R0 y el sistema busca la tasa de contagio
(`beta`) que produce ese R0 en la red (`modelo.calibrar_beta`). R0 se estima como
los contagios esperados de un zombie en una población sana, ponderados por su
número de contactos.

## La población (Manta)

| Parámetro | Valor | Tipo | Justificación |
|---|---|---|---|
| Personas simuladas | 10.000 | Supuesto | Manta tiene **271.145 habitantes** según el Censo 2022 [1]. Se simula a escala 1:27 y los resultados se leen como proporciones. |
| Zona rural | 4,6 % | Fuente | 12.448 personas viven en el área rural (parroquias San Lorenzo y Santa Marianita) y 258.697 en el área urbana [1]. |
| Parroquias urbanas | Tarqui 30,1 %, Manta 25,1 %, Los Esteros 18,1 %, Eloy Alfaro 15,1 %, San Mateo 7,0 % | Supuesto | El INEC publica la ciudad como un solo bloque urbano; no encontramos datos públicos del Censo 2022 por parroquia urbana. El reparto refleja que Tarqui es la parroquia más poblada [4] y se puede reemplazar con los tabulados por parroquia del INEC. |
| Edades | 0-4: 8,1 %, 5-17: 20,4 %, 18-64: 63,5 %, 65+: 8,0 % | Fuente | Manta, Censo 2022: 0-14 años = 66.266 (24,4 %), 15-64 = 183.270 (67,6 %), 65+ = 21.609 (8,0 %) [1]. Para pasar a nuestros grupos se supone un reparto uniforme dentro de cada grupo del censo: 0-4 = 5/15 de 0-14; 5-17 = 10/15 de 0-14 más 3/50 de 15-64; 18-64 = 47/50 de 15-64. |
| Personas por hogar | 3,3 en promedio | Fuente | Tamaño medio del hogar en Manabí, Censo 2022 (bajó de 4,0 en 2010) [2]. |
| Tamaño de aula | 30 | Supuesto | Aula pública típica. |
| Tamaño de grupo de trabajo | 8 | Supuesto | Contactos laborales cercanos. |
| Adultos con trabajo fuera de casa | 56 % | Fuente | Tasa de empleo bruto de Manabí en 2025: 55,9 % (personas con empleo / población en edad de trabajar), ENEMDU anual 2025, Tabla 4 [3]. Incluye el empleo informal, que también genera contactos. |
| Usan bus a diario | 50 % de escolares y adultos, 4 contactos cercanos | Supuesto | |
| Van al Mercado Central (Tarqui) | 30 % de adultos y mayores, 6 contactos | Supuesto | |

**Pesos por capa** (cuánto contagia un día de contacto): hogar 1,0 · colegio 0,5 ·
trabajo 0,4 · bus 0,2 · mercado 0,15. Es un supuesto basado en que los contactos
del hogar son más largos y cercanos, como muestran los estudios de contactos
(Mossong et al., *PLoS Med* 2008, estudio POLYMOD).

## Las intervenciones

| Parámetro | Valor | Tipo | Justificación |
|---|---|---|---|
| Presupuesto total | $20.000 | Supuesto | Se reparte entre vacunas y cierres. Lo que no se gasta en cierres se gasta en vacunas. |
| Costo por vacuna aplicada | $10 | Supuesto | Dosis más aplicación. |
| Vacunas disponibles | 1.000 (10 % de la población) | Supuesto | Stock máximo, aunque sobre dinero. Recurso escaso por diseño del reto. |
| Vacunas por día | 100 | Supuesto | Capacidad de una brigada de vacunación. |
| Día en que se empieza a actuar | 3 | Supuesto | Tiempo para detectar el brote y movilizar recursos. |
| Eficacia | 90 % | Fuente | Rango de las vacunas de ARNm en sus ensayos (Polack et al., *NEJM* 2020: 95 %). La vacuna reduce la probabilidad de ser mordido; no actúa sobre quien ya lo fue. |
| Cierre del mercado | $600 por día | Supuesto | Compensación a comerciantes. |
| Cierre de colegios | $800 por día | Supuesto | Costo de clases a distancia y cuidado infantil. |
| Duración de un cierre | 14 días | Supuesto | Dos periodos de latencia más infeccioso. |
| Cumplimiento del cierre | 80 % | Supuesto | Fracción de contactos de ese lugar que realmente se evitan. |
| Visibilidad | Solo se ven los zombies detectados | Supuesto | Por eso una vacuna puede "perderse" en alguien ya mordido o no detectado. El sistema lo reporta. |

## Referencias de datos abiertos

1. INEC, Censo de Población y Vivienda 2022: población del cantón Manta por área y grupos de edad, vía [citypopulation.de](https://www.citypopulation.de/en/ecuador/admin/manab%C3%AD/1308__manta/) y [ecuadorencifras.gob.ec](https://www.ecuadorencifras.gob.ec/institucional/201-279-personas-mas-viven-en-manabi/).
2. INEC, "201.279 personas más viven en Manabí" (resultados del Censo 2022 para Manabí): [ecuadorencifras.gob.ec](https://www.ecuadorencifras.gob.ec/institucional/201-279-personas-mas-viven-en-manabi/).
3. INEC, Boletín técnico ENEMDU anual enero-diciembre 2025, Tabla 4: [PDF](https://www.ecuadorencifras.gob.ec/documentos/web-inec/EMPLEO/2025/anual/Boletin_tecnico_anual_enero-diciembre_2025.pdf).
4. El Diario, "La Parroquia Tarqui está de fiesta…" (2025): [eldiario.ec](https://www.eldiario.ec/manta/la-parroquia-tarqui-esta-de-fiesta-este-9-de-octubre-celebra-96-anos-de-historia-y-empuje-26092025/).

## Reproducibilidad

La semilla fija la red de Manta y cada repetición `r` usa
`SeedSequence([semilla, r])`. Todas las estrategias comparten los mismos números
aleatorios del brote, así que con la misma configuración y la misma semilla el
resultado es idéntico (lo prueba `tests/test_simulador.py`).
