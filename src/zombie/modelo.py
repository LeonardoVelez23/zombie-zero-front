"""Motor SEIR sobre la red de contactos, en pasos de un día.

Estados: 🟢 S sano · 🟡 E mordido · 🔴 I zombie · 🔵 R exorcizado.

Reproducibilidad: cada repetición usa SeedSequence([semilla, repetición]) y la
divide en flujos independientes (inicio, brote, estrategia). El flujo del brote
consume siempre los mismos números cada día, sin importar la estrategia, así que
todas las estrategias enfrentan exactamente la misma "suerte" (números aleatorios
comunes) y la comparación entre ellas es justa.
"""
from dataclasses import dataclass

import numpy as np

from .config import Escenario, Plaga
from .poblacion import BARRIOS, CAPAS, ESCOLAR, Red

S, E, I, R = 0, 1, 2, 3
CERRABLES = {"mercado": CAPAS.index("mercado"), "colegio": CAPAS.index("colegio")}


@dataclass
class Observacion:
    """Lo que el Comité de Contención puede ver un día dado.

    Solo se ve a los zombies detectados. Un mordido (E), un zombie no detectado o
    un exorcizado que nunca se detectó parecen sanos, así que una estrategia puede
    gastar una vacuna en ellos sin saberlo.
    """
    dia: int
    red: Red
    visible: np.ndarray      # True si se detectó como zombie alguna vez
    vacunado: np.ndarray
    zombies: np.ndarray      # índices de los zombies activos detectados

    def elegibles(self) -> np.ndarray:
        return np.flatnonzero(~self.visible & ~self.vacunado)


@dataclass
class Resultado:
    serie: np.ndarray        # (dias + 1, 4): cuántos S, E, I, R hay cada día
    serie_barrio: np.ndarray  # (dias + 1, len(BARRIOS)): zombies activos por barrio
    nuevos: np.ndarray       # mordidos nuevos cada día
    infectados_total: int
    vacunas_usadas: int
    vacunas_perdidas: int    # aplicadas a quien ya no estaba sano

    @property
    def pico(self) -> int:
        return int(self.serie[:, I].max())

    @property
    def dia_pico(self) -> int:
        return int(self.serie[:, I].argmax())


def _probabilidad_contagio(beta: float, peso: np.ndarray, plaga: Plaga) -> np.ndarray:
    """Probabilidad de que un zombie muerda a un contacto durante todo su periodo infeccioso.

    El periodo infeccioso dura T días con T ~ Geométrica(1/dias_infeccioso);
    cada día la probabilidad de contagio es 1 - exp(-beta * peso).
    """
    q = 1.0 / plaga.dias_infeccioso
    escape = np.exp(-beta * peso)
    return 1.0 - q * escape / (1.0 - (1.0 - q) * escape)


def estimar_r0(red: Red, beta: float, plaga: Plaga) -> float:
    """R0 de primera generación en una población totalmente sana.

    Promedio de contagios esperados por zombie, ponderado por la fuerza de contacto
    (quien tiene más contactos tiene más probabilidad de ser mordido primero).
    """
    p = _probabilidad_contagio(beta, red.peso, plaga)
    por_persona = np.bincount(red.origen, weights=p, minlength=red.n)
    return float(np.average(por_persona, weights=red.fuerza))


def calibrar_beta(red: Red, plaga: Plaga) -> float:
    """Busca por bisección el beta que produce el R0 pedido en esta red."""
    bajo, alto = 0.0, 5.0
    for _ in range(60):
        medio = (bajo + alto) / 2
        if estimar_r0(red, medio, plaga) < plaga.r0:
            bajo = medio
        else:
            alto = medio
    return (bajo + alto) / 2


def casos_iniciales(red: Red, esc: Escenario, rng: np.random.Generator) -> np.ndarray:
    if esc.inicio == "aleatorio":
        candidatos = np.arange(red.n)
    elif esc.inicio == "mercado":
        candidatos = np.flatnonzero(red.va_mercado)
    elif esc.inicio == "colegio":
        candidatos = np.flatnonzero(red.edad == ESCOLAR)
    elif esc.inicio in BARRIOS:
        candidatos = np.flatnonzero(red.barrio == BARRIOS.index(esc.inicio))
    else:
        raise ValueError(f"Punto de inicio desconocido: {esc.inicio!r}")
    return rng.choice(candidatos, size=min(esc.casos_iniciales, len(candidatos)), replace=False)


