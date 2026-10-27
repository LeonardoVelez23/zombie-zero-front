"""Parámetros del escenario.

Cada valor por defecto está justificado (fuente o supuesto) en docs/supuestos.md.
Todo lo que el jurado puede cambiar en el Brote Sorpresa vive aquí.
"""
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Plaga:
    r0: float = 2.5               # contagios por zombie en población sana (COVID ancestral)
    dias_latencia: float = 3.0    # mordido -> zombie
    dias_infeccioso: float = 5.0  # zombie -> exorcizado
    deteccion: float = 0.7        # probabilidad de que un zombie nuevo sea detectado


@dataclass(frozen=True)
class Recursos:
    presupuesto: float = 20_000       # USD para vacunas y cierres
    costo_vacuna: float = 10.0        # USD por dosis aplicada
    vacunas_disponibles: int = 1000   # stock máximo, aunque sobre dinero
    vacunas_por_dia: int = 100        # capacidad diaria de vacunación
    dia_inicio: int = 3               # días hasta que se detecta el brote y se puede actuar
    eficacia: float = 0.9             # reducción de la probabilidad de ser mordido
    dias_cierre: int = 14             # duración de un cierre
    cumplimiento_cierre: float = 0.8  # fracción de contactos del lugar que se evitan al cerrar
    costo_cierre_mercado: float = 600.0  # USD por día de mercado cerrado
    costo_cierre_colegio: float = 800.0  # USD por día de colegios cerrados


@dataclass(frozen=True)
class Escenario:
    n_personas: int = 10_000
    dias: int = 180
    semilla: int = 42
    inicio: str = "aleatorio"     # "aleatorio", "mercado", "colegio" o un barrio de poblacion.BARRIOS
    casos_iniciales: int = 5
    plaga: Plaga = field(default_factory=Plaga)
    recursos: Recursos = field(default_factory=Recursos)

    def a_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def desde_dict(cls, datos: dict) -> "Escenario":
        datos = dict(datos)
        plaga = Plaga(**datos.pop("plaga", {}))
        recursos = Recursos(**datos.pop("recursos", {}))
        return cls(plaga=plaga, recursos=recursos, **datos)
