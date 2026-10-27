"""Línea de comandos: corre la comparación y muestra la recomendación.

Ejemplos:
    python -m zombie.cli
    python -m zombie.cli --r0 5 --vacunas 500 --inicio mercado --semilla 7
    python -m zombie.cli --json > resultado.json
"""
import argparse
import json
import time
from dataclasses import replace

from .config import Escenario
from .montecarlo import comparar


def _argumentos() -> argparse.Namespace:
    base = Escenario()
    p, r = base.plaga, base.recursos
    a = argparse.ArgumentParser(description="Simulador de la plaga zombie en Manta")
    a.add_argument("--semilla", type=int, default=base.semilla)
    a.add_argument("--repeticiones", type=int, default=100)
    a.add_argument("--personas", type=int, default=base.n_personas)
    a.add_argument("--dias", type=int, default=base.dias)
    a.add_argument("--inicio", default=base.inicio)
    a.add_argument("--casos", type=int, default=base.casos_iniciales)
    a.add_argument("--r0", type=float, default=p.r0)
    a.add_argument("--deteccion", type=float, default=p.deteccion)
    a.add_argument("--presupuesto", type=float, default=r.presupuesto)
    a.add_argument("--vacunas", type=int, default=r.vacunas_disponibles)
    a.add_argument("--por-dia", type=int, default=r.vacunas_por_dia)
    a.add_argument("--dia-inicio", type=int, default=r.dia_inicio)
    a.add_argument("--eficacia", type=float, default=r.eficacia)
    a.add_argument("--json", action="store_true", help="imprime el resultado completo en JSON")
    return a.parse_args()


def main() -> None:
    a = _argumentos()
    base = Escenario()
    esc = replace(
        base,
        semilla=a.semilla, n_personas=a.personas, dias=a.dias,
        inicio=a.inicio, casos_iniciales=a.casos,
        plaga=replace(base.plaga, r0=a.r0, deteccion=a.deteccion),
        recursos=replace(base.recursos, presupuesto=a.presupuesto, vacunas_disponibles=a.vacunas,
                         vacunas_por_dia=a.por_dia, dia_inicio=a.dia_inicio, eficacia=a.eficacia),
    )
    inicio = time.perf_counter()
    res = comparar(esc, a.repeticiones)
    if a.json:
        print(json.dumps(res, ensure_ascii=False))
        return

    print(f"R0 {res['r0']} · beta {res['beta']} · {a.repeticiones} repeticiones · "
          f"semilla {a.semilla} · {time.perf_counter() - inicio:.1f} s\n")
    print(f"{'plan':<34} {'vacunas':>7} {'costo':>8} {'infectados':>11} {'rango p5-p95':>16} "
          f"{'salvados':>9} {'gana al azar':>13}")
    for d in res["planes"]:
        inf = d["infectados"]
        salv = d.get("salvados_vs_ninguna", {}).get("media", 0)
        gana = d.get("gana_a_azar")
        gana_txt = f"{gana:.0%}" if gana is not None else "-"
        print(f"{d['nombre']:<34} {d['vacunas']:>7} {d['costo']:>8,.0f} {inf['media']:>11,.0f} "
              f"{inf['p5']:>7,.0f} - {inf['p95']:<7,.0f} {salv:>9,.0f} {gana_txt:>13}")
    v = res["veredicto"]
    print(f"\nRecomendación: {res['recomendado']} · confianza {v['nivel']} "
          f"(gana al azar en {v['gana_a_azar']:.0%} de los brotes)")


if __name__ == "__main__":
    main()
