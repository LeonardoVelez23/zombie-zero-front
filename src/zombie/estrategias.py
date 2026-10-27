"""Estrategias de vacunación.

Todas reciben la misma Observacion y el mismo número de dosis por día; solo
cambia a quién eligen. Las dos primeras son las líneas base que exige el reto.
"""
import numpy as np

from .modelo import Observacion
from .poblacion import Red


class Estrategia:
    nombre = ""
    descripcion = ""

    def preparar(self, red: Red) -> None:
        """Cálculos que dependen solo de la red (se hacen una vez)."""

    def elegir(self, obs: Observacion, dosis: int, rng: np.random.Generator) -> np.ndarray:
        raise NotImplementedError


class NoIntervenir(Estrategia):
    nombre = "ninguna"
    descripcion = "Línea base: no se vacuna a nadie."

    def elegir(self, obs, dosis, rng):
        return np.empty(0, dtype=np.int64)


class Azar(Estrategia):
    nombre = "azar"
    descripcion = "Línea base: las mismas vacunas, repartidas al azar entre quienes parecen sanos."

    def elegir(self, obs, dosis, rng):
        elegibles = obs.elegibles()
        return rng.choice(elegibles, size=min(dosis, len(elegibles)), replace=False)


class Centralidad(Estrategia):
    nombre = "centralidad"
    descripcion = "Vacuna primero a quien tiene más contactos (fuerza en la red): los superpropagadores."

    def preparar(self, red):
        self.orden = np.argsort(-red.fuerza, kind="stable")

    def elegir(self, obs, dosis, rng):
        libres = ~obs.visible & ~obs.vacunado
        return self.orden[libres[self.orden]][:dosis]


class Anillo(Estrategia):
    nombre = "anillo"
    descripcion = ("Vacuna a los contactos de los zombies activos (más expuestos primero) "
                   "y usa las dosis sobrantes en los superpropagadores.")

    def preparar(self, red):
        self.respaldo = Centralidad()
        self.respaldo.preparar(red)

    def elegir(self, obs, dosis, rng):
        red = obs.red
        libres = ~obs.visible & ~obs.vacunado
        aristas = red.aristas_de(obs.zombies)
        exposicion = np.bincount(red.destino[aristas], weights=red.peso[aristas], minlength=red.n)
        candidatos = np.flatnonzero(libres & (exposicion > 0))
        # Más expuestos primero; a igual exposición, más contactos primero.
        orden = np.lexsort((-red.fuerza[candidatos], -exposicion[candidatos]))
        elegidos = candidatos[orden][:dosis]
        if len(elegidos) < dosis:
            libres[elegidos] = False
            resto = self.respaldo.orden[libres[self.respaldo.orden]][:dosis - len(elegidos)]
            elegidos = np.concatenate([elegidos, resto])
        return elegidos


ESTRATEGIAS = {e.nombre: e for e in (NoIntervenir, Azar, Centralidad, Anillo)}
LINEAS_BASE = ("ninguna", "azar")
CANDIDATAS = ("centralidad", "anillo")


def crear(nombre: str, red: Red) -> Estrategia:
    estrategia = ESTRATEGIAS[nombre]()
    estrategia.preparar(red)
    return estrategia
