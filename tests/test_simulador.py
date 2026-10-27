from dataclasses import replace

import numpy as np
import pytest

from zombie.config import Escenario
from zombie.estrategias import Estrategia, crear
from zombie.modelo import calibrar_beta, estimar_r0, simular
from zombie.montecarlo import comparar
from zombie.poblacion import construir_red

ESC = Escenario(n_personas=3000, dias=120)


@pytest.fixture(scope="module")
def red():
    return construir_red(ESC.n_personas, ESC.semilla)


@pytest.fixture(scope="module")
def beta(red):
    return calibrar_beta(red, ESC.plaga)


def test_red_simetrica_y_sin_lazos(red):
    assert (red.origen != red.destino).all()
    ida = set(zip(red.origen.tolist(), red.destino.tolist()))
    assert all((b, a) in ida for a, b in ida)


def test_aristas_de_coincide_con_busqueda_directa(red):
    personas = np.array([0, 5, 17])
    esperado = np.flatnonzero(np.isin(red.origen, personas))
    assert np.array_equal(np.sort(red.aristas_de(personas)), esperado)


def test_calibracion_da_el_r0_pedido(red, beta):
    assert estimar_r0(red, beta, ESC.plaga) == pytest.approx(ESC.plaga.r0, rel=1e-3)


def test_misma_semilla_mismo_resultado(red, beta):
    a = simular(red, ESC, crear("anillo", red), beta, 3)
    b = simular(construir_red(ESC.n_personas, ESC.semilla), ESC, crear("anillo", red), beta, 3)
    assert np.array_equal(a.serie, b.serie)


def test_otra_semilla_otro_resultado(red, beta):
    a = simular(red, ESC, crear("ninguna", red), beta, 0)
    b = simular(red, ESC, crear("ninguna", red), beta, 1)
    assert not np.array_equal(a.serie, b.serie)


def test_la_poblacion_se_conserva(red, beta):
    res = simular(red, ESC, crear("azar", red), beta, 0)
    assert (res.serie.sum(axis=1) == red.n).all()


@pytest.mark.parametrize("nombre", ["azar", "centralidad", "anillo"])
def test_respeta_el_limite_de_vacunas(red, beta, nombre):
    res = simular(red, ESC, crear(nombre, red), beta, 0)
    assert res.vacunas_usadas <= ESC.recursos.vacunas_disponibles


class VacunaZombies(Estrategia):
    def elegir(self, obs, dosis, rng):
        return obs.zombies[:dosis]


def test_prohibido_vacunar_zombies(red, beta):
    with pytest.raises(ValueError, match="zombie"):
        simular(red, ESC, VacunaZombies(), beta, 0)


def test_estrategia_supera_lineas_base():
    res = comparar(ESC, repeticiones=30)
    inf = {d["id"]: d["infectados"]["media"] for d in res["planes"]}
    assert inf[res["recomendado"]] < inf["azar"] < inf["ninguna"]
    assert res["veredicto"]["nivel"] == "solida"


def test_ningun_plan_se_pasa_del_presupuesto():
    res = comparar(ESC, repeticiones=2)
    for d in res["planes"]:
        assert d["costo"] <= ESC.recursos.presupuesto
        assert d["vacunas"] <= ESC.recursos.vacunas_disponibles


def test_azar_y_estrategia_usan_las_mismas_vacunas():
    res = comparar(ESC, repeticiones=2)
    vacunas = {d["id"]: d["vacunas"] for d in res["planes"]}
    assert vacunas["azar"] == vacunas["anillo"] == vacunas["centralidad"]


def test_sin_deteccion_el_anillo_no_ve_zombies(red, beta):
    ciego = replace(ESC, plaga=replace(ESC.plaga, deteccion=0.0))
    anillo = simular(red, ciego, crear("anillo", red), beta, 0)
    centralidad = simular(red, ciego, crear("centralidad", red), beta, 0)
    assert np.array_equal(anillo.serie, centralidad.serie)


def test_cerrar_todo_por_completo_frena_el_contagio(red, beta):
    estricto = replace(ESC, recursos=replace(ESC.recursos, cumplimiento_cierre=1.0, dias_cierre=200))
    nada = crear("ninguna", red)
    abiertos = np.mean([simular(red, estricto, nada, beta, r).infectados_total for r in range(10)])
    cerrados = np.mean([simular(red, estricto, nada, beta, r, ("mercado", "colegio")).infectados_total
                        for r in range(10)])
    assert cerrados < abiertos


def test_brote_sorpresa_cambia_parametros():
    sorpresa = replace(ESC, inicio="mercado",
                       plaga=replace(ESC.plaga, r0=5.0),
                       recursos=replace(ESC.recursos, vacunas_disponibles=150, eficacia=0.5))
    res = comparar(sorpresa, repeticiones=10)
    assert res["r0"] == pytest.approx(5.0, rel=1e-2)
    assert res["veredicto"]["nivel"] in ("solida", "debil", "insuficiente")