def simular(red: Red, esc: Escenario, estrategia, beta: float, repeticion: int = 0,
            cierres: tuple[str, ...] = (), vacunas: int | None = None) -> Resultado:
    """Simula un brote completo.

    `estrategia` decide a quién vacunar cada día, con como máximo `vacunas` dosis
    en total (por defecto, todo el stock). `cierres` son los lugares que se cierran
    desde el día en que se detecta el brote durante `dias_cierre` días.
    """
    rng_inicio, rng_brote, rng_estrategia = (
        np.random.default_rng(s)
        for s in np.random.SeedSequence([esc.semilla, repeticion]).spawn(3)
    )
    plaga, recursos = esc.plaga, esc.recursos
    p_ei = 1.0 / plaga.dias_latencia
    p_ir = 1.0 / plaga.dias_infeccioso
    vacunas = recursos.vacunas_disponibles if vacunas is None else vacunas

    factor_cerrado = np.ones(len(CAPAS))
    for lugar in cierres:
        factor_cerrado[CERRABLES[lugar]] = 1.0 - recursos.cumplimiento_cierre
    fin_cierre = recursos.dia_inicio + recursos.dias_cierre

    estado = np.full(red.n, S, dtype=np.int8)
    iniciales = casos_iniciales(red, esc, rng_inicio)
    estado[iniciales] = I
    detectado = np.zeros(red.n, dtype=bool)
    detectado[iniciales] = rng_inicio.random(len(iniciales)) < plaga.deteccion
    vacunado = np.zeros(red.n, dtype=bool)
    usadas = perdidas = 0

    serie = np.zeros((esc.dias + 1, 4), dtype=np.int64)
    serie_barrio = np.zeros((esc.dias + 1, len(BARRIOS)), dtype=np.int64)
    nuevos = np.zeros(esc.dias + 1, dtype=np.int64)

    def registrar(dia):
        serie[dia] = np.bincount(estado, minlength=4)
        serie_barrio[dia] = np.bincount(red.barrio[estado == I], minlength=len(BARRIOS))

    registrar(0)
    for dia in range(1, esc.dias + 1):
        # Números del brote: siempre se sacan los mismos, haya o no estrategia.
        u_contagio = rng_brote.random(red.n)
        u_ei = rng_brote.random(red.n)
        u_ir = rng_brote.random(red.n)
        u_deteccion = rng_brote.random(red.n)

        # 1. Vacunación del día con las dosis disponibles.
        if dia >= recursos.dia_inicio:
            dosis = min(recursos.vacunas_por_dia, vacunas - usadas)
            if dosis > 0:
                obs = Observacion(dia, red, detectado, vacunado,
                                  np.flatnonzero(detectado & (estado == I)))
                elegidos = np.asarray(estrategia.elegir(obs, dosis, rng_estrategia), dtype=np.int64)
                _validar(elegidos, obs, dosis, estrategia)
                vacunado[elegidos] = True
                usadas += len(elegidos)
                perdidas += int((estado[elegidos] != S).sum())

        # 2. Contagio: presión de los zombies sobre sus contactos (menor en lugares cerrados).
        zombies = np.flatnonzero(estado == I)
        aristas = red.aristas_de(zombies)
        peso = red.peso[aristas]
        if cierres and recursos.dia_inicio <= dia < fin_cierre:
            peso = peso * factor_cerrado[red.capa[aristas]]
        presion = np.bincount(red.destino[aristas], weights=peso, minlength=red.n)
        susceptibilidad = np.where(vacunado, 1.0 - recursos.eficacia, 1.0)
        p_contagio = 1.0 - np.exp(-beta * presion * susceptibilidad)
        mordidos = (estado == S) & (u_contagio < p_contagio)

        # 3. Progresión con el estado del inicio del día.
        nuevos_zombies = (estado == E) & (u_ei < p_ei)
        exorcizados = (estado == I) & (u_ir < p_ir)
        estado[mordidos] = E
        estado[nuevos_zombies] = I
        estado[exorcizados] = R
        detectado |= nuevos_zombies & (u_deteccion < plaga.deteccion)

        registrar(dia)
        nuevos[dia] = int(mordidos.sum())

        # Brote extinguido: ya nada puede cambiar, se repite el último día.
        if serie[dia, E] == 0 and serie[dia, I] == 0:
            serie[dia + 1:] = serie[dia]
            serie_barrio[dia + 1:] = serie_barrio[dia]
            break

    return Resultado(serie=serie, serie_barrio=serie_barrio, nuevos=nuevos,
                     infectados_total=int((estado != S).sum()),
                     vacunas_usadas=usadas, vacunas_perdidas=perdidas)


def _validar(elegidos: np.ndarray, obs: Observacion, dosis: int, estrategia) -> None:
    """Una estrategia nunca puede vacunar de más, repetir, ni vacunar a un caso conocido."""
    nombre = type(estrategia).__name__
    if len(elegidos) > dosis:
        raise ValueError(f"{nombre} pidió {len(elegidos)} vacunas y solo hay {dosis}")
    if len(np.unique(elegidos)) != len(elegidos):
        raise ValueError(f"{nombre} vacunó dos veces a la misma persona")
    if obs.visible[elegidos].any() or obs.vacunado[elegidos].any():
        raise ValueError(f"{nombre} vacunó a un zombie conocido o a un ya vacunado")
